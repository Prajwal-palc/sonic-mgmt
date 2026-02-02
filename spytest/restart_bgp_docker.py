#!/usr/bin/env python3
"""
Script to restart BGP docker on all devices in testbed and verify readiness

Author: Claude Code
Copyright (C) 2025

Usage:
    python3 restart_bgp_docker.py

Description:
    - Connects to all devices in testbeds/testbed_vs_2node.yaml
    - Executes "docker restart bgp" in click CLI
    - Waits for BGP service to be ready
    - Verifies "show bgp summary" works without "% BGP instance not found" error
"""

import sys
import time
import yaml
import paramiko
from pathlib import Path

# Configuration
TESTBED_FILE = Path(__file__).resolve().parent / "testbeds/testbed_vs_2node.yaml"
MAX_WAIT_TIME = 120  # Maximum wait time for BGP to be ready (seconds)
POLL_INTERVAL = 5    # Check BGP status every 5 seconds


def log(msg, level="INFO"):
    """Simple logging function"""
    print(f"[{level}] {msg}")


def banner(msg):
    """Print banner message"""
    print("\n" + "=" * 80)
    print(f"  {msg}")
    print("=" * 80)


def load_testbed(testbed_file):
    """Load testbed configuration from YAML file"""
    if not testbed_file.exists():
        log(f"Testbed file not found: {testbed_file}", "ERROR")
        sys.exit(1)

    try:
        with open(testbed_file, "r") as f:
            testbed = yaml.safe_load(f)
        return testbed
    except Exception as e:
        log(f"Failed to load testbed file: {e}", "ERROR")
        sys.exit(1)


def connect_device(device_name, device_config):
    """Create SSH connection to device"""
    try:
        access = device_config.get("access", {})
        creds = device_config.get("credentials", {})

        host = access.get("ip")
        port = access.get("port", 22)
        username = creds.get("username", "admin")
        password = creds.get("password")

        log(f"Connecting to {device_name} ({host}:{port})")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=30,
            allow_agent=False,
            look_for_keys=False
        )

        log(f"Successfully connected to {device_name}")
        return client

    except Exception as e:
        log(f"Failed to connect to {device_name}: {e}", "ERROR")
        return None


def execute_command(client, command, timeout=30):
    """Execute command on device via SSH"""
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        return_code = stdout.channel.recv_exit_status()

        return {
            'output': output,
            'error': error,
            'return_code': return_code
        }
    except Exception as e:
        log(f"Command execution failed: {e}", "ERROR")
        return None


def restart_bgp_docker(device_name, client):
    """Restart BGP docker container on device"""
    banner(f"Restarting BGP docker on {device_name}")

    try:
        # Execute docker restart bgp
        cmd = "sudo docker restart bgp"
        log(f"Executing: {cmd}")

        result = execute_command(client, cmd, timeout=60)

        if result and result['return_code'] == 0:
            log(f"BGP docker restart command executed successfully on {device_name}")
            log(f"Output: {result['output'].strip()}")
            return True
        else:
            log(f"BGP docker restart failed on {device_name}", "ERROR")
            if result:
                log(f"Error: {result['error']}", "ERROR")
            return False

    except Exception as e:
        log(f"Failed to restart BGP docker on {device_name}: {e}", "ERROR")
        return False


def check_bgp_ready(device_name, client):
    """Check if BGP service is ready by running show bgp summary"""
    try:
        # Use sonic-cli to execute show bgp summary
        cmd = "sonic-cli -c 'show bgp summary'"
        result = execute_command(client, cmd, timeout=10)

        if not result:
            return False

        output = result['output'] + result['error']

        # Check for error message
        if "% BGP instance not found" in output or "BGP instance not found" in output:
            log(f"BGP instance not found on {device_name}", "DEBUG")
            return False

        # Check for connection refused or other errors
        if "Connection refused" in output or "failed" in output.lower():
            log(f"BGP connection issues on {device_name}", "DEBUG")
            return False

        # If we got here without error, BGP is likely ready
        log(f"BGP appears ready on {device_name}", "DEBUG")
        return True

    except Exception as e:
        log(f"BGP readiness check failed on {device_name}: {e}", "DEBUG")
        return False


def wait_for_bgp_ready(device_name, client, max_wait=MAX_WAIT_TIME):
    """Wait for BGP service to be ready after restart"""
    banner(f"Waiting for BGP to be ready on {device_name}")

    # Give it a few seconds for docker to restart
    log(f"Waiting 10 seconds for BGP docker to initialize...")
    time.sleep(10)

    start_time = time.time()
    elapsed = 0

    while elapsed < max_wait:
        if check_bgp_ready(device_name, client):
            log(f"✓ BGP is ready on {device_name} (took {elapsed:.1f} seconds)")
            return True

        log(f"BGP not ready yet on {device_name}, waiting... ({elapsed:.1f}s / {max_wait}s)")
        time.sleep(POLL_INTERVAL)
        elapsed = time.time() - start_time

    log(f"✗ BGP did not become ready on {device_name} within {max_wait} seconds", "ERROR")
    return False


def main():
    """Main function to restart BGP on all devices"""
    banner("BGP Docker Restart Script")

    # Load testbed configuration
    log(f"Loading testbed from: {TESTBED_FILE}")
    testbed = load_testbed(TESTBED_FILE)

    # Get devices
    devices = testbed.get("devices", {})
    if not devices:
        log("No devices found in testbed", "ERROR")
        sys.exit(1)

    log(f"Found {len(devices)} devices: {', '.join(devices.keys())}")

    # Track results
    results = {}
    all_success = True

    # Process each device
    for device_name, device_config in devices.items():
        banner(f"Processing device: {device_name}")

        # Connect to device
        client = connect_device(device_name, device_config)
        if not client:
            results[device_name] = "CONNECTION_FAILED"
            all_success = False
            continue

        try:
            # Restart BGP docker
            restart_success = restart_bgp_docker(device_name, client)
            if not restart_success:
                results[device_name] = "RESTART_FAILED"
                all_success = False
                continue

            # Wait for BGP to be ready
            ready_success = wait_for_bgp_ready(device_name, client)
            if not ready_success:
                results[device_name] = "NOT_READY"
                all_success = False
            else:
                results[device_name] = "SUCCESS"

        finally:
            # Close connection
            client.close()
            log(f"Closed connection to {device_name}")

    # Print summary
    banner("BGP Restart Summary")
    for device, status in results.items():
        status_icon = "✓" if status == "SUCCESS" else "✗"
        print(f"{status_icon} {device}: {status}")

    if all_success:
        log("\n✓ All devices successfully restarted BGP", "SUCCESS")
        return 0
    else:
        log("\n✗ Some devices failed to restart BGP properly", "ERROR")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("\nScript interrupted by user", "WARNING")
        sys.exit(130)
    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)
