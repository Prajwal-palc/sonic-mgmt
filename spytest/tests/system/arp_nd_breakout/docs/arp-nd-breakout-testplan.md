# SONiC OC Feature System Test Plan
## ARP & ND Port Breakout Test Plan — Minimal Topology

---

## 1. Topology

Two hosts connected to a Device Under Test (DUT). ARP/ND testing and Port Breakout validation are performed on DUT ingress interfaces.

```
+-----------+   eth0        eth1   +-----------+
|  Scapy TX +------[ DUT ]--------+  Scapy RX |
| 10.0.0.1  |    Port1  Port2     | 20.0.0.2  |
| MAC: AA:01|  ARP/ND Testing IN  | MAC: BB:02|
+-----------+                     +-----------+
```

### Breakout Extension Topology

```
              100G (Before Breakout)
          +--------------------------------+
          |             DUT                |
          |          Ethernet2             |
          +--------------------------------+

               4x25G (After Breakout)
          +--------------------------------+
          |  Eth2/1  Eth2/2  Eth2/3  Eth2/4 |
          +--------------------------------+
```

### Role Mapping

| Role         | Interface  | IP Address   | MAC Address        |
|--------------|------------|--------------|-------------------|
| TX (Sender)  | eth0       | 10.0.0.1/24  | 00:AA:AA:AA:AA:01 |
| RX (Receiver)| eth1       | 20.0.0.2/24  | 00:BB:BB:BB:BB:02 |
| DUT Port1    | Ethernet0  | 10.0.0.254   | DUT MAC           |
| DUT Port2    | Ethernet1  | 20.0.0.254   | DUT MAC           |

---

## 2. Legend

| Tag | Meaning                          |
|-----|----------------------------------|
| VS  | Virtual DUT (SONiC-VS)           |
| HW  | Physical ASIC required           |
| B   | Both VS and HW                   |
| NEG | Negative / Edge Case             |
| R   | Robustness / Persistence         |

---

## 3. ARP Test Cases (IPv4)

### 3.1 Functional ARP

| TC ID  | Description                    | Tag | Scapy Traffic                  | Expected                    |
|--------|--------------------------------|-----|--------------------------------|-----------------------------|
| ARP-01 | Dynamic ARP learning           | B   | ARP(pdst="10.0.0.254")         | Entry created in show arp   |
| ARP-02 | Static ARP configuration       | B   | Manual static entry            | Persistent across reboot    |
| ARP-03 | Gratuitous ARP update          | B   | ARP(op=2, psrc=10.0.0.1)       | Table updated               |
| ARP-04 | ARP on VLAN interface          | B   | Dot1Q(vlan=100)/ARP()          | Correct VLAN learning       |
| ARP-05 | ARP on PortChannel             | B   | ARP via LAG                    | Uses PortChannel MAC        |

### 3.2 Negative ARP (NEG)

| TC ID   | Description              | Tag | Scapy Traffic           | Expected                      |
|---------|--------------------------|-----|-------------------------|-------------------------------|
| ARP-N01 | Invalid opcode           | NEG | ARP(op=99)              | Dropped                       |
| ARP-N02 | Zero source IP           | NEG | ARP(psrc="0.0.0.0")     | Dropped                       |
| ARP-N03 | ARP table overflow       | HW  | 10K ARP flood           | Proper handling, no crash     |
| ARP-N04 | Duplicate IP detection   | B   | Same IP diff MAC        | Log + correct entry           |

### 3.3 Robustness ARP (R)

| TC ID   | Description                     | Tag | Expected                           |
|---------|---------------------------------|-----|------------------------------------|
| ARP-R01 | ARP persistence after reboot    | B   | Entries restored (if static)       |
| ARP-R02 | ARP aging timeout               | B   | Entry removed after timer          |
| ARP-R03 | ARP during interface flap       | B   | Relearn correctly                  |
| ARP-R04 | Concurrent ARP requests         | B   | No packet loss                     |
| ARP-R05 | ARP counters accuracy           | B   | Counter == TX count                |

---

## 4. IPv6 ND Test Cases

### 4.1 Functional ND

| TC ID | Description                  | Tag | Scapy Traffic        | Expected         |
|-------|------------------------------|-----|----------------------|------------------|
| ND-01 | NS/NA exchange               | B   | ICMPv6ND_NS()        | NA received      |
| ND-02 | ND on VLAN                   | B   | Dot1Q()/ICMPv6ND_NS()| Correct entry    |
| ND-03 | ND on PortChannel            | B   | ND over LAG          | Uses LAG MAC     |
| ND-04 | Duplicate Address Detection  | B   | NS unspecified src   | Correct DAD state|

### 4.2 ND Negative (NEG)

| TC ID  | Description            | Tag | Scapy Traffic         | Expected         |
|--------|------------------------|-----|-----------------------|------------------|
| ND-N01 | Invalid ICMPv6 type    | NEG | ICMPv6(type=200)      | Dropped          |
| ND-N02 | Malformed NS           | NEG | Truncated packet      | Dropped          |
| ND-N03 | ND flood               | HW  | 10K neighbors         | Stable behavior  |

### 4.3 ND Robustness (R)

| TC ID  | Description                         | Tag | Expected                          |
|--------|-------------------------------------|-----|-----------------------------------|
| ND-R01 | ND aging transitions                | B   | REACHABLE→STALE→PROBE verified    |
| ND-R02 | ND during link flap                 | B   | Entry relearned                   |
| ND-R03 | Warm restart ND preservation        | HW  | ≥95% entries retained             |
| ND-R04 | ND state under packet loss          | B   | Proper NUD probing                |

---

## 5. Port Breakout Test Cases

### 5.1 Functional Breakout

| TC ID | Description                  | Tag | Expected                           |
|-------|------------------------------|-----|------------------------------------|
| BO-01 | ARP after 1x100G→4x25G       | HW  | ARP works on all 4 ports           |
| BO-02 | ND after 1x100G→2x50G        | HW  | ND works                           |
| BO-03 | Breakout revert to 100G      | HW  | ARP/ND functional                  |
| BO-04 | ARP on each sub-interface    | HW  | Independent learning               |

### 5.2 Breakout Robustness (R)

| TC ID  | Description                         | Tag | Expected                       |
|--------|-------------------------------------|-----|--------------------------------|
| BO-R01 | ARP table cleanup during breakout   | HW  | No stale entries               |
| BO-R02 | Breakout under active traffic       | HW  | No crash                       |
| BO-R03 | Multiple breakout cycles (10+)      | HW  | Stable final state             |
| BO-R04 | Breakout + VLAN persistence         | HW  | VLAN config retained           |

---

## 6. Dual-Stack & Integration

| TC ID | Description                  | Tag | Expected                    |
|-------|------------------------------|-----|-----------------------------|
| DS-01 | Simultaneous ARP + ND        | B   | Both tables correct         |
| DS-02 | ARP/ND with VRF              | HW  | Isolation maintained        |
| DS-03 | ARP with ACL applied         | B   | ACL doesn't break ARP       |
| DS-04 | ND with CoPP rate limit      | HW  | Rate limited correctly      |

---

## 7. Test Summary

| Suite      | Functional | NEG | R  | Total |
|------------|------------|-----|----| ------|
| ARP        | 5          | 4   | 5  | 14    |
| ND         | 4          | 3   | 4  | 11    |
| Breakout   | 4          | 0   | 4  | 8     |
| Dual-Stack | 4          | 0   | 0  | 4     |
| **TOTAL**  | **17**     | **7**| **13** | **37** |

---

## 8. Pass / Fail Criteria

| Feature      | Pass Condition                    |
|--------------|-----------------------------------|
| ARP Reply    | NA received within 3s             |
| ND Reply     | NA received within 3s             |
| DENY Case    | No packet on RX                   |
| Counter      | Table entry == expected           |
| Breakout     | All sub-interfaces operational    |

---

## 9. File Reference

| File              | Purpose                                |
|-------------------|----------------------------------------|
| setup_ports.py    | Configure test interfaces              |
| arp_tests.py      | ARP functional + NEG + R               |
| nd_tests.py       | ND functional + NEG + R                |
| breakout_tests.py | Port breakout automation               |
| test_runner.py    | Master execution + report              |

---

## 10. Notes

- All scripts require sudo.
- Verify `conf.iface` before sending Scapy traffic.
- Use `tcpdump -i ethX` on RX side for verification.
- Breakout tests require physical ASIC platform.
- Robustness tests validate persistence and consistency.
- NEG tests validate malformed packet handling.

---

## 11. Test Execution

### Prerequisites
- SONiC device with breakout-capable ports
- Scapy installed on test hosts
- Traffic generator support (for Breakout tests on HW)

### Running Tests

```bash
# Full test suite
./bin/spytest --testbed ./testbeds/testbed_arp_nd.yaml \
    tests/system/arp_nd_breakout/ \
    --logs-path ./logs/arp_nd_breakout_test

# ARP tests only
./bin/spytest --testbed ./testbeds/testbed_arp_nd.yaml \
    tests/system/arp_nd_breakout/arp_tests.py \
    --logs-path ./logs/arp_test

# ND tests only
./bin/spytest --testbed ./testbeds/testbed_arp_nd.yaml \
    tests/system/arp_nd_breakout/nd_tests.py \
    --logs-path ./logs/nd_test

# Breakout tests (requires HW)
./bin/spytest --testbed ./testbeds/testbed_hw.yaml \
    tests/system/arp_nd_breakout/breakout_tests.py \
    --logs-path ./logs/breakout_test
```

---

**Test Plan Version:** 1.0
**Last Updated:** March 2026
**Status:** Ready for Implementation
