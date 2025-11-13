"""
Interface XML Parser
Parses interface.xml to extract all CLI commands for testing
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple
from pathlib import Path


class InterfaceXMLParser:
    """Parser for interface.xml to extract CLI commands"""

    def __init__(self, xml_file_path: str):
        """
        Initialize parser with XML file path

        Args:
            xml_file_path: Path to interface.xml file
        """
        self.xml_file = Path(xml_file_path)
        self.tree = None
        self.root = None
        self.commands = {
            'show': [],
            'config': [],
            'update': [],
            'delete': []
        }

        if self.xml_file.exists():
            self.parse()
        else:
            raise FileNotFoundError(f"XML file not found: {xml_file_path}")

    def parse(self):
        """Parse the XML file"""
        try:
            self.tree = ET.parse(self.xml_file)
            self.root = self.tree.getroot()
            self.extract_commands()
        except Exception as e:
            raise Exception(f"Failed to parse XML: {str(e)}")

    def extract_commands(self):
        """Extract all commands from XML"""
        # Extract show commands from enable-view
        self._extract_show_commands()

        # Extract config commands from configure-view and configure-if-view
        self._extract_config_commands()

    def _extract_show_commands(self):
        """Extract show commands"""
        # Find enable-view (search without namespace first)
        enable_view = None
        for view in self.root.iter():
            if view.tag.endswith('VIEW') and view.get('name') == 'enable-view':
                enable_view = view
                break

        if enable_view is not None:
            # Extract show interface commands
            for cmd in enable_view.iter():
                if cmd.tag.endswith('COMMAND'):
                    cmd_name = cmd.get('name', '')
                    if 'show interface' in cmd_name:
                        # Get all parameter combinations
                        self._extract_show_variations(cmd, cmd_name)
                        break  # Only need one occurrence

    def _extract_show_variations(self, cmd_element, base_cmd: str):
        """Extract all variations of show commands"""
        # Base command
        self.commands['show'].append({
            'command': base_cmd,
            'description': cmd_element.get('help', ''),
            'test_cases': [
                {'cmd': 'show interface', 'desc': 'Display all interfaces'},
                {'cmd': 'show interface counters', 'desc': 'Display interface counters'},
                {'cmd': 'show interface status', 'desc': 'Display interface status'},
                {'cmd': 'show interface Ethernet', 'desc': 'Display all Ethernet interfaces'},
                {'cmd': 'show interface Ethernet 0', 'desc': 'Display Ethernet0'},
                {'cmd': 'show interface Ethernet 4', 'desc': 'Display Ethernet4'},
                {'cmd': 'show interface Ethernet 8', 'desc': 'Display Ethernet8'},
            ]
        })

    def _extract_config_commands(self):
        """Extract configuration commands"""
        # Find configure-view for interface command (creation)
        config_view = None
        for view in self.root.iter():
            if view.tag.endswith('VIEW') and view.get('name') == 'configure-view':
                config_view = view
                break

        if config_view is not None:
            # Interface command (creation)
            self.commands['config'].append({
                'command': 'interface Ethernet',
                'description': 'Select an interface (creation)',
                'test_cases': [
                    {'cmd': 'configure terminal\ninterface Ethernet 0', 'desc': 'Create/Enter Ethernet0 config'},
                    {'cmd': 'configure terminal\ninterface Ethernet 4', 'desc': 'Create/Enter Ethernet4 config'},
                    {'cmd': 'configure terminal\ninterface Ethernet 8', 'desc': 'Create/Enter Ethernet8 config'},
                ]
            })

        # Find configure-if-view for interface config commands
        if_view = None
        for view in self.root.iter():
            if view.tag.endswith('VIEW') and view.get('name') == 'configure-if-view':
                if_view = view
                break

        if if_view is not None:
            for cmd in if_view.iter():
                if not cmd.tag.endswith('COMMAND'):
                    continue

                cmd_name = cmd.get('name', '')
                cmd_help = cmd.get('help', '')

                if cmd_name == 'shutdown':
                    self.commands['update'].append({
                        'command': 'shutdown',
                        'description': cmd_help,
                        'test_cases': [
                            {'cmd': 'configure terminal\ninterface Ethernet 4\nshutdown\nend',
                             'desc': 'Disable Ethernet4'}
                        ]
                    })
                elif cmd_name == 'no shutdown':
                    self.commands['update'].append({
                        'command': 'no shutdown',
                        'description': cmd_help,
                        'test_cases': [
                            {'cmd': 'configure terminal\ninterface Ethernet 4\nno shutdown\nend',
                             'desc': 'Enable Ethernet4'}
                        ]
                    })
                elif cmd_name == 'description':
                    self.commands['update'].append({
                        'command': 'description',
                        'description': cmd_help,
                        'test_cases': [
                            {'cmd': 'configure terminal\ninterface Ethernet 4\ndescription Test Interface\nend',
                             'desc': 'Set description on Ethernet4'},
                            {'cmd': 'configure terminal\ninterface Ethernet 4\ndescription "Interface for Testing"\nend',
                             'desc': 'Set description with spaces'}
                        ]
                    })
                elif cmd_name == 'no description':
                    self.commands['delete'].append({
                        'command': 'no description',
                        'description': cmd_help,
                        'test_cases': [
                            {'cmd': 'configure terminal\ninterface Ethernet 4\nno description\nend',
                             'desc': 'Remove description from Ethernet4'}
                        ]
                    })
                elif cmd_name == 'mtu':
                    self.commands['update'].append({
                        'command': 'mtu',
                        'description': cmd_help,
                        'test_cases': [
                            {'cmd': 'configure terminal\ninterface Ethernet 4\nmtu 1500\nend',
                             'desc': 'Set MTU to 1500'},
                            {'cmd': 'configure terminal\ninterface Ethernet 4\nmtu 9000\nend',
                             'desc': 'Set MTU to 9000'},
                        ]
                    })
                elif cmd_name == 'no mtu':
                    self.commands['delete'].append({
                        'command': 'no mtu',
                        'description': cmd_help,
                        'test_cases': [
                            {'cmd': 'configure terminal\ninterface Ethernet 4\nno mtu\nend',
                             'desc': 'Reset MTU to default (9100)'}
                        ]
                    })

    def get_all_commands(self) -> Dict[str, List]:
        """Get all extracted commands organized by type"""
        return self.commands

    def get_test_summary(self) -> Dict:
        """Get summary of test cases"""
        total_tests = 0
        for cmd_type in self.commands:
            for cmd_group in self.commands[cmd_type]:
                total_tests += len(cmd_group.get('test_cases', []))

        return {
            'total_test_cases': total_tests,
            'show_commands': len(self.commands['show']),
            'config_commands': len(self.commands['config']),
            'update_commands': len(self.commands['update']),
            'delete_commands': len(self.commands['delete']),
            'breakdown': {
                'show': sum(len(c.get('test_cases', [])) for c in self.commands['show']),
                'config': sum(len(c.get('test_cases', [])) for c in self.commands['config']),
                'update': sum(len(c.get('test_cases', [])) for c in self.commands['update']),
                'delete': sum(len(c.get('test_cases', [])) for c in self.commands['delete']),
            }
        }

    def print_summary(self):
        """Print command summary"""
        summary = self.get_test_summary()
        print("=" * 70)
        print("Interface XML Command Summary")
        print("=" * 70)
        print(f"Total Test Cases: {summary['total_test_cases']}")
        print()
        print("Command Breakdown:")
        print(f"  Show Commands: {summary['breakdown']['show']} test cases")
        print(f"  Config Commands (Creation): {summary['breakdown']['config']} test cases")
        print(f"  Update Commands: {summary['breakdown']['update']} test cases")
        print(f"  Delete Commands: {summary['breakdown']['delete']} test cases")
        print("=" * 70)


if __name__ == "__main__":
    # Parse interface.xml
    xml_path = "/home/adminuser/draksha/interface.xml"
    parser = InterfaceXMLParser(xml_path)

    # Print summary
    parser.print_summary()

    # Print detailed commands
    print("\nDetailed Commands:")
    print("-" * 70)

    all_commands = parser.get_all_commands()
    for cmd_type, cmd_groups in all_commands.items():
        print(f"\n{cmd_type.upper()} COMMANDS:")
        for group in cmd_groups:
            print(f"  - {group['command']}: {group['description']}")
            for tc in group.get('test_cases', []):
                print(f"    • {tc['desc']}")
