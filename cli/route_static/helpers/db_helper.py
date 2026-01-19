"""
Database Helper Module
Captures database snapshots and configurations from SONiC devices
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class DBHelper:
    """Database snapshot and configuration helper"""

    def __init__(self, ssh_client, db_snapshot_dir: str):
        """
        Initialize DB Helper

        Args:
            ssh_client: SSHClient instance
            db_snapshot_dir: Directory to store DB snapshots
        """
        self.ssh_client = ssh_client
        self.db_snapshot_dir = Path(db_snapshot_dir)
        self.db_snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("DBHelper")

    def capture_snapshot(self, test_name: str, device_name: str) -> Dict[str, str]:
        """
        Capture database snapshot for a test

        Args:
            test_name: Name of the test case
            device_name: Name of the device

        Returns:
            dict: Snapshot data with command outputs
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot = {
            'test_name': test_name,
            'device': device_name,
            'timestamp': timestamp,
            'snapshots': {}
        }

        snapshot_commands = [
            'show running-configuration',
            'show ip route',
            'show ipv6 route',
            'show ip route static',
            'show ipv6 route static',
            'show vrf',
            'show interface status'
        ]

        self.logger.info(f"Capturing DB snapshot for {test_name} on {device_name}")

        for cmd in snapshot_commands:
            try:
                output = self.ssh_client.execute_show_command(cmd)
                snapshot['snapshots'][cmd] = output
                self.logger.debug(f"Captured: {cmd}")
            except Exception as e:
                self.logger.error(f"Failed to capture {cmd}: {str(e)}")
                snapshot['snapshots'][cmd] = f"Error: {str(e)}"

        # Save snapshot to file
        self._save_snapshot(snapshot, test_name, device_name, timestamp)

        return snapshot

    def _save_snapshot(self, snapshot: Dict, test_name: str, device_name: str, timestamp: str):
        """
        Save snapshot to JSON file

        Args:
            snapshot: Snapshot data
            test_name: Test case name
            device_name: Device name
            timestamp: Timestamp string
        """
        filename = f"{device_name}_{test_name}_{timestamp}.json"
        filepath = self.db_snapshot_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(snapshot, f, indent=2)
            self.logger.info(f"Snapshot saved to: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save snapshot: {str(e)}")

    def compare_snapshots(self, before: Dict, after: Dict) -> Dict:
        """
        Compare two database snapshots

        Args:
            before: Snapshot before test
            after: Snapshot after test

        Returns:
            dict: Comparison results
        """
        comparison = {
            'changes_detected': False,
            'differences': {}
        }

        for cmd in before.get('snapshots', {}).keys():
            before_output = before['snapshots'].get(cmd, '')
            after_output = after['snapshots'].get(cmd, '')

            if before_output != after_output:
                comparison['changes_detected'] = True
                comparison['differences'][cmd] = {
                    'before': before_output,
                    'after': after_output
                }

        return comparison

    def get_route_count(self, snapshot: Dict) -> Dict[str, int]:
        """
        Extract route counts from snapshot

        Args:
            snapshot: Database snapshot

        Returns:
            dict: Route counts (ipv4, ipv6)
        """
        route_count = {
            'ipv4_static': 0,
            'ipv6_static': 0
        }

        # Parse IPv4 static routes
        ipv4_output = snapshot['snapshots'].get('show ip route static', '')
        if ipv4_output:
            # Count route entries (this is a simple implementation)
            route_count['ipv4_static'] = ipv4_output.count('via ')

        # Parse IPv6 static routes
        ipv6_output = snapshot['snapshots'].get('show ipv6 route static', '')
        if ipv6_output:
            # Count route entries
            route_count['ipv6_static'] = ipv6_output.count('via ')

        return route_count

    def verify_route_exists(self, snapshot: Dict, prefix: str, ip_version: str = 'ipv4') -> bool:
        """
        Verify if a specific route exists in snapshot

        Args:
            snapshot: Database snapshot
            prefix: Route prefix to check
            ip_version: 'ipv4' or 'ipv6'

        Returns:
            bool: True if route exists
        """
        cmd = f'show {ip_version} route static'
        output = snapshot['snapshots'].get(cmd, '')

        return prefix in output

    def get_all_snapshots(self, test_name: str = None) -> List[str]:
        """
        Get list of all snapshot files

        Args:
            test_name: Optional filter by test name

        Returns:
            list: List of snapshot file paths
        """
        if test_name:
            pattern = f"*_{test_name}_*.json"
        else:
            pattern = "*.json"

        snapshots = list(self.db_snapshot_dir.glob(pattern))
        return [str(s) for s in snapshots]
