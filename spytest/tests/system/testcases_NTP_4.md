# NTP Test Cases - Authentication

## Test Case 2.1.4: Verify authenticated NTP sync

### Test Case ID
`test_ntp_4_verify_authenticated_sync`

### Purpose
Verify that NTP synchronization works correctly with authentication enabled using various authentication types (MD5, SHA1, SHA256, SHA384, SHA512) and that trusted keys are properly enforced

### Test Setup
- Topology: 1 DUT + 1 NTP server with matching authentication configuration
- NTP server must be configured with same authentication key and type
- NTP server must be reachable from DUT

### Test Procedure

#### Step 1: Enable NTP
```
ntp enable
```
or
```
ntp
```

#### Step 2: Enable NTP Authentication
```
ntp authenticate
```

#### Step 3: Configure Authentication Key
```
ntp authentication-key 1 md5 <secret>
```
**Example:**
```
ntp authentication-key 1 md5 MySecretKey123
```

#### Step 4: Configure Trusted Key
```
ntp trusted-key 1
```
**Note:** Only keys marked as trusted will be used for authentication

#### Step 5: Configure NTP Server with Authentication Key
```
ntp server <ip> key 1
```
**Example:**
```
ntp server 192.168.1.1 key 1 iburst
```

#### Step 6: Verify Associations, Status, and Clock
```
show ntp associations
show ntp
show clock
```
**Expected**: NTP should sync successfully with authentication enabled

### Configuration Commands to Test (configure-view)

#### Enable/Disable NTP
```
ntp enable
no ntp enable
```

#### Enable/Disable Authentication
```
ntp authenticate
no ntp authenticate
```
**Important:** When authentication is enabled, only servers configured with valid trusted keys will be used

#### Authentication Key Configuration
```
ntp authentication-key <key-id> <auth-type> <password> [encrypted]
no ntp authentication-key <key-id>
```

**Parameters:**
- `key-id`: 1-65535 (unique identifier for the key)
- `auth-type`: md5, sha1, sha256, sha384, sha512
- `password`: Shared secret (must match on server and client)
- `encrypted`: Optional flag indicating password is already encrypted

**Examples:**
```
ntp authentication-key 1 md5 MySecret123
ntp authentication-key 10 sha1 AnotherSecret456
ntp authentication-key 20 sha256 StrongSecret789
ntp authentication-key 30 sha384 VeryStrongSecret
ntp authentication-key 40 sha512 UltraStrongSecret
```

**Key Guidelines:**
- Use strong passwords (minimum 8 characters recommended)
- Different keys can use different authentication types
- Key ID must match between client and server
- Password must match exactly between client and server
- Authentication type must match between client and server

#### Trusted Key Configuration
```
ntp trusted-key <key-id>
no ntp trusted-key <key-id>
```

**Parameters:**
- `key-id`: 1-65535 (must reference a configured authentication key)

**Important Notes:**
- A key must be defined with `ntp authentication-key` before it can be trusted
- Only trusted keys are used when authentication is enabled
- Multiple keys can be configured as trusted
- Non-trusted keys are ignored even if configured

**Examples:**
```
ntp trusted-key 1
ntp trusted-key 10
ntp trusted-key 20
```

#### NTP Server Configuration with Authentication
```
ntp server <server-addr> [version <version-value>] [association <assoc-value>] [iburst] [key <key-value>] [prefer]
no ntp server <server-addr>
```

**Parameters:**
- `server-addr`: NTP server IP address or hostname
- `version-value`: 3 or 4
- `assoc-value`: server or pool
- `iburst`: Send burst of packets at startup
- `key-value`: 1-65535 (authentication key ID to use for this server)
- `prefer`: Mark this server as preferred

**Examples:**
```
ntp server 192.168.1.1 key 1
ntp server 192.168.1.2 key 10 iburst
ntp server 192.168.1.3 key 20 iburst prefer
```

#### Source Interface Configuration
```
ntp source-interface <ifname>
no ntp source-interface
```

#### VRF Configuration
```
ntp vrf <vrf-name>
no ntp vrf
```

### Show Commands to Validate (enable-view)

**Note:** The following commands are under development and should be executed inside **"sonic-cli"** using **"klish"** mode. Currently, these commands may not produce output.

```
show ntp global
show ntp server
show ntp associations
```

### Legacy Show Commands (Current)
```
show ntp associations
show ntp
show clock
```

### Expected Output

#### 1. show ntp global (klish)

Expected to display:
- NTP enable/disable status
- Authentication enabled/disabled status
- Configured authentication keys (key IDs only, not passwords)
- Trusted keys

Example format:
```
NTP: enabled
Authentication: enabled
Configured Keys: 1, 10, 20
Trusted Keys: 1, 10, 20
Source Interface: none
VRF: default
```

#### 2. show ntp server (klish)

Expected to display:
- Configured NTP servers
- Authentication key used for each server
- Other server options

Example format:
```
Server Address      Version  Association  iburst  prefer  Key
192.168.1.1         4        server       yes     no      1
192.168.1.2         4        server       yes     no      10
```

#### 3. show ntp associations

Expected to display with authentication enabled:
- NTP servers with authentication
- Synchronization status
- Reachability (should be > 0 if auth is correct)

Example format:
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

**With incorrect authentication:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .AUTH.          16 u    -   64  000    0.000    0.000   0.000
```

**Indicators:**
- `*` = Synchronized (authentication successful)
- `.AUTH.` refid = Authentication failure
- `reach 000` = No successful polls (may indicate auth failure)
- `st 16` = Stratum 16 (unreachable, may indicate auth failure)

#### 4. show ntp

Expected to display:
- Authentication status
- Synchronization status
- NTP servers with authentication

Example with authentication enabled:
```
synchronised to NTP server (192.168.1.1) at stratum 2
   time correct to within 12 ms
   polling server every 64 s
   authentication enabled

     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

#### 5. show clock

Expected to display:
- Current system date and time
- Should show accurate time if NTP auth successful

Example:
```
Thu Jan 13 10:30:45 UTC 2025
```

### Validation Criteria

1. **Authentication Key Configuration**
   - Authentication keys should be configured successfully
   - Multiple authentication types should be supported (MD5, SHA1, SHA256, SHA384, SHA512)
   - Key IDs should be unique
   - Commands should execute without errors

2. **Trusted Key Configuration**
   - Trusted keys should reference valid authentication keys
   - Only trusted keys should be used when authentication is enabled
   - Non-trusted keys should be ignored

3. **NTP Server with Authentication**
   - NTP server should be configured with valid key ID
   - Key ID must reference a configured and trusted authentication key
   - Configuration should be accepted without errors

4. **Authentication Enable/Disable**
   - Enabling authentication should require authentication for all NTP communications
   - Disabling authentication should allow unauthenticated NTP
   - Toggle should work correctly

5. **Synchronization with Authentication**
   - Device should sync successfully when:
     - Authentication is enabled on client
     - Correct key ID configured on server entry
     - Key is marked as trusted
     - Key type and password match on server
   - `show ntp associations` should show `reach > 0`
   - System peer should be marked with `*`

6. **Authentication Failure Detection**
   - With incorrect key/password, synchronization should fail
   - `show ntp associations` may show:
     - `.AUTH.` in refid column
     - `reach 000` (no successful polls)
     - `st 16` (unreachable)
   - No system peer selected (`*` missing)

### Test Variations

1. **MD5 Authentication**
   ```
   ntp authentication-key 1 md5 MyMD5Secret
   ntp trusted-key 1
   ntp server 192.168.1.1 key 1
   ```
   - Most common authentication type
   - Widely supported
   - Less secure than SHA variants

2. **SHA1 Authentication**
   ```
   ntp authentication-key 10 sha1 MySHA1Secret
   ntp trusted-key 10
   ntp server 192.168.1.1 key 10
   ```
   - More secure than MD5
   - Good balance of security and compatibility

3. **SHA256 Authentication**
   ```
   ntp authentication-key 20 sha256 MySHA256Secret
   ntp trusted-key 20
   ntp server 192.168.1.1 key 20
   ```
   - Strong security
   - Recommended for production

4. **SHA384 Authentication**
   ```
   ntp authentication-key 30 sha384 MySHA384Secret
   ntp trusted-key 30
   ntp server 192.168.1.1 key 30
   ```
   - Very strong security
   - Higher overhead

5. **SHA512 Authentication**
   ```
   ntp authentication-key 40 sha512 MySHA512Secret
   ntp trusted-key 40
   ntp server 192.168.1.1 key 40
   ```
   - Maximum security
   - Highest overhead
   - May not be supported on all platforms

6. **Multiple Servers with Different Keys**
   ```
   ntp authentication-key 1 md5 Secret1
   ntp authentication-key 2 md5 Secret2
   ntp trusted-key 1
   ntp trusted-key 2
   ntp server 192.168.1.1 key 1
   ntp server 192.168.1.2 key 2
   ```
   - Different servers can use different keys
   - Useful for multi-tier NTP architecture

7. **Trusted vs Non-Trusted Keys**
   ```
   ntp authentication-key 1 md5 TrustedSecret
   ntp authentication-key 2 md5 NonTrustedSecret
   ntp trusted-key 1
   # Note: key 2 is NOT marked as trusted
   ntp server 192.168.1.1 key 1  # Will work
   ntp server 192.168.1.2 key 2  # Will NOT work (not trusted)
   ```

8. **Authentication Disable/Enable**
   - Configure with authentication, verify sync
   - Disable authentication: `no ntp authenticate`
   - Verify sync still works (unauthenticated)
   - Re-enable authentication: `ntp authenticate`
   - Verify sync works again (authenticated)

9. **Incorrect Key (Negative Test)**
   ```
   # Server expects key 1 with password "CorrectSecret"
   ntp authentication-key 1 md5 WrongSecret
   ntp trusted-key 1
   ntp server 192.168.1.1 key 1
   ```
   - Should fail to synchronize
   - Verify appropriate error indication

10. **Missing Trusted Key (Negative Test)**
    ```
    ntp authentication-key 1 md5 MySecret
    # Note: NOT marking key 1 as trusted
    ntp server 192.168.1.1 key 1
    ```
    - Should fail to synchronize when authentication is enabled
    - Key exists but is not trusted

### Detailed Configuration Workflow

#### Complete Authentication Setup (Step-by-Step)

**Step 1: Enable NTP**
```
sonic-cli
configure terminal
ntp enable
```

**Step 2: Enable Authentication**
```
ntp authenticate
```

**Step 3: Configure Authentication Keys**
```
ntp authentication-key 1 md5 MySecret123
ntp authentication-key 10 sha1 AnotherSecret456
ntp authentication-key 20 sha256 StrongSecret789
```

**Step 4: Mark Keys as Trusted**
```
ntp trusted-key 1
ntp trusted-key 10
ntp trusted-key 20
```

**Step 5: Configure NTP Servers with Keys**
```
ntp server 192.168.1.1 key 1 iburst
ntp server 192.168.1.2 key 10 iburst
ntp server 192.168.1.3 key 20 iburst prefer
```

**Step 6: Exit and Verify**
```
end
exit
```

**Step 7: Verify Configuration**
```
show ntp global
show ntp server
show ntp associations
```

**Step 8: Wait for Synchronization**
- Wait 2-5 minutes for initial sync

**Step 9: Verify Sync Status**
```
show ntp
show clock
```

### Authentication Key Management

#### Key Lifecycle

1. **Create Key**
   ```
   ntp authentication-key <id> <type> <password>
   ```

2. **Mark as Trusted**
   ```
   ntp trusted-key <id>
   ```

3. **Associate with Server**
   ```
   ntp server <ip> key <id>
   ```

4. **Update Key Password** (if needed)
   ```
   # Remove old key
   no ntp authentication-key <id>
   # Add with new password
   ntp authentication-key <id> <type> <new-password>
   # Re-mark as trusted
   ntp trusted-key <id>
   ```

5. **Remove Key**
   ```
   # Remove from trusted
   no ntp trusted-key <id>
   # Remove key definition
   no ntp authentication-key <id>
   ```

#### Security Best Practices

1. **Use Strong Passwords**
   - Minimum 8 characters
   - Mix of uppercase, lowercase, numbers, symbols
   - Avoid dictionary words

2. **Use Modern Hash Algorithms**
   - Prefer SHA256 or higher
   - Avoid MD5 for new deployments (legacy only)

3. **Key Rotation**
   - Periodically change authentication keys
   - Use different keys for different servers

4. **Key Storage**
   - Passwords stored in configuration (encrypted if using `encrypted` flag)
   - Protect access to configuration files

5. **Minimal Trusted Keys**
   - Only mark necessary keys as trusted
   - Remove unused keys

### Common Issues and Troubleshooting

#### Issue 1: NTP Not Synchronizing with Authentication Enabled

**Symptoms:**
- `show ntp associations` shows `reach 000`
- No system peer selected
- May see `.AUTH.` in refid

**Possible Causes:**
1. Key ID mismatch between client and server
2. Password mismatch
3. Authentication type mismatch (MD5 vs SHA1, etc.)
4. Key not marked as trusted
5. Server not configured for authentication
6. Authentication not enabled on server

**Troubleshooting Steps:**
```
# Verify authentication is enabled
show ntp global

# Verify key is configured and trusted
show ntp global | grep -i key

# Verify server is configured with correct key
show ntp server

# Try disabling authentication temporarily
no ntp authenticate
# Wait 2-3 minutes
show ntp associations
# If it works without auth, problem is with auth configuration

# Re-enable authentication
ntp authenticate
```

#### Issue 2: Key Configuration Rejected

**Symptoms:**
- Error message when configuring key
- Configuration not accepted

**Possible Causes:**
1. Invalid key ID (not in range 1-65535)
2. Invalid authentication type
3. Syntax error in command

**Troubleshooting:**
```
# Check key ID is in valid range
ntp authentication-key 1 md5 MySecret

# Verify authentication type spelling
# Valid: md5, sha1, sha256, sha384, sha512

# Check for typos
ntp authentication-key 1 md5 MySecret
# Not: ntp auth-key or ntp authentication key
```

#### Issue 3: Trusted Key Not Working

**Symptoms:**
- Key configured but not being used
- Authentication fails even with correct configuration

**Possible Causes:**
1. Key not marked as trusted
2. Authentication not enabled globally

**Troubleshooting:**
```
# Verify key is marked as trusted
show ntp global

# Ensure authentication is enabled
show ntp global | grep -i auth

# Mark key as trusted
ntp trusted-key 1

# Enable authentication
ntp authenticate
```

#### Issue 4: Multiple Authentication Types Not Working

**Symptoms:**
- Some servers sync, others don't
- Mixed results with different auth types

**Possible Causes:**
1. Platform doesn't support all auth types
2. Server doesn't support specific auth type

**Troubleshooting:**
```
# Try MD5 first (most compatible)
ntp authentication-key 1 md5 TestSecret
ntp trusted-key 1
ntp server 192.168.1.1 key 1

# If MD5 works, try SHA types incrementally
ntp authentication-key 10 sha1 TestSecret
ntp trusted-key 10
ntp server 192.168.1.1 key 10
```

### Security Considerations

#### Authentication Strength

**Weakest to Strongest:**
1. MD5 - Legacy, use only for compatibility
2. SHA1 - Better than MD5, but considered weak
3. SHA256 - Recommended minimum for production
4. SHA384 - Very strong
5. SHA512 - Maximum strength

#### Attack Vectors

1. **Man-in-the-Middle**
   - Mitigated by authentication
   - Attacker cannot impersonate server without key

2. **Replay Attacks**
   - NTP protocol includes timestamps
   - Authentication verifies packet integrity

3. **Key Compromise**
   - If key is compromised, attacker can impersonate server
   - Regular key rotation recommended

4. **Brute Force**
   - Strong passwords resist brute force
   - Modern hash algorithms (SHA256+) resist cryptanalytic attacks

### Notes

- **Klish Mode**: Configuration commands are executed in klish mode via "sonic-cli"
- **Development Status**: Some klish show commands are under development
- **Server Configuration**: NTP server must be configured with matching key and authentication type
- **Key Security**: Passwords are case-sensitive and must match exactly
- **Authentication Overhead**: Authentication adds minimal overhead to NTP packets
- **Compatibility**: Ensure both client and server support the chosen authentication type
- **Key Range**: Key IDs from 1 to 65535 are valid
- **Multiple Keys**: Up to 65535 different keys can be configured (practical limit much lower)
- **Trusted Keys**: Only keys marked as trusted are used when authentication is enabled

### Cleanup

After test completion:
```
no ntp server <server-addr>
no ntp trusted-key 1
no ntp trusted-key 10
no ntp trusted-key 20
no ntp authentication-key 1
no ntp authentication-key 10
no ntp authentication-key 20
no ntp authenticate
no ntp enable
```

### Success Criteria Summary

✅ **Test Passes If:**
- Authentication keys configured successfully for all supported types
- Trusted keys configured successfully
- NTP server configured with authentication key
- NTP synchronization successful with authentication enabled
- `show ntp associations` shows synchronized state (reach > 0, system peer marked with *)
- Clock shows accurate time
- Authentication can be toggled (enable/disable) successfully
- Different authentication types work correctly (MD5, SHA1, SHA256, etc.)

❌ **Test Fails If:**
- Authentication key configuration rejected
- Trusted key configuration fails
- NTP fails to synchronize with correct authentication configuration
- Authentication toggle doesn't work
- Supported authentication types fail
- Configuration doesn't persist
- Clock doesn't synchronize with authenticated NTP

### Additional Validation

#### Configuration Persistence Test
1. Configure authentication with keys
2. Save configuration
3. Reboot device
4. Verify authentication still configured
5. Verify NTP still synchronized

#### Authentication Type Comparison Test
1. Configure same server with different auth types sequentially
2. Measure synchronization success rate
3. Compare performance (offset, jitter)
4. Verify all supported types work

#### Multi-Key Rotation Test
1. Configure server with key 1
2. Verify sync
3. Add key 2, configure server with key 2
4. Verify sync with new key
5. Remove key 1
6. Verify sync continues with key 2

### Reference Commands Summary

**Basic Authentication Setup:**
```bash
# Enable NTP
ntp enable

# Enable authentication
ntp authenticate

# Configure key
ntp authentication-key 1 md5 MySecret123

# Mark as trusted
ntp trusted-key 1

# Configure server with key
ntp server 192.168.1.1 key 1 iburst

# Verify
show ntp global
show ntp server
show ntp associations
show ntp
show clock
```

**Multi-Type Authentication:**
```bash
ntp authentication-key 1 md5 MDSecret
ntp authentication-key 10 sha1 SHA1Secret
ntp authentication-key 20 sha256 SHA256Secret

ntp trusted-key 1
ntp trusted-key 10
ntp trusted-key 20

ntp server 192.168.1.1 key 1
ntp server 192.168.1.2 key 10
ntp server 192.168.1.3 key 20
```
