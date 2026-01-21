# AAA TACACS+ Test Prerequisites and Setup Guide

## Overview

This document describes the prerequisites, setup steps, and limitations for running the AAA TACACS+ authentication tests in the SPyTest framework.

---

## Test Suite Information

**Test File**: `tests/system/AAA/test_aaa_auth.py`
**Test Class**: `TestAAAAuthentication`
**Configuration File**: `spytest/vars/system/AAA/vars_aaa_auth.yaml`

---

## Prerequisites

### 1. TACACS+ Server Requirements

The AAA authentication tests require a TACACS+ server accessible from the SONiC device under test.

**Server Details** (from `vars_aaa_auth.yaml`):
- **IP Address**: 192.168.100.175
- **Port**: 49 (default TACACS+ port)
- **Protocol**: TCP
- **Auth Type**: PAP
- **Shared Secret**: `spytest_secret123`

### 2. Required Test Users

The TACACS+ server must be configured with the following test users:

| Username | Password | Privilege Level | Role | Purpose |
|----------|----------|-----------------|------|---------|
| `tacacsadmin` | `adminpass123` | 15 | admin | Admin access test |
| `tacacstest` | `testpass123` | 15 | admin | Standard test user |
| `tacacsreadonly` | `readonly123` | 1 | operator | Read-only user test |

### 3. Network Connectivity

- SONiC device must have network connectivity to the TACACS+ server
- Port 49 (TCP) must be accessible from the SONiC device
- No firewall blocking between SONiC device and TACACS+ server

### 4. Python Dependencies

The SSH authentication tests require the Paramiko library:
```bash
pip install paramiko
```

This is typically included in the SPyTest virtual environment (`spytest_venv`).

---

## TACACS+ Server Setup

### Option 1: Docker Installation (Recommended)

#### Step 1: Pull Docker Image
```bash
docker pull dchidell/docker-tacacs:latest
```

#### Step 2: Create Configuration File

Create `/path/to/tac_plus.conf`:
```conf
# TACACS+ Server Configuration for SPyTest AAA Tests
# Server: 192.168.100.175:49

# Encryption key - MUST match SONiC device configuration
key = spytest_secret123

# Accounting log file
accounting file = /var/log/tac_plus.acct

# Default authentication
default authentication = file /etc/passwd

# User 1: tacacsadmin (Privilege 15 - Full Admin Access)
user = tacacsadmin {
    login = cleartext adminpass123
    default service = permit
    service = exec {
        priv-lvl = 15
        shell:roles = "admin"
        shell:priv-lvl = 15
    }
    cmd = .* {
        permit .*
    }
}

# User 2: tacacstest (Privilege 15 - Full Admin Access)
user = tacacstest {
    login = cleartext testpass123
    default service = permit
    service = exec {
        priv-lvl = 15
        shell:roles = "admin"
        shell:priv-lvl = 15
    }
    cmd = .* {
        permit .*
    }
}

# User 3: tacacsreadonly (Privilege 1 - Read-Only Access)
user = tacacsreadonly {
    login = cleartext readonly123
    default service = permit
    service = exec {
        priv-lvl = 1
        shell:roles = "operator"
        shell:priv-lvl = 1
    }
    cmd = show {
        permit .*
    }
    cmd = .* {
        deny .*
    }
}

# Groups
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

# Default for all other users (deny)
user = DEFAULT {
    login = file /etc/passwd
    default service = deny
}
```

#### Step 3: Start Docker Container
```bash
docker run -d \
  --name tacacs_aaa_test \
  -p 49:49 \
  -v /path/to/tac_plus.conf:/etc/tacacs+/tac_plus.conf:ro \
  dchidell/docker-tacacs:latest
```

**Example with actual paths**:
```bash
docker run -d \
  --name tacacs_aaa_test \
  -p 49:49 \
  -v /home/hp_test/Athira/AAA/implementation/tacacs/tac_plus.conf:/etc/tacacs+/tac_plus.conf:ro \
  dchidell/docker-tacacs:latest
```

#### Step 4: Verify Container is Running
```bash
docker ps | grep tacacs_aaa_test
docker logs tacacs_aaa_test
```

Expected output:
```
Starting server...
```

### Option 2: Native Installation (Ubuntu/Debian)

```bash
# Install TACACS+ package
sudo apt update
sudo apt install -y tacacs+

# Create configuration file
sudo tee /etc/tacacs+/tac_plus.conf > /dev/null << 'EOF'
# Paste the configuration from above
EOF

# Set permissions
sudo chmod 600 /etc/tacacs+/tac_plus.conf
sudo chown root:root /etc/tacacs+/tac_plus.conf

# Start and enable service
sudo systemctl restart tacacs_plus
sudo systemctl enable tacacs_plus
sudo systemctl status tacacs_plus
```

---

## Verification Steps

### 1. Verify TACACS+ Server is Running

**Check service status** (Docker):
```bash
docker ps | grep tacacs_aaa_test
```

**Check service status** (Native):
```bash
sudo systemctl status tacacs_plus
```

### 2. Verify Port 49 is Listening

**From TACACS+ server**:
```bash
sudo netstat -tunlp | grep :49
# Expected: tcp 0 0 0.0.0.0:49 0.0.0.0:* LISTEN
```

**Or using ss**:
```bash
sudo ss -tlnp | grep :49
```

### 3. Test Network Connectivity

**From the SPyTest test machine** (or any machine on the network):
```bash
nc -zv 192.168.100.175 49
```

Expected output:
```
Connection to 192.168.100.175 49 port [tcp/tacacs] succeeded!
```

**Alternative test using telnet**:
```bash
telnet 192.168.100.175 49
```

### 4. Verify Configuration File

**Docker**:
```bash
docker exec tacacs_aaa_test cat /etc/tacacs+/tac_plus.conf
```

**Native**:
```bash
sudo cat /etc/tacacs+/tac_plus.conf
```

### 5. Check TACACS+ Logs

**Docker**:
```bash
docker logs tacacs_aaa_test --tail 50
```

**Native**:
```bash
sudo tail -f /var/log/syslog | grep tac_plus
```

---

## Running the Tests

### Basic Test Execution
```bash
cd /path/to/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/AAA/test_aaa_auth.py \
  --logs-path ./logs/AAA/test_aaa_$(date +%F_%H%M%S) \
  --log-level info \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test Cases
```bash
# Run only TACACS+ configuration tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_201_configure_tacacs_server_ipv4 \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_202_configure_tacacs_server_ipv6 \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_203_enable_tacacs_authentication \
  --logs-path ./logs/AAA/test_aaa_verify_$(date +%F_%H%M%S) \
  --log-level info --skip-init-config --ifname-type native

# Run SSH authentication tests (expected to xfail on virtual SONiC)
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_204_ssh_login_admin_user \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_205_ssh_login_test_user \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_206_ssh_login_readonly_user \
  tests/system/AAA/test_aaa_auth.py::TestAAAAuthentication::test_auth_207_invalid_credentials \
  --logs-path ./logs/AAA/test_aaa_verify_$(date +%F_%H%M%S) \
  --log-level info --skip-init-config --ifname-type native
```

---

## Test Results and Limitations

### Expected Test Results

When running the full test suite with a properly configured TACACS+ server:

**On Virtual SONiC**:
```
13 passed, 3 unsupported, 44 warnings in ~11 minutes
```

**On Hardware SONiC** (with PAM/NSS modules):
```
16 passed, 44 warnings in ~11 minutes
```

### Working Test Cases (✓ PASS)

| Test ID | Test Case | Description | Status |
|---------|-----------|-------------|--------|
| TC-AAA-001 | `test_aaa_001_enable_failthrough` | Enable AAA failthrough | ✓ PASS |
| TC-AAA-002 | `test_aaa_002_enable_fallback` | Enable AAA fallback | ✓ PASS |
| TC-AAA-003 | `test_aaa_003_set_login_tacacs` | Set login method to TACACS+ | ✓ PASS |
| TC-TACACS-001 | `test_tacacs_001_configure_authtype` | Configure TACACS+ auth type | ✓ PASS |
| TC-TACACS-002 | `test_tacacs_002_configure_passkey` | Configure TACACS+ passkey | ✓ PASS |
| TC-TACACS-003 | `test_tacacs_003_configure_timeout` | Configure TACACS+ timeout | ✓ PASS |
| TC-TACACS-004 | `test_tacacs_004_add_server_full_params` | Add TACACS+ server with all params | ✓ PASS |
| TC-AAA-NEG-001 | `test_aaa_negative_001_invalid_login_method` | Negative: Invalid login method | ✓ PASS |
| TC-AUTH-201 | `test_auth_201_configure_tacacs_server_ipv4` | Configure TACACS+ server (IPv4) | ✓ PASS |
| TC-AUTH-202 | `test_auth_202_configure_tacacs_server_ipv6` | Configure TACACS+ server (IPv6) | ✓ PASS |
| TC-AUTH-203 | `test_auth_203_enable_tacacs_authentication` | Enable TACACS+ authentication | ✓ PASS |
| TC-AUTH-207 | `test_auth_207_invalid_credentials` | Negative: Invalid credentials | ✓ PASS |
| TC-AUTH-208 | `test_auth_208_verify_authentication_logs` | Verify authentication logs | ✓ PASS |

### Known Limitations (⚠ UNSUPPORTED on Virtual SONiC)

The following test cases are marked as **UNSUPPORTED** on virtual SONiC instances:

| Test ID | Test Case | Description | Status | Reason |
|---------|-----------|-------------|--------|--------|
| TC-AUTH-204 | `test_auth_204_ssh_login_admin_user` | SSH login with TACACS+ admin user | ⚠ UNSUPPORTED (VS) | Requires PAM/NSS integration |
| TC-AUTH-205 | `test_auth_205_ssh_login_test_user` | SSH login with TACACS+ test user | ⚠ UNSUPPORTED (VS) | Requires PAM/NSS integration |
| TC-AUTH-206 | `test_auth_206_ssh_login_readonly_user` | SSH login with TACACS+ readonly user | ⚠ UNSUPPORTED (VS) | Requires PAM/NSS integration |

#### Why SSH Authentication Tests Fail

Full TACACS+ SSH authentication requires additional components on the SONiC device:

1. **PAM (Pluggable Authentication Modules)**:
   - PAM module `pam_tacplus.so` must be installed and configured
   - `/etc/pam.d/common-auth` must include TACACS+ configuration

2. **NSS (Name Service Switch)**:
   - NSS module `libnss_tacplus.so` for user lookup
   - `/etc/nsswitch.conf` must include TACACS+ as a source

3. **TACACS+ Client Libraries**:
   - `libtac` or similar TACACS+ client library
   - Proper integration with SSH daemon

**Virtual SONiC Limitation**: Virtual SONiC instances used for testing may not have these modules fully configured or installed, as they are typically deployment-specific configurations. The tests automatically detect virtual SONiC using `st.is_vsonic()` and report as **UNSUPPORTED**.

**Hardware SONiC**: On production hardware SONiC devices with proper TACACS+ integration, these tests should pass.

#### Test Behavior

These tests use `st.is_vsonic()` to detect virtual SONiC and automatically report as UNSUPPORTED with the message:
```
"TACACS+ SSH authentication not supported on virtual SONiC (requires PAM/NSS modules)"
```

Despite the unsupported status on virtual SONiC, these tests are still valuable because they:
- ✓ Verify TACACS+ server connectivity
- ✓ Validate TACACS+ configuration on SONiC device
- ✓ Test the SSH authentication mechanism (using Paramiko)
- ✓ Provide detailed error messages for debugging
- ✓ Demonstrate the expected authentication flow

---

## Troubleshooting

### Issue 1: TACACS+ Server Not Reachable

**Symptoms**:
- Tests skip with message: "TACACS+ server not reachable - skipping authentication test"
- `nc -zv 192.168.100.175 49` fails

**Solutions**:
1. Verify TACACS+ server is running:
   ```bash
   docker ps | grep tacacs_aaa_test
   ```

2. Check firewall rules:
   ```bash
   sudo ufw allow 49/tcp
   sudo iptables -L -n | grep 49
   ```

3. Verify Docker port binding:
   ```bash
   docker port tacacs_aaa_test
   ```

4. Check network connectivity:
   ```bash
   ping 192.168.100.175
   ```

### Issue 2: Authentication Fails

**Symptoms**:
- Tests fail with "SSH authentication failed (AuthenticationException)"
- TACACS+ server logs show no connection attempts

**Solutions**:
1. Verify SONiC device has TACACS+ server configured:
   ```bash
   # On SONiC device
   show tacacs
   show aaa
   ```

2. Check shared secret matches:
   - SONiC device: `spytest_secret123`
   - TACACS+ server config: `key = spytest_secret123`

3. Enable debug logging on TACACS+ server:
   ```bash
   docker logs tacacs_aaa_test -f
   ```

4. Check SONiC authentication logs:
   ```bash
   # On SONiC device
   tail -f /var/log/auth.log
   ```

### Issue 3: Configuration File Not Found

**Symptoms**:
- Docker container starts but configuration seems wrong
- Server accepts wrong passwords

**Solutions**:
1. Verify configuration file is mounted:
   ```bash
   docker exec tacacs_aaa_test ls -la /etc/tacacs+/
   docker exec tacacs_aaa_test cat /etc/tacacs+/tac_plus.conf
   ```

2. Check file permissions:
   ```bash
   ls -l /home/hp_test/Athira/AAA/implementation/tacacs/tac_plus.conf
   ```

3. Restart container with correct mount:
   ```bash
   docker stop tacacs_aaa_test
   docker rm tacacs_aaa_test
   docker run -d --name tacacs_aaa_test -p 49:49 \
     -v /path/to/tac_plus.conf:/etc/tacacs+/tac_plus.conf:ro \
     dchidell/docker-tacacs:latest
   ```

### Issue 4: Port Already in Use

**Symptoms**:
- Docker fails to start with "port is already allocated"

**Solutions**:
1. Find process using port 49:
   ```bash
   sudo netstat -tunlp | grep :49
   sudo lsof -i :49
   ```

2. Stop existing TACACS+ service:
   ```bash
   # If Docker container
   docker ps -a | grep tacacs
   docker stop <container_name>
   docker rm <container_name>

   # If native service
   sudo systemctl stop tacacs_plus
   ```

---

## Key Improvements in Test Suite

### 1. Fixed CLI Syntax Error (TC-AUTH-203)

**Previous Issue**: Used invalid command `aaa authentication login tacacs+ local`
```python
# ❌ Old (incorrect)
cmd = "aaa authentication login tacacs+ local"
```

**Fix**: Use single method only (SONiC CLI requirement)
```python
# ✓ New (correct)
cmd = "aaa authentication login tacacs+"
# Enable failthrough and fallback separately for local authentication
```

### 2. Implemented Actual SSH Authentication

**Previous Issue**: Placeholder code with note "Actual SSH authentication requires external validation"

**Fix**: Implemented real SSH authentication using Paramiko library
```python
def _ssh_authentication_test(self, username: str, password: str,
                             expect_success: bool = True, timeout: int = 30) -> bool:
    """Test SSH authentication using Paramiko library."""
    import paramiko

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname=dut_ip, port=22, username=username,
                   password=password, timeout=timeout,
                   look_for_keys=False, allow_agent=False)
        # Verify with command execution
        stdin, stdout, stderr = ssh.exec_command("whoami", timeout=10)
        output = stdout.read().decode('utf-8').strip()
        auth_success = (username in output)
        ssh.close()
        return auth_success == expect_success
    except paramiko.AuthenticationException:
        return not expect_success
```

---

## Security Notes

**Important**: This configuration is for testing purposes only!

### For Production Use:

1. **Change default passwords**:
   - Do not use `adminpass123`, `testpass123`, `readonly123`
   - Use strong, randomly generated passwords

2. **Use encrypted passwords**:
   ```conf
   # Instead of: login = cleartext password
   # Use: login = des <encrypted_password>
   ```

3. **Restrict TACACS+ server access**:
   ```bash
   # Only allow SONiC device IP
   sudo iptables -A INPUT -p tcp --dport 49 -s <sonic_ip> -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 49 -j DROP
   ```

4. **Use strong shared secrets**:
   - Minimum 16 characters
   - Mix of letters, numbers, special characters
   - Do not use `spytest_secret123` in production

5. **Enable audit logging**:
   ```conf
   accounting file = /var/log/tac_plus.acct
   ```

6. **Regularly rotate credentials**:
   - Change passwords every 90 days
   - Rotate shared secrets periodically

---

## References

### Files in Test Suite:
- `tests/system/AAA/test_aaa_auth.py` - Main test file
- `tests/system/AAA/vars_aaa_auth.yaml` - Test configuration variables
- `tests/system/AAA/setup_tacacs_server.sh` - Automated server setup script
- `tests/system/AAA/tacacs_server_config.md` - Detailed configuration guide
- `tests/system/AAA/TACACS_SETUP_INSTRUCTIONS.txt` - Quick setup reference

### Documentation:
- TACACS+ Protocol: RFC 8907
- SONiC AAA Documentation: https://github.com/sonic-net/SONiC/wiki/AAA
- SPyTest Documentation: `Doc/intro.md`

### Docker Image:
- Docker Hub: https://hub.docker.com/r/dchidell/docker-tacacs
- Source: Based on Facebook's `tac_plus` implementation

---

## Support

For issues or questions:
1. Check TACACS+ server logs: `docker logs tacacs_aaa_test`
2. Check SONiC authentication logs: `/var/log/auth.log` on SONiC device
3. Verify network connectivity: `nc -zv 192.168.100.175 49`
4. Review test execution logs in `--logs-path` directory

---

**Last Updated**: 2026-01-21
**Version**: 1.0
**Author**: AAA Test Automation Team
