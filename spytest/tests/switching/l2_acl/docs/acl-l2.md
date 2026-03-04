# L2 ACL Test Plan — Minimal Topology

## Topology

```
  +-----------+   eth0       eth1   +-----------+
  |  Scapy TX +-------[ DUT ]-------+ Scapy RX  |
  | 10.0.0.1  |     Port1  Port2    | 20.0.0.2  |
  | MAC: AA:01|   ACL applied IN    | MAC: BB:02|
  +-----------+                     +-----------+
```

**Two hosts, two DUT ports. All ACLs applied ingress on DUT Port1.**

| Role        | Interface | IP Address  | MAC               |
|-------------|-----------|-------------|-------------------|
| TX (Sender) | eth0      | 10.0.0.1/24 | 00:AA:AA:AA:AA:01 |
| RX (Receiver)| eth1     | 20.0.0.2/24 | 00:BB:BB:BB:BB:02 |

---

## Legend

| Tag | Meaning                                               |
|-----|-------------------------------------------------------|
| B   | Both VS and HW                                        |
| NEG | Negative/edge case test                               |
| R   | Robustness/persistence test                           |

---

## L2 ACL Test Cases (19 cases)

### Functional Test Cases (8 cases)

| TC ID | Description                           | Tag | Scapy Traffic                                         | Expected              |
|-------|---------------------------------------|-----|-------------------------------------------------------|-----------------------|
| L2-01 | Permit exact source MAC               | B   | `Ether(src="00:AA:AA:AA:AA:01")/IP()`                 | Forwarded             |
| L2-02 | Deny exact source MAC                 | B   | `Ether(src="DE:AD:00:00:00:01")/IP()`                 | Dropped               |
| L2-03 | Deny exact destination MAC            | B   | `Ether(dst="FE:ED:00:00:00:02")/IP()`                 | Dropped               |
| L2-04 | Deny broadcast destination MAC        | B   | `Ether(dst="FF:FF:FF:FF:FF:FF")/ARP()`                | Dropped               |
| L2-05 | Deny EtherType ARP (0x0806)           | B   | `Ether(type=0x0806)/ARP()`                            | Dropped               |
| L2-06 | Deny specific VLAN (VLAN 100)         | B   | `Ether()/Dot1Q(vlan=100)/IP()`                        | Dropped               |
| L2-07 | Permit VLAN 10, deny VLAN 200         | B   | `Dot1Q(vlan=10)/IP()` vs `Dot1Q(vlan=200)/IP()`       | 10=Fwd / 200=Drop     |
| L2-08 | ACL rule priority — permit before deny| B   | `Ether(src="00:AA:AA:AA:AA:01")` with deny-all last   | Forwarded (rule 1 wins)|

### Negative/Edge Case Tests (3 cases)

| TC ID | Description                           | Tag | Scapy Traffic                                         | Expected              |
|-------|---------------------------------------|-----|-------------------------------------------------------|-----------------------|
| L2-N01 | MAC case sensitivity (uppercase hex)  | NEG | `Ether(src="00:aa:aa:aa:aa:01")` lowercase vs rule uppercase | Forwarded (case-insensitive) |
| L2-N02 | Multicast destination MAC             | NEG | `Ether(dst="01:00:5E:00:00:01")/IP()`                 | Forwarded (no rule)   |
| L2-N03 | ACL with invalid/corrupt MAC          | NEG | `Ether(src="ZZ:ZZ:ZZ:ZZ:ZZ:ZZ")` - malformed         | Dropped or error handling |

### Robustness/Persistence Tests (8 cases)

| TC ID | Description                           | Tag | Scapy Traffic                                         | Expected              |
|-------|---------------------------------------|-----|-------------------------------------------------------|-----------------------|
| L2-R01 | ACL rule persistence after DUT reboot | B   | Send traffic before/after simulated reboot            | Rules persist, traffic behavior unchanged |
| L2-R02 | ACL modification while traffic active | B   | Update rule, traffic continues mid-stream             | New packets follow updated rule |
| L2-R03 | Multiple ACL updates in rapid succession | B | Rapid enable/disable of ACL rules (10+ cycles)        | No errors, final state consistent |
| L2-R04 | Concurrent traffic on denied/allowed MAC pairs | B | Two flows with different MAC rules active             | Correct handling of both flows (no crosstalk) |
| L2-R05 | ACL counter accuracy after long traffic run | B | 1000+ packets, verify DUT counter == TX count         | Counter accurate, no overflow/reset |
| L2-R06 | VLAN rule persistence across config changes | B | Add/remove other rules, VLAN ACL still works          | Unaffected by other config changes |
| L2-R07 | ACL aging/timeout behavior (if supported) | B | Send initial traffic, wait 5min, re-send              | Consistent behavior (no state timeout) |
| L2-R08 | Mixed permit/deny rules with same match criteria | NEG | First rule permit, second deny, same MAC              | First rule wins (no ambiguity) |

---

## Test Summary

| Suite    | Functional | Negative | Robustness | Total |
|----------|------------|----------|------------|-------|
| L2 ACL   | 8          | 3        | 8          | 19    |

---

## Pass / Fail Criteria

| ACL Action | Pass Condition                              |
|------------|---------------------------------------------|
| PERMIT     | RX count ≥ 90% of TX count                  |
| DENY       | RX count == 0 (all packets dropped)         |
| Counter    | DUT ACL hit counter == TX packet count      |

---

## File Reference

| File                   | Purpose                                   |
|------------------------|-------------------------------------------|
| `setup_ports.py`       | Configure TX/RX Scapy ports (eth0, eth1)  |
| `l2_acl_traffic.py`    | L2-01 → L2-R08 automated traffic tests    |
| `acl_test_runner.py`   | Master runner with VS/HW filter & report  |

---

## Notes

- All scripts require `sudo` (raw packet socket).
- Verify `conf.iface` is set to the correct interface before running.
- Use `tcpdump -i eth1` on the RX side to independently confirm drops.
- Negative (NEG) tests verify edge cases, invalid input handling, and error resilience.
- Robustness (R) tests verify persistence, consistency, and lack of state leakage across reconfigurations.
- All robustness tests should pass on both VS and HW platforms unless explicitly tagged HW.
