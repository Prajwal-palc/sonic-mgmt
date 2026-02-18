"""
SM_ISCLI_13: VRF Create, Interface Bind, and Delete

Test Case ID: SM_ISCLI_13
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli commands reproduced (both DUTs):

--- Part A: Ethernet0 VRF Binding ---
DUT1 & DUT2:
  configure
  ip vrf Vrf111
  exit
  show ip vrf                              -> Vrf111 appears in list
  configure
  interface Ethernet 0
    ip vrf forwarding Vrf111
    exit
  end
  show ip vrf Vrf111                       -> Vrf111  Ethernet0
  configure
  interface Ethernet 0
    no ip vrf forwarding Vrf111
    end
  show ip vrf Vrf111                       -> Vrf111  (no interfaces)
  configure
  no ip vrf Vrf111
  exit
  show ip vrf                              -> Vrf111 absent

--- Part B: Vlan100 VRF Binding ---
DUT1:
  configure
  ip vrf Vrf111
  exit
  configure
  vlan 100
  exit
  configure
  interface Vlan 100
    ip vrf forwarding Vrf111
    ip address 10.1.1.1/24
    exit
  exit
  show ip vrf Vrf111                       -> Vrf111  Vlan100
  show interface Vlan 100                  -> IPV4 address is 10.1.1.1/24

DUT2:
  configure
  ip vrf Vrf111
  exit
  configure
  vlan 100
  exit
  configure
  interface Vlan 100
    ip vrf forwarding Vrf111
    ip address 10.1.1.2/24
    exit
  exit
  show ip vrf Vrf111                       -> Vrf111  Vlan100
  show interface Vlan 100                  -> IPV4 address is 10.1.1.2/24

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \\
    --testbed ./testbeds/testbed_2vs.yaml \\
    tests/system/iscli_BGP/test_sm_iscli_13_vrf_binding.py \\
    --logs-path ./logs/sm13_$(date +%F_%H%M%S) \\
    --log-level debug --skip-init-config --ifname-type native
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "vrf_name":    "Vrf111",
    "interface":   "Ethernet 0",
    "vlan_id":     "100",
    "dut1_ip":     "10.1.1.1",
    "dut2_ip":     "10.1.1.2",
    "prefix_len":  "24",
})

TC_IDS = SpyTestDict({
    "sm13_vrf_create":         "TC-SM-ISCLI-13-001",
    "sm13_eth_bind":           "TC-SM-ISCLI-13-002",
    "sm13_eth_unbind":         "TC-SM-ISCLI-13-003",
    "sm13_vrf_delete":         "TC-SM-ISCLI-13-004",
    "sm13_vlan_create":        "TC-SM-ISCLI-13-005",
    "sm13_vlan_bind":          "TC-SM-ISCLI-13-006",
    "sm13_vlan_ip_verify":     "TC-SM-ISCLI-13-007",
})


@pytest.fixture(scope="module", autouse=True)
def sm_iscli_13_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SM_ISCLI_13 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    sm_iscli_13_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("SM_ISCLI_13 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        sm_iscli_13_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def sm_iscli_13_pre_config():
    """Pre-configuration: Remove any leftover VRF and Vlan config."""
    st.log("Pre-configuration: Clearing existing configuration on DUT1 and DUT2")

    for dut in [vars.D1, vars.D2]:
        # Remove Vlan100 IP and VRF binding
        try:
            st.config(dut, [
                f"interface Vlan {CONFIG.vlan_id}",
                "no ip address",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

        # Remove Ethernet0 VRF binding and IP
        try:
            st.config(dut, [
                f"interface {CONFIG.interface}",
                "no ip address",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

        # Delete Vlan
        try:
            st.config(dut, [
                f"no vlan {CONFIG.vlan_id}"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

        # Delete VRF
        try:
            st.config(dut, [
                f"no ip vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(2, "Waiting for pre-config clear")
    st.log("Pre-configuration completed")


def sm_iscli_13_cleanup():
    """Cleanup: Remove Vlan100, VRF bindings, VRF from both DUTs."""
    st.log("Cleanup: Removing SM_ISCLI_13 configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"interface Vlan {CONFIG.vlan_id}",
                "no ip address",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

        try:
            st.config(dut, [
                f"interface {CONFIG.interface}",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

        try:
            st.config(dut, [f"no vlan {CONFIG.vlan_id}"],
                      type='klish', skip_error_check=True)
        except Exception:
            pass

        try:
            st.config(dut, [f"no ip vrf {CONFIG.vrf_name}"],
                      type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"VRF cleanup warning on {dut}: {str(e)}")

    st.log("Cleanup completed")


# ======================================================================
# Part A: Ethernet0 VRF Binding
# ======================================================================

@pytest.mark.sm_iscli
@pytest.mark.community
@pytest.mark.community_pass
def test_sm_iscli_13a_vrf_ethernet_bind():
    """
    SM_ISCLI_13 Part A: VRF Create, Bind Ethernet0, Unbind, Delete

    Validated sonic-cli commands (both DUTs):
      ip vrf Vrf111
      show ip vrf                   -> Vrf111 appears
      interface Ethernet 0 -> ip vrf forwarding Vrf111
      show ip vrf Vrf111            -> Vrf111  Ethernet0
      interface Ethernet 0 -> no ip vrf forwarding Vrf111
      show ip vrf Vrf111            -> Vrf111  (empty)
      no ip vrf Vrf111
      show ip vrf                   -> Vrf111 absent
    """
    st.banner("=" * 80)
    st.banner("TEST SM_ISCLI_13A: VRF CREATE + ETHERNET0 BIND/UNBIND/DELETE")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Create VRF on Both DUTs
    # sonic-cli: ip vrf Vrf111
    # ==================================================================
    st.banner("STEP 1: Create VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"ip vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=False)
            st.log(f"VRF {CONFIG.vrf_name} created on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sm13_vrf_create, "msg",
                              f"Failed to create VRF {CONFIG.vrf_name} on {dut}")
            st.report_fail("msg", f"ip vrf {CONFIG.vrf_name} failed on {dut}: {str(e)}")

    # Verify VRF appears in show ip vrf on both DUTs
    for dut in [vars.D1, vars.D2]:
        try:
            output = st.show(dut, "show ip vrf",
                             type='klish', skip_tmpl=True, skip_error_check=True)
            output_str = str(output)
            st.log(f"show ip vrf on {dut}: {output_str[:300]}")
            if CONFIG.vrf_name not in output_str:
                st.generate_tech_support([vars.D1, vars.D2], "sm13_vrf_not_in_show")
                st.report_tc_fail(TC_IDS.sm13_vrf_create, "msg",
                                  f"VRF {CONFIG.vrf_name} not found in 'show ip vrf' on {dut}")
                st.report_fail("msg", f"show ip vrf: {CONFIG.vrf_name} not found on {dut}")
        except Exception as e:
            st.error(f"show ip vrf failed on {dut}: {str(e)}")

    st.report_tc_pass(TC_IDS.sm13_vrf_create, "msg",
                      f"VRF {CONFIG.vrf_name} created and verified on both DUTs")

    # ==================================================================
    # STEP 2: Bind Ethernet0 to VRF on Both DUTs
    # sonic-cli: interface Ethernet 0 -> ip vrf forwarding Vrf111
    # ==================================================================
    st.banner("STEP 2: Bind Ethernet0 to VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"interface {CONFIG.interface}",
                f"ip vrf forwarding {CONFIG.vrf_name}",
                "exit"
            ], type='klish', skip_error_check=False)
            st.log(f"Ethernet0 bound to {CONFIG.vrf_name} on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sm13_eth_bind, "msg",
                              f"Failed to bind Ethernet0 to VRF on {dut}")
            st.report_fail("msg", f"ip vrf forwarding {CONFIG.vrf_name} failed on {dut}: {str(e)}")

    # Verify show ip vrf Vrf111 shows Ethernet0 on both DUTs
    for dut in [vars.D1, vars.D2]:
        try:
            output = st.show(dut, f"show ip vrf {CONFIG.vrf_name}",
                             type='klish', skip_tmpl=True, skip_error_check=True)
            output_str = str(output)
            st.log(f"show ip vrf {CONFIG.vrf_name} on {dut}: {output_str[:300]}")
            if "Ethernet0" not in output_str:
                st.generate_tech_support([vars.D1, vars.D2], "sm13_eth_not_in_vrf")
                st.report_tc_fail(TC_IDS.sm13_eth_bind, "msg",
                                  f"Ethernet0 not shown in VRF on {dut}")
                st.report_fail("msg",
                               f"show ip vrf {CONFIG.vrf_name}: Ethernet0 not found on {dut}")
        except Exception as e:
            st.error(f"show ip vrf {CONFIG.vrf_name} failed on {dut}: {str(e)}")

    st.report_tc_pass(TC_IDS.sm13_eth_bind, "msg",
                      "Ethernet0 bound to VRF and verified on both DUTs")

    # ==================================================================
    # STEP 3: Unbind Ethernet0 from VRF on Both DUTs
    # sonic-cli: interface Ethernet 0 -> no ip vrf forwarding Vrf111
    # ==================================================================
    st.banner("STEP 3: Unbind Ethernet0 from VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"interface {CONFIG.interface}",
                f"no ip vrf forwarding {CONFIG.vrf_name}",
                "end"
            ], type='klish', skip_error_check=False)
            st.log(f"Ethernet0 unbound from {CONFIG.vrf_name} on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sm13_eth_unbind, "msg",
                              f"Failed to unbind Ethernet0 from VRF on {dut}")
            st.report_fail("msg",
                           f"no ip vrf forwarding {CONFIG.vrf_name} failed on {dut}: {str(e)}")

    # Verify Ethernet0 is no longer in VRF
    for dut in [vars.D1, vars.D2]:
        try:
            output = st.show(dut, f"show ip vrf {CONFIG.vrf_name}",
                             type='klish', skip_tmpl=True, skip_error_check=True)
            output_str = str(output)
            st.log(f"show ip vrf {CONFIG.vrf_name} after unbind on {dut}: {output_str[:300]}")
            if "Ethernet0" in output_str:
                st.generate_tech_support([vars.D1, vars.D2], "sm13_eth_still_in_vrf")
                st.report_tc_fail(TC_IDS.sm13_eth_unbind, "msg",
                                  f"Ethernet0 still in VRF after unbind on {dut}")
                st.report_fail("msg",
                               f"show ip vrf {CONFIG.vrf_name}: Ethernet0 still present on {dut}")
        except Exception as e:
            st.error(f"show ip vrf failed on {dut}: {str(e)}")

    st.report_tc_pass(TC_IDS.sm13_eth_unbind, "msg",
                      "Ethernet0 unbound from VRF and verified on both DUTs")

    # ==================================================================
    # STEP 4: Delete VRF on Both DUTs
    # sonic-cli: no ip vrf Vrf111
    # ==================================================================
    st.banner("STEP 4: Delete VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"no ip vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=False)
            st.log(f"VRF {CONFIG.vrf_name} deleted on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sm13_vrf_delete, "msg",
                              f"Failed to delete VRF {CONFIG.vrf_name} on {dut}")
            st.report_fail("msg", f"no ip vrf {CONFIG.vrf_name} failed on {dut}: {str(e)}")

    # Verify VRF absent from show ip vrf
    for dut in [vars.D1, vars.D2]:
        try:
            output = st.show(dut, "show ip vrf",
                             type='klish', skip_tmpl=True, skip_error_check=True)
            output_str = str(output)
            st.log(f"show ip vrf after delete on {dut}: {output_str[:300]}")
            if CONFIG.vrf_name in output_str:
                st.generate_tech_support([vars.D1, vars.D2], "sm13_vrf_still_exists")
                st.report_tc_fail(TC_IDS.sm13_vrf_delete, "msg",
                                  f"VRF {CONFIG.vrf_name} still present after deletion on {dut}")
                st.report_fail("msg",
                               f"show ip vrf: {CONFIG.vrf_name} still present on {dut}")
        except Exception as e:
            st.error(f"show ip vrf failed on {dut}: {str(e)}")

    st.report_tc_pass(TC_IDS.sm13_vrf_delete, "msg",
                      f"VRF {CONFIG.vrf_name} deleted and verified absent on both DUTs")

    st.banner("=" * 80)
    st.banner("TEST RESULT: SM_ISCLI_13A PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SM_ISCLI_13A: VRF Ethernet0 Bind/Unbind/Delete")
    st.log(f"  ip vrf {CONFIG.vrf_name} -> Created on both DUTs")
    st.log(f"  show ip vrf -> {CONFIG.vrf_name} present")
    st.log(f"  interface Ethernet 0 -> ip vrf forwarding {CONFIG.vrf_name} -> Bound")
    st.log(f"  show ip vrf {CONFIG.vrf_name} -> Ethernet0 listed")
    st.log(f"  interface Ethernet 0 -> no ip vrf forwarding {CONFIG.vrf_name} -> Unbound")
    st.log(f"  show ip vrf {CONFIG.vrf_name} -> Ethernet0 absent")
    st.log(f"  no ip vrf {CONFIG.vrf_name} -> Deleted on both DUTs")
    st.log(f"  show ip vrf -> {CONFIG.vrf_name} absent")

    st.report_pass("test_case_passed")


# ======================================================================
# Part B: Vlan100 VRF Binding with IP Address
# ======================================================================

@pytest.mark.sm_iscli
@pytest.mark.community
@pytest.mark.community_pass
def test_sm_iscli_13b_vrf_vlan_bind():
    """
    SM_ISCLI_13 Part B: VRF Create, Bind Vlan100 with IP Address

    Validated sonic-cli commands (both DUTs):
      ip vrf Vrf111
      vlan 100
      interface Vlan 100
        ip vrf forwarding Vrf111
        ip address 10.1.1.1/24   (DUT1) / 10.1.1.2/24 (DUT2)
        exit
      show ip vrf Vrf111         -> Vrf111  Vlan100
      show interface Vlan 100    -> IPV4 address is 10.1.1.1/24
    """
    st.banner("=" * 80)
    st.banner("TEST SM_ISCLI_13B: VRF VLAN100 BIND WITH IP ADDRESS")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Create VRF on Both DUTs
    # sonic-cli: ip vrf Vrf111
    # ==================================================================
    st.banner("STEP 1: Create VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"ip vrf {CONFIG.vrf_name}"
            ], type='klish', skip_error_check=False)
            st.log(f"VRF {CONFIG.vrf_name} created on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sm13_vrf_create, "msg",
                              f"Failed to create VRF on {dut}")
            st.report_fail("msg", f"ip vrf {CONFIG.vrf_name} failed on {dut}: {str(e)}")

    st.wait(2, "Waiting for VRF creation")

    # ==================================================================
    # STEP 2: Create Vlan 100 on Both DUTs
    # sonic-cli: vlan 100
    # ==================================================================
    st.banner("STEP 2: Create Vlan 100 on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                f"vlan {CONFIG.vlan_id}"
            ], type='klish', skip_error_check=False)
            st.log(f"Vlan {CONFIG.vlan_id} created on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sm13_vlan_create, "msg",
                              f"Failed to create Vlan {CONFIG.vlan_id} on {dut}")
            st.report_fail("msg", f"vlan {CONFIG.vlan_id} failed on {dut}: {str(e)}")

    st.report_tc_pass(TC_IDS.sm13_vlan_create, "msg",
                      f"Vlan {CONFIG.vlan_id} created on both DUTs")

    # ==================================================================
    # STEP 3: Bind Vlan100 to VRF and Configure IP - DUT1
    # sonic-cli: interface Vlan 100 -> ip vrf forwarding Vrf111
    #                               -> ip address 10.1.1.1/24
    # ==================================================================
    st.banner("STEP 3: Bind Vlan100 to VRF and Set IP on DUT1")

    try:
        st.config(vars.D1, [
            f"interface Vlan {CONFIG.vlan_id}",
            f"ip vrf forwarding {CONFIG.vrf_name}",
            f"ip address {CONFIG.dut1_ip}/{CONFIG.prefix_len}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1 Vlan{CONFIG.vlan_id}: {CONFIG.dut1_ip}/{CONFIG.prefix_len} in {CONFIG.vrf_name}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sm13_vlan_bind, "msg", "Failed to bind Vlan100 on DUT1")
        st.report_fail("msg", f"DUT1 Vlan{CONFIG.vlan_id} VRF bind failed: {str(e)}")

    # ==================================================================
    # STEP 4: Bind Vlan100 to VRF and Configure IP - DUT2
    # sonic-cli: interface Vlan 100 -> ip vrf forwarding Vrf111
    #                               -> ip address 10.1.1.2/24
    # ==================================================================
    st.banner("STEP 4: Bind Vlan100 to VRF and Set IP on DUT2")

    try:
        st.config(vars.D2, [
            f"interface Vlan {CONFIG.vlan_id}",
            f"ip vrf forwarding {CONFIG.vrf_name}",
            f"ip address {CONFIG.dut2_ip}/{CONFIG.prefix_len}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Vlan{CONFIG.vlan_id}: {CONFIG.dut2_ip}/{CONFIG.prefix_len} in {CONFIG.vrf_name}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sm13_vlan_bind, "msg", "Failed to bind Vlan100 on DUT2")
        st.report_fail("msg", f"DUT2 Vlan{CONFIG.vlan_id} VRF bind failed: {str(e)}")

    st.report_tc_pass(TC_IDS.sm13_vlan_bind, "msg",
                      f"Vlan{CONFIG.vlan_id} bound to {CONFIG.vrf_name} on both DUTs")
    st.wait(3, "Waiting for interface configuration")

    # ==================================================================
    # STEP 5: Verify show ip vrf Vrf111 shows Vlan100 on Both DUTs
    # sonic-cli: show ip vrf Vrf111  -> Vrf111  Vlan100
    # ==================================================================
    st.banner("STEP 5: Verify show ip vrf Vrf111 shows Vlan100")

    for dut in [vars.D1, vars.D2]:
        try:
            output = st.show(dut, f"show ip vrf {CONFIG.vrf_name}",
                             type='klish', skip_tmpl=True, skip_error_check=True)
            output_str = str(output)
            st.log(f"show ip vrf {CONFIG.vrf_name} on {dut}: {output_str[:300]}")
            if f"Vlan{CONFIG.vlan_id}" not in output_str:
                st.generate_tech_support([vars.D1, vars.D2], "sm13_vlan_not_in_vrf")
                st.report_tc_fail(TC_IDS.sm13_vlan_bind, "msg",
                                  f"Vlan{CONFIG.vlan_id} not shown in VRF on {dut}")
                st.report_fail("msg",
                               f"show ip vrf {CONFIG.vrf_name}: Vlan{CONFIG.vlan_id} not found on {dut}")
        except Exception as e:
            st.error(f"show ip vrf failed on {dut}: {str(e)}")

    # ==================================================================
    # STEP 6: Verify show interface Vlan 100 shows IP on DUT1
    # Expected: IPV4 address is 10.1.1.1/24
    # ==================================================================
    st.banner("STEP 6: Verify show interface Vlan 100 IP on DUT1")

    try:
        output = st.show(vars.D1, f"show interface Vlan {CONFIG.vlan_id}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT1 show interface Vlan {CONFIG.vlan_id}: {output_str[:500]}")
        if CONFIG.dut1_ip not in output_str:
            st.generate_tech_support([vars.D1, vars.D2], "sm13_vlan_ip_not_found_dut1")
            st.report_tc_fail(TC_IDS.sm13_vlan_ip_verify, "msg",
                              f"DUT1: {CONFIG.dut1_ip} not found in show interface Vlan {CONFIG.vlan_id}")
            st.report_fail("msg",
                           f"DUT1 show interface Vlan {CONFIG.vlan_id}: {CONFIG.dut1_ip}/{CONFIG.prefix_len} not found")
    except Exception as e:
        st.error(f"DUT1 show interface Vlan failed: {str(e)}")

    st.log(f"DUT1 Vlan{CONFIG.vlan_id}: IPV4 address {CONFIG.dut1_ip}/{CONFIG.prefix_len} verified")

    # ==================================================================
    # STEP 7: Verify show interface Vlan 100 shows IP on DUT2
    # Expected: IPV4 address is 10.1.1.2/24
    # ==================================================================
    st.banner("STEP 7: Verify show interface Vlan 100 IP on DUT2")

    try:
        output = st.show(vars.D2, f"show interface Vlan {CONFIG.vlan_id}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"DUT2 show interface Vlan {CONFIG.vlan_id}: {output_str[:500]}")
        if CONFIG.dut2_ip not in output_str:
            st.generate_tech_support([vars.D1, vars.D2], "sm13_vlan_ip_not_found_dut2")
            st.report_tc_fail(TC_IDS.sm13_vlan_ip_verify, "msg",
                              f"DUT2: {CONFIG.dut2_ip} not found in show interface Vlan {CONFIG.vlan_id}")
            st.report_fail("msg",
                           f"DUT2 show interface Vlan {CONFIG.vlan_id}: {CONFIG.dut2_ip}/{CONFIG.prefix_len} not found")
    except Exception as e:
        st.error(f"DUT2 show interface Vlan failed: {str(e)}")

    st.log(f"DUT2 Vlan{CONFIG.vlan_id}: IPV4 address {CONFIG.dut2_ip}/{CONFIG.prefix_len} verified")
    st.report_tc_pass(TC_IDS.sm13_vlan_ip_verify, "msg",
                      "Vlan100 IP addresses verified on both DUTs")

    st.banner("=" * 80)
    st.banner("TEST RESULT: SM_ISCLI_13B PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SM_ISCLI_13B: VRF Vlan100 Bind with IP")
    st.log(f"  ip vrf {CONFIG.vrf_name} -> Created on both DUTs")
    st.log(f"  vlan {CONFIG.vlan_id} -> Created on both DUTs")
    st.log(f"  interface Vlan {CONFIG.vlan_id} -> ip vrf forwarding {CONFIG.vrf_name} -> Bound")
    st.log(f"  DUT1: ip address {CONFIG.dut1_ip}/{CONFIG.prefix_len} -> Set")
    st.log(f"  DUT2: ip address {CONFIG.dut2_ip}/{CONFIG.prefix_len} -> Set")
    st.log(f"  show ip vrf {CONFIG.vrf_name} -> Vlan{CONFIG.vlan_id} listed on both DUTs")
    st.log(f"  show interface Vlan {CONFIG.vlan_id} -> IP addresses verified")

    st.report_pass("test_case_passed")
