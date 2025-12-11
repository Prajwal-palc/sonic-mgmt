# BGP Peer-Group Manual Configuration Reference

This document contains the **exact manual CLI commands** used to validate all 6 BGP peer-group test cases on SONiC devices.

## Device Information

- **DUT1**: 192.168.100.203 (admin/YourPaSsWoRd)
- **DUT2**: 192.168.100.196 (admin/YourPaSsWoRd)
- **Interface**: Ethernet4
- **IP Addresses**: 10.1.1.1/24 (D1), 10.1.1.2/24 (D2)
- **ASN**: 65001
- **Router IDs**: 1.1.1.1 (D1), 2.2.2.2 (D2)

---

## PG-01: Create Peer-Group and Apply to Neighbors

### DUT1 Commands:
```
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic()# router bgp 65001
sonic(-router-bgp)# exit
sonic()# interface Ethernet 4
sonic(-if-Ethernet4)# ip address 10.1.1.1/24
sonic(-if-Ethernet4)# router bgp 65001
sonic(-router-bgp)# router-id 1.1.1.1
sonic(-router-bgp)# neighbor 10.1.1.2 remote-as 65001
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show bgp ipv4 unicast summary
sonic# show bgp summary
```

### DUT2 Commands:
```
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic()# router bgp 65001
sonic(-router-bgp)# exit
sonic()# interface Ethernet 4
sonic(-if-Ethernet4)# ip address 10.1.1.2/24
sonic(-if-Ethernet4)# router bgp 65001
sonic(-router-bgp)# router-id 2.2.2.2
sonic(-router-bgp)# neighbor 10.1.1.1 remote-as 65001
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show bgp ipv4 unicast summary
sonic# show bgp summary
```

### Expected Result:
```
Neighbor    V    AS   MsgRcvd   MsgSent   Up/Down State/PfxRcd
10.1.1.2    4  65001       3         4   00:00:29           0
```

---

## PG-02: Peer-Group Attribute Inheritance

### DUT1 Commands:
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 1.1.1.1
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# timers 30 90
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.2 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
```

### DUT2 Commands:
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 2.2.2.2
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# timers 30 90
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.1 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
```

### Expected Config:
```
peer-group 1
  remote-as 65001
  timers 30 90
  address-family ipv4 unicast
   activate
neighbor 10.1.1.X remote-as 65001
  peer-group 1
  address-family ipv4 unicast
   activate
```

---

## PG-03: Override Peer-Group Attribute on Single Neighbor

### DUT1 Commands (with override):
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 1.1.1.1
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# timers 60 180
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.2 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# timers 10 30
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
```

### DUT2 Commands (no override):
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 2.2.2.2
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# timers 60 180
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.1 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
```

### Expected Config:
```
# DUT1: Neighbor overrides timers
peer-group 1: timers 60 180
neighbor 10.1.1.2: timers 10 30 (overridden)

# DUT2: Neighbor inherits timers
peer-group 1: timers 60 180
neighbor 10.1.1.1: (inherits 60 180)
```

---

## PG-04: Peer-Group with AF-Level Settings

### DUT1 Commands:
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 1.1.1.1
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.2 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# description "Peer with AF inheritance"
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
```

### DUT2 Commands:
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 2.2.2.2
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.1 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# description "Peer with AF inheritance"
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
```

### Expected Config:
```
neighbor 10.1.1.X remote-as 65001
  description Peer with AF inheritance
  peer-group 1
```

---

## PG-05: Peer-Group with Route-Map Inheritance

### DUT1 Commands:
```
sonic# configure
sonic()# route-map RM_IN permit 10
sonic(-route-map)# set local-preference 200
sonic(-route-map)# exit
sonic()# route-map RM_OUT permit 10
sonic(-route-map)# set metric 100
sonic(-route-map)# exit
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 1.1.1.1
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# route-map RM_IN in
sonic(-router-bgp-pg-af)# route-map RM_IN out
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.2 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# exit
sonic(-router-bgp-neighbor)# exit
sonic(-router-bgp)# end
sonic# show route-map
sonic# show running-configuration bgp
```

### DUT2 Commands:
```
sonic# configure
sonic()# route-map RM_IN permit 10
sonic(-route-map)# set local-preference 150
sonic(-route-map)# exit
sonic()# route-map RM_OUT permit 10
sonic(-route-map)# set metric 50
sonic(-route-map)# exit
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 2.2.2.2
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# route-map RM_IN in
sonic(-router-bgp-pg-af)# route-map RM_IN out
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.1 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# exit
sonic(-router-bgp-neighbor)# exit
sonic(-router-bgp)# end
sonic# show route-map
sonic# show running-configuration bgp
```

### Expected Config:
```
peer-group 1
  address-family ipv4 unicast
   route-map RM_IN in
   route-map RM_IN out
```

---

## PG-06: Peer-Group Password/MD5 Inheritance

### DUT1 Commands:
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 1.1.1.1
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# password bgp_secret_password
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.2 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# activate
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
sonic# show bgp summary
```

### DUT2 Commands:
```
sonic# configure
sonic()# router bgp 65001
sonic(-router-bgp)# router-id 2.2.2.2
sonic(-router-bgp)# peer-group 1
sonic(-router-bgp-pg)# remote-as 65001
sonic(-router-bgp-pg)# password bgp_secret_password
sonic(-router-bgp-pg)# address-family ipv4 unicast
sonic(-router-bgp-pg-af)# activate
sonic(-router-bgp-pg-af)# exit
sonic(-router-bgp-pg)# exit
sonic(-router-bgp)# neighbor 10.1.1.1 remote-as 65001
sonic(-router-bgp-neighbor)# peer-group 1
sonic(-router-bgp-neighbor)# address-family ipv4 unicast
sonic(-router-bgp-neighbor-af)# end
sonic# show running-configuration bgp
sonic# show bgp summary
```

### Expected Config:
```
peer-group 1
  remote-as 65001
  password bgp_secret_password
```

### Expected Result:
```
IPv4 Unicast Summary:
Peers 1, using 24 KiB of memory
Peer groups 1, using 64 bytes of memory

Neighbor    V    AS   MsgRcvd   MsgSent   Up/Down State/PfxRcd
10.1.1.2    4  65001      97        96   00:02:38           0
```

---

## Common Verification Commands

```bash
# Show BGP summary
sonic# show bgp summary
sonic# show bgp ipv4 unicast summary

# Show BGP neighbor details
sonic# show bgp neighbor 10.1.1.X

# Show running BGP configuration
sonic# show running-configuration bgp

# Show route-maps
sonic# show route-map

# Show interface status
sonic# show interface status Ethernet4

# Show IP interfaces
sonic# show ip interface
```

---

## Key Observations

1. **No Ping Test**: Manual validation proceeded directly from IP configuration to BGP configuration without ping testing
2. **BGP Session = Connectivity Verified**: Successful BGP session establishment proves IP connectivity
3. **Timers**: keepalive/holdtime format is `timers 30 90` (keepalive holdtime)
4. **Peer-Group Application**: Use `peer-group 1` command under neighbor to attach
5. **Route-Map Application**: Route-maps applied at address-family level on peer-group
6. **Password**: Applied at peer-group level, inherited by all members

---

## Configuration Hierarchy

```
router bgp 65001
├── router-id 1.1.1.1
├── peer-group 1
│   ├── remote-as 65001
│   ├── timers 30 90
│   ├── password bgp_secret_password
│   └── address-family ipv4 unicast
│       ├── activate
│       ├── route-map RM_IN in
│       └── route-map RM_IN out
└── neighbor 10.1.1.2 remote-as 65001
    ├── peer-group 1
    ├── description "..."
    ├── timers 10 30 (optional override)
    └── address-family ipv4 unicast
        └── activate
```

---

**Document Date**: 2025-12-11
**Validated On**: SONiC 4.x with Klish CLI
**Topology**: 2-device (D1-D2) via Ethernet4
