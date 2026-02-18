"""
BGP VRF INSTANCE TEST - SM_ISCLI_32: BGP VRF Instance Create and Remove

Test Case ID: SM_ISCLI_32
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli session (both DUTs):

  DUT1:
    configure
    ip vrf Vrf111
    exit
    show ip vrf                          -> Vrf111 appears in list
    configure
    router bgp 65001 vrf Vrf111
      router-id 1.1.1.1
      exit
    exit
    show running-configuration bgp       -> router bgp 65001 vrf Vrf111 / router-id 1.1.1.1
    configure
    no router bgp vrf Vrf111             -> (workaround - succeeds without AS number)
    exit
    show running-configuration bgp       -> (empty - BGP VRF instance removed)
    configure
    no ip vrf Vrf111
    exit
    show ip vrf                          -> Vrf111 absent

  DUT2 (same steps with router-id 2.2.2.2):
    configure
    ip vrf Vrf111
    exit
    configure
    router bgp 65001 vrf Vrf111
      router-id 2.2.2.2
      exit
    exit
    show running-configuration bgp       -> router bgp 65001 vrf Vrf111 / router-id 2.2.2.2
    configure
    no router bgp vrf Vrf111
    exit
    show running-configuration bgp       -> (empty)
    configure
    no ip vrf Vrf111
    exit

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \\
    --testbed ./testbeds/testbed_2vs.yaml \\
    tests/system/iscli_BGP/test_bgp_p2_32_vrf_instance.py \\
    --logs-path ./logs/p2_32_$(date +%F_%H%M%S) \\
    --log-level debug --skip-init-config --ifname-type native
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "vrf_name":       "Vrf111",
    "asn":            "65001",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
})

TC_IDS = SpyTestDict({
    "p2_32_vrf_create":   "TC-SM-ISCLI-P2-32-001",
    "p2_32_bgp_create":   "TC-SM-ISCLI-P2-32-002",
    "p2_32_show_running": "TC-SM-ISCLI-P2-32-003",
    "p2_32_bgp_remove":   "TC-SM-ISCLI-P2-32-004",
    "p2_32_vrf_remove":   "TC-SM-ISCLI-P2-32-005",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_p2_32_module_hooks(request):
    """Module-level setup and teardown for SM_ISCLI_32."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SM_ISCLI_32 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    bgp_p2_32_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("SM_ISCLI_32 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        bgp_p2_32_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def bgp_p2_32_pre_config():
    """Pre-configuration: Remove any existing BGP VRF instance and VRF on both DUTs."""
    st.log("Pre-configuration: Clearing existing BGP VRF configuration on both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"no router bgp vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            st.config(dut, [
                f"no ip vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(2, "Waiting for pre-config clear")
    st.log("Pre-configuration completed")


def bgp_p2_32_cleanup():
    """Cleanup: Ensure BGP VRF instance and VRF are removed on both DUTs."""
    st.log("Cleanup: Removing BGP VRF instance configuration on both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"no router bgp vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            st.config(dut, [
                f"no ip vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"VRF cleanup warning on {dut}: {str(e)}")

    st.log("Cleanup completed")


@pytest.mark.bgp_vrf
@pytest.mark.community
@pytest.mark.community_pass
def test_bgp_p2_32_vrf_instance():
    """
    SM_ISCLI_32: BGP VRF Instance Create and Remove

    Follows exact manual sonic-cli session on both DUTs:

    Step 1: Create VRF Vrf111 on both DUTs
      sonic-cli: ip vrf Vrf111

    Step 2: Verify VRF exists on both DUTs
      sonic-cli: show ip vrf -> Vrf111 appears

    Step 3: Create BGP instance inside VRF on both DUTs
      DUT1: router bgp 65001 vrf Vrf111 -> router-id 1.1.1.1
      DUT2: router bgp 65001 vrf Vrf111 -> router-id 2.2.2.2

    Step 4: Verify BGP VRF instance in running-config on both DUTs
      sonic-cli: show running-configuration bgp

    Step 5: Remove BGP VRF instance using workaround on both DUTs
      sonic-cli: no router bgp vrf Vrf111

    Step 6: Verify BGP VRF instance removed from running-config on both DUTs
      sonic-cli: show running-configuration bgp -> empty

    Step 7: Remove VRF on both DUTs
      sonic-cli: no ip vrf Vrf111

    Step 8: Verify VRF removed on both DUTs
      sonic-cli: show ip vrf -> Vrf111 absent
    """
    st.banner("=" * 80)
    st.banner("TEST SM_ISCLI_32: BGP VRF INSTANCE CREATE AND REMOVE")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Create VRF Vrf111 on both DUTs
    # sonic-cli: ip vrf Vrf111
    # ==================================================================
    st.banner("STEP 1: Create VRF Vrf111 on Both DUTs")
    st.log(f"Command: ip vrf {CONFIG.vrf_name}")

    try:
        st.config(vars.D1, [
            f"ip vrf {CONFIG.vrf_name}"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1: ip vrf {CONFIG.vrf_name} -> created")
    except Exception as e:
        st.report_tc_fail(TC_IDS.p2_32_vrf_create, "msg",
                          f"DUT1: Failed to create VRF {CONFIG.vrf_name}")
        st.report_fail("msg", f"DUT1: ip vrf {CONFIG.vrf_name} failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"ip vrf {CONFIG.vrf_name}"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2: ip vrf {CONFIG.vrf_name} -> created")
    except Exception as e:
        st.report_tc_fail(TC_IDS.p2_32_vrf_create, "msg",
                          f"DUT2: Failed to create VRF {CONFIG.vrf_name}")
        st.report_fail("msg", f"DUT2: ip vrf {CONFIG.vrf_name} failed: {str(e)}")

    st.wait(2, "Waiting for VRF creation")

    # ==================================================================
    # STEP 2: Verify VRF exists on both DUTs
    # sonic-cli: show ip vrf -> Vrf111 appears in list
    # ==================================================================
    st.banner("STEP 2: Verify VRF Exists on Both DUTs")
    st.log("Command: show ip vrf")

    try:
        output = st.show(vars.D1, "show ip vrf", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT1 show ip vrf: {output_str[:500]}")
        d1_vrf_exists = CONFIG.vrf_name in output_str
    except Exception as e:
        st.error(f"DUT1: show ip vrf failed: {str(e)}")
        d1_vrf_exists = False

    if not d1_vrf_exists:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d1_vrf_not_found")
        st.report_tc_fail(TC_IDS.p2_32_vrf_create, "msg",
                          f"DUT1: VRF {CONFIG.vrf_name} not found in show ip vrf")
        st.report_fail("msg", f"DUT1: show ip vrf: {CONFIG.vrf_name} not found")

    st.log(f"DUT1: VRF {CONFIG.vrf_name} confirmed in show ip vrf")

    try:
        output = st.show(vars.D2, "show ip vrf", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT2 show ip vrf: {output_str[:500]}")
        d2_vrf_exists = CONFIG.vrf_name in output_str
    except Exception as e:
        st.error(f"DUT2: show ip vrf failed: {str(e)}")
        d2_vrf_exists = False

    if not d2_vrf_exists:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d2_vrf_not_found")
        st.report_tc_fail(TC_IDS.p2_32_vrf_create, "msg",
                          f"DUT2: VRF {CONFIG.vrf_name} not found in show ip vrf")
        st.report_fail("msg", f"DUT2: show ip vrf: {CONFIG.vrf_name} not found")

    st.log(f"DUT2: VRF {CONFIG.vrf_name} confirmed in show ip vrf")
    st.report_tc_pass(TC_IDS.p2_32_vrf_create, "msg",
                      f"VRF {CONFIG.vrf_name} created and verified on both DUTs")

    # ==================================================================
    # STEP 3: Create BGP instance inside VRF on both DUTs
    # DUT1: router bgp 65001 vrf Vrf111 -> router-id 1.1.1.1
    # DUT2: router bgp 65001 vrf Vrf111 -> router-id 2.2.2.2
    # ==================================================================
    st.banner("STEP 3: Create BGP Instance Inside VRF on Both DUTs")
    st.log(f"DUT1: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} / router-id {CONFIG.dut1_router_id}")
    st.log(f"DUT2: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} / router-id {CONFIG.dut2_router_id}")

    try:
        st.config(vars.D1, [
            f"router bgp {CONFIG.asn} vrf {CONFIG.vrf_name}",
            f"router-id {CONFIG.dut1_router_id}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} "
               f"router-id {CONFIG.dut1_router_id} -> configured")
    except Exception as e:
        st.report_tc_fail(TC_IDS.p2_32_bgp_create, "msg",
                          "DUT1: Failed to create BGP VRF instance")
        st.report_fail("msg",
                       f"DUT1: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"router bgp {CONFIG.asn} vrf {CONFIG.vrf_name}",
            f"router-id {CONFIG.dut2_router_id}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} "
               f"router-id {CONFIG.dut2_router_id} -> configured")
    except Exception as e:
        st.report_tc_fail(TC_IDS.p2_32_bgp_create, "msg",
                          "DUT2: Failed to create BGP VRF instance")
        st.report_fail("msg",
                       f"DUT2: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} failed: {str(e)}")

    st.report_tc_pass(TC_IDS.p2_32_bgp_create, "msg",
                      f"BGP {CONFIG.asn} vrf {CONFIG.vrf_name} created on both DUTs")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.config(vars.D2, ["end"], type='klish', skip_error_check=True)
    st.wait(3, "Waiting for BGP VRF instance to be active")

    # ==================================================================
    # STEP 4: Verify BGP VRF instance in running-configuration on both DUTs
    # sonic-cli: show running-configuration bgp
    # DUT1 Expected: router bgp 65001 vrf Vrf111 / router-id 1.1.1.1
    # DUT2 Expected: router bgp 65001 vrf Vrf111 / router-id 2.2.2.2
    # ==================================================================
    st.banner("STEP 4: Verify BGP VRF Instance in Running-Configuration on Both DUTs")
    st.log("Command: show running-configuration bgp")

    try:
        output = st.show(vars.D1, "show running-configuration bgp",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT1 show running-configuration bgp: {output_str[:500]}")
        d1_bgp_in_config = (f"router bgp {CONFIG.asn}" in output_str and
                             CONFIG.vrf_name in output_str and
                             CONFIG.dut1_router_id in output_str)
    except Exception as e:
        st.error(f"DUT1: show running-configuration bgp failed: {str(e)}")
        d1_bgp_in_config = False

    if not d1_bgp_in_config:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d1_bgp_vrf_not_in_running_config")
        st.report_tc_fail(TC_IDS.p2_32_show_running, "msg",
                          f"DUT1: BGP VRF instance not found in running-configuration")
        st.report_fail("msg",
                       f"DUT1: show running-configuration bgp: "
                       f"'router bgp {CONFIG.asn} vrf {CONFIG.vrf_name}' not found")

    st.log(f"DUT1: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} "
           f"router-id {CONFIG.dut1_router_id} confirmed")

    try:
        output = st.show(vars.D2, "show running-configuration bgp",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT2 show running-configuration bgp: {output_str[:500]}")
        d2_bgp_in_config = (f"router bgp {CONFIG.asn}" in output_str and
                             CONFIG.vrf_name in output_str and
                             CONFIG.dut2_router_id in output_str)
    except Exception as e:
        st.error(f"DUT2: show running-configuration bgp failed: {str(e)}")
        d2_bgp_in_config = False

    if not d2_bgp_in_config:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d2_bgp_vrf_not_in_running_config")
        st.report_tc_fail(TC_IDS.p2_32_show_running, "msg",
                          f"DUT2: BGP VRF instance not found in running-configuration")
        st.report_fail("msg",
                       f"DUT2: show running-configuration bgp: "
                       f"'router bgp {CONFIG.asn} vrf {CONFIG.vrf_name}' not found")

    st.log(f"DUT2: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} "
           f"router-id {CONFIG.dut2_router_id} confirmed")
    st.report_tc_pass(TC_IDS.p2_32_show_running, "msg",
                      "BGP VRF instance confirmed in running-configuration on both DUTs")

    # ==================================================================
    # STEP 5: Remove BGP VRF instance on both DUTs
    # sonic-cli: no router bgp vrf Vrf111
    # Note: 'no router bgp vrf Vrf111' (without AS) is the correct working syntax
    # ==================================================================
    st.banner("STEP 5: Remove BGP VRF Instance on Both DUTs")
    st.log(f"Command: no router bgp vrf {CONFIG.vrf_name}")

    try:
        st.config(vars.D1, [
            f"no router bgp vrf {CONFIG.vrf_name}"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1: no router bgp vrf {CONFIG.vrf_name} -> executed")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d1_bgp_vrf_remove_failed")
        st.report_tc_fail(TC_IDS.p2_32_bgp_remove, "msg",
                          f"DUT1: Failed to remove BGP VRF instance")
        st.report_fail("msg",
                       f"DUT1: no router bgp vrf {CONFIG.vrf_name} failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"no router bgp vrf {CONFIG.vrf_name}"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2: no router bgp vrf {CONFIG.vrf_name} -> executed")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d2_bgp_vrf_remove_failed")
        st.report_tc_fail(TC_IDS.p2_32_bgp_remove, "msg",
                          f"DUT2: Failed to remove BGP VRF instance")
        st.report_fail("msg",
                       f"DUT2: no router bgp vrf {CONFIG.vrf_name} failed: {str(e)}")

    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.config(vars.D2, ["end"], type='klish', skip_error_check=True)
    st.wait(3, "Waiting for BGP VRF instance removal")

    # ==================================================================
    # STEP 6: Verify BGP VRF instance removed from running-configuration
    # sonic-cli: show running-configuration bgp -> should be empty
    # ==================================================================
    st.banner("STEP 6: Verify BGP VRF Instance Removed from Running-Configuration on Both DUTs")
    st.log("Command: show running-configuration bgp")

    try:
        output = st.show(vars.D1, "show running-configuration bgp",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT1 show running-configuration bgp after removal: {output_str[:500]}")
        d1_bgp_still_present = (f"router bgp {CONFIG.asn}" in output_str and
                                 CONFIG.vrf_name in output_str)
    except Exception as e:
        st.error(f"DUT1: show running-configuration bgp failed: {str(e)}")
        d1_bgp_still_present = True

    if d1_bgp_still_present:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d1_bgp_vrf_not_removed")
        st.report_tc_fail(TC_IDS.p2_32_bgp_remove, "msg",
                          "DUT1: BGP VRF instance still present in running-configuration")
        st.report_fail("msg", "DUT1: BGP VRF instance removal failed - still in running-config")

    st.log(f"DUT1: BGP VRF instance removed from running-configuration")

    try:
        output = st.show(vars.D2, "show running-configuration bgp",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT2 show running-configuration bgp after removal: {output_str[:500]}")
        d2_bgp_still_present = (f"router bgp {CONFIG.asn}" in output_str and
                                 CONFIG.vrf_name in output_str)
    except Exception as e:
        st.error(f"DUT2: show running-configuration bgp failed: {str(e)}")
        d2_bgp_still_present = True

    if d2_bgp_still_present:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d2_bgp_vrf_not_removed")
        st.report_tc_fail(TC_IDS.p2_32_bgp_remove, "msg",
                          "DUT2: BGP VRF instance still present in running-configuration")
        st.report_fail("msg", "DUT2: BGP VRF instance removal failed - still in running-config")

    st.log(f"DUT2: BGP VRF instance removed from running-configuration")
    st.report_tc_pass(TC_IDS.p2_32_bgp_remove, "msg",
                      "BGP VRF instance removed from running-configuration on both DUTs")

    # ==================================================================
    # STEP 7: Remove VRF Vrf111 on both DUTs
    # sonic-cli: no ip vrf Vrf111
    # ==================================================================
    st.banner("STEP 7: Remove VRF Vrf111 on Both DUTs")
    st.log(f"Command: no ip vrf {CONFIG.vrf_name}")

    try:
        st.config(vars.D1, [
            f"no ip vrf {CONFIG.vrf_name}"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1: no ip vrf {CONFIG.vrf_name} -> executed")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d1_vrf_remove_failed")
        st.report_tc_fail(TC_IDS.p2_32_vrf_remove, "msg",
                          f"DUT1: Failed to remove VRF {CONFIG.vrf_name}")
        st.report_fail("msg", f"DUT1: no ip vrf {CONFIG.vrf_name} failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"no ip vrf {CONFIG.vrf_name}"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2: no ip vrf {CONFIG.vrf_name} -> executed")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d2_vrf_remove_failed")
        st.report_tc_fail(TC_IDS.p2_32_vrf_remove, "msg",
                          f"DUT2: Failed to remove VRF {CONFIG.vrf_name}")
        st.report_fail("msg", f"DUT2: no ip vrf {CONFIG.vrf_name} failed: {str(e)}")

    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.config(vars.D2, ["end"], type='klish', skip_error_check=True)
    st.wait(2, "Waiting for VRF removal")

    # ==================================================================
    # STEP 8: Verify VRF removed on both DUTs
    # sonic-cli: show ip vrf -> Vrf111 absent
    # ==================================================================
    st.banner("STEP 8: Verify VRF Removed on Both DUTs")
    st.log("Command: show ip vrf")

    try:
        output = st.show(vars.D1, "show ip vrf", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT1 show ip vrf after removal: {output_str[:500]}")
        d1_vrf_still_exists = CONFIG.vrf_name in output_str
    except Exception as e:
        st.error(f"DUT1: show ip vrf failed: {str(e)}")
        d1_vrf_still_exists = True

    if d1_vrf_still_exists:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d1_vrf_not_removed")
        st.report_tc_fail(TC_IDS.p2_32_vrf_remove, "msg",
                          f"DUT1: VRF {CONFIG.vrf_name} still present in show ip vrf after deletion")
        st.report_fail("msg", f"DUT1: VRF {CONFIG.vrf_name} removal failed")

    st.log(f"DUT1: VRF {CONFIG.vrf_name} removed from show ip vrf")

    try:
        output = st.show(vars.D2, "show ip vrf", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT2 show ip vrf after removal: {output_str[:500]}")
        d2_vrf_still_exists = CONFIG.vrf_name in output_str
    except Exception as e:
        st.error(f"DUT2: show ip vrf failed: {str(e)}")
        d2_vrf_still_exists = True

    if d2_vrf_still_exists:
        st.generate_tech_support([vars.D1, vars.D2], "p2_32_d2_vrf_not_removed")
        st.report_tc_fail(TC_IDS.p2_32_vrf_remove, "msg",
                          f"DUT2: VRF {CONFIG.vrf_name} still present in show ip vrf after deletion")
        st.report_fail("msg", f"DUT2: VRF {CONFIG.vrf_name} removal failed")

    st.log(f"DUT2: VRF {CONFIG.vrf_name} removed from show ip vrf")
    st.report_tc_pass(TC_IDS.p2_32_vrf_remove, "msg",
                      f"VRF {CONFIG.vrf_name} removed and verified on both DUTs")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SM_ISCLI_32 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SM_ISCLI_32: BGP VRF Instance Create and Remove")
    st.log(f"  ip vrf {CONFIG.vrf_name} -> Created on both DUTs")
    st.log(f"  show ip vrf -> {CONFIG.vrf_name} verified on both DUTs")
    st.log(f"  DUT1: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} "
           f"router-id {CONFIG.dut1_router_id} -> Configured")
    st.log(f"  DUT2: router bgp {CONFIG.asn} vrf {CONFIG.vrf_name} "
           f"router-id {CONFIG.dut2_router_id} -> Configured")
    st.log(f"  show running-configuration bgp -> BGP VRF instances confirmed on both DUTs")
    st.log(f"  no router bgp vrf {CONFIG.vrf_name} -> Removed on both DUTs")
    st.log(f"  show running-configuration bgp -> BGP VRF instances absent on both DUTs")
    st.log(f"  no ip vrf {CONFIG.vrf_name} -> VRF removed on both DUTs")
    st.log(f"  show ip vrf -> {CONFIG.vrf_name} absent on both DUTs")

    st.report_pass("test_case_passed")
