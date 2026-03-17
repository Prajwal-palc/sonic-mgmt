# SPyTest Traffic API Implementation Guide

**Reference**: Implementation in `test_l3_acl_basic.py`

This document describes the SPyTest Traffic API patterns used in the L3 ACL test automation.

---

## Overview

The test script implements a complete traffic generation and validation workflow using SPyTest's Traffic API abstraction layer. This provides:

- **Portability**: Works with Scapy, IxNetwork, Spirent via unified API
- **Reliability**: Proven golden sequence prevents race conditions
- **Clarity**: Non-blocking operations with explicit state management
- **Debugging**: Comprehensive logging at each step

---

## Core Method: `_run_traffic_test()`

### Golden Sequence

The method implements the proven 7-step sequence for safe traffic testing:

```python
def _run_traffic_test(self, traffic_config: Mapping[str, Any]) -> tuple[int, int]:
    """
    Golden Sequence:
    1. Config stream   → Configure traffic parameters
    2. Clear stats     → Reset counters on both TX/RX ports
    3. Run traffic     → Start non-blocking transmission
    4. Wait            → Allow time for transmission
    5. Stop traffic    → Stop before reading stats (CRITICAL!)
    6. Drain           → Wait for packets in flight
    7. Read stats      → Collect final statistics
    """
```

### Step 1: Stream Configuration

```python
stream_config = {
    "port_handle": tg_ph_1,                # TX port
    "mode": "create",                      # New stream
    "transmit_mode": "single_burst",       # Send once, not continuous
    "pkts_per_burst": num_pkts,            # Configurable (10 for L3-01)
    "burst_loop_count": 1,                 # Single shot
    "rate_pps": 1000,                      # 1000 packets per second
    "frame_size": 64,                      # L3 ICMP echo size
    "l2_encap": "ethernet_ii",             # Standard Ethernet
    "mac_src": src_mac,                    # TX host MAC
    "mac_dst": dst_mac,                    # RX host MAC
    "l3_protocol": "ipv4",                 # IPv4 only
    "ip_src_addr": src_ip,                 # Source IP (varies by test)
    "ip_dst_addr": dst_ip,                 # Destination IP (20.0.0.2)
    "l4_protocol": "icmp",                 # ICMP ping
    "icmp_type": 8,                        # Echo request
}

stream_handle = tg.tg_traffic_config(**stream_config)
stream_id = stream_handle.get("stream_id")
```

**Key Points**:
- `mode="create"` creates new stream (not "modify" or "append")
- `transmit_mode="single_burst"` = send N packets once (not continuous)
- Frame size 64 bytes is standard for ICMP echo (54 payload + 20 IP header)
- All parameters come from YAML (traffic_config dict)

### Step 2: Clear Statistics (CRITICAL!)

```python
tg.tg_traffic_control(action="clear_stats", port_handle=[tg_ph_1, tg_ph_2])
```

**Why This Matters**:
- Without clearing, you read leftover stats from previous tests
- Can cause false passes (seeing old RX from previous test as current result)
- Always clear BEFORE running traffic
- Clear both TX and RX ports

### Step 3: Start Traffic (Non-blocking)

```python
tg.tg_traffic_control(action="run", handle=stream_id)
```

**Non-blocking Execution**:
- Returns immediately (doesn't wait for transmission)
- Allows Python code to continue while traffic flows
- Different from blocking "transmit" which waits

### Step 4: Wait for Transmission

```python
pkt_tx_time_ms = max(500, num_pkts * inter_delay // 10)
st.wait(pkt_tx_time_ms // 1000 + 2)
```

**Calculation Logic**:
- For 10 packets at 1000 pps = 10 ms transmission time
- Add buffer for network latencies (usually 50-500 ms for L3 routing)
- Default 2 second wait covers most scenarios

### Step 5: Stop Traffic (CRITICAL!)

```python
tg.tg_traffic_control(action="stop", handle=stream_id)
```

**Why Before Stats**:
- Stats may not be final while traffic is still flowing
- Some implementations lock stats until stop is called
- MUST stop before reading stats (Step 7)

### Step 6: Drain (Wait for Packets in Flight)

```python
st.wait(2)  # 2 second drain
```

**Purpose**:
- Network packets may still be in transit after stop
- Buffers in DUT, switches, or receiving side may not be flushed
- 2 seconds allows all in-flight packets to complete

### Step 7: Read Statistics

```python
tx_stats = tg.tg_traffic_stats(port_handle=tg_ph_1, mode="aggregate")
rx_stats = tg.tg_traffic_stats(port_handle=tg_ph_2, mode="aggregate")

# Extract counts (may be returned as strings)
tx_pkts = int(tx_stats.get(tg_ph_1, {}).get("aggregate", {}).get("tx", {}).get("total_pkts", 0))
rx_pkts = int(rx_stats.get(tg_ph_2, {}).get("aggregate", {}).get("rx", {}).get("total_pkts", 0))

return tx_pkts, rx_pkts
```

**Stats Dictionary Structure**:
```python
{
    "1/1": {                           # Port handle
        "aggregate": {
            "tx": {
                "total_pkts": "10",    # Note: returned as STRING
                "total_bytes": "640"
            },
            "rx": {
                "total_pkts": "0",     # Dropped by ACL
                "total_bytes": "0"
            }
        }
    }
}
```

**Important Notes**:
- Stats values are often returned as strings → cast to int()
- Use `.get()` with defaults to handle missing keys safely
- "aggregate" mode sums all traffic (vs per-port mode)

---

## Verification Method: `_verify_traffic_loss()`

### Silent Pass Prevention Guards

The method implements 3 independent guards against false passes:

#### Guard 1: TX > 0 (Stream Ran)

```python
if tx_count <= 0:
    st.error(f"Guard 1 failed: No packets transmitted (TX={tx_count})")
    st.report_fail("msg", f"Traffic stream did not run for {test_id}")
    return False
st.log(f"[GUARD 1] ✓ TX > 0: {tx_count} packets transmitted")
```

**What It Catches**:
- Broken traffic generators
- Failed stream startup
- Configuration errors that prevent TX
- Network cable disconnections

**Failure Scenario**: Test would pass if we didn't check (thinking "no RX is correct"), but actually the test never ran.

#### Guard 2: RX == Expected (Exact Match)

```python
if rx_count != expected_rx:
    st.error(f"Guard 2 failed: RX mismatch (expected={expected_rx}, actual={rx_count})")
    st.report_fail("msg", f"Unexpected RX count for {test_id}: expected {expected_rx}, got {rx_count}")
    return False
st.log(f"[GUARD 2] ✓ RX == Expected: {rx_count} == {expected_rx}")
```

**What It Catches**:
- Partial packet loss vs complete denial
- ACL rule not matching correctly
- Unexpected permit/deny behavior
- Example: L3-01 expects RX=0 (all denied), getting RX=5 means rule isn't working

#### Guard 3: Loss % Verification

```python
loss_pct = 100.0 * (tx_count - rx_count) / tx_count if tx_count > 0 else 0
if abs(loss_pct - expected_loss_pct) > 1.0:  # Allow 1% tolerance
    st.error(f"Guard 3 failed: Loss % mismatch (expected≈{expected_loss_pct}%, actual={loss_pct}%)")
    st.report_fail("msg", f"Unexpected packet loss for {test_id}: expected {expected_loss_pct}%, got {loss_pct}%")
    return False
st.log(f"[GUARD 3] ✓ Loss % verified: {loss_pct:.1f}% ≈ {expected_loss_pct}%")
```

**What It Catches**:
- Rounding errors
- Statistically inconsistent behavior
- Flaky tests (sometimes 95%, sometimes 5% loss)
- Example: If we expect 100% loss but see 95%, something's wrong

**Tolerance**: 1% allows for normal statistical variation

### Why All 3 Guards?

| Test Result | Guard 1 | Guard 2 | Guard 3 | Outcome |
|-------------|---------|---------|---------|---------|
| Traffic didn't run | ✗ | (no data) | (no data) | **FAIL** (silently passed without guard 1) |
| Got 5 of 10 (want 0) | ✓ | ✗ | ✓ | **FAIL** (silently passed without guard 2) |
| Got 100% loss sometimes | ✓ | ✓ | ✗ | **FAIL** (flaky, silently passed without guard 3) |
| Perfect: got 10 TX, 0 RX | ✓ | ✓ | ✓ | **PASS** |

---

## Configuration Parameters (from YAML)

### Per-Test Customization

**L3-01: Deny Host IP**
```yaml
source_ip: "10.0.0.99"      # Exactly matches DENY rule
dest_ip: "20.0.0.2"          # Normal RX host
expected_rx: 0               # All denied
expected_loss_pct: 100
```

**L3-02: Deny Subnet**
```yaml
source_ip: "10.0.0.50"       # Within 10.0.0.0/24 (denied)
dest_ip: "20.0.0.2"
expected_rx: 0
expected_loss_pct: 100
```

**L3-03: Deny Dest IP**
```yaml
source_ip: "10.0.0.1"        # Normal TX host
dest_ip: "20.0.0.99"         # Matches DENY rule (not RX host)
expected_rx: 0
expected_loss_pct: 100
```

**L3-BASELINE: No ACL**
```yaml
source_ip: "10.0.0.1"        # Normal TX host
dest_ip: "20.0.0.2"          # Normal RX host
expected_rx: 10              # All forwarded
expected_loss_pct: 0
```

### Global Parameters
```yaml
defaults:
  traffic:
    num_packets: 10
    inter_packet_delay_ms: 100
    rx_timeout_sec: 4
    pass_criteria_permit: 0.9    # >= 90% for PERMIT
    pass_criteria_deny: 0.0      # == 0% for DENY
```

---

## Error Handling Patterns

### Graceful Degradation

```python
try:
    stream_handle = tg.tg_traffic_config(**stream_config)
    stream_id = stream_handle.get("stream_id")
    st.log(f"[TRAFFIC] Stream created: {stream_id}")
except Exception as e:
    st.error(f"Failed to create traffic stream: {e}")
    return 0, 0  # Return zeros, test will fail on Guard 1
```

**Pattern**:
- Catch exceptions and log clearly
- Return sensible defaults (0, 0)
- Let guards catch the failure (Guard 1: TX not > 0)

### Validation Approach

```python
if not tg:
    st.error("No traffic generator available")
    return 0, 0

if not tg_ph_1 or not tg_ph_2:
    st.error("Failed to get TGen port handles")
    return 0, 0
```

**Benefits**:
- Early exit with clear error
- Prevents cryptic errors later
- Guards will catch the failure

---

## Logging Hierarchy

### Test Flow Logging

```python
st.banner("TEST L3-01: Deny Source IP (Host)")     # Visual separator
st.log("[STEP 1] Configuring ACL rule on DUT")     # High-level steps
st.log(f"[TRAFFIC] Configuring stream: SRC={src_ip} DST={dst_ip}")  # Details
st.log(f"[STATS] TX: {tx_pkts} packets, RX: {rx_pkts} packets")  # Results
st.log(f"[GUARD 1] ✓ TX > 0: {tx_count} packets transmitted")  # Verification
st.log(f"[RESULT] ✓ L3-01 PASSED: ACL correctly denied...")  # Conclusion
```

**Log Tags**:
- `[STEP N]` - Major test phases
- `[TRAFFIC]` - Traffic generation details
- `[STATS]` - Statistics collection
- `[GUARD N]` - Silent pass prevention verification
- `[RESULT]` - Final outcome

---

## Troubleshooting Common Issues

### Issue: Guard 1 Failed (TX = 0)

**Causes**:
- Traffic generator not connected
- Stream configuration invalid
- Port handles incorrect
- Traffic disabled or rate set to 0

**Debug Steps**:
1. Verify TGen connectivity: `st.show(dut, "show interfaces status")`
2. Check port handles: Add `st.log(f"TX port: {tg_ph_1}, RX port: {tg_ph_2}")`
3. Verify stream creation succeeded
4. Check rate isn't 0: `"rate_pps": 1000`

### Issue: Guard 2 Failed (RX != expected)

**Causes**:
- ACL rule not configured correctly
- ACL not applied to correct port
- Routing issue (packets not reaching RX)
- RX host down or disconnected

**Debug Steps**:
1. Verify ACL exists: `st.show(dut, "show acl L3_ACL_L3_01")`
2. Check rule hit counters: `st.show(dut, "show acl statistics")`
3. Verify routing: `st.show(dut, "show ip route")`
4. Test RX connectivity separately: baseline test

### Issue: Guard 3 Failed (Loss % unexpected)

**Causes**:
- Flaky ACL behavior
- Intermittent network issues
- Test race conditions
- Timing issues with packet arrival

**Debug Steps**:
1. Increase wait time: Change `st.wait(2)` to `st.wait(3)`
2. Reduce packet rate to verify: `"rate_pps": 100`
3. Run test multiple times to check consistency
4. Increase tolerance temporarily for debugging

---

## Performance Considerations

### Traffic Rate Selection

```python
"rate_pps": 1000              # 1000 packets/second
```

**Why 1000 pps**:
- Fast enough to complete 10 packets in 10 ms
- Slow enough for L3 processing (no bottlenecking at wire speed)
- Works on all platforms (VM, physical, etc.)

**For Different Scenarios**:
- Stress testing: 100,000 pps
- Wire speed: 1,000,000+ pps
- ACL stress: 10,000 pps
- Normal validation: 1,000 pps (current)

### Packet Count Rationale

```python
"pkts_per_burst": 10          # 10 packets per test
```

**Why 10 packets**:
- Large enough for statistical significance
- Small enough to complete quickly (10-100 ms)
- Standard test size for deterministic behavior
- Allows for 1-2 packet variance without failing

---

## Advanced Topics

### Continuous Traffic (Not Currently Used)

```python
# For long-running tests:
stream_config["transmit_mode"] = "continuous"
stream_config["burst_loop_count"] = 0  # Infinite

tg.tg_traffic_control(action="run", handle=stream_id)
st.wait(10)  # Let run for 10 seconds
tg.tg_traffic_control(action="stop", handle=stream_id)
```

### Per-Port Statistics

```python
# Instead of aggregate, get per-priority stats:
stats = tg.tg_traffic_stats(port_handle=tg_ph_1, mode="streams")
# Returns individual stats for each stream
```

### Bidirectional Traffic

```python
# Create stream in both directions:
handle_1 = tg.tg_traffic_config(port_handle=tg_ph_1, ...)  # TX→RX
handle_2 = tg.tg_traffic_config(port_handle=tg_ph_2, ...)  # RX→TX (reverse)

tg.tg_traffic_control(action="run", handle=[handle_1, handle_2])
```

---

## Summary

The L3 ACL test implementation demonstrates:

1. **Proven Patterns**: Golden sequence prevents race conditions
2. **Defensive Testing**: Triple guards prevent silent passes
3. **Flexibility**: YAML-driven parameters for easy customization
4. **Portability**: SPyTest API works across TGen backends
5. **Clarity**: Comprehensive logging for debugging
6. **Reliability**: Graceful error handling and cleanup

This approach scales to more complex test scenarios (IPv6, BGP, MPLS, QoS) with the same patterns.

