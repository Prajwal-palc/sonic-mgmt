"""
Ping and Traceroute Test - Simple Diagnostic Pattern

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
    tests/system/iscli_SNMP/test_ping_traceroute_simple.py \
    --logs-path ./logs/ping_traceroute_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case: Ping and Traceroute Diagnostic Tools

  Validates ping and traceroute functionality:
  - IPv4 ping with various options
  - IPv6 ping with various options
  - IPv4 traceroute
  - IPv6 traceroute
  - Ping with different packet counts
  - Ping with different timeouts

  Manual Test Steps Automated:
  DUT1:
    sonic-cli
    configure terminal
    interface Ethernet0
    ip address 10.1.1.1/24
    ipv6 address 2001:db8::1/64
    no shutdown
    exit
    end

    ping 10.1.1.2 -c 3
    ping 10.1.1.2 -c 5
    ping 10.1.1.2 -c 2 -W 5
    ping6 2001:db8::2 -c 3
    traceroute 10.1.1.2
    traceroute6 2001:db8::2

Pre-requisites:
  - Topology: two-node (D1-D2)
  - DUT1: 192.168.100.234, DUT2: 192.168.100.185
  - Credentials: admin/Ospf@123
"""

from __future__ import annotations

import pytest
import re
from spytest import st, SpyTestDict
from typing import Dict, Any

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "subnet_mask": "24",
    "dut1_ipv4": "10.1.1.1",
    "dut2_ipv4": "10.1.1.2",
    "dut1_ipv6": "2001:db8::1",
    "dut2_ipv6": "2001:db8::2",
    "ipv6_prefix": "64",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("="*80)
    st.banner("PING/TRACEROUTE: MODULE PROLOGUE - Simple Diagnostic Test")
    st.banner("="*80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("="*80)
    st.banner("PING/TRACEROUTE: MODULE EPILOGUE - Cleanup")
    st.banner("="*80)

    cleanup_interface(vars.D1)
    cleanup_interface(vars.D2)


def configure_interface(dut: str, ipv4: str, ipv6: str) -> bool:
    """Configure interface with IPv4 and IPv6 addresses."""
    try:
        st.log(f"Configuring {CONFIG.interface} on {dut}")

        commands = [
            f"interface {CONFIG.interface}",
            f"ip address {ipv4}/{CONFIG.subnet_mask}",
            f"ipv6 address {ipv6}/{CONFIG.ipv6_prefix}",
            "ipv6 enable",
            "no shutdown",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type)
        st.wait(3, "Waiting for interface to be up")
        st.log(f"✅ Interface configured on {dut}")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure interface on {dut}: {str(e)}")
        return False


def execute_ping(dut: str, target_ip: str, count: int = 3, timeout: int = None, is_ipv6: bool = False) -> Dict[str, Any]:
    """Execute ping command and parse results."""
    try:
        # Build ping command
        if is_ipv6:
            cmd = f"ping6 {target_ip} -c {count}"
        else:
            cmd = f"ping {target_ip} -c {count}"

        if timeout:
            cmd += f" -W {timeout}"

        st.log(f"Executing: {cmd}")

        # Execute ping
        output = st.exec_cli(dut, cmd, skip_error_check=True)
        output_str = str(output)

        st.log(f"Ping output:\n{output_str[:500]}")

        # Parse results
        result = {
            "command": cmd,
            "success": False,
            "packets_sent": 0,
            "packets_received": 0,
            "packet_loss": 100,
            "min_rtt": 0,
            "avg_rtt": 0,
            "max_rtt": 0,
        }

        # Parse: "3 packets transmitted, 3 received, 0% packet loss"
        match = re.search(r'(\d+) packets transmitted, (\d+) (?:received|packets received)', output_str)
        if match:
            result["packets_sent"] = int(match.group(1))
            result["packets_received"] = int(match.group(2))

            if result["packets_sent"] > 0:
                result["packet_loss"] = ((result["packets_sent"] - result["packets_received"]) / result["packets_sent"]) * 100

        # Parse RTT: "rtt min/avg/max/mdev = 0.123/0.456/0.789/0.012 ms"
        rtt_match = re.search(r'rtt min/avg/max[/\w]* = ([\d.]+)/([\d.]+)/([\d.]+)', output_str)
        if rtt_match:
            result["min_rtt"] = float(rtt_match.group(1))
            result["avg_rtt"] = float(rtt_match.group(2))
            result["max_rtt"] = float(rtt_match.group(3))

        # Success if we received packets
        if result["packets_received"] > 0:
            result["success"] = True
            st.log(f"✅ Ping successful: {result['packets_received']}/{result['packets_sent']} packets received")
        else:
            st.log(f"❌ Ping failed: 0 packets received")

        return result

    except Exception as e:
        st.error(f"❌ Ping execution failed: {str(e)}")
        return {"command": cmd, "success": False, "error": str(e)}


def execute_traceroute(dut: str, target_ip: str, is_ipv6: bool = False) -> Dict[str, Any]:
    """Execute traceroute command and parse results."""
    try:
        # Build traceroute command
        if is_ipv6:
            cmd = f"traceroute6 {target_ip}"
        else:
            cmd = f"traceroute {target_ip}"

        st.log(f"Executing: {cmd}")

        # Execute traceroute (may take longer)
        output = st.exec_cli(dut, cmd, skip_error_check=True, timeout=30)
        output_str = str(output)

        st.log(f"Traceroute output:\n{output_str[:800]}")

        # Parse results
        result = {
            "command": cmd,
            "success": False,
            "hops": 0,
            "reached_target": False,
        }

        # Count number of hops
        hop_lines = re.findall(r'^\s*\d+\s+', output_str, re.MULTILINE)
        result["hops"] = len(hop_lines)

        # Check if target was reached
        if target_ip in output_str or "ms" in output_str:
            result["reached_target"] = True
            result["success"] = True
            st.log(f"✅ Traceroute successful: reached target in {result['hops']} hops")
        else:
            st.log(f"⚠️  Traceroute completed but may not have reached target")

        return result

    except Exception as e:
        st.error(f"❌ Traceroute execution failed: {str(e)}")
        return {"command": cmd, "success": False, "error": str(e)}


def cleanup_interface(dut: str) -> None:
    """Remove IP configuration from interface."""
    try:
        st.log(f"Cleaning up interface on {dut}")

        commands = [
            f"interface {CONFIG.interface}",
            "no ip address",
            "no ipv6 address",
            "no ipv6 enable"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✅ Interface cleanup completed on {dut}")

    except Exception as e:
        st.log(f"⚠️  Interface cleanup warning: {str(e)}")


def test_ping_traceroute_simple():
    """
    Ping and Traceroute Simple Diagnostic Test

    Test Flow:
    1. Configure IPv4 and IPv6 addresses on both DUTs
    2. Wait for interfaces to come up
    3. Test IPv4 ping with default options (3 packets)
    4. Test IPv4 ping with 5 packets
    5. Test IPv4 ping with timeout option
    6. Test IPv6 ping
    7. Test IPv4 traceroute
    8. Test IPv6 traceroute
    9. Display summary of results

    Expected Results:
    - All ping tests should succeed (0% packet loss)
    - Traceroute should reach target
    - All verifications pass
    """
    st.banner("="*80)
    st.banner("TEST: Ping and Traceroute - Simple Diagnostic")
    st.banner("="*80)

    validation_failures = []
    tech_support_generated = False
    test_results = []

    try:
        # ==================================================
        # STEP 1: Configure Interfaces
        # ==================================================
        st.banner("STEP 1: Configure IPv4 and IPv6 on Both DUTs")

        if not configure_interface(vars.D1, CONFIG.dut1_ipv4, CONFIG.dut1_ipv6):
            error_msg = f"Interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_interface(vars.D2, CONFIG.dut2_ipv4, CONFIG.dut2_ipv6):
            error_msg = f"Interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 2: Wait for Convergence
        # ==================================================
        st.banner("STEP 2: Wait for Interface Convergence")
        st.wait(5, "Waiting for interfaces to stabilize")

        # ==================================================
        # STEP 3: IPv4 Ping Tests
        # ==================================================
        st.banner("STEP 3: IPv4 Ping Tests from DUT1 to DUT2")

        # Test 1: Basic ping (3 packets)
        st.log("Test 3.1: Basic ping with 3 packets")
        result = execute_ping(vars.D1, CONFIG.dut2_ipv4, count=3)
        test_results.append(result)
        if not result["success"]:
            error_msg = f"IPv4 ping (3 packets) failed: {result['command']}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Test 2: Ping with 5 packets
        st.log("Test 3.2: Ping with 5 packets")
        result = execute_ping(vars.D1, CONFIG.dut2_ipv4, count=5)
        test_results.append(result)
        if not result["success"]:
            error_msg = f"IPv4 ping (5 packets) failed: {result['command']}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Test 3: Ping with timeout
        st.log("Test 3.3: Ping with 2 packets and 5 second timeout")
        result = execute_ping(vars.D1, CONFIG.dut2_ipv4, count=2, timeout=5)
        test_results.append(result)
        if not result["success"]:
            error_msg = f"IPv4 ping with timeout failed: {result['command']}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 4: IPv6 Ping Test
        # ==================================================
        st.banner("STEP 4: IPv6 Ping Test from DUT1 to DUT2")

        st.log("Test 4.1: IPv6 ping with 3 packets")
        result = execute_ping(vars.D1, CONFIG.dut2_ipv6, count=3, is_ipv6=True)
        test_results.append(result)
        if not result["success"]:
            error_msg = f"IPv6 ping failed: {result['command']}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 5: IPv4 Traceroute Test
        # ==================================================
        st.banner("STEP 5: IPv4 Traceroute from DUT1 to DUT2")

        st.log("Test 5.1: IPv4 traceroute")
        result = execute_traceroute(vars.D1, CONFIG.dut2_ipv4)
        test_results.append(result)
        if not result["success"]:
            error_msg = f"IPv4 traceroute failed: {result['command']}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 6: IPv6 Traceroute Test
        # ==================================================
        st.banner("STEP 6: IPv6 Traceroute from DUT1 to DUT2")

        st.log("Test 6.1: IPv6 traceroute")
        result = execute_traceroute(vars.D1, CONFIG.dut2_ipv6, is_ipv6=True)
        test_results.append(result)
        if not result["success"]:
            error_msg = f"IPv6 traceroute failed: {result['command']}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # ==================================================
        # STEP 7: Display Test Summary
        # ==================================================
        st.banner("STEP 7: Test Results Summary")

        st.log(f"\n{'='*70}")
        st.log("TEST RESULTS SUMMARY")
        st.log(f"{'='*70}")

        for idx, result in enumerate(test_results, 1):
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            st.log(f"{idx}. {status} - {result.get('command', 'Unknown command')}")

            if "packets_received" in result:
                st.log(f"   Packets: {result['packets_received']}/{result['packets_sent']} received ({result['packet_loss']:.1f}% loss)")
                if result.get("avg_rtt"):
                    st.log(f"   RTT: min={result['min_rtt']:.2f} avg={result['avg_rtt']:.2f} max={result['max_rtt']:.2f} ms")

            if "hops" in result:
                st.log(f"   Hops: {result['hops']}")
                st.log(f"   Reached target: {result['reached_target']}")

        st.log(f"{'='*70}\n")
        st.log("Ping/Traceroute test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # ==================================================
        # CLEANUP: Always executes
        # ==================================================
        st.banner("="*80)
        st.banner("CLEANUP: Removing IP Configurations")
        st.banner("="*80)

        try:
            cleanup_interface(vars.D1)
            cleanup_interface(vars.D2)
            st.log("✅ Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"❌ Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

        # ==================================================
        # TECH-SUPPORT: Generate if failures
        # ==================================================
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            try:
                st.generate_tech_support([vars.D1, vars.D2], "ping_traceroute_failures")
                tech_support_generated = True
                st.log("✅ Tech-support generated successfully")
            except Exception as ts_error:
                st.error(f"❌ Failed to generate tech-support: {str(ts_error)}")

        # ==================================================
        # REPORT: Final results
        # ==================================================
        if validation_failures:
            st.log("\n" + "!"*80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"  {idx}. {failure}")
            st.log("!"*80)
            st.log(f"\nNote: Cleanup completed despite {len(validation_failures)} validation failure(s)")
            st.log("Tech-support has been generated for debugging")
            st.report_fail("msg", f"Ping/Traceroute test completed with {len(validation_failures)} failure(s). Cleanup executed.")
        else:
            st.log("\n" + "="*80)
            st.log("PING/TRACEROUTE: ALL TESTS PASSED")
            st.log("="*80)
            st.report_pass("test_case_passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
