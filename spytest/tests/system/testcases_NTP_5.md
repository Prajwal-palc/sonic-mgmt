# NTP Test Cases - Authentication Failure (Negative Test)

## Test Case 2.1.5: Verify sync fails with mismatched key

### Test Case ID
`test_ntp_5_verify_sync_fails_mismatched_key`

### Purpose
Verify that NTP synchronization fails when authentication is enabled and the client's authentication key (password, type, or ID) does not match the server's authentication configuration. This is a negative test to ensure authentication is properly enforced.

### Test Setup
- Topology: 1 DUT + 1 NTP server with authentication configured
- NTP server configured with specific authentication key (e.g., key 1, MD5, "ServerSecret")
- DUT (client) configured with DIFFERENT authentication key
- Both client and server have authentication enabled

### Test Procedure

#### Step 1: Enable NTP and Authentication on Client
```
ntp enable
ntp authenticate
```

#### Step 2: Configure CLIENT with Different Key than Server
**Server Configuration** (pre-configured):
```
# On NTP Server (not on DUT)
ntp authentication-key 1 md5 ServerSecret
ntp trusted-key 1
```

**Client Configuration** (on DUT - MISMATCHED):
```
# Different password
ntp authentication-key 1 md5 WrongClientSecret

# OR different key ID
ntp authentication-key 2 md5 ServerSecret

# OR different authentication type
ntp authentication-key 1 sha1 ServerSecret
```

#### Step 3: Mark Key as Trusted
```
ntp trusted-key 1
```
(or `ntp trusted-key 2` if using different key ID)

#### Step 4: Associate Server with Key
```
ntp server <server-ip> key 1
```
(or `key 2` if using different key ID)

#### Step 5: Check Associations and Status
```
show ntp associations
show ntp
```

**Expected Result**:
- Synchronization should FAIL
- Authentication failure indicators should be visible

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

#### Authentication Key Configuration
```
ntp authentication-key <key-id> <auth-type> <password> [encrypted]
no ntp authentication-key <key-id>
```

**Parameters:**
- `key-id`: 1-65535
- `auth-type`: md5, sha1, sha256, sha384, sha512
- `password`: Shared secret (MUST match on server and client for success)
- `encrypted`: Optional flag

#### Trusted Key Configuration
```
ntp trusted-key <key-id>
no ntp trusted-key <key-id>
```

#### NTP Server Configuration
```
ntp server <server-addr> [version <version-value>] [association <assoc-value>] [iburst] [key <key-value>] [prefer]
no ntp server <server-addr>
```

**Parameters:**
- `key-value`: References the authentication key ID

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
```

### Expected Output (Authentication Failure)

#### 1. show ntp associations (With Mismatched Key)

Expected to display authentication failure indicators:

**Example Output:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .AUTH.          16 u    -   64  000    0.000    0.000   0.000
```

**Authentication Failure Indicators:**
- **`.AUTH.` in refid column** - Indicates authentication failure
- **`st 16`** - Stratum 16 means unreachable (authentication failed)
- **`reach 000`** - Zero reachability (no successful polls)
- **No `*` marker** - Server is not selected as system peer
- **`delay/offset/jitter = 0.000`** - No valid time measurements

**Alternative Failure Indicators (platform-dependent):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .INIT.          16 u    -   64  000    0.000    0.000   0.000
```
- **`.INIT.`** - Server not initialized (authentication may be failing)

**Or:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
x192.168.1.1     .GPS.           1 u   32   64  000    0.000    0.000   0.000
```
- **`x` marker** - False ticker (authentication failed, time not trusted)
- **`reach 000`** - No successful authenticated exchanges

#### 2. show ntp

Expected to display:
- Not synchronized status
- No system peer selected
- May show "authentication failure" or similar message

**Example Output:**
```
Not synchronized to NTP server
authentication enabled
no system peer

     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .AUTH.          16 u    -   64  000    0.000    0.000   0.000
```

#### 3. show ntp global (klish)

Expected to display:
- Authentication: enabled
- Configured keys
- Trusted keys

**Example:**
```
NTP: enabled
Authentication: enabled
Configured Keys: 1
Trusted Keys: 1
```

#### 4. show ntp server (klish)

Expected to display server configured with key:

**Example:**
```
Server Address      Version  Association  iburst  prefer  Key
192.168.1.1         4        server       yes     no      1
```

### Validation Criteria

1. **Authentication Failure Detection**
   - NTP should NOT synchronize when keys mismatch
   - `show ntp associations` should indicate failure
   - System should remain unsynchronized

2. **Failure Indicators Present**
   - At least one of these indicators should be visible:
     - `.AUTH.` in refid column
     - `st 16` (unreachable)
     - `reach 000` (no successful polls)
     - `x` marker (false ticker)
     - No `*` marker (no system peer)

3. **Configuration Accepted**
   - Client configuration should be accepted without error
   - Show commands should display configured authentication
   - Failure should be in synchronization, not configuration

4. **System Protection**
   - System time should NOT be affected by server with wrong key
   - No time updates from unauthenticated source
   - Clock remains at previous time or unsynchronized

### Test Variations (Mismatch Scenarios)

#### Scenario 1: Password Mismatch (Same Key ID, Same Type)

**Server:**
```
ntp authentication-key 1 md5 CorrectServerPassword
ntp trusted-key 1
```

**Client:**
```
ntp authentication-key 1 md5 WrongClientPassword
ntp trusted-key 1
ntp server 192.168.1.1 key 1
```

**Expected:** Authentication failure - passwords don't match

---

#### Scenario 2: Authentication Type Mismatch (Same Key ID, Same Password)

**Server:**
```
ntp authentication-key 1 md5 SharedSecret
ntp trusted-key 1
```

**Client:**
```
ntp authentication-key 1 sha1 SharedSecret
ntp trusted-key 1
ntp server 192.168.1.1 key 1
```

**Expected:** Authentication failure - types don't match (MD5 vs SHA1)

---

#### Scenario 3: Key ID Mismatch (Different Key IDs)

**Server:**
```
ntp authentication-key 1 md5 SharedSecret
ntp trusted-key 1
```

**Client:**
```
ntp authentication-key 2 md5 SharedSecret
ntp trusted-key 2
ntp server 192.168.1.1 key 2
```

**Expected:** Authentication failure - server expects key 1, client sends key 2

---

#### Scenario 4: Server Has Authentication, Client Does Not

**Server:**
```
ntp authentication-key 1 md5 ServerSecret
ntp trusted-key 1
ntp authenticate
```

**Client:**
```
# No authentication configured
ntp server 192.168.1.1
```

**Expected:** Authentication failure - server rejects unauthenticated requests

---

#### Scenario 5: Client Has Authentication, Server Does Not

**Server:**
```
# No authentication configured
```

**Client:**
```
ntp authentication-key 1 md5 ClientSecret
ntp trusted-key 1
ntp authenticate
ntp server 192.168.1.1 key 1
```

**Expected:** May work or fail depending on implementation
- If server accepts both auth and non-auth: may work
- If client requires auth but server doesn't support: will fail

---

#### Scenario 6: Case Sensitivity in Password

**Server:**
```
ntp authentication-key 1 md5 MySecret
ntp trusted-key 1
```

**Client:**
```
ntp authentication-key 1 md5 mysecret
ntp trusted-key 1
ntp server 192.168.1.1 key 1
```

**Expected:** Authentication failure - passwords are case-sensitive

---

#### Scenario 7: Whitespace in Password

**Server:**
```
ntp authentication-key 1 md5 MySecret
ntp trusted-key 1
```

**Client:**
```
ntp authentication-key 1 md5 "My Secret"
ntp trusted-key 1
ntp server 192.168.1.1 key 1
```

**Expected:** Authentication failure - passwords don't match exactly

---

#### Scenario 8: Multiple Keys - Wrong Key Selected

**Server:**
```
ntp authentication-key 1 md5 ServerKey1
ntp authentication-key 2 md5 ServerKey2
ntp trusted-key 1
ntp trusted-key 2
```

**Client:**
```
ntp authentication-key 1 md5 ServerKey1
ntp authentication-key 2 md5 WrongKey2
ntp trusted-key 1
ntp trusted-key 2
ntp server 192.168.1.1 key 2
```

**Expected:** Authentication failure on key 2
- Key 1 would work but server is configured with key 2
- Since key 2 doesn't match, authentication fails

### Detailed Test Procedure

#### Complete Step-by-Step Test (Password Mismatch)

**Prerequisites:**
- NTP server configured with: key 1, MD5, password "CorrectServerPassword"
- NTP server authentication enabled
- Server reachable from client

**Step 1: Enable NTP on Client**
```bash
sonic-cli
configure terminal
ntp enable
```

**Step 2: Enable Authentication on Client**
```bash
ntp authenticate
```

**Step 3: Configure WRONG Password on Client**
```bash
ntp authentication-key 1 md5 WrongClientPassword
```

**Step 4: Mark Key as Trusted**
```bash
ntp trusted-key 1
```

**Step 5: Configure NTP Server with Key**
```bash
ntp server 192.168.1.1 key 1 iburst
end
exit
```

**Step 6: Wait for NTP Attempts**
- Wait 2-5 minutes for multiple NTP poll attempts
- Authentication failures occur during polling

**Step 7: Verify Authentication Failure**
```bash
show ntp associations
```

**Expected Output:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .AUTH.          16 u    -   64  000    0.000    0.000   0.000
```

**Step 8: Check NTP Status**
```bash
show ntp
```

**Expected:** Not synchronized, no system peer

**Step 9: Verify Clock Not Updated**
```bash
show clock
```

**Expected:** Time not synchronized from NTP server

**Step 10: Fix Configuration (Positive Verification)**
```bash
sonic-cli
configure terminal
no ntp authentication-key 1
ntp authentication-key 1 md5 CorrectServerPassword
end
exit
```

**Step 11: Wait and Verify Success**
- Wait 2-5 minutes
```bash
show ntp associations
```

**Expected Output:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```
- `*` indicates synchronized
- `reach 377` indicates successful polls
- `.GPS.` or similar valid refid

### Authentication Failure Timeline

**Typical Authentication Failure Sequence:**

| Time | Event | Reach | Status | Description |
|------|-------|-------|--------|-------------|
| T+0 | Configure mismatched key | - | - | Client config complete |
| T+0 | First poll sent | 000 | FAIL | Auth fails, no response processed |
| T+64s | Second poll sent | 000 | FAIL | Auth still failing |
| T+128s | Third poll sent | 000 | FAIL | Auth still failing |
| T+192s | Fourth poll sent | 000 | FAIL | Reach remains 000 |
| T+256s | Fifth poll sent | 000 | FAIL | System recognizes failure |
| T+320s | Continued failures | 000 | FAIL | Persistent auth failure |

**Key Points:**
- Reach never increases from 000
- All polls fail authentication
- Server may be logging authentication failures
- Client never gets valid time data

### Debugging Authentication Failures

#### Client-Side Checks

1. **Verify Client Configuration**
   ```
   show ntp global
   show ntp server
   ```

2. **Check Key Configuration**
   ```
   show running-config | grep ntp
   ```

3. **Verify Authentication Enabled**
   ```
   show ntp global | grep -i auth
   ```

4. **Check Associations for Failure Indicators**
   ```
   show ntp associations
   # Look for .AUTH., reach 000, st 16
   ```

#### Server-Side Checks (if accessible)

1. **Check Server Logs**
   ```bash
   tail -f /var/log/messages | grep -i ntp
   tail -f /var/log/syslog | grep -i ntp
   ```

2. **Look for Authentication Errors**
   - "authentication failed"
   - "incorrect key"
   - "bad auth"
   - "crypto failure"

3. **Verify Server Configuration**
   ```
   ntpq -c "rv 0"
   ntpq -c "associations"
   ```

### Common Mismatch Causes

1. **Password Typos**
   - Misspelled password
   - Extra/missing characters
   - Case sensitivity errors

2. **Configuration Errors**
   - Wrong key ID on client or server
   - Different authentication types
   - Key not marked as trusted

3. **Copy-Paste Issues**
   - Hidden characters
   - Extra whitespace
   - Line breaks in password

4. **Version Incompatibility**
   - Server doesn't support authentication type
   - Client doesn't support authentication type
   - Protocol version mismatch

5. **Timing Issues**
   - Configuration not yet applied
   - NTP service not restarted
   - Cached credentials

### Security Implications

#### What Authentication Failure Protects Against

1. **Rogue NTP Servers**
   - Attacker cannot impersonate authorized server
   - Client rejects time from unauthorized sources

2. **Man-in-the-Middle Attacks**
   - Attacker cannot modify NTP packets
   - Authentication verifies packet integrity

3. **Time Manipulation**
   - Prevents malicious time changes
   - Protects time-sensitive operations (logging, crypto)

4. **Denial of Service**
   - Limits impact of rogue NTP traffic
   - Only authenticated servers can affect time

#### Best Practices

1. **Use Strong Passwords**
   - Minimum 16 characters
   - Mix of characters
   - Avoid dictionary words

2. **Use Modern Algorithms**
   - SHA256 or higher preferred
   - Avoid MD5 for new deployments

3. **Secure Key Distribution**
   - Don't email keys in plain text
   - Use secure channels for distribution
   - Change keys periodically

4. **Monitor Authentication Failures**
   - Log authentication failures
   - Alert on persistent failures
   - Investigate unexpected failures

### Troubleshooting Guide

#### Symptom: reach 000, .AUTH. in refid

**Cause:** Authentication failure

**Resolution:**
1. Verify passwords match exactly
2. Verify authentication types match
3. Verify key IDs match
4. Check case sensitivity
5. Remove and re-enter passwords

#### Symptom: Configuration accepted but sync fails

**Cause:** Configuration error or mismatch

**Resolution:**
1. Double-check server configuration
2. Verify key is marked as trusted
3. Ensure authentication is enabled
4. Wait longer (5-10 minutes)

#### Symptom: Works without auth, fails with auth

**Cause:** Server not configured for authentication

**Resolution:**
1. Verify server has authentication enabled
2. Verify server has matching key configured
3. Contact server administrator

#### Symptom: Some keys work, others don't

**Cause:** Server doesn't support all authentication types

**Resolution:**
1. Use MD5 (most compatible)
2. Check server documentation
3. Test with different authentication types

### Notes

- **Klish Mode**: Configuration commands executed in klish mode via "sonic-cli"
- **Development Status**: Some klish show commands under development
- **Negative Test**: This is a negative test - failure is the expected outcome
- **Server Configuration**: Requires NTP server with authentication enabled
- **Wait Time**: Authentication failures visible within 2-5 poll intervals (2-10 minutes)
- **Reachability**: reach 000 is the primary indicator of total failure
- **Logging**: Server logs may show authentication failures
- **Security**: Authentication failures prevent time manipulation attacks

### Cleanup

After test completion:
```
no ntp server 192.168.1.1
no ntp trusted-key 1
no ntp authentication-key 1
no ntp authenticate
no ntp enable
```

### Success Criteria Summary

✅ **Test Passes If:**
- Configuration accepted without errors
- NTP attempts to synchronize with server
- Authentication failure detected and indicated
- `show ntp associations` shows failure indicators (.AUTH., reach 000, st 16)
- System does NOT synchronize with mismatched key
- System time NOT updated from unauthenticated source
- After fixing key, synchronization succeeds (positive verification)

❌ **Test Fails If:**
- Configuration rejected (should be accepted)
- NTP synchronizes despite mismatched key (SECURITY ISSUE!)
- No failure indicators shown
- System time updated from unauthenticated source
- Authentication not properly enforced

### Positive Verification (Success After Fix)

After verifying authentication failure, fix the configuration and verify success:

**Step 1: Correct the Password**
```bash
no ntp authentication-key 1
ntp authentication-key 1 md5 CorrectServerPassword
```

**Step 2: Wait for Synchronization**
- Wait 2-5 minutes

**Step 3: Verify Success**
```bash
show ntp associations
```

**Expected:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

This positive verification confirms:
- Authentication is working correctly
- Failure was due to mismatch (not other issues)
- System correctly enforces authentication

### Related Test Cases

- **2.1.4**: Verify authenticated NTP sync (positive test)
- **2.1.5**: Verify sync fails with mismatched key (negative test - THIS TEST)
- Together these test both positive and negative authentication scenarios

### Reference: Authentication Mismatch Matrix

| Server Key | Server Type | Server Pass | Client Key | Client Type | Client Pass | Result |
|------------|-------------|-------------|------------|-------------|-------------|--------|
| 1 | MD5 | Secret | 1 | MD5 | Secret | ✅ Success |
| 1 | MD5 | Secret | 1 | MD5 | Wrong | ❌ Fail |
| 1 | MD5 | Secret | 1 | SHA1 | Secret | ❌ Fail |
| 1 | MD5 | Secret | 2 | MD5 | Secret | ❌ Fail |
| 1 | SHA256 | Secret | 1 | SHA256 | Secret | ✅ Success |
| 1 | SHA256 | Secret | 1 | SHA256 | wrong | ❌ Fail |

**Key Takeaway:** ALL parameters must match for authentication to succeed
