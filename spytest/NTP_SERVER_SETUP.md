# NTP Server Setup for Test Environment

This guide explains how to set up a local NTP server for realistic NTP testing with the SONiC DUT.

## Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Environment                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Test Machine (192.168.100.175)                      │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  NTP Server (chrony)                           │  │   │
│  │  │  - Syncs with public NTP pools                 │  │   │
│  │  │  - Serves time to DUT                          │  │   │
│  │  │  - Supports NTP authentication                 │  │   │
│  │  │  - Port: UDP 123                               │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  │                                                        │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │  SPyTest Framework                             │  │   │
│  │  │  - Runs automated NTP tests                    │  │   │
│  │  │  - Controls DUT via SSH                        │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └─────────────────────┬──────────────────────────────────┘   │
│                        │ SSH + NTP                           │
│                        │                                     │
│  ┌─────────────────────▼──────────────────────────────────┐   │
│  │  DUT - smic_sonic1 (192.168.100.133)                  │   │
│  │  ┌──────────────────────────────────────────────────┐ │   │
│  │  │  SONiC OS with IS-CLI (klish)                    │ │   │
│  │  │  ┌────────────────────────────────────────────┐  │ │   │
│  │  │  │  NTP Client (chrony/ntpd)                  │  │ │   │
│  │  │  │  - Syncs with 192.168.100.175             │  │ │   │
│  │  │  │  - Tests authentication keys               │  │ │   │
│  │  │  └────────────────────────────────────────────┘  │ │   │
│  │  └──────────────────────────────────────────────────┘ │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                             │
│  Internet ◄──┐                                              │
│               │ (Optional: for public NTP sync)             │
└───────────────┴─────────────────────────────────────────────┘
```

## Quick Start

### Step 1: Install and Configure NTP Server

Run the setup script on your test machine (192.168.100.175):

```bash
cd /home/hp/Athira/sonic-mgmt/spytest
sudo bash setup_ntp_server.sh
```

This will:
- Install chrony NTP server
- Configure it to serve time to the local network (192.168.100.0/24)
- Set up authentication keys for testing
- Enable and start the service

### Step 2: Verify NTP Server

Run the verification script:

```bash
bash verify_ntp_server.sh
```

This checks:
- ✓ Chrony service is running
- ✓ NTP port (UDP 123) is listening
- ✓ NTP server has upstream sources
- ✓ Time synchronization is working
- ✓ DUT is reachable
- ✓ SSH to DUT works
- ✓ NTP queries from DUT work

### Step 3: Run Tests with Local NTP Server

Option A: Use environment variable (temporary):
```bash
export NTP_ISCLI_VAR_FILE=tests/system/ntp/vars_ntp_iscli_local.yaml

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_iscli.py \
  --logs-path ./logs/test_ntp_local_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

Option B: Modify test script to use local config by default (permanent):
```python
# In test_ntp_iscli.py, change:
DEFAULT_VAR_FILE = Path(__file__).resolve().parent / "vars_ntp_iscli_local.yaml"
```

## Configuration Files

### 1. `setup_ntp_server.sh`
Automated setup script that:
- Installs chrony
- Configures NTP server settings
- Creates authentication keys
- Enables firewall rules if needed

### 2. `vars_ntp_iscli_local.yaml`
Test configuration using local NTP server (192.168.100.175):
- All test servers point to 192.168.100.175
- Authentication keys match chrony.keys
- Realistic, reachable NTP server

### 3. `verify_ntp_server.sh`
Comprehensive verification script to ensure setup is correct

### 4. `/etc/chrony/chrony.conf` (created by setup script)
Main chrony configuration:
- Upstream servers: Google NTP, Debian pool
- Allows clients from 192.168.100.0/24
- Local stratum 10 for isolated testing
- Authentication enabled

### 5. `/etc/chrony/chrony.keys` (created by setup script)
NTP authentication keys matching test requirements:
```
1  MD5    TestKey123
10 SHA256 CompleteKey
15 SHA256 TestAuthKey
20 SHA1   SimpleKey
25 SHA384 SecureKey456
30 SHA512 VerySecureKey789
```

## Benefits of Local NTP Server

### 1. **Reliability**
- Always reachable (no internet dependency)
- Controlled environment
- Predictable behavior

### 2. **Performance**
- Low latency (~1ms vs 50-200ms for internet NTP)
- Faster test execution
- More accurate time sync

### 3. **Testing Capabilities**
- **Authentication testing** - Can configure matching keys on server and client
- **Reachability testing** - Server is always available
- **Configuration testing** - Can modify server config for specific tests
- **Time drift testing** - Can artificially adjust server time

### 4. **Isolation**
- No external dependencies
- Works in air-gapped environments
- Reproducible test results

## Advanced Usage

### Test NTP Query Manually

From DUT:
```bash
ssh admin@192.168.100.133
ntpdate -q 192.168.100.175
# or
chronyc sources
```

From test machine:
```bash
chronyc sources
chronyc tracking
chronyc clients  # Show connected clients
```

### Monitor NTP Traffic

```bash
# On test machine
sudo tcpdump -i any port 123 -n
```

### Check NTP Server Logs

```bash
sudo journalctl -u chrony -f
# or
tail -f /var/log/chrony/measurements.log
```

### Modify Server Time (for drift testing)

```bash
# Set server time ahead by 10 seconds (for testing)
sudo date -s '+10 seconds'

# Let chrony re-sync
sudo systemctl restart chrony
```

### Add More Authentication Keys

Edit `/etc/chrony/chrony.keys`:
```bash
sudo nano /etc/chrony/chrony.keys
# Add:
# 50 SHA512 MyNewSecureKey

sudo systemctl restart chrony
```

## Troubleshooting

### NTP Server Not Responding

1. Check service status:
```bash
systemctl status chrony
```

2. Check if port is listening:
```bash
sudo ss -ulnp | grep :123
```

3. Check firewall:
```bash
sudo ufw status
sudo ufw allow 123/udp  # If needed
```

### DUT Cannot Reach NTP Server

1. Test connectivity:
```bash
ping 192.168.100.175
```

2. Test NTP port:
```bash
nc -u 192.168.100.175 123
```

3. Check DUT routing:
```bash
ip route
```

### Time Not Syncing

1. Check chrony sources:
```bash
chronyc sources -v
```

2. Force sync:
```bash
sudo chronyc makestep
```

3. Check system time:
```bash
timedatectl status
```

### Authentication Failures

1. Verify keys match on both server and client
2. Check key file permissions:
```bash
ls -l /etc/chrony/chrony.keys  # Should be 640
```

3. Check chrony logs:
```bash
sudo journalctl -u chrony | grep -i auth
```

## Files Created/Modified

### On Test Machine (192.168.100.175):
- `/etc/chrony/chrony.conf` - NTP server config
- `/etc/chrony/chrony.keys` - Authentication keys
- `/var/log/chrony/` - Log directory

### In Test Repository:
- `setup_ntp_server.sh` - Setup automation
- `verify_ntp_server.sh` - Verification script
- `tests/system/ntp/vars_ntp_iscli_local.yaml` - Test config with local server
- `NTP_SERVER_SETUP.md` - This documentation

## Comparison: Local vs Public NTP Servers

| Aspect | Public Servers (time.google.com, pool.ntp.org) | Local Server (192.168.100.175) |
|--------|------------------------------------------------|--------------------------------|
| **Latency** | 50-200ms | <1ms |
| **Availability** | Internet required | Always available |
| **Authentication** | Not supported | Fully supported |
| **Control** | None | Full control |
| **Reproducibility** | Variable | Consistent |
| **Security** | Trusted public | Local, controlled |
| **Testing Flexibility** | Limited | High |

## Next Steps

1. **Run full test suite** with local server
2. **Add time synchronization tests** - Verify actual time sync works
3. **Add authentication tests** - Test with various key types
4. **Add negative tests** - Test with wrong keys, unreachable servers
5. **Add performance tests** - Measure sync time, accuracy

## References

- Chrony documentation: https://chrony.tuxfamily.org/documentation.html
- NTP protocol: RFC 5905
- NTP authentication: RFC 8573
- SONiC NTP: https://github.com/sonic-net/SONiC/wiki/Configuration#ntp

## Support

For issues or questions:
1. Check verification script output: `bash verify_ntp_server.sh`
2. Review chrony logs: `sudo journalctl -u chrony`
3. Test manually: `chronyc sources` and `ntpdate -q 192.168.100.175`
