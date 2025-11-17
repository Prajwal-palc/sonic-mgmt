# NTP Test Cases - Encrypted Keys

## Test Case 2.1.6: Verify encrypted NTP keys used for secure sync

### Test Case ID
`test_ntp_6_verify_encrypted_keys_secure_sync`

### Purpose
Verify that NTP synchronization works correctly when using encrypted (pre-encrypted) authentication keys instead of plain-text passwords. This test ensures that the `encrypted` flag in the authentication-key command is properly supported and that encrypted keys provide the same functionality as plain-text keys while offering better security in configuration storage.

### Test Setup
- Topology: 1 DUT + 1 NTP server with encrypted authentication key
- NTP server configured with encrypted authentication key
- DUT (client) configured with matching encrypted authentication key
- Both client and server have authentication enabled

### Test Procedure

#### Step 1: Enable NTP and Authentication
```
ntp enable
ntp authenticate
```
or
```
ntp
ntp authenticate
```

#### Step 2: Configure Authentication Key with Encrypted Flag
```
ntp authentication-key 1 md5 <encrypted-password> encrypted
```

**Example:**
```
ntp authentication-key 1 md5 $1$abc123xyz encrypted
```

**Important Notes:**
- The `encrypted` flag indicates the password is already encrypted
- Encrypted passwords typically start with prefix like `$1$`, `$5$`, `$6$` indicating hash type
- The encrypted string is the output of password encryption (MD5 hash, SHA hash, etc.)
- Must match the encrypted format on the NTP server

#### Step 3: Configure Trusted Key
```
ntp trusted-key 1
```

#### Step 4: Configure NTP Server with Encrypted Key
```
ntp server <ip> key 1
```

**Example:**
```
ntp server 192.168.1.1 key 1 iburst
```

#### Step 5: Verify Associations, Status, and Clock
```
show ntp associations
show ntp
show clock
```

**Expected**: NTP should sync successfully using encrypted key

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

#### Authentication Key Configuration with Encrypted Flag
```
ntp authentication-key <key-id> <auth-type> <password> encrypted
no ntp authentication-key <key-id>
```

**Parameters:**
- `key-id`: 1-65535
- `auth-type`: md5, sha1, sha256, sha384, sha512
- `password`: **Encrypted** password string (not plain-text)
- `encrypted`: Flag indicating password is pre-encrypted

**Plain-text vs Encrypted:**

**Plain-text** (password will be encrypted by system):
```
ntp authentication-key 1 md5 MyPlainTextSecret
```

**Encrypted** (password is already encrypted):
```
ntp authentication-key 1 md5 $1$abc123xyz$hashedpasswordstring encrypted
```

#### Encrypted Password Formats

Different encryption types have different hash formats:

**MD5 Hash** (starts with `$1$`):
```
ntp authentication-key 1 md5 $1$salt$hashedvalue encrypted
```

**SHA-256 Hash** (starts with `$5$`):
```
ntp authentication-key 20 sha256 $5$rounds=5000$salt$hashedvalue encrypted
```

**SHA-512 Hash** (starts with `$6$`):
```
ntp authentication-key 40 sha512 $6$rounds=5000$salt$hashedvalue encrypted
```

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
- Authentication enabled status
- Configured authentication keys (IDs only)
- **Note**: Encrypted passwords should NOT be visible in plain text

Example format:
```
NTP: enabled
Authentication: enabled
Configured Keys: 1, 10, 20
Trusted Keys: 1, 10, 20
Source Interface: none
VRF: default
```

**Security Note**: Show commands should NOT display the actual encrypted password string for security reasons

#### 2. show ntp server (klish)

Expected to display:
- Configured NTP servers
- Authentication key ID used (not the password)
- Other server options

Example format:
```
Server Address      Version  Association  iburst  prefer  Key
192.168.1.1         4        server       yes     no      1
```

#### 3. show ntp associations

Expected to display with encrypted key authentication:

**Success (Encrypted key matches server):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

**Failure (Encrypted key doesn't match):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .AUTH.          16 u    -   64  000    0.000    0.000   0.000
```

#### 4. show ntp

Expected to display:
- Authentication enabled
- Synchronization status
- NTP servers with key reference

Example:
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
- Should show accurate time if NTP sync successful

Example:
```
Thu Jan 13 10:30:45 UTC 2025
```

### Validation Criteria

1. **Encrypted Key Configuration**
   - Encrypted authentication key should be accepted
   - System should recognize `encrypted` flag
   - Configuration should complete without errors

2. **Authentication with Encrypted Key**
   - NTP should authenticate successfully using encrypted key
   - Functionality should be identical to plain-text key
   - Encrypted key provides same security for NTP packets

3. **Synchronization Success**
   - Device should sync with NTP server using encrypted key
   - `show ntp associations` should show successful sync (reach > 0)
   - System peer should be marked with `*`

4. **Configuration Security**
   - Encrypted passwords should not be displayed in plain text
   - Show commands should not reveal the encrypted password
   - Configuration should be more secure than plain-text

5. **Key Format Validation**
   - System should accept properly formatted encrypted passwords
   - Invalid encrypted format should be rejected
   - Encrypted flag should be required for encrypted passwords

6. **Compatibility**
   - Encrypted keys should work with all supported auth types
   - Should work with MD5, SHA1, SHA256, SHA384, SHA512
   - Should be compatible with all other NTP features

### Test Variations

#### Variation 1: MD5 Encrypted Key

```
ntp authentication-key 1 md5 $1$saltsalt$MD5hashedpasswordstring encrypted
ntp trusted-key 1
ntp server 192.168.1.1 key 1 iburst
```

**Expected**: Successful synchronization with MD5 encrypted key

---

#### Variation 2: SHA-256 Encrypted Key

```
ntp authentication-key 20 sha256 $5$rounds=5000$saltsalt$SHA256hashedpasswordstring encrypted
ntp trusted-key 20
ntp server 192.168.1.1 key 20 iburst
```

**Expected**: Successful synchronization with SHA-256 encrypted key

---

#### Variation 3: Multiple Encrypted Keys

```
ntp authentication-key 1 md5 $1$salt1$hash1 encrypted
ntp authentication-key 10 sha1 $1$salt2$hash2 encrypted
ntp authentication-key 20 sha256 $5$salt3$hash3 encrypted

ntp trusted-key 1
ntp trusted-key 10
ntp trusted-key 20

ntp server 192.168.1.1 key 1 iburst
ntp server 192.168.1.2 key 10 iburst
ntp server 192.168.1.3 key 20 iburst
```

**Expected**: All servers sync using their respective encrypted keys

---

#### Variation 4: Plain-text vs Encrypted Comparison

**Test A: Plain-text key**
```
ntp authentication-key 1 md5 MyPlainSecret
ntp trusted-key 1
ntp server 192.168.1.1 key 1
# Verify sync works
```

**Test B: Convert to encrypted and use**
```
# Get encrypted version of "MyPlainSecret"
# Use encrypted version
ntp authentication-key 1 md5 $1$salt$encryptedversion encrypted
ntp trusted-key 1
ntp server 192.168.1.1 key 1
# Verify sync still works
```

**Expected**: Both should work identically

---

#### Variation 5: Encrypted Key with Source Interface

```
ntp authentication-key 1 md5 $1$salt$hash encrypted
ntp trusted-key 1
ntp source-interface Management 0
ntp server 192.168.1.1 key 1 iburst
```

**Expected**: Works with source interface configuration

---

#### Variation 6: Encrypted Key with VRF

```
ntp vrf mgmt
ntp authentication-key 1 md5 $1$salt$hash encrypted
ntp trusted-key 1
ntp server 192.168.1.1 key 1 iburst
```

**Expected**: Works within VRF context

---

#### Variation 7: Invalid Encrypted Format (Negative Test)

```
ntp authentication-key 1 md5 InvalidEncryptedString encrypted
ntp trusted-key 1
ntp server 192.168.1.1 key 1
```

**Expected**: May be rejected or fail to sync (format validation)

---

#### Variation 8: Encrypted Flag with Plain-text Password (Negative Test)

```
ntp authentication-key 1 md5 PlainTextPassword encrypted
ntp trusted-key 1
ntp server 192.168.1.1 key 1
```

**Expected**: Should fail - plain-text marked as encrypted won't work

### Password Encryption Methods

#### How to Generate Encrypted Passwords

**Method 1: Using openssl**
```bash
# MD5 hash
echo -n "MySecret" | openssl passwd -1 -stdin
# Output: $1$saltsalt$hashedpassword

# SHA-256
echo -n "MySecret" | openssl passwd -5 -stdin
# Output: $5$saltsalt$hashedpassword

# SHA-512
echo -n "MySecret" | openssl passwd -6 -stdin
# Output: $6$saltsalt$hashedpassword
```

**Method 2: Using mkpasswd**
```bash
# MD5
mkpasswd -m md5 MySecret
# Output: $1$saltsalt$hashedpassword

# SHA-256
mkpasswd -m sha-256 MySecret
# Output: $5$saltsalt$hashedpassword

# SHA-512
mkpasswd -m sha-512 MySecret
# Output: $6$saltsalt$hashedpassword
```

**Method 3: From Running Configuration**
```
# Configure with plain-text
ntp authentication-key 1 md5 MySecret

# Save configuration
write memory

# View running config to see encrypted version
show running-config | grep ntp-authentication

# Copy the encrypted string for later use
```

### Encrypted Password Format Breakdown

**MD5 Hash Format:**
```
$1$saltsalt$hashedpasswordstringhere
 │  │        │
 │  │        └─ Hashed password (MD5 output)
 │  └────────── Salt (random characters)
 └───────────── Hash type ($1 = MD5)
```

**SHA-256 Hash Format:**
```
$5$rounds=5000$saltsalt$hashedpasswordstringhere
 │  │            │        │
 │  │            │        └─ Hashed password (SHA-256 output)
 │  │            └────────── Salt
 │  └─────────────────────── Number of rounds
 └────────────────────────── Hash type ($5 = SHA-256)
```

**SHA-512 Hash Format:**
```
$6$rounds=5000$saltsalt$hashedpasswordstringhere
 │  │            │        │
 │  │            │        └─ Hashed password (SHA-512 output)
 │  │            └────────── Salt
 │  └─────────────────────── Number of rounds
 └────────────────────────── Hash type ($6 = SHA-512)
```

### Detailed Test Procedure

#### Complete Step-by-Step Test (Encrypted MD5 Key)

**Prerequisites:**
- NTP server configured with encrypted key: key 1, MD5, encrypted password
- Server has matching encrypted password hash
- Server reachable from client

**Step 1: Generate Encrypted Password**
```bash
# On a Linux system or the DUT
echo -n "MySecretPassword" | openssl passwd -1 -stdin
# Example output: $1$abc12345$xyz789hashedpassword
```

**Step 2: Enable NTP on Client**
```bash
sonic-cli
configure terminal
ntp enable
```

**Step 3: Enable Authentication**
```bash
ntp authenticate
```

**Step 4: Configure Encrypted Authentication Key**
```bash
ntp authentication-key 1 md5 $1$abc12345$xyz789hashedpassword encrypted
```

**Step 5: Mark Key as Trusted**
```bash
ntp trusted-key 1
```

**Step 6: Configure NTP Server with Key**
```bash
ntp server 192.168.1.1 key 1 iburst
end
exit
```

**Step 7: Wait for Synchronization**
- Wait 2-5 minutes for NTP sync

**Step 8: Verify Synchronization**
```bash
show ntp associations
```

**Expected Output:**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

**Step 9: Verify NTP Status**
```bash
show ntp
```

**Expected**: Synchronized with authentication enabled

**Step 10: Verify Clock**
```bash
show clock
```

**Expected**: Accurate time synchronized from NTP server

### Advantages of Encrypted Keys

1. **Configuration Security**
   - Passwords not stored in plain-text in configuration files
   - Viewing running-config doesn't reveal actual passwords
   - Safer when configurations are backed up or shared

2. **Compliance**
   - Meets security compliance requirements
   - Prevents password exposure in logs
   - Better audit trail

3. **Password Recovery**
   - Encrypted passwords cannot be reversed
   - Lost passwords must be reset, not recovered
   - Prevents unauthorized access

4. **Multi-Admin Environments**
   - Admins can see encrypted passwords but can't use them elsewhere
   - Prevents password reuse across systems
   - Limits password exposure

### Security Considerations

#### Encrypted Key Strengths

1. **Configuration Files**
   - Encrypted passwords in saved configurations
   - Can share configs without revealing passwords
   - Backup files are more secure

2. **Show Commands**
   - Show running-config displays encrypted version
   - Cannot reverse engineer the original password
   - Reduces password leakage

3. **Hash Types**
   - MD5: Faster but weaker
   - SHA-256/SHA-512: Slower but much stronger
   - Use strongest hash supported by both client and server

#### Encrypted Key Limitations

1. **Encryption vs Hashing**
   - These are actually **hashes**, not encryption
   - Cannot be decrypted to get original password
   - Must match exact hash on server

2. **Hash Collisions**
   - MD5 has known collision vulnerabilities
   - Use SHA-256 or SHA-512 for better security
   - Salt helps prevent rainbow table attacks

3. **Network Security**
   - Encrypted keys protect configuration storage
   - NTP packets still use the key for HMAC authentication
   - Doesn't add additional network-level encryption

### Common Issues and Troubleshooting

#### Issue 1: Encrypted Key Not Working

**Symptoms:**
- Configuration accepted but sync fails
- Authentication failures

**Possible Causes:**
1. Encrypted string doesn't match server
2. Wrong hash format
3. Missing `encrypted` flag

**Troubleshooting:**
```
# Verify encrypted flag is present
show running-config | grep "ntp authentication-key 1"

# Should see:
ntp authentication-key 1 md5 $1$salt$hash encrypted
#                                               ^^^^^^^^^ encrypted flag

# Try with plain-text to verify server connectivity
no ntp authentication-key 1
ntp authentication-key 1 md5 PlainTextPassword
# If this works, issue is with encrypted string
```

#### Issue 2: Invalid Encrypted Format

**Symptoms:**
- Command rejected
- Error message about invalid format

**Possible Causes:**
1. Encrypted string not properly formatted
2. Missing hash type prefix ($1$, $5$, $6$)
3. Special characters causing parsing issues

**Troubleshooting:**
```
# Verify hash format
# MD5 should start with $1$
# SHA-256 should start with $5$
# SHA-512 should start with $6$

# Ensure entire string is provided
# Include salt and hash portions

# Use quotes if necessary
ntp authentication-key 1 md5 "$1$salt$hash" encrypted
```

#### Issue 3: Encrypted Flag Missing

**Symptoms:**
- System treats encrypted hash as plain-text
- Authentication fails

**Troubleshooting:**
```
# Always include 'encrypted' flag for encrypted passwords
ntp authentication-key 1 md5 $1$salt$hash encrypted
#                                               ^^^^^^^^^ Required!

# Without flag, system may try to encrypt the encrypted string
# This double-encryption will not match server
```

#### Issue 4: Hash Mismatch with Server

**Symptoms:**
- Configuration accepted
- Synchronization fails
- .AUTH. in refid

**Troubleshooting:**
```
# Verify server has same encrypted password
# Contact server administrator
# Ensure hash was generated from same plain-text password
# Verify hash type matches (MD5, SHA256, etc.)
```

### Best Practices

1. **Use Strong Hash Types**
   - Prefer SHA-256 or SHA-512 over MD5
   - MD5 only for legacy compatibility
   - Match server's hash type

2. **Secure Password Generation**
   - Generate hashes on secure system
   - Don't email plain-text passwords
   - Don't log plain-text passwords

3. **Key Management**
   - Document which keys use encrypted passwords
   - Keep plain-text passwords in secure vault
   - Rotate keys periodically

4. **Configuration Management**
   - Encrypted configs are safer to store in version control
   - Can share configs without exposing passwords
   - Still protect configurations as they contain sensitive data

5. **Testing**
   - Test with plain-text first to verify connectivity
   - Convert to encrypted after confirming it works
   - Keep plain-text password documented securely

### Notes

- **Klish Mode**: Configuration commands executed in klish mode via "sonic-cli"
- **Development Status**: Some klish show commands under development
- **Encrypted vs Hashed**: These are actually cryptographic hashes, not encryption
- **Server Coordination**: Server must have matching encrypted password
- **Hash Irreversibility**: Cannot recover original password from hash
- **Case Sensitivity**: Encrypted hashes are case-sensitive
- **Special Characters**: May need quotes around encrypted strings
- **Security**: Encrypted keys improve configuration security, not NTP packet security

### Cleanup

After test completion:
```
no ntp server <server-addr>
no ntp trusted-key 1
no ntp authentication-key 1
no ntp authenticate
no ntp enable
```

### Success Criteria Summary

✅ **Test Passes If:**
- Encrypted authentication key configuration accepted
- System recognizes `encrypted` flag correctly
- NTP synchronization successful with encrypted key
- `show ntp associations` shows synchronized state (reach > 0, * marker)
- Clock shows accurate time
- Encrypted passwords not displayed in plain text
- Functionality identical to plain-text keys
- All hash types work (MD5, SHA256, SHA512)

❌ **Test Fails If:**
- Encrypted key configuration rejected
- `encrypted` flag not recognized
- NTP fails to synchronize with correct encrypted key
- System displays encrypted password in plain text
- Encrypted keys don't work as well as plain-text keys
- Hash format validation missing

### Additional Validation

#### Encrypted Key Persistence Test
1. Configure with encrypted key
2. Save configuration
3. Reboot device
4. Verify encrypted key still configured
5. Verify NTP still synchronized

#### Plain-text to Encrypted Migration Test
1. Configure with plain-text password
2. Verify sync works
3. View running-config to get encrypted version
4. Remove plain-text configuration
5. Configure with encrypted version
6. Verify sync still works

#### Multiple Hash Types Test
1. Configure servers with different hash types (MD5, SHA256, SHA512)
2. Use encrypted keys for each
3. Verify all can sync simultaneously
4. Compare performance and security

### Reference Commands Summary

**Configure with Encrypted Key:**
```bash
# Enable NTP and authentication
ntp enable
ntp authenticate

# Configure encrypted key
ntp authentication-key 1 md5 $1$salt$hashedpassword encrypted

# Mark as trusted
ntp trusted-key 1

# Configure server
ntp server 192.168.1.1 key 1 iburst

# Verify
show ntp global
show ntp server
show ntp associations
show ntp
show clock
```

**Generate Encrypted Password:**
```bash
# Using openssl (MD5)
echo -n "MyPassword" | openssl passwd -1 -stdin

# Using openssl (SHA-256)
echo -n "MyPassword" | openssl passwd -5 -stdin

# Using openssl (SHA-512)
echo -n "MyPassword" | openssl passwd -6 -stdin
```

**Compare Plain vs Encrypted:**
```bash
# Plain-text
ntp authentication-key 1 md5 MyPassword

# Encrypted (same password)
ntp authentication-key 1 md5 $1$salt$hash encrypted
```
