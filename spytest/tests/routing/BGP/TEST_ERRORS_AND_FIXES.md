# Test Script Errors Found and Fixes

## File: test_bgp_med_path_selection.py

### Error 1: RouteMap API Method Names (Lines 405, 423)
**Location:** `_configure_route_map()` and `_remove_route_map()`

**Issue:**
```python
# Line 405 - WRONG
rmap.execute_route_map(dut, cli_type=self.data.cli_type)

# Line 423 - WRONG
rmap.unconfig_route_map(dut, cli_type=self.data.cli_type)
```

**Fix:**
```python
# Line 405 - CORRECT
rmap.execute_command(dut, config='yes', cli_type=self.data.cli_type)

# Line 423 - CORRECT
rmap.execute_command(dut, config='no', cli_type=self.data.cli_type)
```

**Reason:** The RouteMap class uses `execute_command(dut, config='yes'/'no', **kwargs)` not `execute_route_map()` or `unconfig_route_map()`.

---

### Error 2: Missing route_map_dir Parameter (Line 484)
**Location:** `_apply_neighbor_route_map()`

**Issue:**
```python
# Line 484-491 - Missing route_map_dir parameter
bgp_api.config_bgp_neighbor_properties(
    dut,
    local_asn=as_number,
    neighbor_ip=neighbor_ip,
    family=family,
    mode="unicast",
    route_map_name=route_map,  # WRONG parameter name
    route_map_direction=direction,  # WRONG parameter name
    cli_type=self.data.cli_type
)
```

**Fix:**
```python
# CORRECT
bgp_api.config_bgp_neighbor_properties(
    dut,
    local_asn=as_number,
    neighbor_ip=neighbor_ip,
    family=family,
    mode="unicast",
    route_map=route_map,        # CORRECT
    route_map_dir=direction,    # CORRECT
    cli_type=self.data.cli_type
)
```

**Reason:** The API uses `route_map` and `route_map_dir` as parameter names, not `route_map_name` and `route_map_direction`.

---

### Error 3: Missing import statement
**Location:** Top of file

**Issue:**
Missing import for `umf_ni` module used in BGP APIs

**Status:** This is actually not an error in our test - the BGP API internally uses umf_ni, we don't need to import it.

---

### Error 4: st.show() Usage (Lines 528, 533, 549, 554)
**Location:** `_verify_bgp_route_med()` and `_get_bgp_best_path()`

**Issue:**
```python
# Lines 528, 533 - May not return parseable output
output = st.show(
    dut, f"show ip bgp {prefix}",
    cli_type=self.data.show_cli_type
)
```

**Potential Issue:**
The `st.show()` function returns output but may not be structured. Better to use specific BGP API functions that parse output.

**Better Approach:**
Use `bgp_api.show_bgp_ipv4_neighbor_vtysh()` or similar functions that return parsed data.

---

## Summary of Required Fixes

1. **Critical:** Fix RouteMap API calls (2 instances)
   - Line 405: `execute_command(dut, config='yes', ...)`
   - Line 423: `execute_command(dut, config='no', ...)`

2. **Critical:** Fix neighbor route-map parameter names (Line 484-491)
   - `route_map_name` → `route_map`
   - `route_map_direction` → `route_map_dir`

3. **Enhancement:** Consider using structured BGP show commands instead of raw st.show()

## Additional Notes

- The test uses simplified verification methods that parse raw CLI output
- For production tests, should use structured JSON output parsing
- Consider adding retry logic for BGP convergence verification
- May need to add BGP session flap detection and handling
