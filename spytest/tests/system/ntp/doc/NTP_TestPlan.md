# NTP Functionality Test Plan — SONiC IS-CLI
**Document Version:** 1.0  
**Last Updated:** 2026-04-02  
**Status:** Draft  
**Module:** NTP (Network Time Protocol)  
**Platform:** SONiC IS-CLI  
**Traffic Generator:** Scapy (on NTP-SRV / DUT2)  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Test Objectives](#2-test-objectives)
3. [CLI Coverage Matrix](#3-cli-coverage-matrix)
4. [Topology](#4-topology)
5. [Environment Setup](#5-environment-setup)
6. [Test Methodology](#6-test-methodology)
7. [Test Case Naming Convention](#7-test-case-naming-convention)
8. [Test Summary](#8-test-summary)
9. [Test Cases](#9-test-cases)
   - [9.1 NTP Enable / Disable](#91-ntp-enable--disable)
   - [9.2 NTP Server Configuration](#92-ntp-server-configuration)
   - [9.3 NTP Authentication Key](#93-ntp-authentication-key)
   - [9.4 NTP Trusted Key](#94-ntp-trusted-key)
   - [9.5 NTP Authentication Enforcement](#95-ntp-authentication-enforcement)
   - [9.6 Full Authentication Workflow](#96-full-authentication-workflow)
   - [9.7 NTP Source Interface](#97-ntp-source-interface)
   - [9.8 NTP VRF Binding](#98-ntp-vrf-binding)
   - [9.9 Show Commands Validation](#99-show-commands-validation)
   - [9.10 NTP Synchronization Validation](#910-ntp-synchronization-validation)
   - [9.11 Scapy Traffic-Based Tests](#911-scapy-traffic-based-tests)
   - [9.12 Configuration Persistence](#912-configuration-persistence)
   - [9.13 Negative / Error Handling](#913-negative--error-handling)
   - [9.14 Scale & Stress](#914-scale--stress)
   - [9.15 Interaction & Edge Cases](#915-interaction--edge-cases)
10. [Pass / Fail Criteria](#10-pass--fail-criteria)
11. [Execution Schedule](#11-execution-schedule)
12. [Deliverables](#12-deliverables)
13. [Risks and Mitigations](#13-risks-and-mitigations)
14. [References](#14-references)

---

## 1. Overview

This document defines the complete test plan for validating the NTP (Network Time Protocol) feature on SONiC IS-CLI. The plan covers all configuration and show commands extracted from the NTP CLI XML definition, runtime synchronization behaviour, NTP authentication (MD5 / SHA variants), source interface selection, VRF binding, and Scapy-based packet-level traffic verification.

The test plan is structured to be directly consumed by Claude (or any automation engine) for:
- **Manual test execution** — step-by-step CLI procedures with expected outputs
- **Script automation** — each test case is self-contained and parameterised

**Total Test Cases: 72**  
**Functional Areas: 15**  
**Estimated Execution Time: 28 hours**

---

## 2. Test Objectives

- Validate `ntp enable` / `no ntp enable` lifecycle
- Verify all `ntp server` options: address (IPv4, IPv6, FQDN), `version`, `association`, `iburst`, `key`, `prefer`
- Validate `ntp authentication-key` creation, update, and deletion for all supported algorithms: **md5, sha1, sha256, sha384, sha512**
- Verify `ntp trusted-key` designation and revocation
- Test full authentication enforcement pipeline: key → trusted-key → authenticate → server key binding → sync
- Validate `ntp source-interface` for all supported types: Ethernet, Loopback, Management, PortChannel, Vlan
- Test `ntp vrf mgmt` and `ntp vrf default` bindings
- Validate all three show commands: `show ntp global`, `show ntp server`, `show ntp associations`
- Verify actual NTP clock synchronisation with a real NTP server
- Use Scapy to craft and capture NTP packets to validate packet-level behaviour (port 123/UDP, authentication extension fields, source IP)
- Verify configuration persistence across daemon restarts and system reloads
- Cover all negative/error cases: invalid key IDs, duplicate servers, missing trusted-key, wrong auth password, invalid VRF
- Validate scale scenarios: multiple servers, multiple auth keys, rapid enable/disable cycles

---

## 3. CLI Coverage Matrix

| CLI Command | Test Cases Covering It |
|---|---|
| `ntp enable` | TC_NTP_ENABLE_001, 002, 003 |
| `no ntp enable` | TC_NTP_ENABLE_002, TC_NTP_PERSIST_002 |
| `ntp authenticate` | TC_NTP_AUTH_ENF_001, 002, TC_NTP_AUTHWF_001–003 |
| `no ntp authenticate` | TC_NTP_AUTH_ENF_002, TC_NTP_AUTHWF_002 |
| `ntp authentication-key <id> <type> <pass>` | TC_NTP_AUTHKEY_001–007 |
| `no ntp authentication-key <id>` | TC_NTP_AUTHKEY_005, 006, TC_NTP_NEG_006 |
| `ntp trusted-key <id>` | TC_NTP_TRUSTED_001–004, TC_NTP_AUTHWF_001 |
| `no ntp trusted-key <id>` | TC_NTP_TRUSTED_003, TC_NTP_AUTHWF_002 |
| `ntp server <addr> [options]` | TC_NTP_SERVER_001–010 |
| `no ntp server <addr>` | TC_NTP_SERVER_007, TC_NTP_NEG_002 |
| `ntp source-interface <type> <id>` | TC_NTP_SRC_001–006 |
| `no ntp source-interface` | TC_NTP_SRC_005, 006 |
| `ntp vrf <name>` | TC_NTP_VRF_001–004 |
| `no ntp vrf` | TC_NTP_VRF_003, 004 |
| `show ntp global` | TC_NTP_SHOW_001, + all config TCs |
| `show ntp server` | TC_NTP_SHOW_002, TC_NTP_SERVER_* |
| `show ntp associations` | TC_NTP_SHOW_003, TC_NTP_SYNC_* |

---

## 4. Topology

### 4.1 Topology Description

```
┌─────────────────────────────────────────────────────────────────┐
│                         TEST TOPOLOGY                           │
│                                                                 │
│   ┌──────────────┐   Eth0 ──────── Eth0  ┌──────────────┐       │
│   │    DUT1      │                       │    DUT2      │       │
│   │  (SONiC)     │   Mgmt ─────── Mgmt   │  (SONiC)     │       │
│   │              │                       │              │       │
│   │  NTP Client  │                       │  NTP Client  │       │
│   └──────┬───────┘                       └──────┬───────┘       │
│          │  Mgmt0 / Eth1                        │               │
│          │                                      │               │
│          └──────────────┬───────────────────────┘               │
│                         │                                       │
│                  ┌──────┴───────┐                               │
│                  │   NTP-SRV    │                               │
│                  │  (Linux VM / │                               │
│                  │  SONiC-VS)   │                               │
│                  │              │                               │
│                  │  chronyd /   │                               │
│                  │  ntpd        │                               │
│                  │  + Scapy     │                               │
│                  └──────────────┘                               │
│                                                                 │
│  Management Network: 192.168.100.0/24                           │
│  NTP-SRV:  192.168.100.10                                       │
│  DUT1 Mgmt: 192.168.100.1  /  DUT1 Eth0: 10.0.0.1/30            │
│  DUT2 Mgmt: 192.168.100.2  /  DUT2 Eth0: 10.0.0.2/30            │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Device Roles

| Device | Role | Notes |
|--------|------|-------|
| **DUT1** | Primary NTP client under test | All NTP CLI commands exercised here |
| **DUT2** | Secondary NTP client / relay | Used for multi-server and VRF scenarios |
| **NTP-SRV** | NTP server + Scapy traffic generator | Runs chronyd/ntpd with auth support; Scapy installed |

### 4.3 Interface Assignment

| Device | Interface | IP Address | Purpose |
|--------|-----------|-----------|---------|
| DUT1 | Management0 | 192.168.100.1/24 | OOB management; default NTP source |
| DUT1 | Ethernet0 | 10.0.0.1/30 | In-band link to DUT2 |
| DUT1 | Loopback0 | 1.1.1.1/32 | Source interface testing |
| DUT2 | Management0 | 192.168.100.2/24 | OOB management |
| DUT2 | Ethernet0 | 10.0.0.2/30 | In-band link to DUT1 |
| NTP-SRV | eth0 | 192.168.100.10/24 | NTP service + Scapy |

### 4.4 NTP Server Setup on NTP-SRV

```bash
# Install and configure chrony on NTP-SRV
sudo apt-get install -y chrony

# /etc/chrony.conf — example with MD5 and SHA256 auth
local stratum 2
allow 192.168.100.0/24
keyfile /etc/chrony.keys
authselectmode require       # enforce auth in auth test scenarios

# /etc/chrony.keys
1 MD5 MySecret123
2 SHA256 SecurePass456
3 SHA1 Sha1Password
4 SHA512 BigSecret789
5 SHA384 MediumSecret

sudo systemctl restart chronyd
```

---

## 5. Environment Setup

### 5.1 Hardware Requirements

| Item | Specification |
|------|--------------|
| DUT1 | SONiC-capable switch or SONiC-VS VM |
| DUT2 | SONiC-capable switch or SONiC-VS VM |
| NTP-SRV | Linux VM (Ubuntu 20.04+) or SONiC-VS container |
| Network | Layer-2 / management network connecting all three devices |

### 5.2 Software Requirements

| Component | Version / Notes |
|-----------|----------------|
| SONiC OS | Target release under test |
| chronyd | 4.x on NTP-SRV (supports MD5, SHA1, SHA256, SHA384, SHA512) |
| Python + Scapy | 2.5.0+ on NTP-SRV |
| ntplib (Python) | For Scapy NTP packet crafting and parsing |

### 5.3 VS vs HW Classification

| Label | Meaning |
|-------|---------|
| `[VS]` | Fully runnable on SONiC Virtual Switch (no physical hardware required) |
| `[HW]` | Requires physical hardware (e.g., real Management0 with DHCP, PHY-dependent timing) |
| `[VS/HW]` | Runs on both; HW recommended for timing-sensitive assertions |

### 5.4 Pre-Test Checklist

```bash
# On DUT1 and DUT2 — clear NTP state before each test
configure terminal
  no ntp enable
  no ntp authenticate
  no ntp server <any>
  no ntp source-interface
  no ntp vrf
  no ntp authentication-key <any>
  no ntp trusted-key <any>
exit

# Confirm clean state
show ntp global
show ntp server
show ntp associations
```

### 5.5 Scapy NTP Packet Skeleton

```python
# ntp_utils.py — shared Scapy helpers for NTP test cases
from scapy.all import *
from scapy.layers.ntp import NTP
import socket

NTP_SRV_IP  = "192.168.100.10"
DUT1_MGMT   = "192.168.100.1"
NTP_PORT    = 123

def craft_ntp_client_request(src_ip=DUT1_MGMT):
    """Craft a basic NTPv4 client request packet."""
    pkt = (
        IP(src=src_ip, dst=NTP_SRV_IP) /
        UDP(sport=RandShort(), dport=NTP_PORT) /
        NTP(version=4, mode=3)   # mode=3: client
    )
    return pkt

def craft_ntp_auth_request(src_ip, key_id, key_type, password):
    """Craft NTP packet with authentication extension (MAC)."""
    import hashlib, struct, time
    # Build raw NTP packet with key ID and MAC fields appended
    ntp_layer = NTP(version=4, mode=3)
    raw_ntp   = bytes(ntp_layer)
    key_id_bytes = struct.pack("!I", key_id)
    if key_type == "md5":
        mac = hashlib.md5(password.encode() + raw_ntp).digest()[:16]
    elif key_type == "sha1":
        mac = hashlib.sha1(password.encode() + raw_ntp).digest()[:20]
    else:
        mac = hashlib.sha256(password.encode() + raw_ntp).digest()[:20]
    auth_ext = key_id_bytes + mac
    pkt = (
        IP(src=src_ip, dst=NTP_SRV_IP) /
        UDP(sport=RandShort(), dport=NTP_PORT) /
        Raw(load=raw_ntp + auth_ext)
    )
    return pkt

def send_and_capture(pkt, iface="eth0", timeout=5):
    """Send packet and capture the NTP server reply."""
    ans, _ = sr(pkt, iface=iface, timeout=timeout, verbose=False)
    return ans

def verify_ntp_source_ip(captured, expected_src_ip):
    """Assert the NTP request was sent from the expected source IP."""
    for snd, rcv in captured:
        assert snd[IP].src == expected_src_ip, \
            f"Source IP mismatch: got {snd[IP].src}, expected {expected_src_ip}"
    return True
```

---

## 6. Test Methodology

### 6.1 General Test Flow

For every test case:

1. **Pre-condition**: Apply the precondition configuration listed in the test case.
2. **Action**: Execute the CLI commands listed step-by-step.
3. **Verification**: Run the show commands and compare against expected output.
4. **Traffic Validation** *(where applicable)*: Run the Scapy script and assert on captured packets.
5. **Cleanup**: Remove all configuration added during the test to restore a clean state.

### 6.2 NTP Synchronisation Convergence Time

- After enabling NTP and configuring a server, allow up to **60 seconds** for `show ntp associations` to show the `*` (selected) prefix before declaring a synchronisation timeout.
- For `iburst` tests, convergence should occur within **15 seconds**.

### 6.3 Scapy Capture Approach

Run Scapy captures **on NTP-SRV** using a background sniffer. DUT1 generates NTP traffic to NTP-SRV as the NTP client. The sniffer validates packet attributes from the server's perspective.

```bash
# Background sniffer on NTP-SRV
sudo python3 -c "
from scapy.all import *
from scapy.layers.ntp import NTP
pkts = sniff(iface='eth0', filter='udp port 123', count=10, timeout=30)
pkts.show()
wrpcap('/tmp/ntp_capture.pcap', pkts)
"
```

---

## 7. Test Case Naming Convention

```
TC_NTP_<CATEGORY>_<NNN>
```

| Category Code | Area |
|--------------|------|
| `ENABLE` | NTP enable / disable |
| `SERVER` | NTP server configuration |
| `AUTHKEY` | Authentication key management |
| `TRUSTED` | Trusted key management |
| `AUTH_ENF` | Authentication enforcement (ntp authenticate) |
| `AUTHWF` | Full authentication workflow (end-to-end) |
| `SRC` | Source interface |
| `VRF` | VRF binding |
| `SHOW` | Show commands |
| `SYNC` | Synchronisation validation |
| `TRAFFIC` | Scapy packet-level tests |
| `PERSIST` | Configuration persistence |
| `NEG` | Negative / error handling |
| `SCALE` | Scale and stress |
| `EDGE` | Interaction and edge cases |

---

## 8. Test Summary

| # | Functional Area | TC IDs | Count | VS/HW |
|---|----------------|--------|-------|-------|
| 1 | NTP Enable / Disable | TC_NTP_ENABLE_001–003 | 3 | VS |
| 2 | NTP Server Configuration | TC_NTP_SERVER_001–010 | 10 | VS |
| 3 | Authentication Key | TC_NTP_AUTHKEY_001–007 | 7 | VS |
| 4 | Trusted Key | TC_NTP_TRUSTED_001–004 | 4 | VS |
| 5 | Authentication Enforcement | TC_NTP_AUTH_ENF_001–003 | 3 | VS |
| 6 | Full Auth Workflow | TC_NTP_AUTHWF_001–005 | 5 | VS/HW |
| 7 | Source Interface | TC_NTP_SRC_001–006 | 6 | VS/HW |
| 8 | VRF Binding | TC_NTP_VRF_001–004 | 4 | VS/HW |
| 9 | Show Commands | TC_NTP_SHOW_001–005 | 5 | VS |
| 10 | Synchronisation Validation | TC_NTP_SYNC_001–006 | 6 | VS/HW |
| 11 | Scapy Traffic-Based | TC_NTP_TRAFFIC_001–007 | 7 | VS/HW |
| 12 | Configuration Persistence | TC_NTP_PERSIST_001–004 | 4 | VS/HW |
| 13 | Negative / Error Handling | TC_NTP_NEG_001–008 | 8 | VS |
| 14 | Scale & Stress | TC_NTP_SCALE_001–005 | 5 | VS/HW |
| 15 | Interaction & Edge Cases | TC_NTP_EDGE_001–005 | 5 | VS |
| | **TOTAL** | | **72** | |

---

## 9. Test Cases

---

### 9.1 NTP Enable / Disable

---

#### TC_NTP_ENABLE_001 — Enable NTP service `[VS]`

**Objective:** Verify that `ntp enable` activates the NTP daemon and is reflected in `show ntp global`.

**Pre-condition:** NTP is disabled (default state). No servers configured.

**Steps:**

```
DUT1# configure terminal
DUT1(config)# ntp enable
DUT1(config)# exit
DUT1# show ntp global
```

**Expected Output:**
```
NTP Configuration:
  Enabled:             True
  Authentication:      False
  Vrf:                 default
  Source Interface:    -
```

**Verification:**
- `Enabled` field shows `True`
- No error messages during `ntp enable`
- NTP daemon process is running: `sudo systemctl status ntp` or `ps aux | grep ntp`

**Cleanup:**
```
DUT1(config)# no ntp enable
```

---

#### TC_NTP_ENABLE_002 — Disable NTP service `[VS]`

**Objective:** Verify `no ntp enable` stops the NTP daemon while preserving other configuration.

**Pre-condition:** NTP is enabled. Server `192.168.100.10` is configured. Auth key 1 (md5) is configured.

**Setup:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10
DUT1(config)# ntp authentication-key 1 md5 MySecret123
```

**Steps:**
```
DUT1(config)# no ntp enable
DUT1(config)# exit
DUT1# show ntp global
DUT1# show ntp server
```

**Expected Output — `show ntp global`:**
```
NTP Configuration:
  Enabled:             False
  Authentication:      False
  Vrf:                 default
  Source Interface:    -
```

**Expected Output — `show ntp server`:**
```
NTP Servers:
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       disabled False    -
```

**Verification:**
- `Enabled` shows `False`
- Server entry and auth key are **retained** (not removed)
- NTP daemon is no longer running or processing packets

**Cleanup:**
```
DUT1(config)# no ntp server 192.168.100.10
DUT1(config)# no ntp authentication-key 1
```

---

#### TC_NTP_ENABLE_003 — Re-enable NTP without re-configuring servers `[VS]`

**Objective:** Verify that disabling and re-enabling NTP resumes synchronisation with previously configured servers without re-entering server configuration.

**Pre-condition:** NTP enabled, server configured, synchronised (show associations shows `*`).

**Setup:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 iburst
```
*(Wait up to 60s for sync)*

**Steps:**
```
DUT1(config)# no ntp enable
DUT1(config)# exit
DUT1# show ntp associations
! Verify: no associations shown (daemon stopped)
DUT1# configure terminal
DUT1(config)# ntp enable
DUT1(config)# exit
! Wait 60s
DUT1# show ntp associations
```

**Expected Output after re-enable:**
```
NTP Associations:
  refid           st t when poll reach  delay  offset  jitter
  ================================================================
 *192.168.100.10  2  u   15  64  377  ...
```

**Verification:**
- After disable: `show ntp associations` returns empty or "NTP is not enabled" message
- After re-enable: `*` prefix appears on `192.168.100.10` within 60 seconds

**Cleanup:**
```
DUT1(config)# no ntp enable
DUT1(config)# no ntp server 192.168.100.10
```

---

### 9.2 NTP Server Configuration

---

#### TC_NTP_SERVER_001 — Add NTP server with IPv4 address `[VS]`

**Objective:** Verify basic NTP server entry creation with IPv4 address.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10
DUT1# show ntp server
```

**Expected Output:**
```
NTP Servers:
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       disabled False    -
```

**Verification:**
- Address, version 4, association `server`, iburst `disabled`, prefer `False`, key `-`

**Cleanup:** `no ntp server 192.168.100.10`

---

#### TC_NTP_SERVER_002 — Add NTP server with IPv6 address `[VS]`

**Objective:** Verify NTP server entry with an IPv6 address.

**Steps:**
```
DUT1(config)# ntp server 2001:db8::1
DUT1# show ntp server
```

**Expected Output:**
```
NTP Servers:
  Address           Version  Association  Iburst   Prefer   Key
  2001:db8::1       4        server       disabled False    -
```

**Verification:** IPv6 address stored and displayed correctly.

**Cleanup:** `no ntp server 2001:db8::1`

---

#### TC_NTP_SERVER_003 — Add NTP server with version 3 `[VS]`

**Objective:** Verify `version 3` option is accepted and stored.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 version 3
DUT1# show ntp server
```

**Expected Output:**
```
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    3        server       disabled False    -
```

**Cleanup:** `no ntp server 192.168.100.10`

---

#### TC_NTP_SERVER_004 — Add NTP server with association type pool `[VS]`

**Objective:** Verify `association pool` option is stored and displayed correctly.

**Steps:**
```
DUT1(config)# ntp server pool.ntp.org association pool iburst
DUT1# show ntp server
```

**Expected Output:**
```
  Address        Version  Association  Iburst   Prefer   Key
  pool.ntp.org   4        pool         enabled  False    -
```

**Cleanup:** `no ntp server pool.ntp.org`

---

#### TC_NTP_SERVER_005 — Add NTP server with iburst enabled `[VS]`

**Objective:** Verify the `iburst` flag is stored correctly.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 iburst
DUT1# show ntp server
```

**Expected Output:**
```
  Iburst: enabled
```

**Cleanup:** `no ntp server 192.168.100.10`

---

#### TC_NTP_SERVER_006 — Add NTP server with prefer flag `[VS]`

**Objective:** Verify the `prefer` flag is stored and shown correctly.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 prefer
DUT1# show ntp server
```

**Expected Output:**
```
  Prefer: True
```

**Cleanup:** `no ntp server 192.168.100.10`

---

#### TC_NTP_SERVER_007 — Add and remove NTP server `[VS]`

**Objective:** Verify `no ntp server` cleanly removes the server entry.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10
DUT1# show ntp server
! Verify server is present
DUT1(config)# no ntp server 192.168.100.10
DUT1# show ntp server
```

**Expected Output after removal:**
```
NTP Servers:
  (empty)
```
or:
```
% No NTP servers configured
```

**Cleanup:** None required.

---

#### TC_NTP_SERVER_008 — Add multiple NTP servers simultaneously `[VS]`

**Objective:** Verify multiple server entries can coexist.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10
DUT1(config)# ntp server 192.168.100.11
DUT1(config)# ntp server 2001:db8::1 version 4 iburst prefer
DUT1# show ntp server
```

**Expected Output:**
```
NTP Servers:
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       disabled False    -
  192.168.100.11    4        server       disabled False    -
  2001:db8::1       4        server       enabled  True     -
```

**Cleanup:**
```
DUT1(config)# no ntp server 192.168.100.10
DUT1(config)# no ntp server 192.168.100.11
DUT1(config)# no ntp server 2001:db8::1
```

---

#### TC_NTP_SERVER_009 — Add server with all options combined `[VS]`

**Objective:** Verify all optional server parameters can be specified together in a single command.

**Pre-condition:** Auth key 1 (md5) is configured and trusted.

**Setup:**
```
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
```

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 version 4 association server iburst key 1 prefer
DUT1# show ntp server
```

**Expected Output:**
```
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       enabled  True     1
```

**Cleanup:**
```
DUT1(config)# no ntp server 192.168.100.10
DUT1(config)# no ntp trusted-key 1
DUT1(config)# no ntp authentication-key 1
```

---

#### TC_NTP_SERVER_010 — Add NTP server using FQDN hostname `[VS/HW]`

**Objective:** Verify an FQDN (hostname) is accepted as a valid server address.

**Note:** DNS resolution must be available. In VS environments, add a `/etc/hosts` entry if no DNS is present.

**Steps:**
```
DUT1(config)# ntp server ntp.example.com
DUT1# show ntp server
```

**Expected Output:**
```
  Address           Version  Association  Iburst   Prefer   Key
  ntp.example.com   4        server       disabled False    -
```

**Cleanup:** `no ntp server ntp.example.com`

---

### 9.3 NTP Authentication Key

---

#### TC_NTP_AUTHKEY_001 — Create auth key with MD5 `[VS]`

**Objective:** Verify `ntp authentication-key` with md5 type is accepted.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1# show ntp global
```

**Expected Output:**
- Command executes without error
- Authentication key is reflected when trusted-key is also set (verified in TC_NTP_TRUSTED_001)

**Verification:** No error messages. Key ID 1 available for trusted-key and server-key binding.

**Cleanup:** `no ntp authentication-key 1`

---

#### TC_NTP_AUTHKEY_002 — Create auth key with SHA1 `[VS]`

**Steps:**
```
DUT1(config)# ntp authentication-key 2 sha1 Sha1Password
```

**Verification:** Command accepted without error.

**Cleanup:** `no ntp authentication-key 2`

---

#### TC_NTP_AUTHKEY_003 — Create auth key with SHA256 `[VS]`

**Steps:**
```
DUT1(config)# ntp authentication-key 3 sha256 SecurePass456
```

**Cleanup:** `no ntp authentication-key 3`

---

#### TC_NTP_AUTHKEY_004 — Create auth key with SHA384 and SHA512 `[VS]`

**Objective:** Verify both SHA384 and SHA512 key types are accepted.

**Steps:**
```
DUT1(config)# ntp authentication-key 4 sha384 MediumSecret
DUT1(config)# ntp authentication-key 5 sha512 BigSecret789
```

**Verification:** Both commands execute without error.

**Cleanup:**
```
DUT1(config)# no ntp authentication-key 4
DUT1(config)# no ntp authentication-key 5
```

---

#### TC_NTP_AUTHKEY_005 — Update existing auth key (re-configure same key-id) `[VS]`

**Objective:** Verify that re-issuing `ntp authentication-key` for an existing key ID overwrites the previous entry.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 OriginalPass
DUT1(config)# ntp authentication-key 1 sha256 UpdatedPass
! Key ID 1 should now use sha256 / UpdatedPass
DUT1# show ntp server
! If key 1 is bound to a server, verify key column still shows 1
```

**Verification:** No duplicate key error; key-id 1 updated to sha256/UpdatedPass.

**Cleanup:** `no ntp authentication-key 1`

---

#### TC_NTP_AUTHKEY_006 — Delete an auth key `[VS]`

**Objective:** Verify `no ntp authentication-key` removes the key.

**Steps:**
```
DUT1(config)# ntp authentication-key 10 md5 TempSecret
DUT1(config)# no ntp authentication-key 10
```

**Verification:** Key 10 is no longer usable; attempting `ntp trusted-key 10` should fail or warn.

---

#### TC_NTP_AUTHKEY_007 — Create auth keys at boundary key IDs `[VS]`

**Objective:** Verify key IDs at valid boundaries (1 and 65535) are accepted.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 MinKey
DUT1(config)# ntp authentication-key 65535 sha256 MaxKey
```

**Verification:** Both accepted without error.

**Cleanup:**
```
DUT1(config)# no ntp authentication-key 1
DUT1(config)# no ntp authentication-key 65535
```

---

### 9.4 NTP Trusted Key

---

#### TC_NTP_TRUSTED_001 — Designate a key as trusted `[VS]`

**Objective:** Verify `ntp trusted-key` marks a previously defined auth key as trusted.

**Pre-condition:** Auth key 1 (md5) is configured.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1# show ntp global
```

**Expected Output — `show ntp global`:**
```
NTP Configuration:
  Enabled:             True
  Authentication:      False
  Vrf:                 default
  Source Interface:    -
```

**Verification:** No error during `ntp trusted-key 1`. Key 1 can now be used in `ntp server ... key 1`.

**Cleanup:**
```
DUT1(config)# no ntp trusted-key 1
DUT1(config)# no ntp authentication-key 1
```

---

#### TC_NTP_TRUSTED_002 — Trust multiple keys simultaneously `[VS]`

**Objective:** Verify more than one key can be trusted at the same time.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 Pass1
DUT1(config)# ntp authentication-key 2 sha256 Pass2
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp trusted-key 2
```

**Verification:** Both keys 1 and 2 are trusted; no error on either command.

**Cleanup:**
```
DUT1(config)# no ntp trusted-key 1
DUT1(config)# no ntp trusted-key 2
DUT1(config)# no ntp authentication-key 1
DUT1(config)# no ntp authentication-key 2
```

---

#### TC_NTP_TRUSTED_003 — Revoke trust from a key `[VS]`

**Objective:** Verify `no ntp trusted-key` removes trusted status while keeping key definition.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# no ntp trusted-key 1
! Key definition (ntp authentication-key 1) should still exist
```

**Verification:**
- `no ntp trusted-key 1` executes without error
- Key 1 definition is retained (can verify by re-trusting with `ntp trusted-key 1`)
- Auth enforcement (if enabled) would now reject servers using key 1

**Cleanup:**
```
DUT1(config)# no ntp authentication-key 1
```

---

#### TC_NTP_TRUSTED_004 — Trusted key at boundary key IDs `[VS]`

**Objective:** Verify trusted-key command works at boundary key IDs (1 and 65535).

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 MinKey
DUT1(config)# ntp authentication-key 65535 sha512 MaxKey
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp trusted-key 65535
```

**Cleanup:**
```
DUT1(config)# no ntp trusted-key 1
DUT1(config)# no ntp trusted-key 65535
DUT1(config)# no ntp authentication-key 1
DUT1(config)# no ntp authentication-key 65535
```

---

### 9.5 NTP Authentication Enforcement

---

#### TC_NTP_AUTH_ENF_001 — Enable authentication enforcement `[VS]`

**Objective:** Verify `ntp authenticate` enables mandatory authentication and is reflected in `show ntp global`.

**Steps:**
```
DUT1(config)# ntp authenticate
DUT1# show ntp global
```

**Expected Output:**
```
NTP Configuration:
  Enabled:             True
  Authentication:      True
  Vrf:                 default
  Source Interface:    -
```

**Verification:** `Authentication` field shows `True`.

**Cleanup:** `no ntp authenticate`

---

#### TC_NTP_AUTH_ENF_002 — Disable authentication enforcement `[VS]`

**Objective:** Verify `no ntp authenticate` disables enforcement while keeping key and trusted-key config.

**Pre-condition:** `ntp authenticate` is enabled. Auth key 1 is configured and trusted.

**Steps:**
```
DUT1(config)# ntp authenticate
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# no ntp authenticate
DUT1# show ntp global
```

**Expected Output:**
```
  Authentication:      False
```

**Verification:**
- Authentication field shows `False`
- Key 1 definition and trusted-key 1 are still present

**Cleanup:**
```
DUT1(config)# no ntp trusted-key 1
DUT1(config)# no ntp authentication-key 1
```

---

#### TC_NTP_AUTH_ENF_003 — Enable/disable authentication enforcement cycle `[VS]`

**Objective:** Verify auth enforcement can be toggled multiple times without error.

**Steps:**
```
DUT1(config)# ntp authenticate
DUT1# show ntp global   ! Authentication: True
DUT1(config)# no ntp authenticate
DUT1# show ntp global   ! Authentication: False
DUT1(config)# ntp authenticate
DUT1# show ntp global   ! Authentication: True
DUT1(config)# no ntp authenticate
```

**Verification:** Each toggle is reflected correctly in `show ntp global`. No errors.

---

### 9.6 Full Authentication Workflow

---

#### TC_NTP_AUTHWF_001 — Full MD5 auth workflow — sync with authenticated server `[VS/HW]`

**Objective:** End-to-end test: configure auth key, trust it, enable auth enforcement, bind key to server, and verify synchronisation with NTP-SRV using MD5.

**Pre-condition:** NTP-SRV has key 1 / MD5 / `MySecret123` configured in `/etc/chrony.keys`.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp authenticate
DUT1(config)# ntp server 192.168.100.10 iburst key 1
DUT1(config)# exit
! Wait up to 60 seconds
DUT1# show ntp global
DUT1# show ntp server
DUT1# show ntp associations
```

**Expected Output — `show ntp global`:**
```
  Enabled:        True
  Authentication: True
```

**Expected Output — `show ntp server`:**
```
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       enabled  False    1
```

**Expected Output — `show ntp associations` (after convergence):**
```
 *192.168.100.10   2  u   ...  377  ...
```
*(the `*` indicates this is the selected, synchronised source)*

**Verification:**
- `*` prefix on `192.168.100.10` in associations output
- `show ntp global` shows Authentication: True
- `show ntp server` shows Key: 1

**Cleanup:**
```
DUT1(config)# no ntp server 192.168.100.10
DUT1(config)# no ntp authenticate
DUT1(config)# no ntp trusted-key 1
DUT1(config)# no ntp authentication-key 1
DUT1(config)# no ntp enable
```

---

#### TC_NTP_AUTHWF_002 — Auth enforcement blocks unauthenticated server sync `[VS/HW]`

**Objective:** Verify that when `ntp authenticate` is enabled, a server configured **without** a key binding is rejected for synchronisation.

**Pre-condition:** NTP-SRV is running. Auth is configured on DUT1 but the server entry has no key.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp authenticate
DUT1(config)# ntp server 192.168.100.10 iburst
! Note: NO key binding on server
DUT1(config)# exit
! Wait 90 seconds
DUT1# show ntp associations
```

**Expected Output:**
```
NTP Associations:
  refid           st t when poll reach  delay  offset  jitter
  ...
  192.168.100.10   16 u  ...
```
*(stratum 16 = unreachable; no `*` prefix — server is not selected because auth enforcement rejected it)*

**Verification:** No `*` on the server. NTP daemon does not synchronise to an unauthenticated source when enforcement is enabled.

**Cleanup:** Standard cleanup (no ntp enable, server, authenticate, etc.)

---

#### TC_NTP_AUTHWF_003 — Wrong password prevents synchronisation `[VS/HW]`

**Objective:** Verify that a mismatched password in the auth key prevents the server from being selected.

**Pre-condition:** NTP-SRV uses MD5 key 1 = `MySecret123`. DUT1 is configured with **wrong** password `WrongPass`.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authentication-key 1 md5 WrongPass
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp authenticate
DUT1(config)# ntp server 192.168.100.10 iburst key 1
DUT1(config)# exit
! Wait 90 seconds
DUT1# show ntp associations
```

**Expected Output:** No `*` on `192.168.100.10`; stratum shown as 16 or association is rejected.

**Verification:** Authentication failure is evident by the absence of the `*` selected indicator.

---

#### TC_NTP_AUTHWF_004 — SHA256 full auth workflow `[VS/HW]`

**Objective:** Same as TC_NTP_AUTHWF_001 but using SHA256 instead of MD5.

**Pre-condition:** NTP-SRV has key 2 / SHA256 / `SecurePass456` in `/etc/chrony.keys`.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authentication-key 2 sha256 SecurePass456
DUT1(config)# ntp trusted-key 2
DUT1(config)# ntp authenticate
DUT1(config)# ntp server 192.168.100.10 iburst key 2
! Wait 60s
DUT1# show ntp associations
```

**Expected Output:** `*192.168.100.10` in associations (synchronised).

---

#### TC_NTP_AUTHWF_005 — Untrusting a key breaks synchronisation `[VS/HW]`

**Objective:** Verify that removing a trusted-key designation causes the NTP daemon to stop accepting that server.

**Pre-condition:** DUT1 is synchronised with NTP-SRV using auth key 1 (MD5, trusted).

**Steps:**
```
! Verify sync first
DUT1# show ntp associations
! Expected: *192.168.100.10 with * prefix
DUT1(config)# no ntp trusted-key 1
! Wait 30s
DUT1# show ntp associations
```

**Expected Output after untrusting:** Server is demoted or loses `*` prefix; stratum 16 or unsynchronised.

---

### 9.7 NTP Source Interface

---

#### TC_NTP_SRC_001 — Set source interface to Management0 `[VS/HW]`

**Objective:** Verify NTP source interface can be set to the Management interface.

**Steps:**
```
DUT1(config)# ntp source-interface Management 0
DUT1# show ntp global
```

**Expected Output:**
```
  Source Interface:    Management0
```

**Cleanup:** `no ntp source-interface`

---

#### TC_NTP_SRC_002 — Set source interface to Loopback0 `[VS]`

**Pre-condition:** Loopback0 exists with IP 1.1.1.1/32.

**Steps:**
```
DUT1(config)# interface Loopback 0
DUT1(config-if)# ip address 1.1.1.1/32
DUT1(config-if)# exit
DUT1(config)# ntp source-interface Loopback 0
DUT1# show ntp global
```

**Expected Output:**
```
  Source Interface:    Loopback0
```

**Cleanup:**
```
DUT1(config)# no ntp source-interface
DUT1(config)# no interface Loopback 0
```

---

#### TC_NTP_SRC_003 — Set source interface to Ethernet0 `[VS/HW]`

**Steps:**
```
DUT1(config)# ntp source-interface Ethernet 0
DUT1# show ntp global
```

**Expected Output:**
```
  Source Interface:    Ethernet0
```

**Cleanup:** `no ntp source-interface`

---

#### TC_NTP_SRC_004 — Set source interface to Vlan interface `[VS]`

**Pre-condition:** Vlan10 exists and has an IP address.

**Steps:**
```
DUT1(config)# vlan 10
DUT1(config)# interface Vlan 10
DUT1(config-if)# ip address 192.168.10.1/24
DUT1(config-if)# exit
DUT1(config)# ntp source-interface Vlan 10
DUT1# show ntp global
```

**Expected Output:**
```
  Source Interface:    Vlan10
```

**Cleanup:**
```
DUT1(config)# no ntp source-interface
DUT1(config)# no interface Vlan 10
DUT1(config)# no vlan 10
```

---

#### TC_NTP_SRC_005 — Remove source interface configuration `[VS]`

**Objective:** Verify `no ntp source-interface` reverts to routing-table-based source selection.

**Steps:**
```
DUT1(config)# ntp source-interface Management 0
DUT1# show ntp global
! Verify Source Interface: Management0
DUT1(config)# no ntp source-interface
DUT1# show ntp global
```

**Expected Output after removal:**
```
  Source Interface:    -
```
or field omitted.

---

#### TC_NTP_SRC_006 — Source interface change reflects in NTP packet source IP `[VS/HW]`

**Objective:** Use Scapy on NTP-SRV to capture NTP packets from DUT1 and verify the source IP matches the configured source interface.

**Pre-condition:** DUT1 has Loopback0 = 1.1.1.1/32. Route from 1.1.1.1 to NTP-SRV is reachable.

**Steps on NTP-SRV:**
```bash
# Start Scapy capture
sudo python3 - <<'EOF'
from scapy.all import *
from scapy.layers.ntp import NTP

pkts = sniff(iface="eth0", filter="udp port 123 and src host 192.168.100.1", count=5, timeout=30)
for p in pkts:
    print(f"Source IP: {p[IP].src}")
    assert p[IP].src == "192.168.100.1", f"Wrong src: {p[IP].src}"
print("PASS: NTP packets from Management0 (192.168.100.1)")
EOF
```

**Steps on DUT1:**
```
DUT1(config)# ntp source-interface Management 0
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 iburst
```

**Expected Scapy Output:**
```
Source IP: 192.168.100.1
PASS: NTP packets from Management0 (192.168.100.1)
```

**Then switch to Loopback0:**
```
DUT1(config)# no ntp source-interface
DUT1(config)# ntp source-interface Loopback 0
```
*(Repeat Scapy capture — source IP should now be 1.1.1.1)*

---

### 9.8 NTP VRF Binding

---

#### TC_NTP_VRF_001 — Bind NTP to management VRF `[VS/HW]`

**Objective:** Verify `ntp vrf mgmt` binds NTP traffic to the management VRF.

**Pre-condition:** Management VRF exists on DUT1.

**Steps:**
```
DUT1(config)# ntp vrf mgmt
DUT1# show ntp global
```

**Expected Output:**
```
  Vrf:   mgmt
```

**Cleanup:** `no ntp vrf`

---

#### TC_NTP_VRF_002 — Bind NTP to default VRF `[VS]`

**Steps:**
```
DUT1(config)# ntp vrf default
DUT1# show ntp global
```

**Expected Output:**
```
  Vrf:   default
```

**Cleanup:** `no ntp vrf`

---

#### TC_NTP_VRF_003 — Remove VRF binding `[VS]`

**Objective:** Verify `no ntp vrf` removes the VRF binding and reverts to default.

**Steps:**
```
DUT1(config)# ntp vrf mgmt
DUT1# show ntp global
! Verify Vrf: mgmt
DUT1(config)# no ntp vrf
DUT1# show ntp global
```

**Expected Output after removal:**
```
  Vrf:   default
```

---

#### TC_NTP_VRF_004 — NTP sync via management VRF `[VS/HW]`

**Objective:** Verify NTP synchronisation functions correctly when bound to `mgmt` VRF with NTP-SRV reachable via management network.

**Pre-condition:** NTP-SRV (192.168.100.10) is reachable via management VRF.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp vrf mgmt
DUT1(config)# ntp server 192.168.100.10 iburst
! Wait 60s
DUT1# show ntp associations
```

**Expected Output:** `*192.168.100.10` selected in associations.

---

### 9.9 Show Commands Validation

---

#### TC_NTP_SHOW_001 — `show ntp global` reflects all configured parameters `[VS]`

**Objective:** Verify `show ntp global` accurately reflects all global NTP parameters simultaneously.

**Setup:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authenticate
DUT1(config)# ntp vrf mgmt
DUT1(config)# ntp source-interface Management 0
```

**Steps:**
```
DUT1# show ntp global
```

**Expected Output:**
```
NTP Configuration:
  Enabled:             True
  Authentication:      True
  Vrf:                 mgmt
  Source Interface:    Management0
```

**Verification:** All four fields show correct values simultaneously.

**Cleanup:**
```
DUT1(config)# no ntp enable
DUT1(config)# no ntp authenticate
DUT1(config)# no ntp vrf
DUT1(config)# no ntp source-interface
```

---

#### TC_NTP_SHOW_002 — `show ntp server` displays all server parameters `[VS]`

**Objective:** Verify `show ntp server` shows all configured per-server options correctly.

**Setup:**
```
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp server 192.168.100.10 version 4 association server iburst key 1 prefer
DUT1(config)# ntp server 192.168.100.11 version 3
DUT1(config)# ntp server 2001:db8::1 association pool iburst
```

**Steps:**
```
DUT1# show ntp server
```

**Expected Output:**
```
NTP Servers:
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       enabled  True     1
  192.168.100.11    3        server       disabled False    -
  2001:db8::1       4        pool         enabled  False    -
```

**Verification:** All three entries; all columns accurate.

---

#### TC_NTP_SHOW_003 — `show ntp associations` during active sync `[VS/HW]`

**Objective:** Verify association table shows `*` prefix, stratum, reach=377, and valid delay/offset/jitter when fully synchronised.

**Pre-condition:** DUT1 is synchronised with NTP-SRV.

**Steps:**
```
DUT1# show ntp associations
```

**Expected Output:**
```
NTP Associations:
  refid           st t when poll reach  delay  offset  jitter
  =================================================================
 *192.168.100.10  2  u  128 1024  377  10.234 -0.233  1.243
```

**Verification:**
- `*` prefix present on selected server
- `reach = 377` (octal — all 8 polls received)
- `st` (stratum) is a number 1–15
- `delay`, `offset`, `jitter` are numeric values

---

#### TC_NTP_SHOW_004 — `show ntp associations` before NTP is enabled `[VS]`

**Objective:** Verify `show ntp associations` returns a clear message when NTP is disabled.

**Pre-condition:** NTP is disabled.

**Steps:**
```
DUT1# show ntp associations
```

**Expected Output:**
```
% NTP is not enabled
```
or:
```
NTP Associations:
  (empty)
```

---

#### TC_NTP_SHOW_005 — `show ntp associations` with multiple servers `[VS/HW]`

**Objective:** Verify multiple servers appear in the associations table with correct prefixes:
- `*` — currently selected source
- `+` — candidate peer (acceptable)
- ` ` (space) — configured but not selected

**Pre-condition:** Two NTP servers configured; NTP-SRV is primary (prefer).

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 prefer iburst
DUT1(config)# ntp server 192.168.100.11 iburst
! Wait 60s
DUT1# show ntp associations
```

**Expected Output:**
```
 *192.168.100.10   2  u  ...  377  ...
  192.168.100.11   2  u  ...  377  ...
```
*(192.168.100.10 selected due to `prefer`)*

---

### 9.10 NTP Synchronisation Validation

---

#### TC_NTP_SYNC_001 — Basic synchronisation with IPv4 NTP server `[VS/HW]`

**Objective:** Verify DUT1 synchronises with NTP-SRV (IPv4) within 60 seconds.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 iburst
! Wait up to 60s
DUT1# show ntp associations
```

**Expected:** `*192.168.100.10` in associations.

**Additional Verification:**
```bash
# On DUT1 shell
date
# Verify the time matches NTP-SRV
ssh admin@192.168.100.10 date
```

---

#### TC_NTP_SYNC_002 — Synchronisation with iburst for faster initial sync `[VS/HW]`

**Objective:** Verify `iburst` achieves synchronisation in under 15 seconds (vs ~60s without iburst).

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 iburst
! Start timer
! Poll show ntp associations every 5 seconds
DUT1# show ntp associations
```

**Expected:** `*192.168.100.10` appears within 15 seconds of enabling NTP.

---

#### TC_NTP_SYNC_003 — Prefer server selection `[VS/HW]`

**Objective:** Verify `prefer` flag causes DUT1 to select the preferred server when multiple are available.

**Pre-condition:** Two NTP servers available (192.168.100.10 and 192.168.100.11), both reachable.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10
DUT1(config)# ntp server 192.168.100.11 iburst prefer
! Wait 60s
DUT1# show ntp associations
```

**Expected:** `*192.168.100.11` is selected (prefer flag wins even if 192.168.100.10 has better metrics).

---

#### TC_NTP_SYNC_004 — Synchronisation using NTPv3 `[VS/HW]`

**Objective:** Verify NTPv3 protocol version option functions correctly.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 version 3 iburst
! Wait 60s
DUT1# show ntp associations
```

**Expected:** Server synchronises using version 3 packets (verifiable via Scapy — NTP version field in packet = 3).

---

#### TC_NTP_SYNC_005 — Synchronisation failover to secondary server `[VS/HW]`

**Objective:** Verify DUT1 fails over to the secondary server when the primary becomes unreachable.

**Pre-condition:** Two servers: NTP-SRV (primary, 192.168.100.10) and a second reachable NTP server (192.168.100.11).

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 iburst prefer
DUT1(config)# ntp server 192.168.100.11 iburst
! Wait for sync with primary
DUT1# show ntp associations  ! Verify *192.168.100.10
! Simulate primary outage (stop chronyd on NTP-SRV or block port 123)
# On NTP-SRV: sudo systemctl stop chronyd
! Wait 120s
DUT1# show ntp associations
```

**Expected:** DUT1 fails over to `*192.168.100.11`.

---

#### TC_NTP_SYNC_006 — Pool association type syncs from pool member `[VS/HW]`

**Objective:** Verify `association pool` resolves DNS pool hostname and synchronises from a pool member.

**Pre-condition:** DNS resolution available for `pool.ntp.org` or a local pool server.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server pool.ntp.org association pool iburst
! Wait 90s
DUT1# show ntp associations
```

**Expected:** One or more pool members appear in associations table with `*` on selected member.

---

### 9.11 Scapy Traffic-Based Tests

---

#### TC_NTP_TRAFFIC_001 — Verify NTP client packets use UDP port 123 `[VS/HW]`

**Objective:** Use Scapy on NTP-SRV to capture NTP requests from DUT1 and verify they use UDP port 123.

**Scapy Script (on NTP-SRV):**
```python
# tc_ntp_traffic_001.py
from scapy.all import *
from scapy.layers.ntp import NTP

print("Capturing NTP packets...")
pkts = sniff(
    iface="eth0",
    filter=f"udp port 123 and src host 192.168.100.1",
    count=3,
    timeout=30
)

assert len(pkts) >= 1, "FAIL: No NTP packets received from DUT1"
for p in pkts:
    assert p[UDP].dport == 123, f"FAIL: Wrong destination port {p[UDP].dport}"
    assert p.haslayer(NTP) or p[UDP].dport == 123, "FAIL: Not an NTP packet"
    print(f"PASS: NTP packet from {p[IP].src}:{p[UDP].sport} → port 123")
    print(f"      NTP version: {p[NTP].version if p.haslayer(NTP) else 'N/A'}")
```

**Expected:**
```
PASS: NTP packet from 192.168.100.1:xxxxx → port 123
      NTP version: 4
```

---

#### TC_NTP_TRAFFIC_002 — Verify NTP packet version matches configured version `[VS/HW]`

**Objective:** Verify that NTP packets sent by DUT1 use the version specified in `ntp server ... version`.

**Steps on DUT1:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 version 3 iburst
```

**Scapy Script (on NTP-SRV):**
```python
# tc_ntp_traffic_002.py
from scapy.all import *
from scapy.layers.ntp import NTP

pkts = sniff(iface="eth0", filter="udp port 123 and src host 192.168.100.1",
             count=3, timeout=30)

for p in pkts:
    if p.haslayer(NTP):
        ver = p[NTP].version
        assert ver == 3, f"FAIL: Expected NTP version 3, got {ver}"
        print(f"PASS: NTP version = {ver}")
```

---

#### TC_NTP_TRAFFIC_003 — Verify source IP in NTP packets matches source-interface `[VS/HW]`

**Objective:** Validate that when `ntp source-interface Loopback 0` is configured, NTP packets carry Loopback0's IP (1.1.1.1) as the source.

**Pre-condition:** DUT1 has Loopback0 = 1.1.1.1/32 and route to NTP-SRV via this address is configured.

**Scapy Script (on NTP-SRV):**
```python
# tc_ntp_traffic_003.py
from scapy.all import *

pkts = sniff(iface="eth0", filter="udp port 123", count=3, timeout=30)
for p in pkts:
    if IP in p:
        src = p[IP].src
        assert src == "1.1.1.1", f"FAIL: Expected src 1.1.1.1, got {src}"
        print(f"PASS: NTP source IP = {src}")
```

---

#### TC_NTP_TRAFFIC_004 — Verify NTP mode field (client mode = 3) in outgoing packets `[VS/HW]`

**Objective:** Verify DUT1 sends NTP client-mode (mode=3) packets to the server.

**Scapy Script (on NTP-SRV):**
```python
# tc_ntp_traffic_004.py
from scapy.all import *
from scapy.layers.ntp import NTP

pkts = sniff(iface="eth0", filter="udp port 123 and src host 192.168.100.1",
             count=3, timeout=30)

for p in pkts:
    if p.haslayer(NTP):
        mode = p[NTP].mode
        assert mode == 3, f"FAIL: Expected NTP mode 3 (client), got {mode}"
        print(f"PASS: NTP mode = {mode} (client)")
```

---

#### TC_NTP_TRAFFIC_005 — Verify NTP server replies with mode 4 (server mode) `[VS/HW]`

**Objective:** Verify NTP-SRV responds to DUT1 with NTP mode=4 (server) packets.

**Scapy Script (on NTP-SRV — capture outgoing replies to DUT1):**
```python
# tc_ntp_traffic_005.py
from scapy.all import *
from scapy.layers.ntp import NTP

pkts = sniff(iface="eth0", filter="udp port 123 and dst host 192.168.100.1",
             count=3, timeout=30)

for p in pkts:
    if p.haslayer(NTP):
        mode = p[NTP].mode
        assert mode == 4, f"FAIL: Expected NTP server mode 4, got {mode}"
        print(f"PASS: NTP server reply mode = {mode}")
```

---

#### TC_NTP_TRAFFIC_006 — Verify iburst sends multiple packets at startup `[VS/HW]`

**Objective:** Verify that when `iburst` is configured, DUT1 sends a burst of NTP packets during initial synchronisation (at least 8 packets in quick succession on first contact).

**Scapy Script (on NTP-SRV — run before enabling NTP on DUT1):**
```python
# tc_ntp_traffic_006.py
from scapy.all import *
import time

start = time.time()
pkts = sniff(iface="eth0", filter="udp port 123 and src host 192.168.100.1",
             timeout=10)  # capture for 10 seconds

elapsed = time.time() - start
print(f"Captured {len(pkts)} NTP packets in {elapsed:.1f}s")
assert len(pkts) >= 6, f"FAIL: Expected burst >=6 packets, got {len(pkts)}"
print("PASS: iburst confirmed — multiple packets sent at startup")
```

---

#### TC_NTP_TRAFFIC_007 — Verify NTP traffic stops after `no ntp enable` `[VS/HW]`

**Objective:** Verify that after `no ntp enable`, DUT1 stops sending NTP UDP packets.

**Steps on DUT1:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp server 192.168.100.10 iburst
! Wait for sync
DUT1(config)# no ntp enable
```

**Scapy Script (on NTP-SRV — run after no ntp enable):**
```python
# tc_ntp_traffic_007.py
from scapy.all import *

pkts = sniff(iface="eth0", filter="udp port 123 and src host 192.168.100.1",
             timeout=30)

assert len(pkts) == 0, f"FAIL: Still receiving NTP packets after disable ({len(pkts)} pkts)"
print("PASS: No NTP packets received after 'no ntp enable'")
```

---

### 9.12 Configuration Persistence

---

#### TC_NTP_PERSIST_001 — Full NTP config persists after `config save` and daemon restart `[VS/HW]`

**Objective:** Verify all NTP configuration is preserved after saving running config and restarting the NTP daemon.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authenticate
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp server 192.168.100.10 iburst key 1 prefer
DUT1(config)# ntp source-interface Management 0
DUT1(config)# ntp vrf mgmt
DUT1(config)# exit
DUT1# write memory
! Restart NTP daemon
DUT1# sudo systemctl restart ntp
! Or trigger config reload
DUT1# show ntp global
DUT1# show ntp server
```

**Expected Output — `show ntp global`:**
```
  Enabled:             True
  Authentication:      True
  Vrf:                 mgmt
  Source Interface:    Management0
```

**Expected Output — `show ntp server`:**
```
  Address           Version  Association  Iburst   Prefer   Key
  192.168.100.10    4        server       enabled  True     1
```

---

#### TC_NTP_PERSIST_002 — NTP config persists across system reboot `[HW]`

**Objective:** Verify NTP configuration survives a full system reboot.

**Steps:**
```
DUT1# write memory
DUT1# sudo reboot
! Wait for system to come back up
DUT1# show ntp global
DUT1# show ntp server
DUT1# show ntp associations
```

**Expected:** All configuration persists; NTP re-synchronises automatically after reboot.

---

#### TC_NTP_PERSIST_003 — `show running-config` accurately reflects NTP state `[VS]`

**Objective:** Verify `show running-config` section for NTP contains all configured parameters.

**Setup:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authenticate
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp server 192.168.100.10 version 4 iburst key 1 prefer
DUT1(config)# ntp source-interface Management 0
DUT1(config)# ntp vrf mgmt
```

**Steps:**
```
DUT1# show running-config | grep -A 20 "ntp"
```

**Expected Output contains:**
```
ntp enable
ntp authenticate
ntp authentication-key 1 md5 <hashed or plaintext>
ntp trusted-key 1
ntp server 192.168.100.10 version 4 iburst key 1 prefer
ntp source-interface Management 0
ntp vrf mgmt
```

---

#### TC_NTP_PERSIST_004 — NTP resumes sync after NTP daemon restart (no reboot) `[VS/HW]`

**Objective:** Verify NTP re-synchronises automatically after the NTP daemon process is restarted without a full system reboot.

**Steps:**
```
! Verify initial sync
DUT1# show ntp associations   ! should show * on 192.168.100.10
! Restart NTP daemon (not whole system)
DUT1(shell)# sudo systemctl restart ntp
! Wait 60s
DUT1# show ntp associations
```

**Expected:** `*192.168.100.10` reappears within 60 seconds.

---

### 9.13 Negative / Error Handling

---

#### TC_NTP_NEG_001 — Enable NTP with no server configured `[VS]`

**Objective:** Verify system behaves gracefully when NTP is enabled with no servers configured.

**Steps:**
```
DUT1(config)# ntp enable
DUT1# show ntp associations
```

**Expected:** Empty associations table or informational message like "No NTP servers configured". No crash or error.

---

#### TC_NTP_NEG_002 — Remove non-existent NTP server `[VS]`

**Objective:** Verify `no ntp server` for an unconfigured server returns a clear error.

**Steps:**
```
DUT1(config)# no ntp server 10.99.99.99
```

**Expected:** Error message such as `% NTP server 10.99.99.99 not found` or `% Entry not found`.

---

#### TC_NTP_NEG_003 — Configure auth key with invalid key ID `[VS]`

**Objective:** Verify key IDs outside the valid range (1–65535) are rejected.

**Steps:**
```
DUT1(config)# ntp authentication-key 0 md5 TestPass
DUT1(config)# ntp authentication-key 65536 md5 TestPass
```

**Expected:** Both commands rejected with appropriate error messages.

---

#### TC_NTP_NEG_004 — Trust a key ID that has no authentication-key defined `[VS]`

**Objective:** Verify that `ntp trusted-key` for an undefined key ID is rejected.

**Steps:**
```
DUT1(config)# ntp trusted-key 99
```

**Expected:** Error message such as `% Authentication key 99 is not defined`.

---

#### TC_NTP_NEG_005 — Assign server key binding to undefined key ID `[VS]`

**Objective:** Verify that `ntp server ... key <id>` with an undefined key ID is rejected.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 key 99
```

**Expected:** Error: key 99 is not defined, or the configuration is rejected.

---

#### TC_NTP_NEG_006 — Delete auth key while it is referenced by a trusted-key `[VS]`

**Objective:** Verify the system warns or handles gracefully when deleting a key that is still trusted.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 MySecret123
DUT1(config)# ntp trusted-key 1
DUT1(config)# no ntp authentication-key 1
DUT1# show ntp global
```

**Expected:** Either:
- An error preventing deletion while trusted
- A warning that the key is referenced by trusted-key 1
- The key is removed but a warning is logged

**Verification:** System remains stable; no crash. Trusted-key reference state is documented.

---

#### TC_NTP_NEG_007 — Configure invalid VRF name for NTP `[VS]`

**Objective:** Verify that `ntp vrf` with a non-existent VRF name is rejected.

**Steps:**
```
DUT1(config)# ntp vrf nonexistent_vrf
```

**Expected:** Error message such as `% VRF 'nonexistent_vrf' not found`.

---

#### TC_NTP_NEG_008 — Configure source interface that does not exist `[VS]`

**Objective:** Verify that `ntp source-interface` referencing a non-existent interface is rejected or handled gracefully.

**Steps:**
```
DUT1(config)# ntp source-interface Loopback 999
```

**Expected:** Error or warning that the interface does not exist. Configuration may not be stored or is stored with a warning.

---

### 9.14 Scale & Stress

---

#### TC_NTP_SCALE_001 — Configure maximum number of NTP servers `[VS]`

**Objective:** Verify the system accepts the maximum supported number of NTP server entries without error.

**Note:** SONiC typically supports up to 10 NTP servers. Confirm the actual limit from the platform documentation.

**Steps:**
```bash
# Use a loop to add 10 NTP servers
for i in $(seq 1 10); do
    sonic-cli -c "configure terminal" -c "ntp server 192.168.1.$i"
done
```

```
DUT1# show ntp server
```

**Expected:** All 10 servers listed. No error up to the maximum count.

---

#### TC_NTP_SCALE_002 — Configure maximum number of authentication keys `[VS]`

**Objective:** Verify a large number of auth keys (e.g., 50) can be configured.

**Steps:**
```bash
for i in $(seq 1 50); do
    sonic-cli -c "configure terminal" \
              -c "ntp authentication-key $i md5 Password$i" \
              -c "ntp trusted-key $i"
done
```

```
DUT1# show ntp global
```

**Expected:** System accepts all 50 keys without degradation or error.

**Cleanup:** Remove all keys in a loop.

---

#### TC_NTP_SCALE_003 — Rapid NTP enable/disable cycles `[VS]`

**Objective:** Verify system stability when NTP is toggled rapidly.

**Steps:**
```bash
for i in $(seq 1 20); do
    sonic-cli -c "configure terminal" -c "ntp enable"
    sleep 1
    sonic-cli -c "configure terminal" -c "no ntp enable"
    sleep 1
done
```

**Expected:** System remains stable throughout; no daemon crash; show commands work after each cycle.

---

#### TC_NTP_SCALE_004 — Concurrent configuration of all NTP parameters `[VS]`

**Objective:** Apply the complete NTP configuration (all parameters) in a single configuration session and verify correctness.

**Steps:**
```
DUT1(config)# ntp enable
DUT1(config)# ntp authenticate
DUT1(config)# ntp authentication-key 1 md5 Pass1
DUT1(config)# ntp authentication-key 2 sha256 Pass2
DUT1(config)# ntp authentication-key 3 sha512 Pass3
DUT1(config)# ntp trusted-key 1
DUT1(config)# ntp trusted-key 2
DUT1(config)# ntp trusted-key 3
DUT1(config)# ntp server 192.168.100.10 version 4 iburst key 1 prefer
DUT1(config)# ntp server 192.168.100.11 version 4 key 2
DUT1(config)# ntp server 192.168.100.12 version 3
DUT1(config)# ntp source-interface Management 0
DUT1(config)# ntp vrf mgmt
DUT1# show ntp global
DUT1# show ntp server
```

**Expected:** All parameters reflected accurately; no partial config or errors.

---

#### TC_NTP_SCALE_005 — High-frequency Scapy NTP packet injection toward DUT1 `[VS/HW]`

**Objective:** Verify DUT1 remains stable when flooded with NTP UDP packets from NTP-SRV (simulates high-rate external NTP traffic).

**Scapy Script (on NTP-SRV):**
```python
# tc_ntp_scale_005.py
from scapy.all import *
from scapy.layers.ntp import NTP

DUT1_IP = "192.168.100.1"
NTP_PORT = 123

pkt = (
    IP(dst=DUT1_IP) /
    UDP(dport=NTP_PORT) /
    NTP(version=4, mode=4)   # server reply mode
)

print("Sending 1000 NTP packets to DUT1...")
sendp([pkt] * 1000, iface="eth0", inter=0.001, verbose=False)
print("Done. Verify DUT1 stability with 'show ntp global'")
```

**Steps on DUT1 (after flood):**
```
DUT1# show ntp global
DUT1# show ntp associations
```

**Expected:** DUT1 remains responsive; NTP daemon is not crashed; associations are still showing valid state.

---

### 9.15 Interaction & Edge Cases

---

#### TC_NTP_EDGE_001 — Configure server key binding before defining auth key `[VS]`

**Objective:** Verify the order dependency: adding a server with `key <id>` before defining `ntp authentication-key <id>` — determine if this is allowed or rejected.

**Steps:**
```
DUT1(config)# ntp server 192.168.100.10 key 5
! Key 5 not yet defined
DUT1# show ntp server
```

**Expected:** Either error (rejected — key not defined) or accepted with warning. Document the actual behaviour.

---

#### TC_NTP_EDGE_002 — Change auth key type for an already-trusted key `[VS]`

**Objective:** Verify that updating the algorithm for a trusted key (e.g., md5 → sha256) does not leave the trusted-key in an inconsistent state.

**Steps:**
```
DUT1(config)# ntp authentication-key 1 md5 Pass1
DUT1(config)# ntp trusted-key 1
! Now change the type
DUT1(config)# ntp authentication-key 1 sha256 Pass2
DUT1# show ntp global
```

**Expected:** Key 1 is updated to sha256; trusted-key 1 still valid. Synchronisation with NTP-SRV continues if sha256 matches on both sides.

---

#### TC_NTP_EDGE_003 — VRF change while NTP is synchronised `[VS/HW]`

**Objective:** Verify that changing the NTP VRF binding while NTP is actively synchronised causes NTP to re-establish synchronisation via the new VRF.

**Pre-condition:** DUT1 is synchronised via default VRF.

**Steps:**
```
DUT1# show ntp associations   ! * on server
DUT1(config)# ntp vrf mgmt
! Wait 60s
DUT1# show ntp associations
```

**Expected:** NTP re-synchronises via mgmt VRF; associations table still shows selected server.

---

#### TC_NTP_EDGE_004 — Source interface removal while NTP is synchronised `[VS/HW]`

**Objective:** Verify that removing `ntp source-interface` does not permanently break NTP; it should fall back to routing-table-based source selection.

**Steps:**
```
DUT1(config)# ntp source-interface Loopback 0
! Wait for sync (show ntp associations — * present)
DUT1(config)# no ntp source-interface
! Wait 60s
DUT1# show ntp associations
```

**Expected:** NTP continues to synchronise (or re-synchronises) using the default source IP selection.

---

#### TC_NTP_EDGE_005 — Server removed while synchronised, fallback to second server `[VS/HW]`

**Objective:** Verify that removing the currently selected server entry causes NTP to fail over to an alternative configured server.

**Pre-condition:** Two servers configured; DUT1 is synced to primary (192.168.100.10).

**Steps:**
```
DUT1# show ntp associations   ! * on 192.168.100.10
DUT1(config)# no ntp server 192.168.100.10
! Wait 60s
DUT1# show ntp associations
```

**Expected:** `*192.168.100.11` (secondary) becomes the selected source.

---

## 10. Pass / Fail Criteria

### Pass Criteria

A test case **passes** if all of the following are true:

- All CLI commands execute without errors (unless testing negative scenarios)
- `show ntp global` accurately reflects configured state (Enabled, Authentication, VRF, Source Interface)
- `show ntp server` displays all server entries with correct per-server parameters
- `show ntp associations` shows `*` prefix on the selected server within the specified convergence time
- `reach` value in associations reaches `377` (all 8 polls succeeded) within 5 poll intervals
- Scapy assertions pass: correct source IP, correct NTP version, correct UDP port, correct NTP mode
- Configuration persists after daemon restart or system reboot
- System remains stable (no crash, no hang, responsive to CLI) after scale/stress tests

### Fail Criteria

A test case **fails** if any of the following occur:

- CLI command returns an unexpected error (for positive test cases)
- `show` command output does not match expected values
- NTP fails to synchronise within the specified timeout
- Scapy captures packets with wrong source IP, version, or NTP mode
- Authentication test cases synchronise when they should be blocked (or vice versa)
- System becomes unresponsive or NTP daemon crashes
- Configuration is lost after daemon restart or reboot
- `reach` stays at `0` or stays below `100` (decimal) beyond 5 poll intervals

---

## 11. Execution Schedule

| Phase | Test Cases | Area | Duration |
|-------|-----------|------|---------|
| Phase 1 | TC_NTP_ENABLE_001–003 | NTP Enable/Disable | 1 hour |
| Phase 2 | TC_NTP_SERVER_001–010 | Server Configuration | 2 hours |
| Phase 3 | TC_NTP_AUTHKEY_001–007 | Authentication Keys | 1.5 hours |
| Phase 4 | TC_NTP_TRUSTED_001–004 | Trusted Keys | 1 hour |
| Phase 5 | TC_NTP_AUTH_ENF_001–003 | Auth Enforcement | 1 hour |
| Phase 6 | TC_NTP_AUTHWF_001–005 | Full Auth Workflow | 3 hours |
| Phase 7 | TC_NTP_SRC_001–006 | Source Interface | 1.5 hours |
| Phase 8 | TC_NTP_VRF_001–004 | VRF Binding | 1.5 hours |
| Phase 9 | TC_NTP_SHOW_001–005 | Show Commands | 1 hour |
| Phase 10 | TC_NTP_SYNC_001–006 | Sync Validation | 3 hours |
| Phase 11 | TC_NTP_TRAFFIC_001–007 | Scapy Traffic Tests | 3 hours |
| Phase 12 | TC_NTP_PERSIST_001–004 | Config Persistence | 2 hours |
| Phase 13 | TC_NTP_NEG_001–008 | Negative / Error | 1.5 hours |
| Phase 14 | TC_NTP_SCALE_001–005 | Scale & Stress | 2.5 hours |
| Phase 15 | TC_NTP_EDGE_001–005 | Edge Cases | 2 hours |
| **TOTAL** | **72 test cases** | | **28 hours** |

---

## 12. Deliverables

- Test execution log for each test case (pass/fail with actual vs expected output)
- `show ntp global`, `show ntp server`, `show ntp associations` dumps for each test
- Scapy PCAP files: `/tmp/ntp_capture_<tc_id>.pcap` for all traffic-based tests
- Defect reports (bug IDs) for all failures
- Summary report with pass/fail statistics by functional area
- Authentication matrix — which key types (md5/sha1/sha256/sha384/sha512) passed end-to-end sync

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| NTP-SRV chronyd does not support all hash types | Medium | Use chrony 4.x+ which supports SHA256/384/512; fall back to ntpd if needed |
| VS environment clock drift affects timing tests | Medium | Use `iburst` and longer timeouts; mark timing-sensitive tests as [HW] |
| DNS resolution unavailable for FQDN tests | Low | Add local `/etc/hosts` entries on DUT1 for FQDN test cases |
| Management VRF not configured on VS | Medium | Set up VRF in pre-test setup; skip TC_NTP_VRF_004 if not available |
| NTP sync tests take longer on VS due to clock accuracy | Medium | Extend timeout to 120s for VS sync tests; poll every 10s |
| Scapy on NTP-SRV cannot capture if interface is bridged | Low | Ensure promiscuous mode enabled: `sudo ip link set eth0 promisc on` |
| Key deletion with trusted-key reference may crash daemon | High | Test in isolated environment; capture syslog during TC_NTP_NEG_006 |

---

## 14. References

- [RFC 2328] — OSPFv2 (for protocol context)
- [RFC 5905] — Network Time Protocol Version 4
- [RFC 8633] — NTP Best Current Practices
- SONiC NTP CLI XML: `ntp.xml` (provided)
- chrony documentation: https://chrony.tuxfamily.org/documentation.html
- Scapy NTP layer: `scapy.layers.ntp`
- SONiC CLI Reference Guide

---

*End of NTP Test Plan — Version 1.0*
