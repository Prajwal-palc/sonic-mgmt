#!/usr/bin/env python3
"""
Script to identify all files necessary to execute specified test scripts.
This script analyzes test files, their imports, and dependencies to create
a comprehensive list of all required files.
"""

import os
import re
import ast
from pathlib import Path
from typing import Set, List, Dict

# Base directory
BASE_DIR = Path(__file__).parent.resolve()

# Test files to analyze
TEST_FILES = [
    "tests/routing/BGP/test_bgp_ipv4_basic_ebgp.py",
    "tests/routing/BGP/test_bgp_svi_ipv4_ebgp.py",
    "tests/routing/BGP/test_bgp_portchannel_ipv4_ebgp.py",
    "tests/routing/BGP/test_bgp_loopback_ipv4_ebgp.py",
    "tests/routing/BGP/test_bgp_ipv4_basic.py",
    "tests/routing/BGP/test_bgp_svi_ipv4.py",
    "tests/routing/BGP/test_bgp_portchannel_ipv4.py",
    "tests/routing/BGP/test_bgp_loopback_ipv4.py",
    "tests/routing/BGP/test_bgp_ebgp_connected_static_redistribution.py",
    "tests/routing/BGP/test_bgp_advanced_features.py",
    "tests/routing/BGP/test_ipv4_bgp_route_reflector.py",
    "tests/routing/BGP/test_bgp_med_weight.py",
    "tests/system/ntp/test_ntp_iscli.py",
    "tests/system/ntp/test_ntp_functional.py",
]

# Files already identified
required_files = set()
processed_files = set()


def find_var_file_from_test(test_file_path: Path) -> List[str]:
    """Extract variable file references from test file."""
    var_files = []
    try:
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # Look for DEFAULT_VAR_FILE pattern
            var_file_pattern = r'DEFAULT_VAR_FILE\s*=\s*.*?["\']([^"\']+\.yaml)["\']'
            matches = re.findall(var_file_pattern, content)
            for match in matches:
                # Resolve relative to test file directory
                var_file = test_file_path.parent / match
                if var_file.exists():
                    var_files.append(str(var_file.relative_to(BASE_DIR)))

            # Also look for direct yaml references
            yaml_pattern = r'["\']([^"\']*vars_[^"\']*\.yaml)["\']'
            matches = re.findall(yaml_pattern, content)
            for match in matches:
                var_file = test_file_path.parent / match
                if var_file.exists():
                    var_files.append(str(var_file.relative_to(BASE_DIR)))

    except Exception as e:
        print(f"Error reading {test_file_path}: {e}")

    return list(set(var_files))


def extract_imports_from_file(file_path: Path) -> Set[str]:
    """Extract import statements from a Python file."""
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return imports


def resolve_import_to_file(import_name: str) -> List[str]:
    """Resolve an import name to actual file paths."""
    files = []

    # Convert import name to file path
    # e.g., "apis.routing.bgp" -> "apis/routing/bgp.py"
    path_parts = import_name.split('.')

    # Try as module file
    module_file = BASE_DIR / '/'.join(path_parts[:]) / '__init__.py' if len(path_parts) > 1 else None
    direct_file = BASE_DIR / (('/'.join(path_parts) + '.py'))

    if direct_file.exists():
        files.append(str(direct_file.relative_to(BASE_DIR)))

    if module_file and module_file.exists():
        files.append(str(module_file.relative_to(BASE_DIR)))

    # Also check for package init
    package_init = BASE_DIR / '/'.join(path_parts) / '__init__.py'
    if package_init.exists() and str(package_init.relative_to(BASE_DIR)) not in files:
        files.append(str(package_init.relative_to(BASE_DIR)))

    return files


def analyze_file(file_path: str):
    """Recursively analyze a file and its dependencies."""
    if file_path in processed_files:
        return

    processed_files.add(file_path)
    required_files.add(file_path)

    full_path = BASE_DIR / file_path

    if not full_path.exists():
        print(f"Warning: File not found: {file_path}")
        return

    # If it's a test file, find its var file
    if file_path.endswith('.py') and 'test_' in file_path:
        var_files = find_var_file_from_test(full_path)
        for vf in var_files:
            required_files.add(vf)

    # Extract imports
    if file_path.endswith('.py'):
        imports = extract_imports_from_file(full_path)

        for imp in imports:
            # Only process internal imports (apis, utilities, spytest)
            if any(imp.startswith(prefix) for prefix in ['apis', 'utilities', 'spytest']):
                resolved_files = resolve_import_to_file(imp)
                for rf in resolved_files:
                    analyze_file(rf)


def identify_core_framework_files() -> List[str]:
    """Identify essential spytest core files needed for execution."""
    core_files = [
        # Core framework
        "spytest/__init__.py",
        "spytest/framework.py",
        "spytest/st.py",
        "spytest/dicts.py",
        "spytest/net.py",
        "spytest/testbed.py",
        "spytest/infra.py",
        "spytest/splugin.py",

        # Configuration files
        "reporting/syslogs.yaml",
        "testbeds/sonic_errors.yaml",

        # Entry point
        "bin/spytest",

        # Utilities init
        "utilities/__init__.py",
        "apis/__init__.py",
        "apis/common/__init__.py",
        "apis/routing/__init__.py",
        "apis/switching/__init__.py",
        "apis/system/__init__.py",
    ]

    return [f for f in core_files if (BASE_DIR / f).exists()]


def main():
    """Main function to identify all required files."""
    print("=" * 80)
    print("IDENTIFYING DEPENDENCIES FOR TEST FILES")
    print("=" * 80)

    # Analyze each test file
    for test_file in TEST_FILES:
        print(f"\nAnalyzing: {test_file}")
        analyze_file(test_file)

    # Add core framework files
    print("\nAdding core framework files...")
    core_files = identify_core_framework_files()
    required_files.update(core_files)

    # Sort and categorize files
    test_files_list = sorted([f for f in required_files if 'tests/' in f and f.endswith('.py')])
    var_files_list = sorted([f for f in required_files if f.endswith('.yaml')])
    api_files_list = sorted([f for f in required_files if 'apis/' in f and f.endswith('.py')])
    utility_files_list = sorted([f for f in required_files if 'utilities/' in f and f.endswith('.py')])
    framework_files_list = sorted([f for f in required_files if 'spytest/' in f])
    other_files = sorted([f for f in required_files if f not in test_files_list + var_files_list + api_files_list + utility_files_list + framework_files_list])

    # Write results to file
    output_file = BASE_DIR / "required_files_list.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# REQUIRED FILES FOR TEST EXECUTION\n")
        f.write(f"# Total files: {len(required_files)}\n")
        f.write("# Generated by identify_dependencies.py\n\n")

        f.write("## TEST FILES\n")
        for tf in test_files_list:
            f.write(f"{tf}\n")

        f.write("\n## VARIABLE FILES (YAML)\n")
        for vf in var_files_list:
            f.write(f"{vf}\n")

        f.write("\n## API MODULES\n")
        for af in api_files_list:
            f.write(f"{af}\n")

        f.write("\n## UTILITY MODULES\n")
        for uf in utility_files_list:
            f.write(f"{uf}\n")

        f.write("\n## FRAMEWORK FILES\n")
        for ff in framework_files_list:
            f.write(f"{ff}\n")

        f.write("\n## OTHER FILES\n")
        for of in other_files:
            f.write(f"{of}\n")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Test files: {len(test_files_list)}")
    print(f"Variable files: {len(var_files_list)}")
    print(f"API modules: {len(api_files_list)}")
    print(f"Utility modules: {len(utility_files_list)}")
    print(f"Framework files: {len(framework_files_list)}")
    print(f"Other files: {len(other_files)}")
    print(f"\nTotal files: {len(required_files)}")
    print(f"\nOutput written to: {output_file}")

    return list(required_files)


if __name__ == "__main__":
    main()
