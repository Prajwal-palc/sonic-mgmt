# OSPFv2 System Test Plan
### Platform: SONiC / D-Link DUT · Spytest Framework · Community SONiC

---

## Table of Contents
1. [Overview](#1-overview)
2. [Topology](#2-topology)
3. [IP Addressing and Interface Plan](#3-ip-addressing-and-interface-plan)
4. [Software and Framework Requirements](#4-software-and-framework-requirements)
5. [Spytest Conventions Used in This Plan](#5-spytest-conventions-used-in-this-plan)
6. [Test Cases — Basic Adjacency and Hello](#6-test-cases--basic-adjacency-and-hello)
7. [Test Cases — LSA Types and LSDB](#7-test-cases--lsa-types-and-lsdb)
8. [Test Cases — Area Types](#8-test-cases--area-types)
9. [Test Cases — Route Types and SPF](#9-test-cases--route-types-and-spf)
10. [Test Cases — Authentication](#10-test-cases--authentication)
11. [Test Cases — BFD Integration](#11-test-cases--bfd-integration)
12. [Test Cases — Route Redistribution and Summarization](#12-test-cases--route-redistribution-and-summarization)
13. [Test Cases — Traffic Forwarding (Scapy)](#13-test-cases--traffic-forwarding-scapy)
14. [Test Cases — Negative Cases](#14-test-cases--negative-cases)
15. [Test Cases — Corner Cases](#15-test-cases--corner-cases)
16. [Test Cases — Persistence Cases](#16-test-cases--persistence-cases)
17. [Test Cases — Scaling Cases](#17-test-cases--scaling-cases)
18. [Appendix A — CLI Reference](#appendix-a--cli-reference)
19. [Appendix B — Scapy Snippets](#appendix-b--scapy-snippets)

---

## 1. Overview

This document defines the system-level test plan for OSPFv2 feature validation on SONiC/D-Link DUTs using the **Spytest** framework from the community SONiC project. Tests cover functional correctness, protocol compliance (RFC 2328), traffic forwarding, negative behavior, corner cases, persistence after reloads/failovers, and scaling limits.

**DUT**: SONiC (FRR-based OSPF) or D-Link network OS  
**Supporting devices**: Broadcom or D-Link boxes acting as traffic generator (TGen) with **Scapy** APIs from the Spytest framework  
**Test framework**: Spytest (community SONiC) — `apis/routing/ospf.py`, `apis/traffic/scapy.py`

---

## 2. Topology

### 2.1 VS Topology — 4 Nodes

```
                    Area 0 — backbone (0.0.0.0)
         ┌──────────────────────────────────────────────────┐
         │                                                  │
[TGen]──P1──eth1──[ D1  ABR  ]──eth2──eth1──[ D2  ASBR  ] │
         │         SONiC/D-Link               SONiC/D-Link  │
         │         10.1.1.1/30               10.1.2.2/30   │
         └────────────────────────────────────────────────────┘
         P2 (traffic)  │eth3
                       │ Area 1 (0.0.0.1)
                 ┌─────┴──────────────┐
                 │ [ D3  Router  ]    │
                 │   SONiC/D-Link     │
                 │   10.1.3.2/30      │
                 └────────────────────┘
                        │eth2
                       P2──[TGen]  10.1.4.0/30 (traffic source)
```

| Node | Role | OS | Loopback | Area(s) |
|------|------|----|----------|---------|
| D1 | ABR | SONiC / D-Link | 1.1.1.1/32 | Area 0 + Area 1 |
| D2 | ASBR (ext route source) | SONiC / D-Link | 2.2.2.2/32 | Area 0 |
| D3 | Internal router | SONiC / D-Link | 3.3.3.3/32 | Area 1 |
| TGen | Traffic gen + Scapy OSPF emulation | Broadcom / D-Link | N/A | External |

**VS topology notes:**
- TGen can emulate OSPF neighbors using Scapy on P1 (Area 0) and P2 (Area 1).
- D2 redistributes connected/static routes as Type-5 LSAs.
- D1 performs ABR summarization and Type-3/4 LSA origination.
- All 4 nodes can be brought up as Docker containers in VS mode.

### 2.2 HW Topology — Minimum (2 DUTs + 1 TGen)

```
  ┌─────────────────────────────────┐
  │  TGen (Scapy / Broadcom/D-Link) │
  │  P1 ──── (Area 0) ──── eth1 ──── D1 (ABR) ──── eth2 ──── eth1 ──── D2
  │  P3 ──── (Area 1) ──── eth3 ────  SONiC            SONiC/D-Link
  │  P2 ──── (traffic) ────────────────────────────── eth2 ────────────────
  └─────────────────────────────────┘
           Scapy emulates OSPF peer(s)
```

| Node | Role | OS | Physical Ports |
|------|------|----|----------------|
| D1 | ABR | SONiC / D-Link | eth1 (Area0 to TGen), eth2 (Area0 to D2), eth3 (Area1 to TGen) |
| D2 | Router / ASBR | SONiC / D-Link | eth1 (Area0 to D1), eth2 (traffic to TGen) |
| TGen | Traffic gen + Scapy | Broadcom / D-Link | P1→D1:eth1, P2→D2:eth2, P3→D1:eth3 |

**HW topology notes:**
- TGen acts as an OSPF neighbor (via Scapy) on P1 (Area 0) and P3 (Area 1).
- TGen:P2 is the pure traffic source/sink for forwarding validation.
- Only 2 physical DUT cables (D1–D2) are required; TGen handles OSPF emulation on the remaining links.
- Management (OOB) network required for all 3 devices.

---

## 3. IP Addressing and Interface Plan

### VS Topology

| Link | DUT | Interface | IP Address | Area |
|------|-----|-----------|------------|------|
| TGen:P1 ↔ D1 | D1 | Ethernet0 | 10.1.1.2/30 | 0.0.0.0 |
| TGen:P1 ↔ D1 | TGen | eth1 | 10.1.1.1/30 | — |
| D1 ↔ D2 | D1 | Ethernet4 | 10.1.2.1/30 | 0.0.0.0 |
| D1 ↔ D2 | D2 | Ethernet0 | 10.1.2.2/30 | 0.0.0.0 |
| D1 ↔ D3 | D1 | Ethernet8 | 10.1.3.1/30 | 0.0.0.1 |
| D1 ↔ D3 | D3 | Ethernet0 | 10.1.3.2/30 | 0.0.0.1 |
| TGen:P2 ↔ D3 | D3 | Ethernet4 | 10.1.4.2/30 | — |
| TGen:P2 ↔ D3 | TGen | eth2 | 10.1.4.1/30 | — |
| D1 loopback | D1 | lo | 1.1.1.1/32 | 0.0.0.0 |
| D2 loopback | D2 | lo | 2.2.2.2/32 | 0.0.0.0 |
| D3 loopback | D3 | lo | 3.3.3.3/32 | 0.0.0.1 |

### HW Topology

| Link | DUT | Interface | IP Address | Area |
|------|-----|-----------|------------|------|
| TGen:P1 ↔ D1 | D1 | Ethernet0 | 10.1.1.2/30 | 0.0.0.0 |
| TGen:P3 ↔ D1 | D1 | Ethernet8 | 10.1.3.2/30 | 0.0.0.1 |
| D1 ↔ D2 | D1 | Ethernet4 | 10.1.2.1/30 | 0.0.0.0 |
| D1 ↔ D2 | D2 | Ethernet0 | 10.1.2.2/30 | 0.0.0.0 |
| TGen:P2 ↔ D2 | D2 | Ethernet4 | 10.1.4.2/30 | — |
| D1 loopback | D1 | lo | 1.1.1.1/32 | 0.0.0.0 |
| D2 loopback | D2 | lo | 2.2.2.2/32 | 0.0.0.0 |

### External / redistributed prefix pools

| Pool Name | Prefix | Purpose |
|-----------|--------|---------|
| EXT-POOL-1 | 172.16.0.0/24 | Static routes redistributed into OSPF as Type-5 LSA from D2 |
| EXT-POOL-2 | 192.168.0.0/24 | Connected routes redistributed from D2 |
| SUMMARY-1 | 10.1.0.0/16 | Summary advertised by ABR (D1) into Area 0 |

---

## 4. Software and Framework Requirements

| Component | Version / Notes |
|-----------|-----------------|
| SONiC image | 202305 or later with FRR ≥ 8.x |
| FRR | 8.4+ (bundled with SONiC) |
| Spytest | community SONiC spytest (`tests/routing/test_ospf*.py`) |
| Python | 3.9+ |
| Scapy | 2.5+ (installed on TGen or via `pip install scapy`) |
| pytest | 7.x |
| TGen OS | Broadcom SONIC or D-Link NOS with Scapy installable |

**Spytest modules used:**
```
apis/routing/ospf.py          — OSPF config and verification APIs
apis/routing/ip.py            — IP route table, prefix verification
apis/system/basic.py          — Reload, save, link flap helpers
apis/traffic/scapy.py         — Scapy-based packet send/receive
apis/routing/bgp.py           — Optional, for redistribution from BGP
```

---

## 5. Spytest Conventions Used in This Plan

All test functions follow the Spytest convention. Each TC maps to a function in `tests/routing/test_ospfv2_system.py`.

```python
import pytest
from spytest import st
from apis.routing import ospf as ospf_obj
from apis.routing import ip as ip_obj
from apis.traffic import scapy as tgen

# DUT fixture handles topo assignment
# 'dut1' → D1, 'dut2' → D2, 'dut3' → D3

def test_ospf_basic_adjacency(dut1, dut2):
    # Configure OSPF on dut1 and dut2
    ospf_obj.config_ospf_router(dut1, router_id='1.1.1.1', vrf='default')
    ospf_obj.config_ospf_network(dut1, network='10.1.1.0/30', area='0.0.0.0')
    # Verify adjacency
    result = ospf_obj.verify_ospf_neighbor(dut1, neighbor='10.1.2.2', state='Full')
    if result:
        st.report_pass('test_case_passed')
    else:
        st.report_fail('test_case_failed', 'Adjacency not reaching Full state')
```

**Scapy traffic send/receive pattern (via TGen):**
```python
from scapy.all import Ether, IP, ICMP, sendp, sniff

# Send traffic from TGen:P1 toward D3 via D1
pkt = Ether()/IP(src='10.1.1.1', dst='3.3.3.3')/ICMP()
tgen.send_packet(tgen_handle, port='P1', pkt=pkt, count=1000, rate_pps=100)
rx = tgen.capture_packets(tgen_handle, port='P2', timeout=10)
# Verify packet count
assert len(rx) >= 990, "Packet loss too high"
```

**Scapy OSPF emulation (neighbor bring-up on TGen):**
```python
from scapy.all import *
from scapy.contrib.ospf import *

# OSPF Hello from TGen to D1 (Area 0)
hello = (Ether(dst="01:00:5e:00:00:05") /
         IP(src="10.1.1.1", dst="224.0.0.5", ttl=1) /
         OSPF_Hdr(src="10.1.1.1", area="0.0.0.0") /
         OSPF_Hello(mask="255.255.255.252", hellointerval=10,
                    deadinterval=40, router="10.1.1.1"))
sendp(hello, iface="eth1", loop=1, inter=10)
```

---

## 6. Test Cases — Basic Adjacency and Hello

### TC-OSPF-001 — Two-router adjacency in Area 0 (Point-to-Point)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-001 |
| **Platform** | VS / HW |
| **Priority** | P1 (smoke) |
| **Topo** | D1 ↔ D2 on Area 0 link only |

**Pre-config:**
```bash
# D1
vtysh -c "conf t" -c "router ospf" -c "ospf router-id 1.1.1.1" \
      -c "network 10.1.2.0/30 area 0.0.0.0" -c "exit"

# D2
vtysh -c "conf t" -c "router ospf" -c "ospf router-id 2.2.2.2" \
      -c "network 10.1.2.0/30 area 0.0.0.0" -c "exit"
```

**Steps:**
1. Configure OSPF router IDs and network on D1 and D2.
2. Wait for hello/dead timer cycle (40 s).
3. Verify neighbor state on D1 reaches `Full`.
4. Verify neighbor state on D2 reaches `Full`.
5. Verify LSDB contains Router-LSA (Type-1) from both peers.

**Expected result:** Both D1 and D2 report neighbor state `Full`. LSDB contains Type-1 LSA from each router.

**Spytest API:**
```python
ospf_obj.verify_ospf_neighbor(dut1, neighbor='10.1.2.2', state='Full')
ospf_obj.verify_ospf_neighbor(dut2, neighbor='10.1.2.1', state='Full')
ospf_obj.verify_ospf_lsdb(dut1, lsa_type='router', adv_router='2.2.2.2')
```

---

### TC-OSPF-002 — DR/BDR election on broadcast network
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-002 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | TGen:P1 ↔ D1 on Area 0 (broadcast segment, TGen emulates a neighbor via Scapy) |

**Steps:**
1. Configure D1 `ip ospf priority 100` on Ethernet0 (highest priority → DR).
2. TGen sends OSPF Hello with priority=1 from 10.1.1.1.
3. Wait for 40 s dead interval.
4. Verify D1 is elected DR; TGen-emulated neighbor is BDR or DROTHER.
5. Verify Type-2 (Network) LSA is originated by the DR.

**Expected result:** D1 is DR. Network-LSA (Type-2) is present in LSDB with D1 as originator.

**CLI:**
```bash
show ip ospf interface Ethernet0     # shows DR/BDR/DROTHER role
show ip ospf database network        # verify Type-2 LSA
```

---

### TC-OSPF-003 — Adjacency with custom hello/dead timers
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-003 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | D1 ↔ D2 |

**Steps:**
1. Set hello-interval=5, dead-interval=20 on both D1 and D2 Ethernet4.
2. Bring up OSPF.
3. Verify adjacency reaches Full within 25 s.
4. Confirm hello-interval=5 in neighbor table.

**Expected result:** Adjacency formed with 5/20 timers. `show ip ospf neighbor` shows configured timers.

**CLI:**
```bash
interface Ethernet4
  ip ospf hello-interval 5
  ip ospf dead-interval 20
```

---

### TC-OSPF-004 — OSPF adjacency across VLAN subinterface
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-004 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | D1 ↔ D2 on VLAN 100 |

**Steps:**
1. Create VLAN 100 on D1 and D2; assign Ethernet4 as member.
2. Assign IP 10.1.2.1/30 on Vlan100 of D1, 10.1.2.2/30 on D2.
3. Configure OSPF `network 10.1.2.0/30 area 0`.
4. Verify Full adjacency.

**Expected result:** Full adjacency over VLAN subinterface. Route to D2 loopback appears in `show ip route ospf`.

---

### TC-OSPF-005 — OSPF passive interface
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-005 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | D1 with TGen on eth1 |

**Steps:**
1. Configure D1 with `passive-interface Ethernet0` under OSPF.
2. TGen sends OSPF Hellos on that interface.
3. Verify no OSPF neighbor is formed on D1 Ethernet0.
4. Verify the network is still advertised (Type-1 LSA bit set for the prefix).

**Expected result:** No OSPF adjacency formed on passive interface. The prefix is still advertised in LSDB.

---

## 7. Test Cases — LSA Types and LSDB

### TC-OSPF-011 — Type-1 (Router) LSA origination and flooding
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-011 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | Full VS topo (D1, D2, D3) |

**Steps:**
1. Bring up full adjacency between D1, D2 (Area 0) and D1, D3 (Area 1).
2. Verify Type-1 LSA from D1 present in both Area 0 and Area 1 LSDB.
3. Check D1 Type-1 LSA link count matches configured interfaces.

**Expected result:** Each router originates one Type-1 LSA per area. Link count correct. Sequence number increments on link-state change.

**CLI:**
```bash
show ip ospf database router             # view Type-1 LSAs
show ip ospf database router adv-router 1.1.1.1
```

---

### TC-OSPF-012 — Type-2 (Network) LSA on broadcast segment
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-012 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | D1 as DR on Area 0 broadcast link |

**Steps:**
1. Confirm D1 is DR on Area 0 link to D2.
2. Verify Type-2 LSA originated by D1 in LSDB.
3. Check Type-2 LSA attached routers match actual neighbors.

**Expected result:** Type-2 LSA present. Attached routers field matches all OSPF neighbors on that segment.

---

### TC-OSPF-013 — Type-3 (Summary) LSA generation by ABR
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-013 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | D1 as ABR between Area 0 and Area 1 |

**Steps:**
1. D3 (Area 1) has loopback 3.3.3.3/32.
2. D1 ABR generates Type-3 LSA for 3.3.3.3/32 into Area 0.
3. Verify Type-3 LSA present in Area 0 LSDB with D1 as ABR.
4. Verify D2 installs inter-area route to 3.3.3.3/32.

**Expected result:** Type-3 LSA from D1 in Area 0. D2 shows `O IA 3.3.3.3/32` in routing table.

**CLI:**
```bash
show ip ospf database summary          # Type-3 LSAs
show ip route ospf                     # inter-area routes
```

---

### TC-OSPF-014 — Type-4 (ASBR Summary) LSA
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-014 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | D2 as ASBR, D1 as ABR |

**Steps:**
1. D2 redistributes static into OSPF → becomes ASBR.
2. D1 (ABR) generates Type-4 LSA into Area 1 for D2's ASBR router ID.
3. Verify D3 (Area 1) has Type-4 LSA with ASBR=2.2.2.2.
4. Verify D3 can resolve external route via D1→D2.

**Expected result:** Type-4 LSA present in Area 1. D3 resolves AS-external routes through the ASBR.

---

### TC-OSPF-015 — Type-5 (AS External) LSA redistribution
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-015 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | D2 ASBR redistributes static 172.16.0.0/24 |

**Pre-config:**
```bash
# D2
ip route 172.16.0.0/24 Null0
vtysh -c "conf t" -c "router ospf" \
      -c "redistribute static metric 20 metric-type 2"
```

**Steps:**
1. Configure static route on D2 and redistribute into OSPF.
2. Verify Type-5 LSA 172.16.0.0/24 in LSDB of D1, D2, D3.
3. Verify route appears in `show ip route` on D1 and D3 as `O E2`.
4. Verify metric is 20 (Type-2 external metric).

**Expected result:** `O E2 172.16.0.0/24 [110/20]` appears on all routers. Type-5 LSA flooding scope is AS-wide.

---

### TC-OSPF-016 — Type-7 (NSSA External) LSA in NSSA area
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-016 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | Area 1 configured as NSSA; D3 redistributes connected |

**Steps:**
1. Configure Area 1 as NSSA on D1 and D3.
2. D3 redistributes connected route 192.168.100.0/24 into OSPF.
3. Verify Type-7 LSA in Area 1 LSDB on D1 and D3.
4. D1 translates Type-7 → Type-5 and floods into Area 0.
5. Verify D2 sees `O E2 192.168.100.0/24`.

**Expected result:** Type-7 LSA in Area 1. D1 performs Type-7→Type-5 translation. D2 has external route.

---

### TC-OSPF-017 — LSA refresh and MaxAge handling
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-017 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | D1 ↔ D2 |

**Steps:**
1. Bring up adjacency. Record LSA sequence number.
2. Wait for 30 min (or inject an artificial 1800 s LS age via Scapy).
3. Verify LSA is refreshed (sequence number increments, LS age resets).
4. Inject an LSA with MaxAge (3600) via Scapy. Verify it is flushed from LSDB.

**Expected result:** LSA refresh before MaxAge. MaxAge LSA is acknowledged and removed from LSDB.

**Scapy usage:** Send crafted OSPF LSU packet with `ls_age=3600` for a target LSA.

---

## 8. Test Cases — Area Types

### TC-OSPF-021 — Stub area — block Type-5 LSA, inject default route
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-021 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | Area 1 as stub; D3 in stub area |

**CLI:**
```bash
# D1 and D3
router ospf
  area 0.0.0.1 stub
```

**Steps:**
1. Configure Area 1 as stub on D1 and D3.
2. D2 redistributes 172.16.0.0/24 (Type-5 LSA) into OSPF.
3. Verify Type-5 LSA is NOT present in Area 1 LSDB (D3).
4. Verify D3 has a default route `O*IA 0.0.0.0/0` via D1 (Type-3 default from ABR).
5. D3 can still reach 172.16.0.0/24 via default route.

**Expected result:** No Type-5 LSAs in stub area. Default route injected by ABR. Connectivity maintained via default.

---

### TC-OSPF-022 — Totally stub area — block Type-3 and Type-5 LSAs
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-022 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | Area 1 as totally stub |

**CLI:**
```bash
# D1 only (ABR controls this)
router ospf
  area 0.0.0.1 stub no-summary
```

**Steps:**
1. Configure totally stub on ABR (D1) for Area 1.
2. Verify no Type-3 LSAs (except the default) in D3's LSDB.
3. Verify no Type-5 LSAs in D3's LSDB.
4. Verify only `0.0.0.0/0` as inter-area route on D3.

**Expected result:** D3 LSDB contains only Type-1, Type-2, and the default Type-3 LSA from ABR. Minimal LSDB.

---

### TC-OSPF-023 — NSSA area — allow external redistribution without Type-5
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-023 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | Area 1 as NSSA; D3 as ASBR in NSSA |

**Steps:**
1. Configure Area 1 as NSSA on D1 and D3.
2. Redistribute static/connected on D3 into OSPF.
3. Verify Type-7 LSA in Area 1. Verify NO Type-5 LSAs from outside in Area 1.
4. D1 translates Type-7 → Type-5 and floods outside Area 1.

---

### TC-OSPF-024 — Totally NSSA area
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-024 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | Area 1 as totally NSSA |

**CLI:**
```bash
area 0.0.0.1 nssa no-summary
```

**Steps:**
1. Configure totally NSSA on ABR D1.
2. Verify D3 has no Type-3 LSAs (except default).
3. Verify D3 can still redistribute and generate Type-7 LSAs.

---

### TC-OSPF-025 — Virtual link across transit area
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-025 |
| **Platform** | VS |
| **Priority** | P2 |
| **Topo** | Extended VS: D2 in Area 2 (transit), D3 in Area 1 disconnected from backbone — use virtual link |

**Steps:**
1. Create Area 2 as transit between backbone and a new Area 3.
2. Configure virtual link from D1 to D3 through transit area.
3. Verify OSPF adjacency formed over virtual link.
4. Verify routes from Area 3 appear in backbone.

**CLI:**
```bash
# D1
router ospf
  area 0.0.0.2 virtual-link 3.3.3.3
# D3
router ospf
  area 0.0.0.2 virtual-link 1.1.1.1
```

---

## 9. Test Cases — Route Types and SPF

### TC-OSPF-031 — Intra-area route (O) installation
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-031 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. D1 and D2 in Area 0. D1 loopback 1.1.1.1/32 advertised.
2. Verify D2 has `O 1.1.1.1/32` (intra-area) in routing table.
3. Verify cost = interface cost on path.

**Expected result:** `O 1.1.1.1/32 [110/x]` on D2. Route type is intra-area.

---

### TC-OSPF-032 — Inter-area route (O IA) via ABR
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-032 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. D3 loopback 3.3.3.3/32 in Area 1.
2. D1 (ABR) generates Type-3 LSA.
3. Verify D2 has `O IA 3.3.3.3/32 [110/x]`.

---

### TC-OSPF-033 — External Type-1 (O E1) route
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-033 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**CLI:**
```bash
# D2 redistribute with metric-type 1
redistribute static metric 10 metric-type 1
```

**Steps:**
1. D2 redistributes 172.16.0.0/24 as metric-type 1.
2. Verify D1 and D3 have `O E1 172.16.0.0/24`.
3. Verify cost accumulates (internal path cost + external metric).

---

### TC-OSPF-034 — External Type-2 (O E2) route and cost comparison
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-034 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. D2 redistributes with metric-type 2.
2. Verify E2 metric does NOT accumulate (fixed external metric).
3. Verify E1 is preferred over E2 when both advertise the same prefix.

---

### TC-OSPF-035 — ECMP with OSPF (equal-cost multipath)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-035 |
| **Platform** | VS / HW |
| **Priority** | P2 |
| **Topo** | Two parallel links between D1 and D2, same cost |

**Steps:**
1. Assign same cost to both parallel D1-D2 links.
2. Verify routing table on D2 shows two next-hops (ECMP) for D1 loopback.
3. Use Scapy to send traffic with varying 5-tuple.
4. Verify traffic distributed across both links.

**CLI:**
```bash
show ip route ospf    # look for two next-hops on same prefix
```

---

### TC-OSPF-036 — SPF re-computation on link failure
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-036 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Verify all routes in steady state.
2. Shutdown D1–D2 link (Ethernet4 on D1).
3. Measure convergence time (start timer at shutdown, stop when route is updated in D3 routing table).
4. Verify alternate path used (if available) or route withdrawn.

**Expected result:** SPF recomputed within ≤ 5 s (default timers). Routes updated. No forwarding black hole after reconvergence.

**Spytest:**
```python
import time
st.config(dut1, "sudo ip link set Ethernet4 down")
t0 = time.time()
# Poll until route changes
ospf_obj.wait_for_ospf_route_withdrawal(dut3, prefix='10.1.2.0/30', timeout=15)
convergence_time = time.time() - t0
st.log(f"Convergence time: {convergence_time:.2f}s")
assert convergence_time < 10, "Convergence too slow"
```

---

### TC-OSPF-037 — OSPF cost manipulation
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-037 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Two equal-cost paths exist from D3 to D2.
2. Increase cost on one path interface.
3. Verify traffic shifts to lower-cost path.
4. Restore original cost, verify ECMP restored.

---

## 10. Test Cases — Authentication

### TC-OSPF-041 — Plain-text (simple) authentication
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-041 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**CLI:**
```bash
# D1 and D2
interface Ethernet4
  ip ospf authentication
  ip ospf authentication-key mysecret
```

**Steps:**
1. Configure simple auth on D1 and D2.
2. Verify adjacency forms.
3. Use Scapy to capture Hello packets and verify auth type=1.
4. Change key on D1 only → verify adjacency drops.
5. Restore matching key → verify adjacency reforms.

---

### TC-OSPF-042 — MD5 cryptographic authentication
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-042 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**CLI:**
```bash
interface Ethernet4
  ip ospf authentication message-digest
  ip ospf message-digest-key 1 md5 mymd5secret
```

**Steps:**
1. Configure MD5 auth on D1 and D2.
2. Verify adjacency reaches Full.
3. Capture OSPF Hello with Scapy, verify auth-type=2 and MD5 digest present.
4. Send malformed auth Hello from TGen (wrong key), verify D1 discards it (no adjacency).

---

### TC-OSPF-043 — MD5 key rollover (non-disruptive key change)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-043 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Add a new key ID 2 with new password on both D1 and D2 (both keys active).
2. Verify adjacency remains Full during key overlap period.
3. Remove old key ID 1.
4. Verify adjacency still Full with only key ID 2.

---

### TC-OSPF-044 — Authentication mismatch (negative)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-044 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. D1 configured with MD5 key; D2 configured with no auth.
2. Verify NO adjacency is formed.
3. Verify error logs/debug messages on D1 (auth type mismatch).

**Expected result:** Adjacency stays in `Init` or `ExStart` and never reaches `Full`.

---

## 11. Test Cases — BFD Integration

### TC-OSPF-047 — BFD-assisted fast failure detection
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-047 |
| **Platform** | HW (BFD requires hardware support) |
| **Priority** | P1 |

**CLI:**
```bash
# D1
router ospf
  bfd all-interfaces
# Or per-interface:
interface Ethernet4
  ip ospf bfd
```

**Steps:**
1. Enable BFD on D1–D2 link.
2. Bring up OSPF adjacency. Verify BFD session is Up.
3. Simulate physical failure: shutdown Ethernet4 on D2.
4. Measure time from failure to OSPF route withdrawal (should be < 1 s with BFD).
5. Restore link. Verify OSPF and BFD sessions recover.

**Expected result:** Route withdrawal in < 1 s (BFD detection interval ~300 ms). Compare to ~40 s without BFD (dead interval).

---

### TC-OSPF-048 — BFD echo mode
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-048 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. Enable BFD echo mode on D1.
2. Verify BFD session state shows echo mode negotiated.
3. Verify failure detection still < 1 s.

---

### TC-OSPF-049 — OSPF reconvergence after BFD session flap
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-049 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. Force BFD session down/up 10 times rapidly.
2. Verify OSPF adjacency remains stable (no unnecessary SPF runs).
3. Verify OSPF error/flap counters are within acceptable range.

---

## 12. Test Cases — Route Redistribution and Summarization

### TC-OSPF-051 — Redistribute static routes into OSPF
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-051 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Add 5 static routes on D2 pointing to Null0 (simulating connected networks).
2. Redistribute static into OSPF with metric-type 2 and metric 20.
3. Verify all 5 Type-5 LSAs in LSDB.
4. Verify all 5 routes appear on D1 and D3 as `O E2`.

---

### TC-OSPF-052 — Redistribute connected routes
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-052 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**CLI:**
```bash
router ospf
  redistribute connected metric-type 2 metric 10
```

**Steps:**
1. Add loopback interfaces on D2 with prefixes 192.168.1.0/24–192.168.5.0/24.
2. Redistribute connected.
3. Verify all 5 prefixes as O E2 on D1 and D3.

---

### TC-OSPF-053 — Redistribute with route-map filtering
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-053 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Configure a route-map that permits only 172.16.0.0/24 and denies 172.16.1.0/24.
2. Apply route-map to redistribution on D2.
3. Verify 172.16.0.0/24 appears in LSDB; 172.16.1.0/24 does NOT.

---

### TC-OSPF-054 — ABR route summarization (Type-3 summary)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-054 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**CLI:**
```bash
# D1 ABR
router ospf
  area 0.0.0.1 range 10.1.3.0/24
```

**Steps:**
1. D3 has multiple loopbacks: 10.1.3.1/32, 10.1.3.2/32, 10.1.3.3/32.
2. Configure ABR summary range 10.1.3.0/24 for Area 1.
3. Verify D2 sees one summary Type-3 LSA (10.1.3.0/24) instead of 3 individual LSAs.
4. Verify D2 route table shows `O IA 10.1.3.0/24`.

---

### TC-OSPF-055 — ASBR external route summarization
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-055 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**CLI:**
```bash
# D2
router ospf
  summary-address 172.16.0.0/22
```

**Steps:**
1. D2 redistributes 172.16.0.0/24, 172.16.1.0/24, 172.16.2.0/24, 172.16.3.0/24.
2. Apply ASBR summary 172.16.0.0/22.
3. Verify only one Type-5 LSA (172.16.0.0/22) is flooded.

---

### TC-OSPF-056 — Redistribution loop prevention (tag-based)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-056 |
| **Platform** | VS |
| **Priority** | P2 |

**Steps:**
1. Configure mutual redistribution between OSPF and static with a tag.
2. Apply route-map to block routes with the OSPF tag from being re-redistributed.
3. Verify no routing loop or route explosion occurs.

---

## 13. Test Cases — Traffic Forwarding (Scapy)

### TC-OSPF-061 — End-to-end IPv4 forwarding through OSPF routes
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-061 |
| **Platform** | VS / HW |
| **Priority** | P1 |
| **Topo** | TGen:P1 → D1 → D3 → TGen:P2 |

**Steps:**
1. Verify all OSPF routes converged.
2. TGen sends 10,000 UDP packets from 10.1.1.1 (P1) to 10.1.4.1 (P2) via OSPF path.
3. Measure received packet count on TGen:P2.
4. Verify packet loss < 0.1%.

**Scapy:**
```python
from scapy.all import Ether, IP, UDP, sendp, sniff

pkts = [Ether()/IP(src='10.1.1.1', dst='10.1.4.1')/
        UDP(sport=1024, dport=9999)/b'X'*64
        for _ in range(10000)]
tgen.send_burst(tgen_p1, pkts, rate_pps=1000)
rx = tgen.capture(tgen_p2, duration=12, bpf='udp and dst port 9999')
loss = (10000 - len(rx)) / 10000 * 100
assert loss < 0.1, f"Packet loss {loss:.2f}% exceeds threshold"
```

---

### TC-OSPF-062 — Traffic forwarding over inter-area (O IA) route
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-062 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Route from TGen (Area 0) to D3 loopback (Area 1 — inter-area route).
2. Send 10,000 packets, verify no loss.
3. Verify TTL decrements correctly (one hop per router).

---

### TC-OSPF-063 — Traffic forwarding over external (O E2) route
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-063 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. External route 172.16.0.0/24 redistributed by D2.
2. TGen (P1) sends traffic to 172.16.0.1 (must egress via D2).
3. Capture on TGen:P2 (connected to D2) — verify traffic arrives.

---

### TC-OSPF-064 — Traffic reconvergence after link failure
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-064 |
| **Platform** | HW |
| **Priority** | P1 |

**Steps:**
1. Start continuous traffic stream (1000 pps) from TGen:P1 to TGen:P2.
2. After 5 s, physically unplug D1–D2 link.
3. Measure traffic interruption window.
4. Verify traffic resumes via alternate path (if configured) or drops cleanly.

**Expected result:** Traffic interruption window < 10 s (without BFD) or < 1 s (with BFD).

---

### TC-OSPF-065 — OSPF ECMP traffic distribution (Scapy hash validation)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-065 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. Two equal-cost paths between TGen:P1 and TGen:P2.
2. Send 10,000 flows with varying 5-tuple (src-ip, dst-ip, src-port, dst-port, proto).
3. Capture on both paths.
4. Verify both paths receive traffic (distribution within 10%–90% on either side).

---

### TC-OSPF-066 — TTL propagation and ICMP unreachable
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-066 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. TGen sends packet with TTL=1 toward D3 (2 hops away).
2. D1 (first hop) decrements TTL to 0, sends ICMP Time Exceeded.
3. Capture on TGen:P1, verify ICMP Time Exceeded from D1.

**Scapy:**
```python
pkt = Ether()/IP(src='10.1.1.1', dst='3.3.3.3', ttl=1)/ICMP()
rx = tgen.send_and_receive(tgen_p1, pkt, timeout=5, bpf='icmp')
assert any(ICMP in p and p[ICMP].type == 11 for p in rx)
```

---

## 14. Test Cases — Negative Cases

### TC-OSPF-071 — Mismatched Hello/Dead timers (no adjacency)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-071 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. D1: hello=10, dead=40. D2: hello=5, dead=20.
2. Verify NO adjacency formed.
3. Verify D1 logs "Hello timer mismatch" or equivalent.

**Expected result:** Adjacency stays at `Init`. No `Full` state reached.

---

### TC-OSPF-072 — Mismatched area IDs (no adjacency)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-072 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. D1 assigns Ethernet4 to Area 0. D2 assigns same interface to Area 1.
2. Verify no adjacency. Verify log message indicating area mismatch.

---

### TC-OSPF-073 — MTU mismatch causing DD exchange failure
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-073 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. D1 MTU=1500. D2 MTU=9100 (jumbo frames, with MTU check enabled).
2. Verify OSPF adjacency stuck in `ExStart` or `Exchange`.
3. Set `ip ospf mtu-ignore` on D1 interface.
4. Verify adjacency now reaches `Full`.

---

### TC-OSPF-074 — Duplicate router ID conflict
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-074 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Configure D1 and D2 with the same router-id 1.1.1.1.
2. Attempt OSPF adjacency.
3. Verify routing instability or error message. Routes may not install correctly.
4. Fix: set unique router IDs; verify recovery.

**Expected result:** Duplicate router IDs cause LSA conflicts. Log shows duplicate warning. Correcting router IDs restores stable adjacency.

---

### TC-OSPF-075 — OSPF packet injection via Scapy (replay attack)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-075 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Capture a valid OSPF Hello from D1 using Scapy.
2. Replay the same Hello from TGen with the same sequence number.
3. With authentication disabled: verify DUT processes the replayed Hello.
4. Enable MD5 auth: replay the captured Hello (with invalid auth).
5. Verify DUT drops the replayed packet.

**Expected result:** Without auth, replayed Hellos are processed (potential risk). With MD5, replayed packets are dropped.

---

### TC-OSPF-076 — LSA with invalid checksum
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-076 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Use Scapy to craft an LSU packet with a corrupted checksum in one LSA.
2. Send to D1.
3. Verify D1 discards the malformed LSA.
4. Verify LSDB is unaffected (no partial update).

**Scapy:**
```python
from scapy.contrib.ospf import OSPF_LSUpd, OSPF_Router_LSA
lsu = (IP(src='10.1.1.1', dst='224.0.0.5') /
       OSPF_Hdr(src='10.1.1.1', area='0.0.0.0') /
       OSPF_LSUpd())
# Corrupt checksum
lsu[OSPF_Router_LSA].chksum = 0xDEAD
sendp(Ether()/lsu, iface='eth1')
```

---

### TC-OSPF-077 — Adjacency with incompatible options field
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-077 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. TGen sends Hello with Options=0x00 (no capabilities) to D1 which requires E-bit.
2. Verify D1 does not form adjacency (E-bit mismatch in non-stub area).

---

### TC-OSPF-078 — Route flap — rapid interface up/down
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-078 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Flap the D1–D2 link 50 times in 60 s.
2. Verify OSPF converges to stable state after final link up.
3. Verify no stale routes remain.
4. Verify memory usage on DUT has not grown significantly (no leak).

---

### TC-OSPF-079 — OSPF process restart (daemon crash recovery)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-079 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Bring up full adjacency.
2. Kill the OSPF daemon (FRR `ospfd`) on D1.
3. Measure time until daemon restarts and adjacency is restored.
4. Verify all routes re-installed after recovery.

**CLI:**
```bash
sudo systemctl restart frr
# or: sudo killall ospfd
```

---

### TC-OSPF-080 — Max LSA limit enforcement
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-080 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**CLI:**
```bash
router ospf
  max-lsa 100 90 warning-only
```

**Steps:**
1. Configure max-lsa 100 on D1.
2. Flood > 100 LSAs from TGen (Scapy OSPF emulation).
3. Verify D1 logs warning at 90% threshold.
4. Verify behavior at 100% (warning-only = log, not shutdown).

---

## 15. Test Cases — Corner Cases

### TC-OSPF-086 — OSPF over loopback interface (stub host route /32)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-086 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Configure OSPF network including loopback 1.1.1.1/32.
2. Verify loopback is advertised as a host route (/32) not /32-stub.
3. FRR always treats loopback as /32 stub link in Type-1 LSA.

---

### TC-OSPF-087 — Link cost = 65535 (maximum)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-087 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Set `ip ospf cost 65535` on D1–D2 link.
2. Verify LSA contains cost=65535.
3. If alternate path exists, verify traffic takes alternate path.
4. If no alternate: verify route is still installed with max cost.

---

### TC-OSPF-088 — OSPF over unnumbered interface
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-088 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Configure Ethernet4 as unnumbered (borrowing loopback IP).
2. Configure OSPF on unnumbered interface with `ip ospf network point-to-point`.
3. Verify adjacency and route installation.

---

### TC-OSPF-089 — Simultaneous SPF triggers (multiple link events)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-089 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Simultaneously trigger 3 link failures on different interfaces.
2. Verify SPF is not triggered redundantly (SPF throttle timer active).
3. Verify all routes converge correctly after a single batched SPF run.

---

### TC-OSPF-090 — OSPF neighbor with maximum number of retransmissions
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-090 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Block ACK packets from D2 to D1 (iptables drop OSPF packets from D2's IP).
2. Verify D1 retransmits LSU up to `retransmit-interval` × max attempts.
3. After max retransmissions with no ACK, verify D1 logs an error.

---

### TC-OSPF-091 — OSPF over link with high packet loss (50% drop)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-091 |
| **Platform** | VS (netem) |
| **Priority** | P3 |

**Steps:**
1. Use `tc netem loss 50%` on D1–D2 link (VS only).
2. Verify OSPF adjacency can still form (due to retransmit).
3. Verify convergence time increases but no permanent failure.

---

### TC-OSPF-092 — Area 0.0.0.0 backbone with no non-backbone areas
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-092 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Single area domain (Area 0 only, no other areas).
2. Verify basic operation: adjacency, LSDB, routing table.

---

### TC-OSPF-093 — OSPF with IPv6 interface addresses on DUT (dual-stack isolation)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-093 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Add IPv6 addresses alongside IPv4 on OSPF interfaces.
2. Verify OSPFv2 operation is not affected by IPv6 configuration.
3. Verify no OSPFv2 packets are sent over IPv6.

---

### TC-OSPF-094 — Zero OSPF metric (cost=0) advertisement
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-094 |
| **Platform** | VS / HW |
| **Priority** | P3 |

**Steps:**
1. Set `ip ospf cost 0` on an interface.
2. Verify OSPF treats cost 0 as cost 1 (RFC 2328 minimum cost is 1) or uses 0.
3. Verify route installation is correct.

---

### TC-OSPF-095 — OSPF with VRF (non-default VRF isolation)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-095 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Create VRF `test_vrf` on D1.
2. Move one interface into `test_vrf`.
3. Configure OSPF in `test_vrf`.
4. Verify OSPF in VRF is isolated from default VRF OSPF.
5. Verify routes in `test_vrf` routing table only.

---

## 16. Test Cases — Persistence Cases

### TC-OSPF-096 — OSPF state after DUT warm reboot
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-096 |
| **Platform** | HW |
| **Priority** | P1 |

**Steps:**
1. Bring up full OSPF topology. Verify all routes.
2. Initiate warm reboot on D1 (`sudo warm-reboot`).
3. Monitor adjacency states from D2 and D3 during reboot.
4. After reboot: verify OSPF adjacency re-established within 120 s.
5. Verify all routes match pre-reboot state.
6. Verify no duplicate router-ID or stale LSA issues.

---

### TC-OSPF-097 — OSPF state after cold reboot
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-097 |
| **Platform** | HW |
| **Priority** | P1 |

**Steps:**
1. Bring up full OSPF topology.
2. Power cycle D1 (cold reboot).
3. Verify neighbors D2 and D3 detect D1 absence (dead interval expires).
4. After D1 restarts: verify full OSPF re-convergence within 180 s.

---

### TC-OSPF-098 — OSPF configuration persistence after `config save`
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-098 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**CLI:**
```bash
sudo config save -y
```

**Steps:**
1. Configure OSPF with areas, auth, BFD, redistribution.
2. Run `config save`.
3. Reboot DUT.
4. Verify all OSPF config is restored from `/etc/sonic/config_db.json`.
5. Verify adjacencies form automatically after reboot.

---

### TC-OSPF-099 — OSPF persistence across FRR service restart
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-099 |
| **Platform** | VS / HW |
| **Priority** | P1 |

**Steps:**
1. Bring up adjacency. Record LSDB state.
2. Restart FRR: `sudo systemctl restart frr`.
3. Verify OSPF re-establishes adjacency within 60 s.
4. Verify LSDB matches pre-restart state.

---

### TC-OSPF-100 — Config DB reload with OSPF running
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-100 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**CLI:**
```bash
sudo config reload -y
```

**Steps:**
1. Trigger config reload on D1.
2. Monitor OSPF adjacency on D2.
3. Verify adjacency recovers within 120 s.
4. Verify no duplicate LSAs or stale entries in LSDB.

---

### TC-OSPF-101 — Traffic continuity during OSPF GR (Graceful Restart)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-101 |
| **Platform** | HW |
| **Priority** | P2 |

**CLI:**
```bash
router ospf
  graceful-restart grace-period 120
```

**Steps:**
1. Enable Graceful Restart on D1.
2. Start continuous traffic stream.
3. Restart OSPF process on D1.
4. Verify traffic is not interrupted during the GR grace period.
5. Verify helper routers (D2, D3) honor the grace LSA.

---

### TC-OSPF-102 — OSPF route persistence across SWSS restart
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-102 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. Verify OSPF routes in `show ip route`.
2. Restart SWSS: `sudo systemctl restart swss`.
3. Verify OSPF routes are re-programmed in HW (AppDB → ASIC) after SWSS restarts.

---

## 17. Test Cases — Scaling Cases

### TC-OSPF-106 — Maximum OSPF neighbors on a single DUT
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-106 |
| **Platform** | VS (Scapy multi-neighbor emulation) |
| **Priority** | P2 |

**Setup:** TGen runs Scapy threads emulating N OSPF neighbors (up to platform max, typically 256).

**Steps:**
1. Start Scapy threads emulating 50, 100, 150, 200 neighbors on D1.
2. Verify D1 forms `Full` adjacency with all N neighbors.
3. Verify CPU usage on D1 remains < 80%.
4. Verify LSDB size scales linearly.

**Scapy:**
```python
import threading
def emulate_neighbor(ip, router_id):
    # Send periodic OSPF Hellos for this neighbor
    while True:
        hello = make_ospf_hello(src_ip=ip, router_id=router_id)
        sendp(hello, iface='eth1', verbose=0)
        time.sleep(10)

threads = [threading.Thread(target=emulate_neighbor,
                             args=(f'10.100.{i//256}.{i%256}', f'{i}.{i}.{i}.{i}'))
           for i in range(1, 201)]
for t in threads:
    t.start()
```

---

### TC-OSPF-107 — Large LSDB (1000+ LSAs)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-107 |
| **Platform** | VS |
| **Priority** | P2 |

**Steps:**
1. Scapy floods 1000 Type-5 (external) LSAs from TGen into D1.
2. Verify D1 accepts and stores all LSAs in LSDB.
3. Verify SPF convergence time with 1000 LSAs (< 5 s expected).
4. Verify memory usage is within acceptable bounds.

---

### TC-OSPF-108 — Maximum routes in OSPF routing table
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-108 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. TGen emulates an ASBR and floods 16,000 Type-5 LSAs (representing 16k external prefixes).
2. Verify D1 installs all routes in FIB.
3. Verify route lookup latency is within acceptable range.
4. Send traffic to 100 random destinations, verify forwarding is correct.

---

### TC-OSPF-109 — SPF timer throttling under rapid topology changes
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-109 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**CLI:**
```bash
router ospf
  timers throttle spf 50 200 5000
```

**Steps:**
1. Configure SPF throttle: initial=50ms, min=200ms, max=5000ms.
2. Trigger 20 rapid link flaps in 10 s.
3. Verify SPF is triggered at increasing intervals (exponential backoff).
4. Verify CPU usage remains bounded.

---

### TC-OSPF-110 — Maximum number of OSPF areas
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-110 |
| **Platform** | VS |
| **Priority** | P3 |

**Steps:**
1. Using VS, configure D1 as ABR connected to 10 different areas.
2. Each area has 1 router connected to D1.
3. Verify OSPF forms adjacency in all 10 areas.
4. Verify inter-area routes are installed for all areas.

---

### TC-OSPF-111 — OSPF with large number of redistributed prefixes (10k static)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-111 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Configure 10,000 static routes on D2 redistributed into OSPF.
2. Verify all 10,000 Type-5 LSAs appear in LSDB.
3. Verify D1 and D3 have all 10,000 external routes.
4. Remove all static routes at once. Verify LSA flush and route withdrawal.

---

### TC-OSPF-112 — OSPF convergence time measurement (baseline)
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-112 |
| **Platform** | HW |
| **Priority** | P1 (benchmark) |

**Steps:**
1. Measure time-to-full-adjacency from first Hello sent to `Full` state.
2. Measure time-to-route from adjacency `Full` to route appearing in `show ip route`.
3. Repeat 10 times and report min/max/avg.
4. Baseline: adjacency < 5 s, route installation < 1 s after Full state.

---

### TC-OSPF-113 — OSPF stress test — sustained high-rate LSA flooding
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-113 |
| **Platform** | HW |
| **Priority** | P3 |

**Steps:**
1. TGen Scapy floods LSAs at 100 LSAs/s for 60 s (6000 total).
2. Verify D1 processes all LSAs without crashing or memory exhaustion.
3. Verify ACK behavior is correct.
4. After flood stops: verify LSDB stabilizes.

---

### TC-OSPF-114 — Concurrent OSPF + BGP + Static routes scaling
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-114 |
| **Platform** | VS / HW |
| **Priority** | P2 |

**Steps:**
1. Configure 5000 OSPF routes, 5000 BGP routes, 2000 static routes on D1 simultaneously.
2. Verify no route conflicts or memory corruption.
3. Verify route priorities (admin distance) are correctly applied.

---

### TC-OSPF-115 — OSPF neighbor scale: 64 neighbors with traffic
| Field | Value |
|-------|-------|
| **TC ID** | TC-OSPF-115 |
| **Platform** | HW |
| **Priority** | P2 |

**Steps:**
1. D1 has 64 physical interfaces, each connected to TGen ports emulating OSPF neighbors.
2. Bring up all 64 adjacencies.
3. Inject 1000 traffic flows distributed across all 64 paths.
4. Verify zero packet loss at steady state.
5. Verify DUT CPU < 60%, memory < 80%.

---

## Appendix A — CLI Reference

### OSPF Configuration (SONiC via vtysh / FRR)

```bash
# Enter FRR CLI
vtysh

# Basic OSPF setup
configure terminal
router ospf
  ospf router-id 1.1.1.1
  network 10.1.1.0/30 area 0.0.0.0
  network 10.1.3.0/30 area 0.0.0.1
  passive-interface default
  no passive-interface Ethernet0
exit

# Interface-level OSPF
interface Ethernet0
  ip ospf area 0.0.0.0
  ip ospf hello-interval 10
  ip ospf dead-interval 40
  ip ospf cost 10
  ip ospf priority 100
  ip ospf authentication message-digest
  ip ospf message-digest-key 1 md5 secret123
exit

# Area types
router ospf
  area 0.0.0.1 stub
  area 0.0.0.1 stub no-summary       # totally stub
  area 0.0.0.1 nssa
  area 0.0.0.1 nssa no-summary       # totally NSSA
  area 0.0.0.1 range 10.1.3.0/24    # ABR summarization
  summary-address 172.16.0.0/22      # ASBR external summarization

# Redistribution
  redistribute static metric-type 2 metric 20
  redistribute connected metric-type 1 metric 10
  redistribute bgp metric-type 2 route-map OSPF-IN

# SPF throttling
  timers throttle spf 50 200 5000

# BFD
  bfd all-interfaces

# Graceful restart
  graceful-restart grace-period 120
  graceful-restart helper-only

# Max LSA
  max-lsa 10000 90 warning-only

exit
```

### Verification Commands

```bash
show ip ospf                              # process summary
show ip ospf neighbor                     # neighbor table
show ip ospf neighbor detail              # detailed neighbor info
show ip ospf database                     # LSDB summary
show ip ospf database router              # Type-1 LSAs
show ip ospf database network             # Type-2 LSAs
show ip ospf database summary             # Type-3 LSAs
show ip ospf database asbr-summary        # Type-4 LSAs
show ip ospf database external            # Type-5 LSAs
show ip ospf database nssa-external       # Type-7 LSAs
show ip ospf interface                    # interface OSPF state
show ip ospf interface Ethernet0          # specific interface
show ip route ospf                        # OSPF routes in RIB
show ip ospf border-routers               # ABR/ASBR list
debug ospf adj                            # adjacency debug
debug ospf lsa                            # LSA debug
debug ospf spf                            # SPF debug
```

### SONiC-specific CLI

```bash
# Save config
sudo config save -y

# FRR service management
sudo systemctl restart frr
sudo systemctl status frr

# Check OSPF process
sudo docker exec bgp vtysh -c "show ip ospf neighbor"

# OSPF config in config_db (if using OSPF via config_db)
sudo sonic-cfggen -d --var-json OSPF
```

---

## Appendix B — Scapy Snippets

### OSPF Hello Packet

```python
from scapy.all import *
from scapy.contrib.ospf import *

def send_ospf_hello(iface, src_ip, router_id, area='0.0.0.0',
                    mask='255.255.255.252', hello_int=10, dead_int=40,
                    priority=1, neighbors=None):
    """Send periodic OSPF Hello from TGen to form adjacency."""
    pkt = (Ether(dst="01:00:5e:00:00:05") /
           IP(src=src_ip, dst="224.0.0.5", ttl=1, proto=89) /
           OSPF_Hdr(src=router_id, area=area) /
           OSPF_Hello(mask=mask, hellointerval=hello_int,
                      deadinterval=dead_int, router=router_id,
                      backup=router_id if priority else '0.0.0.0',
                      neighbor=neighbors or []))
    sendp(pkt, iface=iface, loop=1, inter=hello_int, verbose=0)
```

### OSPF LSU with Type-5 External LSA

```python
def flood_type5_lsas(iface, src_ip, asbr_id, prefixes, area='0.0.0.0'):
    """Flood Type-5 External LSAs into OSPF domain via TGen."""
    lsas = []
    for prefix in prefixes:
        net, length = prefix.split('/')
        lsa = OSPF_External_LSA(
            age=1,
            options=0x02,
            type=5,
            id=net,
            adrouter=asbr_id,
            seq=0x80000001,
            mask=cidr_to_mask(int(length)),
            metric=20,
            fwdaddr='0.0.0.0',
            tag=0
        )
        lsas.append(lsa)
    
    lsu = (Ether(dst="01:00:5e:00:00:05") /
           IP(src=src_ip, dst="224.0.0.5", ttl=1, proto=89) /
           OSPF_Hdr(src=asbr_id, area=area) /
           OSPF_LSUpd(lsalist=lsas))
    sendp(lsu, iface=iface, verbose=0)
```

### Traffic Send and Receive (Forwarding Verification)

```python
import time
from scapy.all import Ether, IP, UDP, sendp, AsyncSniffer

def verify_forwarding(tx_iface, rx_iface, src_ip, dst_ip,
                      pkt_count=1000, rate_pps=500, timeout=15):
    """
    Send UDP packets on tx_iface, capture on rx_iface.
    Returns: (sent, received, loss_percent)
    """
    pkts = [Ether() / IP(src=src_ip, dst=dst_ip) /
            UDP(sport=1024+i, dport=9999) / b'P'*64
            for i in range(pkt_count)]
    
    # Start capture
    sniffer = AsyncSniffer(iface=rx_iface,
                           filter=f'udp and dst host {dst_ip} and dst port 9999',
                           store=True)
    sniffer.start()
    
    # Send
    time.sleep(0.2)
    sendp(pkts, iface=tx_iface, inter=1/rate_pps, verbose=0)
    time.sleep(timeout)
    sniffer.stop()
    
    rx_count = len(sniffer.results)
    loss = (pkt_count - rx_count) / pkt_count * 100
    return pkt_count, rx_count, loss


# Usage
sent, received, loss = verify_forwarding(
    tx_iface='eth1', rx_iface='eth2',
    src_ip='10.1.1.1', dst_ip='10.1.4.1',
    pkt_count=10000, rate_pps=1000
)
assert loss < 0.1, f"Loss {loss:.2f}% exceeds threshold"
```

### Convergence Time Measurement

```python
import time
import subprocess

def measure_convergence(dut_ssh, prefix, max_wait=30):
    """
    Poll 'show ip route <prefix>' until route appears or disappears.
    Returns convergence time in seconds.
    """
    start = time.time()
    while time.time() - start < max_wait:
        result = dut_ssh.execute('show ip route ' + prefix)
        if 'O' in result:   # OSPF route present
            return time.time() - start
        time.sleep(0.1)
    raise TimeoutError(f"Route {prefix} not converged within {max_wait}s")
```

### OSPF MD5 Auth Hello (Authentication Testing)

```python
def send_ospf_hello_md5(iface, src_ip, router_id, key_id, key,
                         area='0.0.0.0'):
    """Send OSPF Hello with MD5 auth."""
    pkt = (Ether(dst="01:00:5e:00:00:05") /
           IP(src=src_ip, dst="224.0.0.5", ttl=1, proto=89) /
           OSPF_Hdr(src=router_id, area=area,
                    authtype=2, authdata=0) /
           OSPF_Hello(mask='255.255.255.252',
                      hellointerval=10, deadinterval=40,
                      router=router_id))
    # Note: Scapy contrib ospf handles MD5 computation via:
    # from scapy.contrib.ospf import OspfMD5Sig
    sendp(pkt, iface=iface, verbose=0)
```

---

## Test Case Summary Table

| TC ID | Title | Platform | Priority | Category |
|-------|-------|----------|----------|----------|
| TC-OSPF-001 | Two-router adjacency Area 0 | VS/HW | P1 | Adjacency |
| TC-OSPF-002 | DR/BDR election broadcast | VS/HW | P1 | Adjacency |
| TC-OSPF-003 | Custom hello/dead timers | VS/HW | P1 | Adjacency |
| TC-OSPF-004 | OSPF over VLAN | VS/HW | P2 | Adjacency |
| TC-OSPF-005 | Passive interface | VS/HW | P2 | Adjacency |
| TC-OSPF-011 | Type-1 Router LSA | VS/HW | P1 | LSA/LSDB |
| TC-OSPF-012 | Type-2 Network LSA | VS/HW | P1 | LSA/LSDB |
| TC-OSPF-013 | Type-3 Summary LSA (ABR) | VS/HW | P1 | LSA/LSDB |
| TC-OSPF-014 | Type-4 ASBR Summary LSA | VS/HW | P2 | LSA/LSDB |
| TC-OSPF-015 | Type-5 External LSA | VS/HW | P1 | LSA/LSDB |
| TC-OSPF-016 | Type-7 NSSA LSA | VS/HW | P2 | LSA/LSDB |
| TC-OSPF-017 | LSA refresh and MaxAge | VS/HW | P2 | LSA/LSDB |
| TC-OSPF-021 | Stub area | VS/HW | P1 | Area Types |
| TC-OSPF-022 | Totally stub area | VS/HW | P2 | Area Types |
| TC-OSPF-023 | NSSA area | VS/HW | P1 | Area Types |
| TC-OSPF-024 | Totally NSSA | VS/HW | P2 | Area Types |
| TC-OSPF-025 | Virtual link | VS | P2 | Area Types |
| TC-OSPF-031 | Intra-area route (O) | VS/HW | P1 | Routes/SPF |
| TC-OSPF-032 | Inter-area route (O IA) | VS/HW | P1 | Routes/SPF |
| TC-OSPF-033 | External E1 route | VS/HW | P1 | Routes/SPF |
| TC-OSPF-034 | External E2 route | VS/HW | P1 | Routes/SPF |
| TC-OSPF-035 | ECMP multipath | VS/HW | P2 | Routes/SPF |
| TC-OSPF-036 | SPF recompute on link failure | VS/HW | P1 | Routes/SPF |
| TC-OSPF-037 | OSPF cost manipulation | VS/HW | P2 | Routes/SPF |
| TC-OSPF-041 | Plain-text authentication | VS/HW | P1 | Auth |
| TC-OSPF-042 | MD5 authentication | VS/HW | P1 | Auth |
| TC-OSPF-043 | MD5 key rollover | VS/HW | P2 | Auth |
| TC-OSPF-044 | Auth mismatch (negative) | VS/HW | P1 | Auth/Negative |
| TC-OSPF-047 | BFD fast failure detection | HW | P1 | BFD |
| TC-OSPF-048 | BFD echo mode | HW | P2 | BFD |
| TC-OSPF-049 | OSPF reconvergence after BFD flap | HW | P2 | BFD |
| TC-OSPF-051 | Redistribute static into OSPF | VS/HW | P1 | Redistribution |
| TC-OSPF-052 | Redistribute connected | VS/HW | P1 | Redistribution |
| TC-OSPF-053 | Redistribute with route-map | VS/HW | P2 | Redistribution |
| TC-OSPF-054 | ABR summarization | VS/HW | P1 | Summarization |
| TC-OSPF-055 | ASBR external summarization | VS/HW | P2 | Summarization |
| TC-OSPF-056 | Redistribution loop prevention | VS | P2 | Redistribution |
| TC-OSPF-061 | E2E IPv4 forwarding | VS/HW | P1 | Traffic |
| TC-OSPF-062 | Inter-area traffic forwarding | VS/HW | P1 | Traffic |
| TC-OSPF-063 | External route traffic | VS/HW | P1 | Traffic |
| TC-OSPF-064 | Traffic reconvergence after failure | HW | P1 | Traffic |
| TC-OSPF-065 | ECMP traffic distribution | HW | P2 | Traffic |
| TC-OSPF-066 | TTL and ICMP unreachable | VS/HW | P2 | Traffic |
| TC-OSPF-071 | Hello timer mismatch | VS/HW | P1 | Negative |
| TC-OSPF-072 | Area ID mismatch | VS/HW | P1 | Negative |
| TC-OSPF-073 | MTU mismatch | HW | P2 | Negative |
| TC-OSPF-074 | Duplicate router ID | VS/HW | P1 | Negative |
| TC-OSPF-075 | OSPF packet replay attack | VS/HW | P2 | Negative |
| TC-OSPF-076 | LSA with invalid checksum | VS/HW | P2 | Negative |
| TC-OSPF-077 | Incompatible options field | VS/HW | P2 | Negative |
| TC-OSPF-078 | Route flap (rapid up/down) | VS/HW | P1 | Negative |
| TC-OSPF-079 | OSPF process restart | VS/HW | P1 | Negative |
| TC-OSPF-080 | Max LSA limit enforcement | VS/HW | P2 | Negative |
| TC-OSPF-086 | OSPF over loopback /32 | VS/HW | P2 | Corner |
| TC-OSPF-087 | Max link cost 65535 | VS/HW | P2 | Corner |
| TC-OSPF-088 | Unnumbered interface OSPF | VS/HW | P2 | Corner |
| TC-OSPF-089 | Simultaneous multiple SPF triggers | VS/HW | P2 | Corner |
| TC-OSPF-090 | Max LSU retransmissions | VS/HW | P2 | Corner |
| TC-OSPF-091 | OSPF over lossy link (50% drop) | VS | P3 | Corner |
| TC-OSPF-092 | Single area (Area 0 only) | VS/HW | P1 | Corner |
| TC-OSPF-093 | Dual-stack isolation (IPv4/IPv6) | VS/HW | P2 | Corner |
| TC-OSPF-094 | Zero-cost (cost=0) interface | VS/HW | P3 | Corner |
| TC-OSPF-095 | OSPF in non-default VRF | VS/HW | P2 | Corner |
| TC-OSPF-096 | Persistence: warm reboot | HW | P1 | Persistence |
| TC-OSPF-097 | Persistence: cold reboot | HW | P1 | Persistence |
| TC-OSPF-098 | Persistence: config save | VS/HW | P1 | Persistence |
| TC-OSPF-099 | Persistence: FRR restart | VS/HW | P1 | Persistence |
| TC-OSPF-100 | Persistence: config reload | VS/HW | P2 | Persistence |
| TC-OSPF-101 | Traffic during Graceful Restart | HW | P2 | Persistence |
| TC-OSPF-102 | Routes after SWSS restart | HW | P2 | Persistence |
| TC-OSPF-106 | Max OSPF neighbors (200+) | VS | P2 | Scaling |
| TC-OSPF-107 | Large LSDB (1000+ LSAs) | VS | P2 | Scaling |
| TC-OSPF-108 | Max routes (16k external) | HW | P2 | Scaling |
| TC-OSPF-109 | SPF throttling under rapid changes | VS/HW | P2 | Scaling |
| TC-OSPF-110 | Max OSPF areas (10 areas) | VS | P3 | Scaling |
| TC-OSPF-111 | 10k redistributed prefixes | VS/HW | P2 | Scaling |
| TC-OSPF-112 | Convergence time baseline | HW | P1 | Scaling |
| TC-OSPF-113 | Sustained high-rate LSA flood | HW | P3 | Scaling |
| TC-OSPF-114 | OSPF + BGP + Static concurrent | VS/HW | P2 | Scaling |
| TC-OSPF-115 | 64 neighbors with live traffic | HW | P2 | Scaling |

**Total: 70 test cases**
- P1 (critical): 22 cases
- P2 (high): 38 cases
- P3 (medium): 10 cases
- VS-only: 3 cases
- HW-only: 10 cases
- VS/HW: 57 cases
