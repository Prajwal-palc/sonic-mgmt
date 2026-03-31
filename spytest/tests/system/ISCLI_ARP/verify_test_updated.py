#!/usr/bin/env python3
"""Verify test_arp_05_aging_timeout.py has been updated to dynamic ARP"""

import sys

# Read the test file
with open('/home/hp_test/draksha/sonic-mgmt/spytest/tests/system/iscli_ARP/test_arp_05_aging_timeout.py', 'r') as f:
    content = f.read()

# Check for NEW code markers
new_markers = [
    "ARP Aging/Timeout with Dynamic Entries",
    "Verify that DYNAMIC ARP entries DO age out",
    "cannot test ARP aging",
    "verify_arp_entry_state",
    "get_arp_timeout",
    "switchport access Vlan",
]

# Check for OLD code markers (should NOT be present)
old_markers = [
    "cannot proceed with static ARP",
    "required for static ARP",
    "dut1_static_mac",
    "dut2_static_mac",
]

print("=" * 80)
print("VERIFICATION: test_arp_05_aging_timeout.py")
print("=" * 80)

all_good = True

print("\n✓ Checking for NEW dynamic ARP code markers:")
for marker in new_markers:
    if marker in content:
        print(f"  ✓ Found: {marker}")
    else:
        print(f"  ✗ MISSING: {marker}")
        all_good = False

print("\n✓ Checking OLD static ARP code is removed:")
for marker in old_markers:
    if marker not in content:
        print(f"  ✓ Removed: {marker}")
    else:
        print(f"  ✗ STILL PRESENT: {marker}")
        all_good = False

print("\n" + "=" * 80)
if all_good:
    print("✅ SUCCESS: File has been updated to DYNAMIC ARP mode")
    print("=" * 80)
    sys.exit(0)
else:
    print("❌ FAILURE: File still has old code or missing new code")
    print("=" * 80)
    sys.exit(1)
