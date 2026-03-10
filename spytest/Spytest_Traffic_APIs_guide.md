# SpyTest Traffic APIs — Complete In-Depth Guide

> **Audience:** SONiC test engineers writing or reviewing traffic-based test cases using SpyTest.  
> **Scope:** API usage, internals, custom API creation, silent-pass prevention, best practices, and a fully annotated test case scenario.

---

## Table of Contents

1. [What Are SpyTest Traffic APIs?](#1-what-are-spytest-traffic-apis)
2. [Architecture & Backend Internals](#2-architecture--backend-internals)
3. [SpyTest APIs vs Raw Scapy — Detailed Comparison](#3-spytest-apis-vs-raw-scapy--detailed-comparison)
4. [How to Use the Traffic APIs Properly](#4-how-to-use-the-traffic-apis-properly)
5. [Writing Custom Traffic APIs When Built-ins Are Not Enough](#5-writing-custom-traffic-apis-when-built-ins-are-not-enough)
6. [Silent Pass Cases — Detection & Prevention](#6-silent-pass-cases--detection--prevention)
7. [Things to Ensure When Using Traffic APIs](#7-things-to-ensure-when-using-traffic-apis)
8. [Additional Traffic API Capabilities](#8-additional-traffic-api-capabilities)
9. [End-to-End Test Case Scenario — Fully Annotated](#9-end-to-end-test-case-scenario--fully-annotated)
10. [Debugging Traffic Issues](#10-debugging-traffic-issues)
11. [Summary Reference Card](#11-summary-reference-card)

---

## 1. What Are SpyTest Traffic APIs?

SpyTest (SONiC Python Test Framework) provides a **Traffic Abstraction Layer** on top of packet generators — whether that is software (Scapy on a Linux host) or hardware (IxNetwork, Spirent, ixia-c).

The core idea is that your test script never talks directly to Scapy or IxNetwork. It talks to one unified API set. The driver underneath is swappable without changing a single line of test code.

### Why This Matters

Without this abstraction, if you write a test using raw Scapy and later need to run it on IxNetwork hardware for line-rate testing, you would have to rewrite the entire test. With SpyTest Traffic APIs, only the backend configuration changes.

```
+----------------------------------------------------------------------+
¦                          TEST SCRIPT (.py)                           ¦
¦                                                                      ¦
¦   tg.tg_traffic_config(...)   ? Define what packets to send         ¦
¦   tg.tg_traffic_control(...)  ? Start / Stop / Clear               ¦
¦   tg.tg_traffic_stats(...)    ? Read TX/RX counts and loss          ¦
+----------------------------------------------------------------------+
                                  ¦
                                  ¦  One unified API surface
                                  ¦  (your test code never changes)
                                  ?
+----------------------------------------------------------------------+
¦               SpyTest TG Abstraction Layer  (tgen/tg.py)             ¦
¦                                                                      ¦
¦  Receives your API call, inspects the configured backend, and        ¦
¦  dispatches to the correct driver class below.                       ¦
¦                                                                      ¦
¦  +-----------------+   +------------------+   +------------------+  ¦
¦  ¦  ScapyDriver    ¦   ¦   IxiaDriver     ¦   ¦  SpirentDriver   ¦  ¦
¦  ¦  (software)     ¦   ¦   (hardware)     ¦   ¦  (hardware)      ¦  ¦
¦  ¦                 ¦   ¦                  ¦   ¦                  ¦  ¦
¦  ¦  Uses raw Scapy ¦   ¦  Uses IxNetwork  ¦   ¦  Uses Spirent    ¦  ¦
¦  ¦  sendp/sniff    ¦   ¦  REST/TCL API    ¦   ¦  STC API         ¦  ¦
¦  +-----------------+   +------------------+   +------------------+  ¦
+-----------+----------------------------------------------------------+
            ¦
            ?
+----------------------------------------------------------------------+
¦                   Physical / Virtual Network                         ¦
¦                                                                      ¦
¦   NIC (TGen Port 1) ------? DUT ------? NIC (TGen Port 2)           ¦
¦   Packets sent                           Packets captured & counted  ¦
+----------------------------------------------------------------------+
```

**Reading this diagram:**
- The top box is your test script — it only ever calls three API families.
- The middle box is the abstraction layer. It acts like a router: it receives your call and sends it to the right driver based on testbed config.
- The bottom box is the actual physical path packets travel. The TGen port is either a Linux NIC (Scapy) or a hardware TGen card.
- The important point: swapping the driver in the middle does NOT require changes in the top or bottom boxes.

---

## 2. Architecture & Backend Internals

### 2.1 What Happens Step by Step When You Call `tg_traffic_config`

Understanding this internal flow is critical. Many bugs and silent passes come from not knowing what happens between your API call and actual packet transmission.

```
YOUR CALL:
tg.tg_traffic_config(port_handle=tg_ph_1, mac_src='00:01:02:03:04:05',
                     ip_src_addr='10.0.0.1', rate_pps=1000, ...)
    ¦
    ¦  Step 1: Parameter Validation
    ¦  SpyTest checks that all provided params are valid keys.
    ¦  Unknown params are silently ignored (common source of bugs!).
    ¦  port_handle is validated against known connected ports.
    ¦
    ?
+-----------------------------------------------------+
¦  tg.py  dispatch()                                  ¦
¦  Looks up backend: "scapy" / "ixia" / "spirent"    ¦
¦  Calls: ScapyDriver.tg_traffic_config(...)          ¦
+-----------------------------------------------------+
                       ¦
                       ¦  Step 2: Stream Descriptor Built
                       ¦  All params stored in internal dict:
                       ¦  stream_table[stream_id] = {
                       ¦      'port': tg_ph_1,
                       ¦      'mac_src': '00:01:02:03:04:05',
                       ¦      'rate_pps': 1000, ...
                       ¦  }
                       ¦
                       ?
+-----------------------------------------------------+
¦  ScapyDriver._build_packet()                        ¦
¦                                                     ¦
¦  Reads stream_table entry and stacks Scapy layers:  ¦
¦                                                     ¦
¦  pkt = Ether(src=mac_src, dst=mac_dst)              ¦
¦  if vlan_enable:                                    ¦
¦      pkt = pkt / Dot1Q(vlan=vlan_id)               ¦
¦  if l3_protocol == 'ipv4':                          ¦
¦      pkt = pkt / IP(src=ip_src, dst=ip_dst, ttl=64)¦
¦  if l4_protocol == 'udp':                           ¦
¦      pkt = pkt / UDP(sport=..., dport=...)          ¦
¦  pkt = pad_to(pkt, frame_size)                      ¦
¦                                                     ¦
¦  Result stored as stream_table[id]['scapy_pkt']     ¦
+-----------------------------------------------------+
                       ¦
                       ¦  Step 3: Return stream_id to caller
                       ¦  han = {'stream_id': 'stream_1'}
                       ?
    CALL RETURNS — No packet has been sent yet!
    Traffic only starts when tg_traffic_control(action='run') is called.
```

**Key takeaway from this diagram:** `tg_traffic_config` only *defines* the stream and builds the packet object in memory. Nothing is sent to the wire at this point. This is a common misconception — calling config does not start traffic.

---

### 2.2 What Happens When You Call `tg_traffic_control(action='run')`

```
tg.tg_traffic_control(action='run', handle=stream_id)
    ¦
    ?
ScapyDriver._start_stream(stream_id)
    ¦
    +-- Retrieves pre-built scapy_pkt from stream_table
    ¦
    +-- Starts AsyncSniffer on the RX port(s)
    ¦   +----------------------------------------------------+
    ¦   ¦  AsyncSniffer(iface=rx_iface,                      ¦
    ¦   ¦               prn=count_packet_callback,           ¦
    ¦   ¦               store=False)   ? runs in background  ¦
    ¦   ¦  This must start BEFORE TX begins.                 ¦
    ¦   ¦  If it starts after, early packets are missed.     ¦
    ¦   +----------------------------------------------------+
    ¦
    +-- Spawns TX thread
        +----------------------------------------------------+
        ¦  while not stop_event.is_set():                    ¦
        ¦      sendp(pkt, iface=tx_iface, verbose=False)     ¦
        ¦      tx_counter += 1                               ¦
        ¦      time.sleep(1 / rate_pps)   ? rate throttle   ¦
        +----------------------------------------------------+
        
        TX thread and RX sniffer now run concurrently.
        
        TX Port NIC ---- wire ----? DUT ---- wire ----? RX Port NIC
             ¦                                               ¦
             ¦  sendp() puts frames on wire                  ¦
             ¦                                          AsyncSniffer
             ¦                                          counts inbound
             ?                                          frames
        tx_counter++                               rx_counter++
```

**Why the sniffer start order matters:** The AsyncSniffer is started *before* the TX thread in a correct implementation. If for any reason (e.g. in a custom or patched driver) the sniffer starts after TX, you will miss the first batch of packets. This leads to RX < TX, and artificially high loss numbers — or if your test only checks `loss_pct < threshold` without checking absolute RX > 0, a silent pass.

---

### 2.3 Stats Collection — What `tg_traffic_stats` Actually Returns

```
tg.tg_traffic_stats(port_handle=tg_ph_2, mode='aggregate')
    ¦
    ?
ScapyDriver reads two data sources:

    Source 1: TX Counter Dict
    +----------------------------------------------+
    ¦  _tx_counters[port_handle] = {               ¦
    ¦      'total_pkts': 10000,   ? incremented    ¦
    ¦      'total_bytes': 640000  ¦  by TX thread  ¦
    ¦  }                          ¦  per sendp()   ¦
    +----------------------------------------------+

    Source 2: RX Counter Dict (populated by AsyncSniffer callback)
    +----------------------------------------------+
    ¦  _rx_counters[port_handle] = {               ¦
    ¦      'total_pkts': 9985,    ? incremented    ¦
    ¦      'total_bytes': 638800  ¦  by sniffer    ¦
    ¦  }                          ¦  prn callback  ¦
    +----------------------------------------------+

    Assembled into return dict:
    {
      tg_ph_2: {
        'aggregate': {
          'tx': {'total_pkts': '10000', 'pkt_rate': '1000.0'},
          'rx': {'total_pkts': '9985',  'pkt_rate': '998.5'}
        }
      }
    }
    
    Loss = (10000 - 9985) / 10000 * 100 = 0.15%
```

**Important:** All values in the stats dict are returned as **strings**, not integers. Always cast with `int(stats[ph]['aggregate']['rx']['total_pkts'])` before doing arithmetic. Comparing a string `'9985'` with an integer `0` using `>` will give unexpected results in Python.

---

## 3. SpyTest APIs vs Raw Scapy — Detailed Comparison

The SpyTest Traffic APIs use Scapy under the hood in the software backend — but using them directly vs using the abstraction layer are very different experiences in practice.

### 3.1 Conceptual Difference

```
RAW SCAPY APPROACH                    SPYTEST TRAFFIC API APPROACH
---------------------------------     ---------------------------------
You manage everything manually:       SpyTest manages for you:

  Build packet layers yourself          Declarative params ? auto-built
  Call sendp() (blocking)               Non-blocking TX thread
  Manage timing manually                rate_pps enforced internally
  Start sniff() yourself                AsyncSniffer auto-started
  Count captured list manually          Counters auto-incremented
  Know OS interface name (eth0)         Logical port handle abstraction
  Rewrite test for each TGen            Same test works on all TGens
  No built-in loss calculation          tg_traffic_stats gives loss
  No stream concept                     Multiple streams per port
```

### 3.2 Side-by-Side Code: Same Test, Two Approaches

**Task:** Send 1000 UDP packets from Port 1, receive on Port 2, report loss.

#### Raw Scapy (Manual)

```python
import time
import threading
from scapy.all import Ether, IP, UDP, sendp, AsyncSniffer

# You must know the actual OS NIC names
TX_IFACE = "eth1"
RX_IFACE = "eth2"

# Build packet manually — layer by layer
pkt = (Ether(src="00:00:01:00:00:01", dst="00:aa:bb:cc:dd:ee") /
       IP(src="10.0.0.1", dst="10.0.0.2", ttl=64) /
       UDP(sport=1234, dport=5678) /
       b"X" * 18)   # Manual padding to 60 bytes

# Start sniffer BEFORE sending (easy to forget!)
rx_pkts = []
sniffer = AsyncSniffer(iface=RX_IFACE, prn=lambda p: rx_pkts.append(p), store=False)
sniffer.start()

# Send — this blocks the calling thread
# Rate control: inter=0.001 means 1000 pps, calculated manually
tx_count = 1000
sendp(pkt, iface=TX_IFACE, count=tx_count, inter=0.001, verbose=False)

# Wait for last packets to arrive
time.sleep(1)
sniffer.stop()

rx_count = len(rx_pkts)
loss_pct = (tx_count - rx_count) / tx_count * 100

print(f"TX: {tx_count}, RX: {rx_count}, Loss: {loss_pct:.2f}%")
# No assertion helpers — you write those yourself
# If you forget to start sniffer first, rx_count = 0 silently
```

**Problems with this approach:**
- Blocks the thread during sending — cannot do DUT actions while traffic runs
- `inter=0.001` is approximate; OS scheduling affects real rate
- No port-handle concept — hard to scale to multi-port tests
- Not portable — `eth1`/`eth2` names are machine-specific
- Sniffer start is easy to forget or mis-sequence
- No built-in stream concept — multi-stream needs manual threading

#### SpyTest Traffic API (Proper)

```python
from spytest import st

def test_udp_forwarding(fixture_data):
    vars = st.ensure_min_topology("D1T1:2")
    tg, tg_ph_list = st.get_tg_info(vars)
    tg_ph_1 = tg_ph_list[0]   # logical TX port handle
    tg_ph_2 = tg_ph_list[1]   # logical RX port handle

    # Define stream — params map to Scapy layers internally
    han = tg.tg_traffic_config(
        port_handle  = tg_ph_1,
        mode         = 'create',
        transmit_mode= 'single_burst',   # send exactly N packets
        pkts_per_burst = 1000,
        rate_pps     = 1000,
        frame_size   = 64,
        l2_encap     = 'ethernet_ii',
        mac_src      = '00:00:01:00:00:01',
        mac_dst      = '00:aa:bb:cc:dd:ee',
        l3_protocol  = 'ipv4',
        ip_src_addr  = '10.0.0.1',
        ip_dst_addr  = '10.0.0.2',
        l4_protocol  = 'udp',
        udp_src_port = 1234,
        udp_dst_port = 5678,
    )
    stream_id = han['stream_id']

    # Clear any leftover counts from previous tests
    tg.tg_traffic_control(action='clear_stats', port_handle=tg_ph_list)

    # Non-blocking start — you can do DUT actions while traffic flows
    tg.tg_traffic_control(action='run', handle=stream_id)
    st.wait(3)
    tg.tg_traffic_control(action='stop', handle=stream_id)
    st.wait(1)  # drain

    # Structured stats — no manual counting
    tx_s = tg.tg_traffic_stats(port_handle=tg_ph_1, mode='aggregate')
    rx_s = tg.tg_traffic_stats(port_handle=tg_ph_2, mode='aggregate')

    tx = int(tx_s[tg_ph_1]['aggregate']['tx']['total_pkts'])
    rx = int(rx_s[tg_ph_2]['aggregate']['rx']['total_pkts'])

    # Built-in assertion helpers
    assert tx > 0, "Nothing was transmitted"
    assert rx > 0, "Nothing received — DUT not forwarding"

    loss_pct = (tx - rx) / tx * 100
    st.log(f"TX={tx}, RX={rx}, Loss={loss_pct:.2f}%")
    assert loss_pct < 1.0, f"Unacceptable loss: {loss_pct:.2f}%"
    st.report_pass('test_case_passed')
```

**Advantages gained:**
- Non-blocking TX ? DUT actions possible mid-traffic
- Portable across any testbed (Scapy, IxNetwork, etc.)
- Rate is enforced by the driver, not manual `inter=` calculation
- Sniffer lifecycle managed internally — no sequencing errors
- Stream concept allows multi-stream from one port trivially
- Stats returned as structured dict — consistent across backends

---

## 4. How to Use the Traffic APIs Properly

### 4.1 The Correct API Call Sequence

Always follow this sequence. Deviating from it — especially steps 3 and 5 — is the most common source of test bugs.

```
+--------------------------------------------------------------------+
¦              MANDATORY SEQUENCE FOR EVERY TRAFFIC TEST            ¦
¦--------------------------------------------------------------------¦
¦ #  ¦ Action                              ¦ API Call               ¦
¦----+-------------------------------------+------------------------¦
¦ 1  ¦ Get port handles from topology      ¦ st.get_tg_info(vars)   ¦
¦ 2  ¦ Configure stream(s)                 ¦ tg_traffic_config()    ¦
¦ 3  ¦ CLEAR STATS  ? never skip this     ¦ tg_traffic_control     ¦
¦    ¦                                     ¦ (action='clear_stats') ¦
¦ 4  ¦ Start traffic                       ¦ tg_traffic_control     ¦
¦    ¦                                     ¦ (action='run')         ¦
¦ 5  ¦ Wait / do DUT actions               ¦ st.wait(N)             ¦
¦ 6  ¦ STOP traffic ? before reading stats ¦ tg_traffic_control     ¦
¦    ¦                                     ¦ (action='stop')        ¦
¦ 7  ¦ Drain wait (2s)                     ¦ st.wait(2)             ¦
¦ 8  ¦ Collect stats                       ¦ tg_traffic_stats()     ¦
¦ 9  ¦ Assert TX > 0 AND RX > 0            ¦ Python assert          ¦
¦ 10 ¦ Calculate and assert loss           ¦ Python arithmetic      ¦
¦ 11 ¦ Teardown: stop all, remove streams  ¦ tg_traffic_control     ¦
+-------------------------------------------------------------------+
```

### 4.2 Transmit Modes Explained

```
TRANSMIT MODES
------------------------------------------------------------------

  continuous          single_burst           multi_burst
  -----------         -------------          ------------
  +---------+         +------+               +--+  +--+  +--+
  ¦¦¦¦¦¦¦¦¦¦¦         ¦¦¦¦¦¦¦¦               ¦¦¦¦  ¦¦¦¦  ¦¦¦¦
  ¦         ¦         +------+               +--+  +--+  +--+
  ¦  Sends  ¦          Sends N               Sends N bursts
  ¦ forever ¦          pkts then             of M pkts each
  ¦ until   ¦          stops                 with gap between
  ¦ stopped ¦          automatically         ? use for bursty
  +---------+                                  traffic tests
  
  ? Use for          ? Use for             
    sustained          exact count
    load tests         tests

  Params needed:     pkts_per_burst=N      burst_loop_count=N
  rate_pps           rate_pps              pkts_per_burst=M
                                           inter_burst_gap=G
```

### 4.3 Field Increment / Range Traffic

A powerful feature not available in simple raw Scapy usage is automatic field increment. This lets one stream simulate many different source IPs, MACs, or ports without multiple streams.

```python
# Simulate 100 unique source IPs: 10.0.1.1 to 10.0.1.100
han = tg.tg_traffic_config(
    port_handle   = tg_ph_1,
    mode          = 'create',
    ip_src_addr   = '10.0.1.1',
    ip_src_mode   = 'increment',     # auto-increment the field
    ip_src_step   = '0.0.0.1',       # step size per packet
    ip_src_count  = 100,             # wrap after 100 values

    # Similarly for MACs:
    mac_src       = '00:00:01:00:00:01',
    mac_src_mode  = 'increment',
    mac_src_step  = '00:00:00:00:00:01',
    mac_src_count = 50,

    # And for ports:
    udp_src_port      = 1024,
    udp_src_port_mode = 'increment',
    udp_src_port_step = 1,
    udp_src_port_count= 100,
    ...
)
```

Internally, the ScapyDriver generates a list of packets with these field values and cycles through them in the TX thread. This is the SpyTest equivalent of what hardware TGens call a "flow group."

---

## 5. Writing Custom Traffic APIs When Built-ins Are Not Enough

This is one of the most important and under-documented topics. **Yes, you absolutely can write new APIs** — and in practice you often must, because:

- The built-in `tg_traffic_config` does not expose every possible Scapy field
- You need a protocol not covered (e.g. MPLS, VXLAN, GRE, custom EtherType)
- You want a helper that combines stream setup + DUT verification in one call
- You need to send a crafted malformed/invalid packet for negative testing

### 5.1 Pattern 1: Wrapper Helper Function (Simplest)

When the underlying API supports what you need but the call is verbose, write a wrapper.

```python
# apis/traffic_utils.py

from spytest import st

def send_and_verify_traffic(tg, tg_ph_tx, tg_ph_rx, stream_params,
                             duration=10, loss_threshold=1.0):
    """
    Convenience wrapper: configure ? clear ? run ? stop ? verify.
    Returns (tx, rx, loss_pct) tuple.
    Always guards against silent pass.
    
    Example:
        tx, rx, loss = send_and_verify_traffic(
            tg, tg_ph_1, tg_ph_2,
            stream_params={
                'mac_src': '00:01:02:03:04:05',
                'ip_src_addr': '10.0.0.1',
                'ip_dst_addr': '10.0.0.2',
                'rate_pps': 1000,
                'frame_size': 128,
            }
        )
    """
    # Merge with required defaults
    base_params = {
        'mode': 'create',
        'transmit_mode': 'continuous',
        'l2_encap': 'ethernet_ii',
        'l3_protocol': 'ipv4',
        'frame_size': 64,
    }
    base_params.update(stream_params)
    base_params['port_handle'] = tg_ph_tx

    han = tg.tg_traffic_config(**base_params)
    stream_id = han.get('stream_id')
    if not stream_id:
        st.error("Stream config failed — stream_id is None")
        return 0, 0, 100.0

    tg.tg_traffic_control(action='clear_stats',
                          port_handle=[tg_ph_tx, tg_ph_rx])
    tg.tg_traffic_control(action='run', handle=stream_id)
    st.wait(duration)
    tg.tg_traffic_control(action='stop', handle=stream_id)
    st.wait(2)

    tx_s = tg.tg_traffic_stats(port_handle=tg_ph_tx, mode='aggregate')
    rx_s = tg.tg_traffic_stats(port_handle=tg_ph_rx, mode='aggregate')

    tx = int(tx_s[tg_ph_tx]['aggregate']['tx']['total_pkts'])
    rx = int(rx_s[tg_ph_rx]['aggregate']['rx']['total_pkts'])

    if tx == 0:
        st.error("Silent pass guard: TX = 0. Stream did not send.")
        return 0, 0, 100.0
    if rx == 0:
        st.error("Silent pass guard: RX = 0. DUT not forwarding.")
        return tx, 0, 100.0

    loss_pct = (tx - rx) / tx * 100
    st.log(f"Traffic result: TX={tx}, RX={rx}, Loss={loss_pct:.2f}%")

    if loss_pct >= loss_threshold:
        st.report_fail('traffic_verification_failed',
                       f"Loss {loss_pct:.2f}% exceeds {loss_threshold}%")

    return tx, rx, loss_pct
```

### 5.2 Pattern 2: Raw Scapy Injection for Unsupported Protocols

When `tg_traffic_config` does not support a protocol (e.g. MPLS, VXLAN, GRE, custom EtherType), you bypass the stream config layer and use raw Scapy directly, but still use the SpyTest port handle to resolve the interface name.

```python
# apis/custom_pkt_send.py

from scapy.all import (Ether, IP, UDP, MPLS, GRE,
                       sendp, AsyncSniffer)
from spytest import st

def send_mpls_traffic(tg, tg_ph_tx, tg_ph_rx,
                      mpls_label=100, src_ip='10.0.0.1',
                      dst_ip='10.0.0.2', count=1000, rate_pps=500):
    """
    Send MPLS-encapsulated traffic using raw Scapy.
    tg_traffic_config does not support MPLS natively,
    so we build the packet ourselves but use SpyTest's
    port resolution to get the interface name.
    """
    # Get actual OS interface name from the logical port handle
    tx_iface = tg.get_port_iface(tg_ph_tx)
    rx_iface = tg.get_port_iface(tg_ph_rx)

    # Build MPLS packet manually
    pkt = (Ether(src='00:00:01:00:00:01', dst='00:00:02:00:00:01') /
           MPLS(label=mpls_label, cos=0, s=1, ttl=64) /
           IP(src=src_ip, dst=dst_ip, ttl=63) /
           UDP(sport=1234, dport=5678) /
           b'X' * 18)

    rx_count = [0]  # mutable counter for callback

    def rx_callback(pkt):
        # Filter only MPLS packets with expected label
        if pkt.haslayer(MPLS) and pkt[MPLS].label == mpls_label:
            rx_count[0] += 1

    sniffer = AsyncSniffer(iface=rx_iface, prn=rx_callback, store=False)
    sniffer.start()
    st.wait(0.1)  # Small wait to ensure sniffer is ready

    inter = 1.0 / rate_pps
    sendp(pkt, iface=tx_iface, count=count, inter=inter, verbose=False)

    st.wait(1)  # Allow last packets to arrive
    sniffer.stop()

    tx = count
    rx = rx_count[0]
    loss_pct = (tx - rx) / tx * 100 if tx > 0 else 100.0

    st.log(f"MPLS Traffic: TX={tx}, RX={rx}, Loss={loss_pct:.2f}%")

    if tx == 0 or rx == 0:
        st.report_fail('traffic_verification_failed',
                       f"MPLS TX={tx} RX={rx} — check MPLS config on DUT")
    if loss_pct >= 1.0:
        st.report_fail('traffic_verification_failed',
                       f"MPLS loss {loss_pct:.2f}% too high")

    return tx, rx, loss_pct


def send_vxlan_traffic(tg, tg_ph_tx, tg_ph_rx, vni=1000,
                       outer_src='192.168.1.1', outer_dst='192.168.1.2',
                       inner_src='10.0.0.1',   inner_dst='10.0.0.2',
                       count=500):
    """
    VXLAN encapsulated traffic — also not in tg_traffic_config natively.
    """
    from scapy.contrib.vxlan import VXLAN

    tx_iface = tg.get_port_iface(tg_ph_tx)
    rx_iface = tg.get_port_iface(tg_ph_rx)

    inner_pkt = (Ether(src='aa:bb:cc:00:00:01', dst='aa:bb:cc:00:00:02') /
                 IP(src=inner_src, dst=inner_dst) /
                 UDP(sport=100, dport=200))

    outer_pkt = (Ether() /
                 IP(src=outer_src, dst=outer_dst) /
                 UDP(sport=4789, dport=4789) /
                 VXLAN(vni=vni, flags='Instance') /
                 inner_pkt)

    rx_count = [0]
    sniffer = AsyncSniffer(
        iface=rx_iface,
        prn=lambda p: rx_count.__setitem__(0, rx_count[0]+1)
                      if p.haslayer(VXLAN) and p[VXLAN].vni == vni else None,
        store=False
    )
    sniffer.start()
    st.wait(0.1)

    sendp(outer_pkt, iface=tx_iface, count=count, verbose=False)
    st.wait(1)
    sniffer.stop()

    tx, rx = count, rx_count[0]
    loss_pct = (tx - rx) / tx * 100 if tx > 0 else 100.0
    st.log(f"VXLAN VNI={vni}: TX={tx}, RX={rx}, Loss={loss_pct:.2f}%")
    return tx, rx, loss_pct
```

### 5.3 Pattern 3: Extend the ScapyDriver (Advanced)

If you need a permanent extension that behaves like a native API call across all tests, you can subclass or monkey-patch the ScapyDriver.

```python
# spytest/tgen/scapy_ext.py  (your extension file)

from spytest.tgen.scapy import ScapyDriver
from scapy.all import Ether, IP, GRE

class ExtendedScapyDriver(ScapyDriver):
    """
    Extends the base ScapyDriver with GRE and MPLS support.
    Register this in testbed config to use it automatically.
    """

    def tg_traffic_config(self, **kwargs):
        # Intercept if custom protocol is requested
        if kwargs.get('l3_protocol') == 'gre':
            return self._config_gre_stream(**kwargs)
        # Fall through to original for everything else
        return super().tg_traffic_config(**kwargs)

    def _config_gre_stream(self, **kwargs):
        """Handle GRE stream configuration."""
        port_handle  = kwargs['port_handle']
        outer_src    = kwargs.get('gre_outer_src', '1.1.1.1')
        outer_dst    = kwargs.get('gre_outer_dst', '2.2.2.2')
        inner_src    = kwargs.get('ip_src_addr', '10.0.0.1')
        inner_dst    = kwargs.get('ip_dst_addr', '10.0.0.2')

        pkt = (Ether() /
               IP(src=outer_src, dst=outer_dst) /
               GRE() /
               IP(src=inner_src, dst=inner_dst))

        stream_id = self._register_custom_stream(port_handle, pkt, kwargs)
        return {'stream_id': stream_id}
```

### 5.4 When to Use Which Pattern

```
                    DO YOU NEED A NEW API?
                           ¦
              +-------------------------+
              ¦                         ¦
    Is it just repeated setup      Is it a missing
    logic / boilerplate?           protocol/field?
              ¦                         ¦
         Pattern 1:              +-----------------+
         Write a wrapper         ¦                 ¦
         helper function         Temporary         Permanent
                                 one-off?          reusable?
                                 ¦                 ¦
                              Pattern 2:        Pattern 3:
                              Raw Scapy          Extend
                              injection          ScapyDriver
                              in test file       subclass
```

---

## 6. Silent Pass Cases — Detection & Prevention

A **silent pass** is when your test reports PASS but the feature under test is actually broken. Traffic-based tests are particularly vulnerable because there are many ways for packet counts to appear correct when they are not.

### 6.1 Anatomy of a Silent Pass

```
EXAMPLE: Stream not started, test still passes

tg.tg_traffic_config(...)        ? Stream configured OK
                                     (but stream_id never used below)

# BUG: forgot to call tg_traffic_control(action='run')
# or: called it with wrong handle

st.wait(10)                       ? Waits for nothing

stats = tg.tg_traffic_stats(...)
tx = int(stats[ph]['aggregate']['tx']['total_pkts'])   # = 0
rx = int(stats[ph]['aggregate']['rx']['total_pkts'])   # = 0

# BAD ASSERTION — only checks percentage, not absolutes:
loss_pct = 0  (because 0-0/0 or division is skipped)
assert loss_pct < 1.0   ? PASSES! But nothing was tested!

Result: Test reports PASS. DUT forwarding was never verified.
```

### 6.2 All Known Silent Pass Scenarios

```
+-----------------------------------------------------------------------------------+
¦ SILENT PASS SCENARIO               ¦ ROOT CAUSE & FIX                             ¦
+------------------------------------+----------------------------------------------¦
¦ TX = 0, loss = 0%                  ¦ Stream not started or wrong handle.          ¦
¦                                    ¦ FIX: assert tx > 0 before loss check.        ¦
+------------------------------------+----------------------------------------------¦
¦ RX = 0, loss = 100% but test passes¦ Test only checks absolute rx count "rx > 0"  ¦
¦                                    ¦ with wrong threshold. FIX: assert rx > 0.    ¦
+------------------------------------+----------------------------------------------¦
¦ Stats not cleared before run       ¦ Old RX count from previous test inflates rx. ¦
¦                                    ¦ FIX: Always clear_stats before run.          ¦
+------------------------------------+----------------------------------------------¦
¦ Stats read BEFORE stop             ¦ TX counter still incrementing while you read.¦
¦                                    ¦ FIX: Always stop ? wait(2) ? then read.      ¦
+------------------------------------+----------------------------------------------¦
¦ Wrong port handle for RX stats     ¦ Reading tg_ph_1 (TX port) for RX count.     ¦
¦                                    ¦ tg_ph_1 RX is always ~0. FIX: use tg_ph_2.  ¦
+------------------------------------+----------------------------------------------¦
¦ Unknown param silently ignored     ¦ Typo in param name (e.g. 'vlan_Id').         ¦
¦                                    ¦ SpyTest ignores unknown params, uses default.¦
¦                                    ¦ FIX: Cross-check param names against docs.   ¦
+------------------------------------+----------------------------------------------¦
¦ Frame size < 64 bytes              ¦ NIC drops undersized frames silently.         ¦
¦                                    ¦ FIX: Always frame_size >= 64.                ¦
+------------------------------------+----------------------------------------------¦
¦ ARP not resolved for L3 traffic    ¦ DUT drops all frames (no ARP entry).         ¦
¦                                    ¦ tx=1000, rx=0, but test may not check rx=0.  ¦
¦                                    ¦ FIX: tg_arp_control or static ARP on DUT.    ¦
+------------------------------------+----------------------------------------------¦
¦ Exception caught silently          ¦ try/except swallows stream config failure.   ¦
¦                                    ¦ FIX: Never bare-except traffic setup code.   ¦
+------------------------------------+----------------------------------------------¦
¦ stats dict key error caught        ¦ KeyError on 'total_pkts' ? defaults to 0.   ¦
¦                                    ¦ FIX: Validate stats dict structure first.    ¦
+-----------------------------------------------------------------------------------+
```

### 6.3 Silent Pass Prevention Template

Copy this pattern into every traffic test.

```python
def _verify_traffic(tg, tg_ph_tx, tg_ph_rx, stream_id,
                    duration=10, min_pkts=100, max_loss_pct=1.0):
    """
    Standard traffic verification block with full silent-pass protection.
    Use this pattern in every test that involves traffic.
    """
    # -- Guard 1: Validate stream_id -------------------------
    if not stream_id:
        st.report_fail('traffic_verification_failed',
                       'stream_id is None — tg_traffic_config failed')

    # -- Step: Clear old stats --------------------------------
    tg.tg_traffic_control(action='clear_stats',
                          port_handle=[tg_ph_tx, tg_ph_rx])

    # -- Step: Run --------------------------------------------
    tg.tg_traffic_control(action='run', handle=stream_id)
    st.wait(duration)

    # -- Step: Stop BEFORE reading stats ----------------------
    tg.tg_traffic_control(action='stop', handle=stream_id)
    st.wait(2)  # Drain in-flight packets

    # -- Step: Collect stats -----------------------------------
    tx_stats = tg.tg_traffic_stats(port_handle=tg_ph_tx, mode='aggregate')
    rx_stats = tg.tg_traffic_stats(port_handle=tg_ph_rx, mode='aggregate')

    # -- Guard 2: Cast to int (stats are strings!) ------------
    try:
        tx = int(tx_stats[tg_ph_tx]['aggregate']['tx']['total_pkts'])
        rx = int(rx_stats[tg_ph_rx]['aggregate']['rx']['total_pkts'])
    except (KeyError, TypeError, ValueError) as e:
        st.report_fail('traffic_verification_failed',
                       f'Stats dict has unexpected structure: {e}')
        return

    st.log(f"Traffic stats: TX={tx}, RX={rx}")

    # -- Guard 3: TX must be non-zero -------------------------
    if tx == 0:
        st.report_fail('traffic_verification_failed',
                       'TX = 0: stream was not transmitting')

    # -- Guard 4: RX must be non-zero (absolute) --------------
    if rx == 0:
        st.report_fail('traffic_verification_failed',
                       'RX = 0: DUT is not forwarding any traffic')

    # -- Guard 5: Minimum packet count ------------------------
    if rx < min_pkts:
        st.report_fail('traffic_verification_failed',
                       f'RX={rx} below minimum expected {min_pkts}')

    # -- Guard 6: Loss percentage -----------------------------
    loss_pct = (tx - rx) / tx * 100
    st.log(f"Packet loss: {loss_pct:.2f}%")
    if loss_pct > max_loss_pct:
        st.report_fail('traffic_verification_failed',
                       f'Loss {loss_pct:.2f}% > threshold {max_loss_pct}%')
```

---

## 7. Things to Ensure When Using Traffic APIs

### 7.1 Pre-Test DUT Readiness Checklist

```
BEFORE STARTING ANY TRAFFIC TEST
---------------------------------------------------------------------

  DUT LAYER 1
  ? All relevant DUT interfaces are in 'up' state
  ? TGen ports have active link to DUT (check with show interface)
  ? Speed/duplex/MTU match between TGen and DUT port

  DUT LAYER 2  
  ? VLANs created and ports added as members if using tagged traffic
  ? STP converged (or disabled for test) — STP blocking causes RX=0
  ? MAC table not at capacity if testing MAC learning

  DUT LAYER 3
  ? IP addresses configured on SVI/routed interfaces
  ? Routes present for traffic destination subnets
  ? ARP resolved for TGen next-hop IPs
    ? Use: tg.tg_arp_control(handle=stream_id, arp_target='all')
    ? Or:  add static ARP entries on DUT

  TGEN SIDE
  ? Correct port handles used for TX and RX (don't swap them)
  ? rate_pps does not exceed DUT or NIC capability
  ? frame_size >= 64 bytes (NIC drops shorter frames silently)
  ? Stats cleared before the test run

  TIMING
  ? Wait for ARP to resolve before starting traffic
  ? Wait for routing protocols to converge before traffic test
  ? Wait after stop() before reading stats
```

### 7.2 MTU and Frame Size Pitfalls

```
                 FRAME SIZE RULES
                 -----------------------------------------
                 
  Minimum Ethernet frame: 64 bytes (including FCS)
  
  If you set frame_size=40:
  +-------------------------------------------------------+
  ¦  SpyTest/Scapy builds 40-byte frame                  ¦
  ¦  NIC driver silently drops it (below min frame size)  ¦
  ¦  TX counter may still increment in software           ¦
  ¦  RX = 0 at destination                                ¦
  ¦  Result: 100% loss — looks like DUT bug              ¦
  +-------------------------------------------------------+
  
  If you set frame_size=9200 but DUT MTU is 1500:
  +-------------------------------------------------------+
  ¦  DUT drops or fragments jumbo frames                  ¦
  ¦  RX count drops significantly                         ¦
  ¦  Looks like packet loss — actually MTU mismatch       ¦
  +-------------------------------------------------------+
  
  Safe defaults:
  ? Use frame_size=64  for max-rate small-packet testing
  ? Use frame_size=1280 for typical IPv6 minimum MTU tests
  ? Use frame_size=1500 for standard Ethernet MTU tests
  ? Set DUT MTU before testing with jumbo frames (>1500)
```

---

## 8. Additional Traffic API Capabilities

### 8.1 Bidirectional Traffic

```python
# Send traffic in both directions simultaneously
han = tg.tg_traffic_config(
    port_handle   = tg_ph_1,
    mode          = 'create',
    bidirectional = 1,          # ? Automatically creates reverse stream too
    rate_pps      = 500,
    ...
)
# This creates two streams: tg_ph_1?tg_ph_2 and tg_ph_2?tg_ph_1
# Both start/stop together with the same stream_id
```

### 8.2 Capture and Packet Inspection

```python
# Capture specific packets for field-level verification
tg.tg_packet_config_buffers(port_handle=tg_ph_2, capture_mode='trigger')
tg.tg_traffic_control(action='run', handle=stream_id)
st.wait(5)
tg.tg_traffic_control(action='stop', handle=stream_id)

# Get captured packets
cap = tg.tg_packet_stats(port_handle=tg_ph_2)
pkts = cap.get('captured_pkts', [])

# Inspect fields on first captured packet
for pkt in pkts[:5]:
    st.log(f"  VLAN: {pkt.get('vlan_id')}, TTL: {pkt.get('ip_ttl')}")
    # Verify DUT decremented TTL
    assert int(pkt.get('ip_ttl', 0)) == 63, "TTL not decremented by DUT"
```

### 8.3 Multiple Streams on One Port

```python
# Stream 1: Background load
s1 = tg.tg_traffic_config(
    port_handle=tg_ph_1, mode='create',
    rate_pps=800, ip_src_addr='10.1.0.1', ip_dst_addr='10.2.0.1',
    ...
)

# Stream 2: Specific test traffic mixed in
s2 = tg.tg_traffic_config(
    port_handle=tg_ph_1, mode='create',
    rate_pps=200, ip_src_addr='10.1.0.2', ip_dst_addr='10.2.0.2',
    vlan_id=200,
    ...
)

# Start both streams together
tg.tg_traffic_control(action='run',
    handle=[s1['stream_id'], s2['stream_id']])
st.wait(10)
tg.tg_traffic_control(action='stop',
    handle=[s1['stream_id'], s2['stream_id']])

# Read per-stream stats (not just aggregate)
stats = tg.tg_traffic_stats(port_handle=tg_ph_1, mode='streams')
```

### 8.4 Protocol-Specific APIs

```python
# ARP — resolve before L3 traffic
tg.tg_arp_control(handle=stream_id, arp_target='all')

# IPv6 Neighbor Discovery
tg.tg_nd_control(handle=stream_id, nd_target='all')

# Interface setup on TGen side (create IP interface on TGen port)
tg.tg_interface_config(
    port_handle  = tg_ph_1,
    mode         = 'config',
    intf_ip_addr = '192.168.1.1',
    gateway      = '192.168.1.254',
    src_mac_addr = '00:00:01:00:00:01',
    vlan         = 1,
    vlan_id      = 100,
)

# BGP session setup (if TGen supports it)
tg.tg_bgp_config(
    handle        = tg_intf_handle,
    mode          = 'enable',
    active_connect_enable = 1,
    remote_ip     = '192.168.1.254',
    remote_as     = 65001,
    local_as      = 65002,
)
```

---

## 9. End-to-End Test Case Scenario — Fully Annotated

### Scenario: IPv4 L3 Forwarding Across VLANs with Packet Loss Verification

**What this test proves:** When a packet arrives on VLAN 100 destined for a subnet behind VLAN 200, the DUT correctly routes it, rewrites Layer 2 headers, decrements TTL, and forwards with less than 1% loss.

### 9.1 Physical Topology

```
                         +-----------------------------------------+
                         ¦             DUT  (SONiC Switch)          ¦
                         ¦                                          ¦
  +---------------+      ¦  Ethernet0              Ethernet4        ¦      +---------------+
  ¦   TGen Host   ¦      ¦  +---------+          +---------+        ¦      ¦   TGen Host   ¦
  ¦               ¦      ¦  ¦ VLAN100 ¦          ¦ VLAN200 ¦        ¦      ¦               ¦
  ¦  Port 1       +------¦  ¦SVI IP:  ¦  Route   ¦SVI IP:  ¦        +------¦  Port 2       ¦
  ¦  (TX)         ¦      ¦  ¦.1.254/24¦---------?¦.2.254/24¦        ¦      ¦  (RX)         ¦
  ¦               ¦      ¦  +---------+          +---------+        ¦      ¦               ¦
  ¦ IP: 192.168.  ¦      ¦                                          ¦      ¦ IP: 192.168.  ¦
  ¦    1.1/24     ¦      ¦  ARP: .1.1 ? TGen1 MAC                   ¦      ¦    2.1/24     ¦
  ¦ MAC:00:00:01: ¦      ¦  ARP: .2.1 ? TGen2 MAC                   ¦      ¦ MAC:00:00:02: ¦
  ¦   00:00:01    ¦      ¦                                          ¦      ¦   00:00:01    ¦
  +---------------+      +-----------------------------------------+      +---------------+
  
  tg_ph_1 handle                                                           tg_ph_2 handle
```

**Reading this topology:**
- TGen Port 1 is connected to DUT Ethernet0, which is a member of VLAN 100. The DUT's VLAN 100 SVI has IP 192.168.1.254.
- TGen Port 2 is connected to DUT Ethernet4, which is a member of VLAN 200. The DUT's VLAN 200 SVI has IP 192.168.2.254.
- The DUT has a route between the two subnets (either static or via IGP).
- Static ARP entries tell the DUT the MAC addresses of both TGen ports so it can rewrite L2 headers when forwarding.

---

### 9.2 Packet Transformation Inside the DUT

This diagram shows what actually happens to the packet as it traverses the DUT. Understanding this is critical when debugging loss.

```
PACKET AS SENT BY TGEN PORT 1
+----------------------------------------------------------+
¦ Eth Dst  ¦ Eth Src  ¦ VLAN 100 ¦  IP Hdr  ¦   UDP + Data ¦
¦ DUT_MAC  ¦ 00:00:01:¦ 802.1Q   ¦ src:.1.1 ¦ sport:1234   ¦
¦ Eth0     ¦ 00:00:01 ¦ PCP=0    ¦ dst:.2.1 ¦ dport:5678   ¦
¦          ¦          ¦          ¦ TTL=64   ¦              ¦
+----------------------------------------------------------+
     ¦
     ¦  Arrives at DUT Ethernet0
     ?
     
DUT PROCESSING (step by step inside SONiC):

  Step 1: VLAN tag accepted
          Ethernet0 is configured as access/trunk for VLAN 100.
          DUT accepts the frame and strips or reads the 802.1Q tag.
          Frame is associated with VLAN 100 in the switching fabric.

  Step 2: L3 routing decision
          Destination IP = 192.168.2.1
          DUT checks routing table: 192.168.2.0/24 ? Vlan200 SVI
          Next hop: 192.168.2.1 (directly connected on Vlan200)

  Step 3: ARP lookup for destination
          DUT looks up ARP cache: 192.168.2.1 ? 00:00:02:00:00:01
          (This must be in the ARP table — if not, DUT drops the frame!)

  Step 4: L2 rewrite
          Ethernet Dst:  00:00:02:00:00:01  (TGen Port 2 MAC)
          Ethernet Src:  DUT Ethernet4 MAC  (DUT's own MAC for Vlan200)
          
  Step 5: TTL decrement
          IP TTL: 64 ? 63  (DUT is a router, it decrements TTL)
          IP checksum recalculated.

  Step 6: Egress VLAN tagging
          Ethernet4 is configured for VLAN 200.
          DUT adds 802.1Q tag with VLAN ID 200 on egress.

     ?
PACKET AS RECEIVED BY TGEN PORT 2
+----------------------------------------------------------+
¦ Eth Dst  ¦ Eth Src  ¦ VLAN 200 ¦  IP Hdr  ¦   UDP + Data ¦
¦ 00:00:02:¦ DUT_MAC  ¦ 802.1Q   ¦ src:.1.1 ¦ sport:1234   ¦
¦ 00:00:01 ¦ Eth4     ¦ PCP=0    ¦ dst:.2.1 ¦ dport:5678   ¦
¦          ¦          ¦          ¦ TTL=63   ¦              ¦
+----------------------------------------------------------+

CHANGES MADE BY DUT:
  Eth Dst:  DUT_MAC ? 00:00:02:00:00:01   ? L2 rewrite for egress
  Eth Src:  00:00:01:00:00:01 ? DUT_MAC   ? L2 rewrite (DUT's own MAC)
  VLAN tag: 100 ? 200                     ? Inter-VLAN routing
  TTL:      64 ? 63                       ? Routing hop decrement
  Payload:  unchanged                     ? DUT only does L3 routing
```

---

### 9.3 Full Test Execution Flow — Annotated

```
+--------------------------------------------------------------------------+
¦               TEST EXECUTION TIMELINE                                   ¦
¦--------------------------------------------------------------------------¦
¦                                                                          ¦
¦  t=0s  [SETUP PHASE]                                                     ¦
¦  ----------------------------------------------------------------------  ¦
¦  DUT: Create VLAN 100 and 200                                            ¦
¦  DUT: Add Ethernet0 ? VLAN 100, Ethernet4 ? VLAN 200                    ¦
¦  DUT: Set IP on Vlan100 SVI = 192.168.1.254/24                          ¦
¦  DUT: Set IP on Vlan200 SVI = 192.168.2.254/24                          ¦
¦  DUT: Static ARP: 192.168.1.1 ? 00:00:01:00:00:01 on Vlan100           ¦
¦  DUT: Static ARP: 192.168.2.1 ? 00:00:02:00:00:01 on Vlan200           ¦
¦  DUT: Enable IP routing                                                  ¦
¦  ? These must all be done BEFORE traffic starts.                        ¦
¦  ? If ARP is missing, DUT will drop all packets silently.               ¦
¦                                                                          ¦
¦  t=1s  [STREAM CONFIGURATION]                                            ¦
¦  ----------------------------------------------------------------------  ¦
¦  tg_traffic_config(port_handle=tg_ph_1,                                 ¦
¦      mac_src='00:00:01:00:00:01', mac_dst=DUT_ETH0_MAC,                 ¦
¦      vlan_id=100, ip_src='192.168.1.1', ip_dst='192.168.2.1',          ¦
¦      rate_pps=1000, frame_size=128, transmit_mode='continuous')         ¦
¦  ? Returns: stream_id = 'stream_1'                                      ¦
¦  ? Nothing sent to wire yet. Packet object created in memory.           ¦
¦                                                                          ¦
¦  t=2s  [CLEAR STATS]                                                     ¦
¦  ----------------------------------------------------------------------  ¦
¦  tg_traffic_control(action='clear_stats', port_handle=[ph1, ph2])       ¦
¦  ? Resets: tx_counter=0, rx_counter=0 for both ports                   ¦
¦  ? NEVER skip this. Old counts from previous tests cause false results. ¦
¦                                                                          ¦
¦  t=3s  [START TRAFFIC]                                                   ¦
¦  ----------------------------------------------------------------------  ¦
¦  tg_traffic_control(action='run', handle='stream_1')                    ¦
¦  ? AsyncSniffer starts on Port 2 (RX)                                  ¦
¦  ? TX thread starts on Port 1                                           ¦
¦  ? 1000 pkt/s flowing: Port1 ? Eth0 ? DUT ? Eth4 ? Port2              ¦
¦                                                                          ¦
¦  t=3s–13s  [TRAFFIC RUNNING]                                             ¦
¦  ----------------------------------------------------------------------  ¦
¦                                                                          ¦
¦  Port 1 TX    ¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦  ~10,000 pkts sent  ¦
¦  DUT routing  ¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦  L2/L3 processing   ¦
¦  Port 2 RX    ¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦¦  ~9,990 pkts recv   ¦
¦                                                                          ¦
¦  ? During this window you CAN do DUT actions (e.g. flap interface,     ¦
¦    change route, verify counters) because TX is non-blocking.           ¦
¦                                                                          ¦
¦  t=13s  [STOP TRAFFIC]                                                   ¦
¦  ----------------------------------------------------------------------  ¦
¦  tg_traffic_control(action='stop', handle='stream_1')                   ¦
¦  ? TX thread stopped                                                    ¦
¦  ? AsyncSniffer stopped after 2s drain wait                             ¦
¦  ? MUST stop before reading stats. Reading during TX gives partial      ¦
¦    counts and incorrect loss calculations.                               ¦
¦                                                                          ¦
¦  t=15s  [COLLECT AND VALIDATE STATS]                                     ¦
¦  ----------------------------------------------------------------------  ¦
¦  tx_stats = tg_traffic_stats(port_handle=tg_ph_1)                       ¦
¦  rx_stats = tg_traffic_stats(port_handle=tg_ph_2)                       ¦
¦                                                                          ¦
¦  tx = 10000   (from Port 1 TX counter)                                  ¦
¦  rx = 9990    (from Port 2 RX counter)                                  ¦
¦                                                                          ¦
¦  Silent pass guard: assert tx > 0  ?  (10000 > 0)                      ¦
¦  Silent pass guard: assert rx > 0  ?  (9990  > 0)                      ¦
¦  Loss = (10000-9990)/10000 * 100 = 0.10%                               ¦
¦  Loss check: 0.10% < 1.0%  ?  TEST PASSES                              ¦
¦                                                                          ¦
¦  t=16s  [TEARDOWN]                                                       ¦
¦  ----------------------------------------------------------------------  ¦
¦  tg_traffic_control(action='stop', port_handle=[ph1,ph2])  ? safety    ¦
¦  Remove VLAN, IP, ARP config from DUT                                   ¦
¦  ? Always teardown even if test fails. Use try/finally.                 ¦
+--------------------------------------------------------------------------+
```

---

### 9.4 Complete Executable Test Code

```python
"""
test_l3_vlan_forwarding.py

Tests IPv4 L3 forwarding between VLAN 100 and VLAN 200 on a SONiC DUT.
Verifies packet delivery with < 1% loss and correct TTL decrement.
"""

import pytest
from spytest import st
import apis.vlan as vlan_api
import apis.ip_intf as ip_api


# --- Fixtures --------------------------------------------------------------

@pytest.fixture(scope='module')
def l3_fwd_setup():
    """Configure DUT for L3 forwarding test. Teardown runs after all tests."""
    vars = st.ensure_min_topology("D1T1:2")
    dut = vars.D1
    tg, tg_ph_list = st.get_tg_info(vars)
    tg_ph_1 = tg_ph_list[0]
    tg_ph_2 = tg_ph_list[1]

    # -- DUT Configuration -------------------------------------------------
    # Create VLANs
    vlan_api.create_vlan(dut, [100, 200])

    # Add DUT ports to VLANs
    vlan_api.add_vlan_member(dut, 100, [vars.D1T1P1], tagging_mode=True)
    vlan_api.add_vlan_member(dut, 200, [vars.D1T1P2], tagging_mode=True)

    # Configure IPs on SVIs
    ip_api.config_ip_addr_interface(dut, 'Vlan100', '192.168.1.254', '24')
    ip_api.config_ip_addr_interface(dut, 'Vlan200', '192.168.2.254', '24')

    # Add static ARP — CRITICAL for L3 forwarding without live ARP
    ip_api.add_static_arp(dut, '192.168.1.1', '00:00:01:00:00:01', 'Vlan100')
    ip_api.add_static_arp(dut, '192.168.2.1', '00:00:02:00:00:01', 'Vlan200')

    # Enable IP routing (should be on by default but be explicit)
    st.config(dut, 'ip routing')

    yield {
        'dut': dut, 'tg': tg,
        'tg_ph_1': tg_ph_1, 'tg_ph_2': tg_ph_2,
        'vars': vars
    }

    # -- Teardown -----------------------------------------------------------
    ip_api.delete_static_arp(dut, '192.168.1.1', 'Vlan100')
    ip_api.delete_static_arp(dut, '192.168.2.1', 'Vlan200')
    ip_api.delete_ip_interface(dut, 'Vlan100', '192.168.1.254', '24')
    ip_api.delete_ip_interface(dut, 'Vlan200', '192.168.2.254', '24')
    vlan_api.delete_vlan_member(dut, 100, [vars.D1T1P1])
    vlan_api.delete_vlan_member(dut, 200, [vars.D1T1P2])
    vlan_api.delete_vlan(dut, [100, 200])


# --- Test Functions --------------------------------------------------------

def test_l3_ipv4_vlan_forwarding_no_loss(l3_fwd_setup):
    """
    Verify IPv4 traffic is forwarded from VLAN100 to VLAN200 with < 1% loss.
    """
    tg      = l3_fwd_setup['tg']
    tg_ph_1 = l3_fwd_setup['tg_ph_1']
    tg_ph_2 = l3_fwd_setup['tg_ph_2']
    vars    = l3_fwd_setup['vars']

    # -- Stream Config ------------------------------------------------------
    han = tg.tg_traffic_config(
        port_handle    = tg_ph_1,
        mode           = 'create',
        transmit_mode  = 'continuous',
        rate_pps       = 1000,
        frame_size     = 128,
        l2_encap       = 'ethernet_ii_vlan',
        mac_src        = '00:00:01:00:00:01',
        mac_dst        = vars.D1T1P1_mac,  # DUT Ethernet0 MAC
        vlan_enable    = 1,
        vlan_id        = 100,
        l3_protocol    = 'ipv4',
        ip_src_addr    = '192.168.1.1',
        ip_dst_addr    = '192.168.2.1',
        ip_ttl         = 64,
        l4_protocol    = 'udp',
        udp_src_port   = 1234,
        udp_dst_port   = 5678,
    )
    stream_id = han.get('stream_id')
    assert stream_id, "tg_traffic_config failed — no stream_id returned"

    try:
        # -- Clear ? Run ? Wait ? Stop ? Drain -----------------------------
        tg.tg_traffic_control(action='clear_stats',
                              port_handle=[tg_ph_1, tg_ph_2])

        tg.tg_traffic_control(action='run', handle=stream_id)
        st.wait(10)
        tg.tg_traffic_control(action='stop', handle=stream_id)
        st.wait(2)

        # -- Collect Stats --------------------------------------------------
        tx_stats = tg.tg_traffic_stats(port_handle=tg_ph_1, mode='aggregate')
        rx_stats = tg.tg_traffic_stats(port_handle=tg_ph_2, mode='aggregate')

        tx = int(tx_stats[tg_ph_1]['aggregate']['tx']['total_pkts'])
        rx = int(rx_stats[tg_ph_2]['aggregate']['rx']['total_pkts'])
        st.log(f"TX={tx}, RX={rx}")

        # -- Silent Pass Guards ---------------------------------------------
        if tx == 0:
            st.report_fail('traffic_verification_failed',
                           'TX=0: stream did not transmit')
        if rx == 0:
            st.report_fail('traffic_verification_failed',
                           'RX=0: DUT not forwarding — check ARP, VLAN, route')

        # -- Loss Check -----------------------------------------------------
        loss_pct = (tx - rx) / tx * 100
        st.log(f"Loss={loss_pct:.2f}%")
        if loss_pct >= 1.0:
            st.report_fail('traffic_verification_failed',
                           f'Loss {loss_pct:.2f}% exceeds 1% threshold')

    finally:
        # Safety: always stop, even if test fails mid-run
        tg.tg_traffic_control(action='stop', handle=stream_id)
        tg.tg_traffic_config(mode='remove', stream_id=stream_id)

    st.report_pass('test_case_passed')


def test_l3_ipv4_ttl_decrement(l3_fwd_setup):
    """
    Verify that DUT decrements TTL by 1 when routing.
    Captures received packets and checks TTL field.
    """
    tg      = l3_fwd_setup['tg']
    tg_ph_1 = l3_fwd_setup['tg_ph_1']
    tg_ph_2 = l3_fwd_setup['tg_ph_2']
    vars    = l3_fwd_setup['vars']

    han = tg.tg_traffic_config(
        port_handle   = tg_ph_1, mode='create',
        transmit_mode = 'single_burst', pkts_per_burst=10,
        rate_pps=100, frame_size=128,
        l2_encap='ethernet_ii_vlan',
        mac_src='00:00:01:00:00:01', mac_dst=vars.D1T1P1_mac,
        vlan_enable=1, vlan_id=100,
        l3_protocol='ipv4', ip_src_addr='192.168.1.1',
        ip_dst_addr='192.168.2.1', ip_ttl=64,
        l4_protocol='udp', udp_src_port=1234, udp_dst_port=5678,
    )
    stream_id = han.get('stream_id')

    # Enable packet capture on RX port
    tg.tg_packet_config_buffers(port_handle=tg_ph_2, capture_mode='trigger')

    try:
        tg.tg_traffic_control(action='clear_stats',
                              port_handle=[tg_ph_1, tg_ph_2])
        tg.tg_traffic_control(action='run', handle=stream_id)
        st.wait(2)
        tg.tg_traffic_control(action='stop', handle=stream_id)
        st.wait(1)

        cap = tg.tg_packet_stats(port_handle=tg_ph_2)
        pkts = cap.get('captured_pkts', [])

        if not pkts:
            st.report_fail('traffic_verification_failed',
                           'No packets captured on RX port')

        # Check TTL on first captured packet
        for pkt in pkts[:5]:
            received_ttl = int(pkt.get('ip_ttl', 0))
            st.log(f"Received TTL={received_ttl} (expected 63)")
            if received_ttl != 63:
                st.report_fail('traffic_verification_failed',
                               f'TTL={received_ttl}, expected 63 (64-1)')

    finally:
        tg.tg_traffic_control(action='stop', handle=stream_id)
        tg.tg_traffic_config(mode='remove', stream_id=stream_id)

    st.report_pass('test_case_passed')
```

---

## 10. Debugging Traffic Issues

### 10.1 Decision Tree for Traffic Test Failures

```
TRAFFIC TEST FAILED
        ¦
        +-- TX = 0?
        ¦       YES ? Stream not started. Check stream_id, action='run' call.
        ¦       NO  ? Continue ?
        ¦
        +-- RX = 0?
        ¦       YES ? +--------------------------------------------------+
        ¦             ¦  Most likely causes (check in order):            ¦
        ¦             ¦  1. ARP not resolved on DUT                      ¦
        ¦             ¦  2. Route missing for destination subnet         ¦
        ¦             ¦  3. VLAN not configured on DUT port              ¦
        ¦             ¦  4. STP blocking the port                        ¦
        ¦             ¦  5. DUT interface is down                        ¦
        ¦             ¦  6. Wrong port handle used for RX stats          ¦
        ¦             ¦  7. Sniffer started after TX (timing issue)      ¦
        ¦             +--------------------------------------------------+
        ¦       NO  ? Continue ?
        ¦
        +-- Loss > threshold?
        ¦       YES ? +--------------------------------------------------+
        ¦             ¦  1. Rate too high for DUT CPU (lower rate_pps)   ¦
        ¦             ¦  2. Frame size mismatch / jumbo not enabled      ¦
        ¦             ¦  3. DUT dropping due to buffer overflow          ¦
        ¦             ¦  4. Stats read before stop (partial count)       ¦
        ¦             ¦  5. Multiple tests sharing same TGen port        ¦
        ¦             +--------------------------------------------------+
        ¦       NO  ? Continue ?
        ¦
        +-- TX and RX both > 0, loss acceptable, but test fails?
                    ? Check field-level validation (TTL, VLAN ID, MAC)
                    ? Check DUT counters (show interface counters)
                    ? Enable packet capture to inspect actual frames
```

### 10.2 Useful Debug Commands During Test Development

```python
# 1. Check DUT interface counters while traffic is running
st.config(dut, 'show interface counters')

# 2. Check ARP table before running traffic
st.config(dut, 'show arp')

# 3. Check routing table
st.config(dut, 'show ip route')

# 4. Enable verbose Scapy output temporarily
# In ScapyDriver, sendp() verbose=False by default.
# Change to verbose=True in the driver to see per-packet output.

# 5. Dump the raw stats dict to see full structure
import json
stats = tg.tg_traffic_stats(port_handle=tg_ph_2, mode='aggregate')
st.log(json.dumps(stats, indent=2))

# 6. Check that stream was built correctly
# (Only available if you have access to the ScapyDriver internals)
# driver.stream_table[stream_id]['scapy_pkt'].show()
```

---

## 11. Summary Reference Card

```
+--------------------------------------------------------------------------+
¦                 SPYTEST TRAFFIC API — COMPLETE REFERENCE                ¦
¦--------------------------------------------------------------------------¦
¦ API                   ¦ Purpose & Key Notes                             ¦
¦-----------------------+--------------------------------------------------¦
¦ tg_traffic_config()   ¦ Defines a stream. Builds pkt in memory.        ¦
¦                       ¦ Does NOT send anything. Returns stream_id.     ¦
¦-----------------------+--------------------------------------------------¦
¦ tg_traffic_control()  ¦ action='run'         ? Start TX thread        ¦
¦                       ¦ action='stop'        ? Stop TX thread         ¦
¦                       ¦ action='clear_stats' ? Reset all counters     ¦
¦-----------------------+--------------------------------------------------¦
¦ tg_traffic_stats()    ¦ Returns TX/RX counts as STRINGS.               ¦
¦                       ¦ Always int() cast before arithmetic.           ¦
¦                       ¦ Call AFTER stop, not during TX.               ¦
¦-----------------------+--------------------------------------------------¦
¦ tg_arp_control()      ¦ Resolve ARP before ANY L3 traffic test.        ¦
¦-----------------------+--------------------------------------------------¦
¦ tg_interface_config() ¦ Set TGen port IP/gateway for protocol tests.   ¦
¦-----------------------+--------------------------------------------------¦
¦ tg_packet_stats()     ¦ Get captured packets for field inspection.     ¦
¦--------------------------------------------------------------------------¦
¦                          GOLDEN RULES                                   ¦
¦--------------------------------------------------------------------------¦
¦  1.  ALWAYS clear_stats before run (stale counts = false results)       ¦
¦  2.  ALWAYS stop before reading final stats                             ¦
¦  3.  ALWAYS assert tx > 0 (prevents silent pass on missing run call)    ¦
¦  4.  ALWAYS assert rx > 0 (prevents silent pass on DUT drop)            ¦
¦  5.  ALWAYS log tx, rx, and loss_pct for every test                     ¦
¦  6.  ALWAYS int() cast stats values before arithmetic                   ¦
¦  7.  ALWAYS resolve ARP before L3 routing tests                         ¦
¦  8.  ALWAYS clean up streams in teardown (use try/finally)              ¦
¦  9.  NEVER read stats during active TX                                  ¦
¦  10. NEVER set frame_size < 64 bytes                                    ¦
¦--------------------------------------------------------------------------¦
¦                     WHEN TO WRITE CUSTOM APIS                           ¦
¦--------------------------------------------------------------------------¦
¦  Pattern 1 — Wrapper helper: for repeated setup/verify boilerplate      ¦
¦  Pattern 2 — Raw Scapy injection: for missing protocols (MPLS/VXLAN)    ¦
¦  Pattern 3 — ScapyDriver subclass: for permanent reusable extensions    ¦
+--------------------------------------------------------------------------+
```
