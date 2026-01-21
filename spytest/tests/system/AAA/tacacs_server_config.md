# TACACS+ Server Configuration for AAA Tests

## Server Details
- **IP Address**: 192.168.100.175
- **Port**: 49 (default TACACS+)
- **Secret Key**: `spytest_secret123`
- **Auth Type**: PAP

## Required Test Users

### 1. Admin User (Privilege 15)
- **Username**: `tacacsadmin`
- **Password**: `adminpass123`
- **Privilege Level**: 15 (full admin access)

### 2. Test User (Privilege 15)
- **Username**: `tacacstest`
- **Password**: `testpass123`
- **Privilege Level**: 15 (full admin access)

### 3. Read-only User (Privilege 1)
- **Username**: `tacacsreadonly`
- **Password**: `readonly123`
- **Privilege Level**: 1 (read-only access)

---

## TACACS+ Server Configuration (tac_plus)

If using **tac_plus** (common open-source TACACS+ server), create `/etc/tacacs+/tac_plus.conf`:

```conf
# TACACS+ Server Configuration for SPyTest AAA Tests
# Server: 192.168.100.175:49
# Generated for test_aaa_auth.py

# Encryption key - must match SONiC device configuration
key = spytest_secret123

# Accounting log file
accounting file = /var/log/tac_plus.acct

# Authentication configuration
default authentication = file /etc/tacacs+/tac_plus.passwd

# User: tacacsadmin (privilege 15 - full admin)
user = tacacsadmin {
    login = des $1$abc$XYZ123encrypted
    # For PAP: use cleartext password for testing
    # login = cleartext adminpass123
    default service = permit
    service = exec {
        priv-lvl = 15
        shell:roles = "admin"
    }
}

# User: tacacstest (privilege 15 - full admin)
user = tacacstest {
    login = cleartext testpass123
    default service = permit
    service = exec {
        priv-lvl = 15
        shell:roles = "admin"
    }
}

# User: tacacsreadonly (privilege 1 - read-only)
user = tacacsreadonly {
    login = cleartext readonly123
    default service = permit
    service = exec {
        priv-lvl = 1
        shell:roles = "operator"
    }
}

# Default group settings
group = admins {
    default service = permit
    service = exec {
        priv-lvl = 15
    }
}

group = operators {
    default service = permit
    service = exec {
        priv-lvl = 1
    }
}
```

---

## Installation & Setup (Ubuntu/Debian)

### 1. Install tac_plus
```bash
sudo apt update
sudo apt install -y tacacs+
```

### 2. Create configuration file
```bash
sudo nano /etc/tacacs+/tac_plus.conf
# Paste the configuration above
```

### 3. Set permissions
```bash
sudo chmod 600 /etc/tacacs+/tac_plus.conf
sudo chown root:root /etc/tacacs+/tac_plus.conf
```

### 4. Start/restart TACACS+ service
```bash
sudo systemctl restart tacacs_plus
sudo systemctl enable tacacs_plus
sudo systemctl status tacacs_plus
```

### 5. Verify service is listening
```bash
sudo netstat -tunlp | grep 49
# Should show: tcp 0 0 0.0.0.0:49 0.0.0.0:* LISTEN <pid>/tac_plus
```

---

## Alternative: Docker TACACS+ Server

If you want to use Docker for easier setup:

```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3'
services:
  tacacs:
    image: dchidell/docker-tacacs
    container_name: tacacs_server
    ports:
      - "192.168.100.175:49:49"
    environment:
      - TACACS_SECRET=spytest_secret123
    volumes:
      - ./tac_plus.conf:/etc/tacacs+/tac_plus.conf:ro
    restart: unless-stopped
EOF

# Start the container
docker-compose up -d

# Check logs
docker logs tacacs_server
```

---

## Testing TACACS+ Server Configuration

### From the TACACS+ server machine:
```bash
# Test local connection
echo "" | nc -v localhost 49

# Check service status
sudo systemctl status tacacs_plus

# View logs
sudo tail -f /var/log/syslog | grep tac_plus
```

### From the SONiC device (192.168.100.246):
```bash
# Test connectivity
telnet 192.168.100.175 49

# Or use netcat
nc -zv 192.168.100.175 49
```

---

## SONiC Device Configuration

Once TACACS+ server is configured, configure SONiC:

```bash
# Enter configuration mode
sonic-cli
configure terminal

# Configure TACACS+ server
tacacs server 192.168.100.175 \
  authtype pap \
  key spytest_secret123 \
  timeout 10 \
  port 49 \
  priority 1

# Enable TACACS+ authentication
aaa authentication login tacacs+
aaa authentication failthrough enable
aaa authentication fallback enable

# Verify configuration
show tacacs
show aaa

# Exit configuration
exit
exit
```

---

## Troubleshooting

### 1. Check TACACS+ server is running
```bash
sudo systemctl status tacacs_plus
sudo ps aux | grep tac_plus
```

### 2. Check firewall rules
```bash
# Allow TACACS+ port 49
sudo ufw allow 49/tcp
# Or for iptables:
sudo iptables -A INPUT -p tcp --dport 49 -j ACCEPT
```

### 3. Enable debug logging
Edit `/etc/tacacs+/tac_plus.conf` and add:
```conf
accounting file = /var/log/tac_plus.acct
```

Restart service:
```bash
sudo systemctl restart tacacs_plus
sudo tail -f /var/log/syslog
```

### 4. Test authentication manually
```bash
# Use tactest tool if available
tactest -s 192.168.100.175 -k spytest_secret123 \
  -u tacacstest -p testpass123 -r authenticate

# Or test with SSH from SONiC device
ssh tacacstest@192.168.100.246
# Enter password: testpass123
```

---

## Security Notes

1. **Change default passwords** in production environments
2. **Use encrypted passwords** instead of cleartext in production
3. **Restrict TACACS+ server access** with firewall rules
4. **Use strong shared secrets** (not `spytest_secret123`)
5. **Enable logging** for audit purposes
6. **Regularly rotate credentials**

---

## Quick Verification Checklist

- [ ] TACACS+ server installed and running
- [ ] Port 49 is accessible from SONiC device (192.168.100.246)
- [ ] Configuration file has correct secret key (`spytest_secret123`)
- [ ] All three users configured: tacacsadmin, tacacstest, tacacsreadonly
- [ ] SONiC device has TACACS+ server configured
- [ ] AAA authentication enabled on SONiC device
- [ ] Test SSH login with each user

---

## Contact

For issues with TACACS+ server setup, check:
- TACACS+ logs: `/var/log/syslog` or `/var/log/messages`
- SONiC AAA logs: `/var/log/auth.log` on SONiC device
- Server connectivity: `nc -zv 192.168.100.175 49`
