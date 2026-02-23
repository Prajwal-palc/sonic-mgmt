#!/usr/bin/env python3
"""
Link Finder - Testbed Link Status Checker

This script reads a SONiC testbed YAML file, connects to all devices,
checks the status of all links defined in the topology, and generates
a comprehensive link status report.

Usage:
    python link_finder.py <testbed_yaml_file>
    python link_finder.py testbeds/testbed_vs_d1d3.yaml

Output:
    logs/link_finder.txt - Detailed link status report
"""

import sys
import os
import yaml
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class LinkFinder:
    """Check link status for all connections in a testbed YAML file."""

    def __init__(self, testbed_file: str):
        self.testbed_file = testbed_file
        self.testbed_data = None
        self.devices = {}
        self.topology = {}
        self.link_status = []
        self.report_lines = []

    def load_testbed(self) -> bool:
        """Load and parse the testbed YAML file."""
        try:
            with open(self.testbed_file, 'r') as f:
                self.testbed_data = yaml.safe_load(f)

            self.devices = self.testbed_data.get('devices', {})
            self.topology = self.testbed_data.get('topology', {})

            self.log(f"Loaded testbed: {self.testbed_file}")
            self.log(f"Found {len(self.devices)} devices")
            self.log(f"Found {len(self.topology)} topology entries")
            return True

        except FileNotFoundError:
            self.log(f"ERROR: Testbed file not found: {self.testbed_file}")
            return False
        except yaml.YAMLError as e:
            self.log(f"ERROR: Failed to parse YAML: {e}")
            return False

    def log(self, message: str):
        """Add a message to the report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        print(line)
        self.report_lines.append(line)

    def ssh_command(self, device_name: str, command: str, timeout: int = 10) -> Tuple[bool, str]:
        """Execute SSH command on a device."""
        device = self.devices.get(device_name)
        if not device:
            return False, f"Device {device_name} not found in testbed"

        access = device.get('access', {})
        creds = device.get('credentials', {})

        ip = access.get('ip')
        port = access.get('port', 22)
        username = creds.get('username', 'admin')
        password = creds.get('password', '')

        if not ip:
            return False, f"No IP address for device {device_name}"

        # Use sshpass for password-based SSH
        ssh_cmd = [
            'sshpass', '-p', password,
            'ssh', '-o', 'StrictHostKeyChecking=no',
            '-o', 'UserKnownHostsFile=/dev/null',
            '-o', f'ConnectTimeout={timeout}',
            '-p', str(port),
            f'{username}@{ip}',
            command
        ]

        try:
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"SSH command timed out after {timeout}s"
        except Exception as e:
            return False, f"SSH error: {str(e)}"

    def check_interface_status(self, device_name: str, interface: str) -> Dict:
        """Check the status of an interface on a device."""
        status_info = {
            'device': device_name,
            'interface': interface,
            'reachable': False,
            'admin_state': 'unknown',
            'oper_state': 'unknown',
            'link_state': 'unknown',
            'speed': 'unknown',
            'mtu': 'unknown',
            'error': None
        }

        # Try to get interface status using SONiC show commands
        success, output = self.ssh_command(
            device_name,
            f"show interfaces status {interface} 2>/dev/null || ip link show {interface} 2>/dev/null"
        )

        if not success:
            status_info['error'] = f"Failed to connect or execute command: {output}"
            return status_info

        status_info['reachable'] = True

        # Parse output for interface state
        # Try SONiC format first
        if 'Oper' in output or 'Admin' in output:
            # SONiC show interfaces status format
            for line in output.split('\n'):
                if interface in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        # Typical format: Interface  Lanes  Speed  MTU  FEC  Alias  Vlan  Oper  Admin
                        try:
                            # Look for Oper and Admin columns
                            if 'up' in line.lower():
                                status_info['oper_state'] = 'up'
                            elif 'down' in line.lower():
                                status_info['oper_state'] = 'down'
                        except:
                            pass

        # Parse Linux ip link output
        if 'state UP' in output or 'UP' in output:
            status_info['link_state'] = 'up'
            if 'NO-CARRIER' in output:
                status_info['oper_state'] = 'down (no carrier)'
            else:
                status_info['oper_state'] = 'up'
        elif 'state DOWN' in output or 'DOWN' in output:
            status_info['link_state'] = 'down'
            status_info['oper_state'] = 'down'

        # Check admin state
        if 'NO-CARRIER' in output:
            status_info['admin_state'] = 'up (no carrier)'
        elif 'LOWER_UP' in output:
            status_info['admin_state'] = 'up'
            status_info['oper_state'] = 'up'

        # Extract MTU
        mtu_match = re.search(r'mtu\s+(\d+)', output)
        if mtu_match:
            status_info['mtu'] = mtu_match.group(1)

        # Extract speed if available
        speed_match = re.search(r'(\d+)G|(\d+)M', output)
        if speed_match:
            status_info['speed'] = speed_match.group(0)

        return status_info

    def check_all_links(self):
        """Check status of all links defined in topology."""
        self.log("\n" + "="*80)
        self.log("CHECKING LINK STATUS FOR ALL TOPOLOGY CONNECTIONS")
        self.log("="*80 + "\n")

        link_count = 0
        links_checked = set()  # To avoid checking same link twice

        for device_name, device_topo in self.topology.items():
            interfaces = device_topo.get('interfaces', {})

            for local_intf, connection in interfaces.items():
                remote_device = connection.get('EndDevice')
                remote_intf = connection.get('EndPort')

                if not remote_device or not remote_intf:
                    continue

                # Create unique link identifier (sorted to avoid duplicates)
                link_id = tuple(sorted([
                    (device_name, local_intf),
                    (remote_device, remote_intf)
                ]))

                if link_id in links_checked:
                    continue

                links_checked.add(link_id)
                link_count += 1

                self.log(f"\nLink #{link_count}: {device_name}:{local_intf} <---> {remote_device}:{remote_intf}")
                self.log("-" * 80)

                # Check local interface
                local_status = self.check_interface_status(device_name, local_intf)

                # Check remote interface
                remote_status = self.check_interface_status(remote_device, remote_intf)

                # Log local status
                self.log(f"  {device_name}:{local_intf}")
                self.log(f"    Reachable:    {local_status['reachable']}")
                if local_status['reachable']:
                    self.log(f"    Oper State:   {local_status['oper_state']}")
                    self.log(f"    Link State:   {local_status['link_state']}")
                    self.log(f"    Speed:        {local_status['speed']}")
                    self.log(f"    MTU:          {local_status['mtu']}")
                else:
                    self.log(f"    Error:        {local_status['error']}")

                # Log remote status
                self.log(f"  {remote_device}:{remote_intf}")
                self.log(f"    Reachable:    {remote_status['reachable']}")
                if remote_status['reachable']:
                    self.log(f"    Oper State:   {remote_status['oper_state']}")
                    self.log(f"    Link State:   {remote_status['link_state']}")
                    self.log(f"    Speed:        {remote_status['speed']}")
                    self.log(f"    MTU:          {remote_status['mtu']}")
                else:
                    self.log(f"    Error:        {remote_status['error']}")

                # Determine overall link status
                link_ok = (
                    local_status['reachable'] and
                    remote_status['reachable'] and
                    'up' in local_status['oper_state'].lower() and
                    'up' in remote_status['oper_state'].lower()
                )

                status_symbol = "✓" if link_ok else "✗"
                status_text = "UP" if link_ok else "DOWN/ISSUE"

                self.log(f"  Link Status:  [{status_symbol}] {status_text}")

                # Store link status for summary
                self.link_status.append({
                    'link_id': link_count,
                    'local_device': device_name,
                    'local_intf': local_intf,
                    'remote_device': remote_device,
                    'remote_intf': remote_intf,
                    'status': status_text,
                    'local_status': local_status,
                    'remote_status': remote_status
                })

        if link_count == 0:
            self.log("\nWARNING: No links found in topology!")

    def generate_summary(self):
        """Generate summary statistics."""
        self.log("\n" + "="*80)
        self.log("LINK STATUS SUMMARY")
        self.log("="*80 + "\n")

        total_links = len(self.link_status)
        up_links = sum(1 for link in self.link_status if link['status'] == 'UP')
        down_links = total_links - up_links

        self.log(f"Total Links:      {total_links}")
        self.log(f"Links UP:         {up_links}")
        self.log(f"Links DOWN:       {down_links}")

        if total_links > 0:
            up_percentage = (up_links / total_links) * 100
            self.log(f"Link Up Rate:     {up_percentage:.1f}%")

        # List down links
        if down_links > 0:
            self.log("\n" + "="*80)
            self.log("LINKS WITH ISSUES")
            self.log("="*80 + "\n")

            for link in self.link_status:
                if link['status'] != 'UP':
                    self.log(f"Link #{link['link_id']}: {link['local_device']}:{link['local_intf']} <---> "
                           f"{link['remote_device']}:{link['remote_intf']}")

                    local = link['local_status']
                    remote = link['remote_status']

                    if not local['reachable']:
                        self.log(f"  - {link['local_device']} not reachable: {local['error']}")
                    elif 'down' in local['oper_state'].lower():
                        self.log(f"  - {link['local_device']}:{link['local_intf']} is DOWN")

                    if not remote['reachable']:
                        self.log(f"  - {link['remote_device']} not reachable: {remote['error']}")
                    elif 'down' in remote['oper_state'].lower():
                        self.log(f"  - {link['remote_device']}:{link['remote_intf']} is DOWN")

    def check_device_reachability(self):
        """Check if all devices are reachable."""
        self.log("\n" + "="*80)
        self.log("DEVICE REACHABILITY CHECK")
        self.log("="*80 + "\n")

        for device_name, device_info in self.devices.items():
            access = device_info.get('access', {})
            ip = access.get('ip', 'N/A')

            self.log(f"Device: {device_name} ({ip})")

            success, output = self.ssh_command(device_name, "hostname")

            if success:
                hostname = output.strip()
                self.log(f"  Status:   [✓] REACHABLE")
                self.log(f"  Hostname: {hostname}")
            else:
                self.log(f"  Status:   [✗] UNREACHABLE")
                self.log(f"  Error:    {output}")

    def save_report(self, output_file: str):
        """Save the report to a file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            f.write('\n'.join(self.report_lines))

        print(f"\nReport saved to: {output_path.absolute()}")

    def run(self):
        """Main execution flow."""
        self.log("="*80)
        self.log("LINK FINDER - TESTBED LINK STATUS CHECKER")
        self.log("="*80)
        self.log(f"Testbed File: {self.testbed_file}")
        self.log(f"Start Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("")

        # Load testbed
        if not self.load_testbed():
            return False

        # Check device reachability
        self.check_device_reachability()

        # Check all links
        self.check_all_links()

        # Generate summary
        self.generate_summary()

        # Footer
        self.log("\n" + "="*80)
        self.log(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("="*80)

        return True


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python link_finder.py <testbed_yaml_file>")
        print("Example: python link_finder.py testbeds/testbed_vs_d1d3.yaml")
        sys.exit(1)

    testbed_file = sys.argv[1]

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = logs_dir / f"link_finder_{timestamp}.txt"

    # Run link finder
    finder = LinkFinder(testbed_file)
    success = finder.run()

    # Save report
    finder.save_report(output_file)

    # Also save as link_finder.txt (latest)
    latest_file = logs_dir / "link_finder.txt"
    finder.save_report(latest_file)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
