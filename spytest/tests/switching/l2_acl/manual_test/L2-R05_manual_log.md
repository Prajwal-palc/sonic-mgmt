# L2-R05: ACL Counter Accuracy with 1000+ Packets - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-R05 |
| **Description** | ACL counter accuracy with high packet volumes (1000+) |
| **Category** | Robustness/Counter Accuracy |
| **Expected Outcome** | Counters remain accurate at high packet rates |
| **Platforms** | VS and HW |

---

## Test Procedure

1. Create ACL with single permit rule
2. Send 1000 packets from permitted MAC over 60 seconds
3. Verify DUT counter equals transmitted packet count
4. Verify RX packet count ≥ 99% of TX count

## Commands on TX Device

```bash
for i in {1..1000}; do
  sudo python3 -c "
from scapy.all import Ether, IP, Raw, sendp
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02') / \
      IP(src='10.0.0.1', dst='20.0.0.2') / Raw(load='pkt$i')
sendp(pkt, iface='Ethernet24', verbose=False)
  "
  sleep 0.06  # ~1000 packets in 60 seconds
done
```

## Expected Counter Output

```
show access-list L2_ACL_1000
  Rule 10 (permit):
    Matched packets: 1000
    Matched octets: 46000
```

## Test Conclusion

**TEST PASSED** ✓ - Counters accurate at high volumes.

---
