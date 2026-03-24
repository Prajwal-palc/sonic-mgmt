# ARP Manual Test Case 09 - Interface Flap

## Test Information

| Field | Value |
|-------|-------|
| **Test ID** | ARP-FLAP-01 |
| **Feature** | ARP (Address Resolution Protocol) |
| **Test Case** | Verify ARP behavior during Interface Flap |
| **Test Item** | Functional |
| **Test Objective** | Validate that dynamic ARP entries are cleared when interface goes down and re-learned when interface comes back up |
| **Expected Result** | Dynamic ARP entries are removed on interface shutdown; Entries are re-learned on interface no-shutdown |

## Test Topology

- **Device Under Test (DUT):** SONiC Switch
- **Peer Device:** Connected device on VLAN 100
- **IP Configuration:**
  - DUT VLAN 100 IP: 10.1.1.1/24
  - Peer Device IP: 10.1.1.2

## Pre-requisites

1. VLAN 100 configured on DUT
2. IP address assigned to VLAN 100 interface
3. Interface up and operational
4. Connectivity established with peer device

## Test Steps

### Step 1: Configure VLAN and IP Address

```bash
sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(config-if-Vlan100)# ip address 10.1.1.1/24
sonic(config-if-Vlan100)# exit
sonic(config)# exit
```

**Verification:**
```bash
sonic# show ip interface brief
```

**Expected Output:**
```
Interface    IP Address/Mask      Admin/Oper
------------ -------------------- -----------
Vlan100      10.1.1.1/24          up/up
```

### Step 2: Generate Dynamic ARP Entry (via Traffic)

#### Send Ping to Trigger ARP Learning
```bash
sonic# ping 10.1.1.2 -c 3
```

**Expected Output:**
```
PING 10.1.1.2 (10.1.1.2): 56 data bytes
64 bytes from 10.1.1.2: icmp_seq=0 ttl=64 time=1.5 ms
64 bytes from 10.1.1.2: icmp_seq=1 ttl=64 time=0.8 ms
64 bytes from 10.1.1.2: icmp_seq=2 ttl=64 time=0.9 ms

--- 10.1.1.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss
```

### Step 3: Verify Dynamic ARP Entry Before Interface Flap

```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
192.168.100.1            7c:5a:1c:b1:f2:f6  Management0       -                   Dynamic            Fwd
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Dynamic            Fwd
```

**Observation:**
- ARP entry for 10.1.1.2 is present
- **Type is "Dynamic"** (learned from traffic)
- State is "Fwd"

### Step 4: Shutdown VLAN 100 Interface

```bash
sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(config-if-Vlan100)# shutdown
sonic(config-if-Vlan100)# exit
sonic(config)# exit
```

**Verification - Interface Status:**
```bash
sonic# show ip interface brief
```

**Expected Output:**
```
Interface    IP Address/Mask      Admin/Oper
------------ -------------------- -----------
Vlan100      10.1.1.1/24          down/down
```

**Observation:** Interface is administratively down

### Step 5: Verify Dynamic ARP Entry Cleared After Shutdown

```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
192.168.100.1            7c:5a:1c:b1:f2:f6  Management0       -                   Dynamic            Fwd
```

**Observation:**
- ARP entry for 10.1.1.2 **REMOVED** (dynamic entry cleared on interface down)
- Only Management0 ARP entry remains (unaffected)
- ✓ **CRITICAL VALIDATION:** Dynamic ARP entries are flushed when interface goes down

### Step 6: Bring Interface Back Up (No-Shutdown)

```bash
sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(config-if-Vlan100)# no shutdown
sonic(config-if-Vlan100)# exit
sonic(config)# exit
```

**Verification - Interface Status:**
```bash
sonic# show ip interface brief
```

**Expected Output:**
```
Interface    IP Address/Mask      Admin/Oper
------------ -------------------- -----------
Vlan100      10.1.1.1/24          up/up
```

**Observation:** Interface is back up

### Step 7: Verify ARP Entry Still Absent (Before Re-Learning)

```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
192.168.100.1            7c:5a:1c:b1:f2:f6  Management0       -                   Dynamic            Fwd
```

**Observation:**
- ARP entry for 10.1.1.2 still absent
- Entry is not automatically restored (requires re-learning)

### Step 8: Generate Traffic to Trigger ARP Re-Learning

```bash
sonic# ping 10.1.1.2 -c 3
```

**Expected Output:**
```
PING 10.1.1.2 (10.1.1.2): 56 data bytes
64 bytes from 10.1.1.2: icmp_seq=0 ttl=64 time=1.8 ms
64 bytes from 10.1.1.2: icmp_seq=1 ttl=64 time=0.9 ms
64 bytes from 10.1.1.2: icmp_seq=2 ttl=64 time=0.8 ms

--- 10.1.1.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss
```

**Observation:** Connectivity restored

### Step 9: Verify Dynamic ARP Entry Re-Learned

```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
192.168.100.1            7c:5a:1c:b1:f2:f6  Management0       -                   Dynamic            Fwd
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Dynamic            Fwd
```

**Observation:**
- ARP entry for 10.1.1.2 **RE-LEARNED** (dynamic entry restored)
- Same MAC address as before (22:58:e5:4d:e2:7d)
- **Type is "Dynamic"** (re-learned from traffic)
- State is "Fwd"
- ✓ **CRITICAL VALIDATION:** Dynamic ARP re-learning works after interface comes back up

### Step 10: Test Summary - State Transitions

| Step | Interface State | Ping Sent | ARP Entry (10.1.1.2) | Type    | Result |
|------|----------------|-----------|----------------------|---------|--------|
| 3    | up/up          | Yes       | Present              | Dynamic | ✓ Initial learning |
| 5    | down/down      | No        | **ABSENT**           | N/A     | ✓ Cleared on shutdown |
| 6    | up/up          | No        | **ABSENT**           | N/A     | ✓ Not auto-restored |
| 9    | up/up          | Yes       | Present              | Dynamic | ✓ Re-learned |

### Step 11: Additional Test - Static ARP Persistence (Comparison)

To demonstrate the difference between static and dynamic ARP behavior during interface flap:

#### Configure Static ARP Entry
```bash
sonic# configure terminal
sonic(config)# arp 10.1.1.3 aa:bb:cc:dd:ee:ff Vlan100
sonic(config)# exit
```

#### Verify Both Static and Dynamic Entries
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Dynamic            Fwd
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Static             Fwd
```

#### Shutdown Interface Again
```bash
sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(config-if-Vlan100)# shutdown
sonic(config-if-Vlan100)# exit
sonic(config)# exit
```

#### Check ARP Table After Shutdown
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Static             Fwd
```

**Observation:**
- Dynamic entry (10.1.1.2) **REMOVED** on shutdown
- Static entry (10.1.1.3) **PERSISTS** (not affected by interface state)
- ✓ Confirms static entries are configuration-based, not interface-state-dependent

#### Cleanup Static Entry
```bash
sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(config-if-Vlan100)# no shutdown
sonic(config-if-Vlan100)# exit
sonic(config)# no arp 10.1.1.3 Vlan100
sonic(config)# exit
```

## Expected Results

1. **Dynamic ARP Clearing on Interface Down:**
   - All dynamic ARP entries on Vlan100 are removed when interface is shut down
   - Other interfaces' ARP entries remain unaffected

2. **No Auto-Restoration:**
   - ARP entries are not automatically restored when interface comes back up
   - Entries remain absent until new traffic triggers re-learning

3. **Dynamic ARP Re-Learning:**
   - ARP re-learning occurs when traffic is sent after interface comes up
   - Re-learned entries have Type="Dynamic"
   - Same MAC address is learned (if peer hasn't changed)

4. **Static vs Dynamic Behavior:**
   - Static ARP entries persist during interface flap (configuration-based)
   - Dynamic ARP entries are cleared on shutdown (interface-state-dependent)

## Actual Result

**Test Status:** PASS ✓

- Dynamic ARP entries cleared on interface shutdown ✓
- Entries not auto-restored on interface no-shutdown ✓
- ARP re-learning successful after sending traffic ✓
- Static entries persist during flap (as expected) ✓
- Interface flap handling works correctly ✓

## Notes

- **Dynamic ARP entries are interface-state-dependent:** They are flushed when the interface goes operationally down
- **Static ARP entries are configuration-based:** They persist regardless of interface state
- **ARP re-learning requires traffic:** Entries won't reappear until ARP request/reply is triggered
- **Graceful handling:** System cleanly removes stale entries to prevent blackhole scenarios

## Use Cases

This test validates critical behavior for:
- **Maintenance scenarios:** Interface shutdowns should clear stale entries
- **Link flap events:** Brief outages trigger ARP cleanup and re-learning
- **High availability:** Fast convergence through ARP re-learning after recovery
- **Static vs Dynamic:** Different persistence models for different use cases

## Post-conditions / Cleanup

- Remove any static ARP entries used for testing
- Ensure interface is in no-shutdown state
- Restore baseline configuration
- Confirm ARP table is clean
- Collect logs if any anomaly observed
