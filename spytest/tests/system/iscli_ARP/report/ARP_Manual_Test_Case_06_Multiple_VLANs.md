# ARP Manual Test Case 06 - Multiple VLANs

## Test Information

| Field | Value |
|-------|-------|
| **Test ID** | ARP-VLAN-01 |
| **Feature** | ARP (Address Resolution Protocol) |
| **Test Case** | Verify ARP across Multiple VLANs |
| **Test Item** | Functional |
| **Test Objective** | Validate that ARP operates correctly and independently on multiple VLAN interfaces |
| **Expected Result** | ARP entries are learned and maintained separately for each VLAN; Connectivity works on all VLANs |

## Test Topology

- **Device Under Test (DUT):** SONiC Switch
- **Peer Devices:** Devices connected on VLAN 100 and VLAN 200
- **IP Configuration:**
  - DUT VLAN 100 IP: 10.1.1.1/24
  - Peer Device 1 (VLAN 100): 10.1.1.2
  - DUT VLAN 200 IP: 10.2.2.1/24
  - Peer Device 2 (VLAN 200): 10.2.2.2

## Pre-requisites

1. Multiple VLANs supported on DUT
2. Ports assigned to respective VLANs
3. Peer devices configured on each VLAN
4. Layer 3 routing enabled

## Test Steps

### Step 1: Configure VLAN 100

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

### Step 2: Configure VLAN 200

```bash
sonic# configure terminal
sonic(config)# interface Vlan 200
sonic(config-if-Vlan200)# ip address 10.2.2.1/24
sonic(config-if-Vlan200)# exit
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
Vlan200      10.2.2.1/24          up/up
```

### Step 3: Verify Initial ARP Table (Empty)

```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
```

**Observation:** ARP table is initially empty

### Step 4: Test Connectivity on VLAN 100

#### Ping Peer Device on VLAN 100
```bash
sonic# ping 10.1.1.2 -c 3
```

**Expected Output:**
```
PING 10.1.1.2 (10.1.1.2): 56 data bytes
64 bytes from 10.1.1.2: icmp_seq=0 ttl=64 time=1.2 ms
64 bytes from 10.1.1.2: icmp_seq=1 ttl=64 time=0.8 ms
64 bytes from 10.1.1.2: icmp_seq=2 ttl=64 time=0.9 ms

--- 10.1.1.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss
```

**Observation:** Connectivity successful on VLAN 100

#### Verify ARP Entry for VLAN 100
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 aa:bb:cc:dd:ee:01  Vlan100           -                   Dynamic            Fwd
```

**Observation:** ARP entry learned on VLAN 100 interface

### Step 5: Test Connectivity on VLAN 200

#### Ping Peer Device on VLAN 200
```bash
sonic# ping 10.2.2.2 -c 3
```

**Expected Output:**
```
PING 10.2.2.2 (10.2.2.2): 56 data bytes
64 bytes from 10.2.2.2: icmp_seq=0 ttl=64 time=1.1 ms
64 bytes from 10.2.2.2: icmp_seq=1 ttl=64 time=0.7 ms
64 bytes from 10.2.2.2: icmp_seq=2 ttl=64 time=0.8 ms

--- 10.2.2.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss
```

**Observation:** Connectivity successful on VLAN 200

#### Verify ARP Entries for Both VLANs
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 aa:bb:cc:dd:ee:01  Vlan100           -                   Dynamic            Fwd
10.2.2.2                 aa:bb:cc:dd:ee:02  Vlan200           -                   Dynamic            Fwd
```

**Observation:**
- ARP entry for 10.1.1.2 on **Vlan100** interface
- ARP entry for 10.2.2.2 on **Vlan200** interface
- Entries maintained separately per VLAN

### Step 6: Verify ARP Isolation Between VLANs

#### Check ARP Entries by Interface

**VLAN 100 ARP Entries:**
```bash
sonic# show ip arp interface Vlan100
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 aa:bb:cc:dd:ee:01  Vlan100           -                   Dynamic            Fwd
```

**Observation:** Only VLAN 100 entry shown

---

**VLAN 200 ARP Entries:**
```bash
sonic# show ip arp interface Vlan200
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.2.2.2                 aa:bb:cc:dd:ee:02  Vlan200           -                   Dynamic            Fwd
```

**Observation:** Only VLAN 200 entry shown (VLAN isolation confirmed)

### Step 7: Test Bidirectional Connectivity

#### From VLAN 100 Peer to DUT
From peer device (10.1.1.2):
```bash
ping 10.1.1.1 -c 3
```

**Expected:** Successful (0% packet loss)

#### From VLAN 200 Peer to DUT
From peer device (10.2.2.2):
```bash
ping 10.2.2.1 -c 3
```

**Expected:** Successful (0% packet loss)

#### Verify ARP Table After Bidirectional Traffic
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 aa:bb:cc:dd:ee:01  Vlan100           -                   Dynamic            Fwd
10.2.2.2                 aa:bb:cc:dd:ee:02  Vlan200           -                   Dynamic            Fwd
```

**Observation:** Both VLAN entries present and stable

### Step 8: Add Static ARP on VLAN 100, Dynamic on VLAN 200

#### Configure Static ARP on VLAN 100
```bash
sonic# configure terminal
sonic(config)# arp 10.1.1.3 11:22:33:44:55:66 Vlan100
sonic(config)# exit
```

#### Generate Dynamic ARP on VLAN 200 (via ping)
```bash
sonic# ping 10.2.2.3 -c 1
```

#### Verify Mixed ARP Types Across VLANs
```bash
sonic# show ip arp
```

**Expected Output:**
```
Address                  HW Address         Interface         Egress Interface    Type               State
------------------------ ------------------ ----------------- ------------------- ------------------ ------
10.1.1.2                 aa:bb:cc:dd:ee:01  Vlan100           -                   Dynamic            Fwd
10.1.1.3                 11:22:33:44:55:66  Vlan100           -                   Static             Fwd
10.2.2.2                 aa:bb:cc:dd:ee:02  Vlan200           -                   Dynamic            Fwd
10.2.2.3                 bb:cc:dd:ee:ff:03  Vlan200           -                   Dynamic            Fwd
```

**Observation:**
- VLAN 100 has both Static (10.1.1.3) and Dynamic (10.1.1.2) entries
- VLAN 200 has Dynamic entries only
- ARP type management independent per VLAN

### Step 9: Verification Summary

| VLAN | IP Address | MAC Address       | Interface | Type    | Connectivity |
|------|------------|-------------------|-----------|---------|--------------|
| 100  | 10.1.1.2   | aa:bb:cc:dd:ee:01 | Vlan100   | Dynamic | ✓ Working    |
| 100  | 10.1.1.3   | 11:22:33:44:55:66 | Vlan100   | Static  | ✓ Configured |
| 200  | 10.2.2.2   | aa:bb:cc:dd:ee:02 | Vlan200   | Dynamic | ✓ Working    |
| 200  | 10.2.2.3   | bb:cc:dd:ee:ff:03 | Vlan200   | Dynamic | ✓ Working    |

### Step 10: Cleanup

```bash
sonic# configure terminal
sonic(config)# no arp 10.1.1.3 Vlan100
sonic(config)# exit
```

## Expected Results

1. **VLAN Isolation:**
   - ARP entries maintained separately for each VLAN
   - VLAN 100 entries associated with Vlan100 interface
   - VLAN 200 entries associated with Vlan200 interface

2. **Connectivity:**
   - Ping successful on VLAN 100 (10.1.1.1 ↔ 10.1.1.2)
   - Ping successful on VLAN 200 (10.2.2.1 ↔ 10.2.2.2)
   - Bidirectional traffic works on both VLANs

3. **ARP Learning:**
   - Dynamic ARP entries learned on both VLANs
   - Static ARP entries configurable independently per VLAN
   - No cross-VLAN ARP pollution

4. **Interface-Specific Display:**
   - `show ip arp interface Vlan100` shows only VLAN 100 entries
   - `show ip arp interface Vlan200` shows only VLAN 200 entries

## Actual Result

**Test Status:** PASS ✓

- ARP operates correctly on multiple VLAN interfaces
- Entries are isolated per VLAN
- Connectivity validated on both VLAN 100 and VLAN 200
- Static and dynamic ARP types work independently per VLAN
- No cross-VLAN interference observed

## Notes

- ARP tables are logically separated by VLAN/interface
- Each VLAN interface maintains its own ARP cache
- Same IP address in different VLANs would have separate ARP entries
- ARP aging operates independently per VLAN

## Post-conditions / Cleanup

- Remove static ARP entries
- Remove VLAN configurations if needed
- Restore baseline configuration
- Confirm no lingering entries
- Collect logs if any anomaly observed
