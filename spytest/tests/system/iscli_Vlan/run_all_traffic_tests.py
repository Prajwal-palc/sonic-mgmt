#!/usr/bin/env python3
"""
Traffic Test Orchestrator for 4-Device VLAN Topology

This script orchestrates all traffic generation tests for the 4-device VLAN topology.
It runs various traffic scenarios including:
- VLAN10 untagged traffic (unicast + broadcast)
- VLAN20 tagged traffic (unicast + broadcast)
- Port-Channel traffic (unicast + broadcast + load-balance)

Usage:
    sudo python3 run_all_traffic_tests.py --config traffic_config.yaml
    sudo python3 run_all_traffic_tests.py --quick-test
    sudo python3 run_all_traffic_tests.py --scenario vlan10_only

Requirements:
    - Scapy library
    - Root/sudo privileges
    - SSH access to devices (for remote traffic generation)
"""

import argparse
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class TrafficOrchestrator:
    """Orchestrate traffic generation tests across 4-device topology."""

    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize traffic orchestrator.

        Args:
            config_file: Path to YAML configuration file
        """
        self.config_file = config_file or self._get_default_config()
        self.config = self._load_config()
        self.results = []

        print(f"[INFO] Traffic Orchestrator initialized")
        print(f"[INFO] Config file: {self.config_file}")

    def _get_default_config(self) -> str:
        """Get default configuration file path."""
        return str(
            Path(__file__).parent.parent.parent.parent
            / "spytest"
            / "vars"
            / "system"
            / "iscli_Vlan"
            / "vars_4device_vlan_topology.yaml"
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, "r") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"[ERROR] Config file not found: {self.config_file}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"[ERROR] Failed to parse YAML: {e}")
            sys.exit(1)

    def _run_command(self, command: List[str], description: str) -> bool:
        """
        Run a command and capture output.

        Args:
            command: Command and arguments as list
            description: Description of what command does

        Returns:
            True if command succeeded, False otherwise
        """
        print(f"\n[RUNNING] {description}")
        print(f"[CMD] {' '.join(command)}")

        start_time = time.time()

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            elapsed = time.time() - start_time

            if result.returncode == 0:
                print(f"[SUCCESS] {description} (took {elapsed:.2f}s)")
                self.results.append({
                    "description": description,
                    "status": "PASS",
                    "elapsed": elapsed,
                    "command": " ".join(command),
                })
                return True
            else:
                print(f"[FAILED] {description}")
                print(f"[ERROR] {result.stderr}")
                self.results.append({
                    "description": description,
                    "status": "FAIL",
                    "elapsed": elapsed,
                    "command": " ".join(command),
                    "error": result.stderr,
                })
                return False

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[EXCEPTION] {description}: {e}")
            self.results.append({
                "description": description,
                "status": "ERROR",
                "elapsed": elapsed,
                "command": " ".join(command),
                "error": str(e),
            })
            return False

    def run_vlan10_untagged_tests(self, interface: str) -> bool:
        """
        Run VLAN10 untagged traffic tests.

        Args:
            interface: Interface to send traffic on

        Returns:
            True if all tests passed
        """
        print("\n" + "=" * 80)
        print("VLAN10 UNTAGGED TRAFFIC TESTS")
        print("=" * 80)

        script = str(Path(__file__).parent / "traffic_vlan10_untagged.py")
        scenarios = self.config.get("traffic_scenarios", {})

        all_passed = True

        # Unicast traffic
        unicast_cfg = scenarios.get("untagged_unicast", {})
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "unicast",
            "--dst-mac", "00:11:22:33:44:02",
            "--count", str(unicast_cfg.get("packet_count", 100)),
            "--size", str(unicast_cfg.get("packet_size", 64)),
        ]
        if not self._run_command(cmd, "VLAN10 Untagged Unicast Traffic"):
            all_passed = False

        time.sleep(1)

        # Broadcast traffic
        broadcast_cfg = scenarios.get("untagged_broadcast", {})
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "broadcast",
            "--count", str(broadcast_cfg.get("packet_count", 50)),
            "--size", str(broadcast_cfg.get("packet_size", 64)),
        ]
        if not self._run_command(cmd, "VLAN10 Untagged Broadcast Traffic"):
            all_passed = False

        return all_passed

    def run_vlan20_tagged_tests(self, interface: str) -> bool:
        """
        Run VLAN20 tagged traffic tests.

        Args:
            interface: Interface to send traffic on

        Returns:
            True if all tests passed
        """
        print("\n" + "=" * 80)
        print("VLAN20 TAGGED TRAFFIC TESTS")
        print("=" * 80)

        script = str(Path(__file__).parent / "traffic_vlan20_tagged.py")
        scenarios = self.config.get("traffic_scenarios", {})

        all_passed = True

        # Unicast traffic
        unicast_cfg = scenarios.get("tagged_unicast", {})
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "unicast",
            "--dst-mac", "00:11:22:33:55:02",
            "--vlan", "20",
            "--count", str(unicast_cfg.get("packet_count", 100)),
            "--size", str(unicast_cfg.get("packet_size", 64)),
        ]
        if not self._run_command(cmd, "VLAN20 Tagged Unicast Traffic"):
            all_passed = False

        time.sleep(1)

        # Broadcast traffic
        broadcast_cfg = scenarios.get("tagged_broadcast", {})
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "broadcast",
            "--vlan", "20",
            "--count", str(broadcast_cfg.get("packet_count", 50)),
            "--size", str(broadcast_cfg.get("packet_size", 64)),
        ]
        if not self._run_command(cmd, "VLAN20 Tagged Broadcast Traffic"):
            all_passed = False

        return all_passed

    def run_portchannel_tests(self, interface: str) -> bool:
        """
        Run Port-Channel traffic tests.

        Args:
            interface: Interface to send traffic on

        Returns:
            True if all tests passed
        """
        print("\n" + "=" * 80)
        print("PORT-CHANNEL (LAG50) TRAFFIC TESTS")
        print("=" * 80)

        script = str(Path(__file__).parent / "traffic_portchannel.py")
        scenarios = self.config.get("traffic_scenarios", {})

        all_passed = True

        # Unicast traffic
        unicast_cfg = scenarios.get("portchannel_unicast", {})
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "unicast",
            "--dst-mac", "00:11:22:33:55:02",
            "--vlan", "20",
            "--count", str(unicast_cfg.get("packet_count", 200)),
            "--size", str(unicast_cfg.get("packet_size", 64)),
        ]
        if not self._run_command(cmd, "Port-Channel Unicast Traffic"):
            all_passed = False

        time.sleep(1)

        # Broadcast traffic
        broadcast_cfg = scenarios.get("portchannel_broadcast", {})
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "broadcast",
            "--vlan", "20",
            "--count", str(broadcast_cfg.get("packet_count", 100)),
            "--size", str(broadcast_cfg.get("packet_size", 64)),
        ]
        if not self._run_command(cmd, "Port-Channel Broadcast Traffic"):
            all_passed = False

        time.sleep(1)

        # Load-balance traffic
        cmd = [
            "python3", script,
            "--iface", interface,
            "--mode", "load-balance",
            "--dst-mac", "00:11:22:33:55:02",
            "--vlan", "20",
            "--count", "500",
        ]
        if not self._run_command(cmd, "Port-Channel Load Balance Traffic"):
            all_passed = False

        return all_passed

    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")

        print(f"\nTotal Tests: {total_tests}")
        print(f"  PASSED: {passed}")
        print(f"  FAILED: {failed}")
        print(f"  ERRORS: {errors}")

        print("\nDetailed Results:")
        print("-" * 80)

        for i, result in enumerate(self.results, 1):
            status_symbol = "✓" if result["status"] == "PASS" else "✗"
            print(f"{i}. [{status_symbol}] {result['description']}")
            print(f"   Status: {result['status']}, Time: {result['elapsed']:.2f}s")
            if result["status"] != "PASS" and "error" in result:
                print(f"   Error: {result['error'][:100]}")
            print()

        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"traffic_test_results_{timestamp}.yaml"

        try:
            with open(results_file, "w") as f:
                yaml.dump({
                    "summary": {
                        "total": total_tests,
                        "passed": passed,
                        "failed": failed,
                        "errors": errors,
                    },
                    "results": self.results,
                }, f, default_flow_style=False)
            print(f"[INFO] Results saved to: {results_file}")
        except Exception as e:
            print(f"[WARNING] Failed to save results: {e}")

        return passed == total_tests


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Traffic Test Orchestrator for 4-Device VLAN Topology"
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to YAML configuration file",
    )

    parser.add_argument(
        "--interface",
        "-i",
        default="eth0",
        help="Network interface to send traffic on (default: eth0)",
    )

    parser.add_argument(
        "--scenario",
        choices=["all", "vlan10_only", "vlan20_only", "portchannel_only"],
        default="all",
        help="Test scenario to run (default: all)",
    )

    parser.add_argument(
        "--quick-test",
        action="store_true",
        help="Run quick test with reduced packet counts",
    )

    args = parser.parse_args()

    # Create orchestrator
    orchestrator = TrafficOrchestrator(config_file=args.config)

    # Modify config for quick test
    if args.quick_test:
        print("[INFO] Running quick test mode (reduced packet counts)")
        for scenario in orchestrator.config.get("traffic_scenarios", {}).values():
            if "packet_count" in scenario:
                scenario["packet_count"] = max(10, scenario["packet_count"] // 10)

    print("\n" + "=" * 80)
    print("TRAFFIC TEST ORCHESTRATOR - 4-DEVICE VLAN TOPOLOGY")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Interface: {args.interface}")
    print(f"Scenario: {args.scenario}")
    print("=" * 80)

    # Run tests based on scenario
    all_passed = True

    if args.scenario in ["all", "vlan10_only"]:
        if not orchestrator.run_vlan10_untagged_tests(args.interface):
            all_passed = False

    if args.scenario in ["all", "vlan20_only"]:
        if not orchestrator.run_vlan20_tagged_tests(args.interface):
            all_passed = False

    if args.scenario in ["all", "portchannel_only"]:
        if not orchestrator.run_portchannel_tests(args.interface):
            all_passed = False

    # Print summary
    summary_passed = orchestrator.print_summary()

    print("\n" + "=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if all_passed and summary_passed:
        print("\n[SUCCESS] All traffic tests PASSED")
        sys.exit(0)
    else:
        print("\n[FAILED] Some traffic tests FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
