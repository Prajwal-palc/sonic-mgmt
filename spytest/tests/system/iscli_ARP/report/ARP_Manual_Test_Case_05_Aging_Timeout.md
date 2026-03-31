# ARP Manual Test Case 05 - Aging Timeout

## Test Information

| Field | Value |
|-------|-------|
| **Test ID** | ARP-AGING-01 |
| **Feature** | ARP (Address Resolution Protocol) |
| **Test Case** | Verify ARP Aging Timeout |
| **Test Item** | Functional |
| **Test Objective** | Validate that dynamic ARP entries age out after the configured timeout period while static ARP entries persist indefinitely |
| **Expected Result** | Dynamic ARP entries are removed after aging timeout expires; Static ARP entries remain in the table indefinitely |

## Test Topology

- **Device Under Test (DUT):** SONiC Switch
- **Peer Device:** Connected device on VLAN 100
- **IP Configuration:**
  - DUT VLAN 100 IP: 10.1.1.1/24
  - Peer Device IP: 10.1.1.2

## Pre-requisites

1. VLAN 100 configured on DUT
2. IP address assigned to VLAN 100 interface
3. Connectivity established with peer device
4. Default ARP aging timeout: 60 seconds

## Test Steps

### Step 1: Configure VLAN and IP Address

```bash
sonic# configure terminal
sonic(config)# interface Vlan 100
sonic(config-if-Vlan100)# ip address 10.1.1.1/24
sonic(config-if-Vlan100)# exit
sonic(config)# exit
```

### Step 2: Configure Static ARP Entry

```bash
sonic# configure terminal
sonic(config)# arp 10.1.1.2 22:58:e5:4d:e2:7d Vlan100
sonic(config)# exit
```

**Verification:**
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
```

### Step 3: Generate Dynamic ARP Entry

```bash
sonic# ping 10.1.1.3 -c 3
```

**Verification:**
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Dynamic            Fwd
```

### Step 4: Monitor ARP Entries Over Aging Period

**Configure monitoring interval:** 60 seconds timeout, check every 15 seconds

#### T=0 seconds (Initial State)
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Dynamic            Fwd
```

**Observation:** Both static and dynamic entries present

---

#### T=15 seconds
```bash
# Wait 15 seconds
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Dynamic            Fwd
```

**Observation:** Both entries still present (within timeout)

---

#### T=30 seconds
```bash
# Wait 15 more seconds (total 30 seconds elapsed)
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Dynamic            Fwd
```

**Observation:** Both entries still present (within timeout)

---

#### T=45 seconds
```bash
# Wait 15 more seconds (total 45 seconds elapsed)
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
10.1.1.3                 aa:bb:cc:dd:ee:ff  Vlan100           -                   Dynamic            Fwd
```

**Observation:** Both entries still present (approaching timeout)

---

#### T=60 seconds (Timeout Reached)
```bash
# Wait 15 more seconds (total 60 seconds elapsed)
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
```

**Observation:** Dynamic entry (10.1.1.3) **aged out and removed**, Static entry (10.1.1.2) **persists**

---

#### T=90 seconds (Post-Timeout Verification)
```bash
# Wait 30 more seconds (total 90 seconds elapsed)
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 22:58:e5:4d:e2:7d  Vlan100           -                   Static             Fwd
```

**Observation:** Static entry **still present**, confirming static entries do not age out

---

### Step 5: Verification Summary

| Time | Static ARP (10.1.1.2) | Dynamic ARP (10.1.1.3) | Result |
|------|----------------------|------------------------|--------|
| T=0  | Present (Static)     | Present (Dynamic)      | ✓ Both present |
| T=15 | Present (Static)     | Present (Dynamic)      | ✓ Both present |
| T=30 | Present (Static)     | Present (Dynamic)      | ✓ Both present |
| T=45 | Present (Static)     | Present (Dynamic)      | ✓ Both present |
| T=60 | Present (Static)     | **REMOVED**            | ✓ Dynamic aged out |
| T=90 | Present (Static)     | **REMOVED**            | ✓ Static persists |

### Step 6: Cleanup

```bash
sonic# configure terminal
sonic(config)# no arp 10.1.1.2 Vlan100
sonic(config)# exit
```

## Expected Results

1. **Dynamic ARP Entry Aging:**
   - Dynamic ARP entry (10.1.1.3) is present immediately after ping
   - Entry persists for up to 60 seconds (aging timeout)
   - Entry is **automatically removed** after 60-second timeout expires
   - Type remains "Dynamic" throughout its lifetime

2. **Static ARP Entry Persistence:**
   - Static ARP entry (10.1.1.2) remains in table indefinitely
   - Entry persists beyond 60-second timeout (verified at T=90)
   - Type remains "Static" throughout monitoring period
   - Entry is not affected by aging timer

3. **Timeout Behavior:**
   - Aging timeout operates correctly (60 seconds)
   - Only dynamic entries are aged out
   - Static entries immune to aging

## Actual Result

**Test Status:** PASS ✓

- Dynamic ARP entry aged out after 60 seconds as expected
- Static ARP entry persisted beyond timeout period
- Aging timeout mechanism working correctly
- Type field remained accurate throughout test

## Notes

- Default ARP aging timeout in SONiC: 60 seconds
- Aging timeout is configurable via `ip arp timeout <seconds>` command
- Only dynamic ARP entries are subject to aging
- Static ARP entries require manual removal via `no arp` command
- Monitoring intervals should be frequent enough to catch aging boundary (recommended: timeout/4)

## Post-conditions / Cleanup

- Remove static ARP entry
- Restore default configuration
- Confirm ARP table is clean
- Collect logs if any anomaly observed
