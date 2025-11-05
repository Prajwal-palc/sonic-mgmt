#!/usr/bin/env python3
"""
BGP Cleanup Script
Removes all BGP configuration from both test devices
"""

import sys
import os

# Add SpyTest to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spytest import st
from spytest.dicts import SpyTestDict
import apis.routing.bgp as bgp_api

def cleanup_bgp_on_device(dut_name):
    """Remove BGP configuration from a device."""
    try:
        st.banner(f"Cleaning up BGP configuration on {dut_name}")

        # Try to remove BGP using klish CLI
        result = bgp_api.config_router_bgp_mode(
            dut_name,
            config="no",
            cli_type="klish",
            skip_error_check=True
        )

        if result:
            st.log(f"✓ Successfully removed BGP configuration from {dut_name}")
            return True
        else:
            st.log(f"⚠ BGP removal returned False for {dut_name} (may not exist)")
            return True  # Not an error if BGP doesn't exist

    except Exception as e:
        st.error(f"✗ Failed to remove BGP from {dut_name}: {str(e)}")
        return False

def main():
    """Main cleanup function."""
    # Initialize SpyTest
    st.banner("BGP Cleanup Script - Starting")

    # Get testbed file
    testbed = "./testbeds/testbed_vs_2d.yaml"

    st.log(f"Using testbed: {testbed}")

    # Note: This script needs to be run within SpyTest framework
    # with active connections to devices
    st.log("Note: This script requires active SpyTest device connections")
    st.log("Run this as: ./bin/spytest --testbed ./testbeds/testbed_vs_2d.yaml cleanup_bgp.py")

    success = True

    # Clean up both devices
    for dut in ["smic_sonic1", "smic_sonic2"]:
        if not cleanup_bgp_on_device(dut):
            success = False

    if success:
        st.banner("✓ BGP cleanup completed successfully on all devices")
        return 0
    else:
        st.banner("✗ BGP cleanup encountered errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())
