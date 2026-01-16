# NTP Server Quick Start Guide

## 3-Step Setup

### Step 1: Install NTP Server
```bash
cd /home/hp/Athira/sonic-mgmt/spytest
sudo ./setup_ntp_server.sh
```

### Step 2: Verify Setup
```bash
./verify_ntp_server.sh
```

### Step 3: Run Tests
```bash
export NTP_ISCLI_VAR_FILE=tests/system/ntp/vars_ntp_iscli_local.yaml

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_iscli.py \
  --logs-path ./logs/test_ntp_local_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

## What This Does

### NTP Server Setup (192.168.100.175)
- ✓ Installs and configures chrony NTP server
- ✓ Syncs with Google/Debian NTP pools
- ✓ Serves time to DUT (192.168.100.133)
- ✓ Enables NTP authentication with test keys
- ✓ Listens on UDP port 123

### Test Configuration
- ✓ All test servers point to 192.168.100.175 (local, always reachable)
- ✓ Authentication keys match server configuration
- ✓ Tests use realistic, working NTP server

## Benefits

| Feature | Before (Public NTP) | After (Local NTP) |
|---------|--------------------|--------------------|
| **Latency** | 50-200ms | <1ms |
| **Reliability** | Internet required | Always available |
| **Authentication** | Not supported | Fully supported |
| **Testing** | Limited | Full control |

## Useful Commands

### Check NTP Server Status
```bash
chronyc sources       # Show upstream NTP sources
chronyc tracking      # Show sync status
chronyc clients       # Show connected clients
systemctl status chrony
```

### Test from DUT
```bash
ssh admin@192.168.100.133
ntpdate -q 192.168.100.175
chronyc sources
```

### Monitor NTP Traffic
```bash
sudo tcpdump -i any port 123 -n
```

### Check Logs
```bash
sudo journalctl -u chrony -f
```

## Troubleshooting

### Problem: NTP server not responding
**Solution:**
```bash
sudo systemctl restart chrony
sudo ss -ulnp | grep :123  # Should show chronyd listening
```

### Problem: DUT cannot reach NTP server
**Solution:**
```bash
ping 192.168.100.175  # From DUT
sudo ufw allow 123/udp  # If firewall is blocking
```

### Problem: Time not syncing
**Solution:**
```bash
sudo chronyc makestep  # Force time step
chronyc sources -v     # Check source status
```

## Files Created

- **setup_ntp_server.sh** - Automated installation and configuration
- **verify_ntp_server.sh** - Verification and testing
- **vars_ntp_iscli_local.yaml** - Test configuration with local server
- **NTP_SERVER_SETUP.md** - Detailed documentation
- **/etc/chrony/chrony.conf** - NTP server configuration
- **/etc/chrony/chrony.keys** - Authentication keys

## Next Steps

After setup is complete:
1. Review verification results
2. Run test suite
3. Check test results in logs directory
4. Review **NTP_SERVER_SETUP.md** for advanced usage

## Support

- Read full documentation: `cat NTP_SERVER_SETUP.md`
- Verify setup: `./verify_ntp_server.sh`
- Check chrony docs: https://chrony.tuxfamily.org/
