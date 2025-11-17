# NTP Test Cases - Clock Drift Detection and Correction

## Test Case 2.1.7: Verify NTP detects/corrects clock drift

### Test Case ID
`test_ntp_7_verify_ntp_detects_corrects_clock_drift`

### Purpose
Verify that NTP correctly detects clock drift when the system clock is manually skewed and automatically corrects the time back to the accurate time from the NTP server. This test validates NTP's core functionality of maintaining accurate time despite manual clock changes or system clock drift.

### Test Setup
- Topology: 1 DUT + 1 NTP server
- NTP server must be reachable and providing accurate time
- Ability to manually change system clock on DUT
- Sufficient monitoring time to observe drift correction (10-30 minutes)

### Test Procedure

#### Step 1: Configure NTP Server and Enable NTP
```
ntp server <ip>
ntp enable
```
or
```
ntp server <ip>
ntp
```

#### Step 2: Wait for Initial Synchronization
- Wait for NTP to synchronize with server (5-10 minutes)
- Verify synchronization is established
```
show ntp associations
show ntp
show clock
```

#### Step 3: Record Baseline
- Record current time from `show clock`
- Record NTP offset from `show ntp associations`
- Note synchronization status

#### Step 4: Manually Skew Clock
**Option A: Skip forward 5 minutes**
```bash
date -s "+5 minutes"
```

**Option B: Skip backward 5 minutes**
```bash
date -s "-5 minutes"
```

#### Step 5: Monitor Associations, Status & Clock Over Time
Monitor at regular intervals (every 1-2 minutes) for 10-30 minutes:
```
show ntp associations
show ntp
show clock
```

**What to Monitor:**
- NTP offset values (should show ~300 seconds initially, then decrease)
- Reachability status (should remain 377 or similar)
- Clock correction progress
- Synchronization status (may temporarily show unsynchronized)

### Configuration Commands to Test (configure-view)

#### Enable/Disable NTP
```
ntp enable
no ntp enable
```

#### NTP Server Configuration
```
ntp server <server-addr> [version <version-value>] [association <assoc-value>] [iburst] [key <key-value>] [prefer]
no ntp server <server-addr>
```

**Parameters:**
- `server-addr`: NTP server IP address or hostname
- `version-value`: 3 or 4
- `assoc-value`: server or pool
- `iburst`: Send burst of packets at startup (recommended for faster sync)
- `key-value`: 1-65535 (authentication key ID)
- `prefer`: Mark this server as preferred

#### Authentication Configuration
```
ntp authenticate
no ntp authenticate
```

#### Authentication Key Configuration
```
ntp authentication-key <key-id> <auth-type> <password> [encrypted]
no ntp authentication-key <key-id>
```

#### Trusted Key Configuration
```
ntp trusted-key <key-id>
no ntp trusted-key <key-id>
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

#### 1. show ntp associations (Before Drift)

Normal synchronized state before manual clock change:

```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

**Key Values:**
- `*` marker: Synchronized
- `reach 377`: Good reachability
- `offset 0.456`: Small offset (milliseconds)

#### 2. show ntp associations (Immediately After +5 Min Drift)

After manually advancing clock by 5 minutes:

```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .GPS.            1 u   10   64  377    0.123  -300.123  10.234
                                                                ^^^^^^^^  ^^^^^^
                                                              Large offset High jitter
```

**Key Indicators:**
- `*` marker may disappear (temporarily unsynchronized)
- `offset -300`: Approximately -300 seconds (5 minutes behind server)
- `jitter` increases due to sudden change
- Negative offset means local clock is ahead of server

#### 3. show ntp associations (5 Minutes After Drift)

NTP detecting and correcting drift:

```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   45   64  377    0.123  -180.456   5.123
                                                                ^^^^^^^^
                                                           Offset reducing
```

**Progress Indicators:**
- `*` marker returns (re-synchronized)
- `offset` decreasing toward zero
- `jitter` decreasing
- Clock being corrected gradually

#### 4. show ntp associations (After Full Correction)

After NTP has corrected the drift (10-30 minutes):

```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   55   64  377    0.123    1.234   0.890
                                                                 ^^^^^^
                                                           Back to normal
```

**Correction Complete:**
- `*` marker present
- `offset` back to small value (< 5 seconds)
- `jitter` back to normal low values
- Clock is accurate again

#### 5. show ntp

**Before Drift:**
```
synchronised to NTP server (192.168.1.1) at stratum 2
   time correct to within 12 ms
   polling server every 64 s
```

**After Drift (detecting):**
```
not synchronised
   time may not be accurate
   polling server every 64 s

   offset: -300.123 seconds
```

**After Correction:**
```
synchronised to NTP server (192.168.1.1) at stratum 2
   time correct to within 50 ms
   polling server every 64 s
```

#### 6. show clock

**Before Drift:**
```
Thu Jan 13 10:30:45 UTC 2025
```

**Immediately After +5 Min Drift:**
```
Thu Jan 13 10:35:45 UTC 2025
                 ^^
              5 minutes ahead
```

**During Correction (gradual):**
```
Thu Jan 13 10:34:15 UTC 2025  (gradually moving back)
Thu Jan 13 10:33:30 UTC 2025
Thu Jan 13 10:32:45 UTC 2025
...
```

**After Correction:**
```
Thu Jan 13 10:30:50 UTC 2025  (back to accurate time)
```

### Validation Criteria

1. **Drift Detection**
   - NTP should detect the manual clock change
   - Offset value should reflect the drift amount
   - May temporarily lose synchronization

2. **Automatic Correction**
   - NTP should automatically correct the clock
   - No manual intervention required
   - Clock should gradually return to accurate time

3. **Correction Time**
   - Small drifts (< 128ms): Corrected immediately via slew
   - Medium drifts (128ms - 1000s): Corrected gradually via slew
   - Large drifts (> 1000s): May be stepped or require longer correction

4. **Synchronization Maintained**
   - NTP should remain reachable during correction
   - Eventually return to synchronized state
   - `*` marker should reappear

5. **Offset Values**
   - Should show large offset initially
   - Offset should decrease over time
   - Final offset should be small (< 5 seconds)

6. **System Stability**
   - System should remain stable during correction
   - No crashes or hangs
   - All services should continue operating

### Test Variations

#### Variation 1: Forward Drift (+5 Minutes)

**Procedure:**
1. Synchronize with NTP server
2. Advance clock by 5 minutes: `date -s "+5 minutes"`
3. Monitor correction

**Expected:**
- Large negative offset (~-300 seconds)
- NTP slews clock backward
- Correction takes 10-30 minutes

---

#### Variation 2: Backward Drift (-5 Minutes)

**Procedure:**
1. Synchronize with NTP server
2. Move clock back 5 minutes: `date -s "-5 minutes"`
3. Monitor correction

**Expected:**
- Large positive offset (~+300 seconds)
- NTP slews clock forward
- Correction takes 10-30 minutes

---

#### Variation 3: Small Drift (+30 Seconds)

**Procedure:**
1. Synchronize with NTP server
2. Advance clock by 30 seconds: `date -s "+30 seconds"`
3. Monitor correction

**Expected:**
- Moderate offset (~-30 seconds)
- Faster correction (5-10 minutes)
- May not lose sync status

---

#### Variation 4: Large Drift (+30 Minutes)

**Procedure:**
1. Synchronize with NTP server
2. Advance clock by 30 minutes: `date -s "+30 minutes"`
3. Monitor correction

**Expected:**
- Very large offset (~-1800 seconds)
- May exceed panic threshold
- Could require NTP restart or step
- Longer correction time

---

#### Variation 5: Repeated Drift Corrections

**Procedure:**
1. Synchronize with NTP server
2. Skew clock +5 minutes, wait for correction
3. Skew clock -5 minutes, wait for correction
4. Verify NTP continues to work

**Expected:**
- NTP handles multiple drift corrections
- Continues to function properly
- No degradation in performance

---

#### Variation 6: Drift During Initial Synchronization

**Procedure:**
1. Configure NTP server but don't wait for sync
2. Immediately skew clock
3. Observe synchronization and correction

**Expected:**
- May take longer to establish sync
- Should eventually synchronize and correct
- May require more patience

### Clock Correction Methods

#### Method 1: Slew (Gradual Adjustment)

**Used for:** Small to medium drifts (< 1000 seconds)

**Characteristics:**
- Gradual time adjustment
- Clock never jumps backward
- Time always moves forward
- Adjustment rate: typically 0.5ms per second
- For 5 minutes (300s): Takes ~600 seconds (10 minutes) to correct

**Advantages:**
- Smooth correction
- No time discontinuities
- Safe for applications relying on monotonic time

---

#### Method 2: Step (Immediate Jump)

**Used for:** Large drifts (> 1000 seconds) or initial sync

**Characteristics:**
- Immediate time change
- Clock jumps to correct time
- Can go forward or backward
- Instantaneous correction

**Advantages:**
- Fast correction
- Accurate time immediately

**Disadvantages:**
- Can break applications expecting monotonic time
- May trigger alarms or errors
- Logs may show time discontinuities

---

#### Method 3: Panic (Too Large to Correct)

**Used for:** Extremely large drifts (> panic threshold, typically 1000s)

**Characteristics:**
- NTP refuses to correct
- Requires manual intervention or configuration change
- NTP may stop or require restart

**Indicators:**
- NTP logs show "panic" or "clock too far off"
- Synchronization fails
- Manual clock reset required

### NTP Offset Interpretation

**Offset Sign Convention:**

- **Negative Offset** (e.g., -300s):
  - Local clock is AHEAD of NTP server
  - Local time: 10:35:00, Server time: 10:30:00
  - NTP needs to slow down or step back local clock

- **Positive Offset** (e.g., +300s):
  - Local clock is BEHIND NTP server
  - Local time: 10:25:00, Server time: 10:30:00
  - NTP needs to speed up or step forward local clock

### Expected Correction Timeline

**For 5-Minute (300-second) Drift:**

| Time | Offset | Action | Status |
|------|--------|--------|--------|
| T+0 (drift applied) | -300s | Drift detected | Unsynchronized |
| T+2 min | -280s | Slewing | Re-synchronizing |
| T+5 min | -240s | Slewing | Synchronized |
| T+10 min | -180s | Slewing | Synchronized |
| T+15 min | -120s | Slewing | Synchronized |
| T+20 min | -60s | Slewing | Synchronized |
| T+25 min | -20s | Slewing | Synchronized |
| T+30 min | -2s | Nearly corrected | Synchronized |
| T+35 min | -0.5s | Correction complete | Synchronized |

**Note:** Actual timeline varies based on:
- NTP implementation
- Slew rate configuration
- Poll interval
- Network conditions

### Monitoring Commands

#### Continuous Monitoring Script

```bash
#!/bin/bash
# Monitor NTP drift correction

echo "Starting NTP drift correction monitoring..."
echo "Time, Offset, Jitter, Reach, Sync Status" > ntp_monitor.log

for i in {1..30}; do
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    # Get NTP associations
    ntp_output=$(ntpq -p 2>/dev/null | tail -1)

    # Extract offset, jitter, reach
    offset=$(echo $ntp_output | awk '{print $9}')
    jitter=$(echo $ntp_output | awk '{print $10}')
    reach=$(echo $ntp_output | awk '{print $7}')
    sync=$(echo $ntp_output | awk '{print $1}' | grep -o '^\*' || echo "unsync")

    # Log to file
    echo "$timestamp, $offset, $jitter, $reach, $sync" >> ntp_monitor.log

    # Display to console
    echo "[$timestamp] Offset: ${offset}s, Jitter: ${jitter}ms, Reach: $reach, Sync: $sync"

    # Wait 60 seconds between checks
    sleep 60
done

echo "Monitoring complete. Results in ntp_monitor.log"
```

#### Manual Monitoring

```bash
# Check every 2 minutes
watch -n 120 'ntpq -p; echo; date'

# Or manually
while true; do
    clear
    echo "=== NTP Status ==="
    ntpq -p
    echo
    echo "=== Current Time ==="
    date
    echo
    echo "Press Ctrl+C to stop"
    sleep 120
done
```

### Detailed Test Procedure

#### Complete Step-by-Step Test (+5 Minute Forward Drift)

**Step 1: Configure and Synchronize**
```bash
# Configure NTP
sonic-cli
configure terminal
ntp enable
ntp server 192.168.1.1 iburst
end
exit

# Wait for synchronization (5-10 minutes)
sleep 300

# Verify synchronized
show ntp associations
# Should see * marker and low offset
```

**Step 2: Record Baseline**
```bash
# Record current time
baseline_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "Baseline time: $baseline_time"

# Record NTP offset
ntpq -p | tail -1
# Record offset value
```

**Step 3: Apply Drift**
```bash
# Advance clock by 5 minutes
date -s "+5 minutes"

# Verify drift applied
date
# Should show 5 minutes ahead of baseline
```

**Step 4: Monitor Correction (30 minutes)**
```bash
# Monitor every 2 minutes for 30 minutes
for i in {1..15}; do
    echo "=== Check $i/15 ($(date +"%H:%M:%S")) ==="

    # Show NTP associations
    ntpq -p

    # Show current time
    date

    # Wait 2 minutes
    sleep 120
done
```

**Step 5: Verify Correction Complete**
```bash
# Final check
ntpq -p
# Offset should be < 5 seconds
# Should have * marker

date
# Time should be accurate (within 1 second of NTP server)
```

**Step 6: Calculate Correction Time**
```bash
# Note when offset returns to < 1 second
# Calculate total correction time
# Document results
```

### Common Observations

#### Observation 1: Immediate Loss of Sync

After applying drift, the `*` marker may immediately disappear:

```
Before:  *192.168.1.1     .GPS.       1 u   32   64  377    0.123    0.456   0.789
After:    192.168.1.1     .GPS.       1 u   10   64  377    0.123  -300.123  10.234
          ^ No asterisk (unsynchronized)
```

**This is normal** - NTP detects the large offset and temporarily marks itself as unsynchronized.

---

#### Observation 2: Gradual Offset Reduction

Offset should decrease over time:

```
T+0:  offset -300.123s
T+5:  offset -240.567s
T+10: offset -180.234s
T+15: offset -120.891s
T+20: offset -60.456s
T+25: offset -20.123s
T+30: offset -2.567s
```

---

#### Observation 3: Jitter Spike

Jitter may spike initially then settle:

```
Before drift: jitter 0.789ms
After drift:  jitter 10.234ms (spike)
During correction: jitter 5.123ms
After correction: jitter 0.890ms
```

### Troubleshooting

#### Issue 1: NTP Not Correcting Drift

**Symptoms:**
- Offset remains large
- No progress toward zero
- Clock stays wrong

**Possible Causes:**
1. Drift exceeds panic threshold
2. NTP service stopped
3. Firewall blocking NTP

**Resolution:**
```bash
# Check NTP service status
systemctl status ntp

# Restart NTP if needed
systemctl restart ntp

# Check for panic threshold
ntpq -c "rv 0" | grep panic

# Check NTP is running
ps aux | grep ntp
```

---

#### Issue 2: Correction Taking Too Long

**Symptoms:**
- Offset decreasing very slowly
- Correction taking hours

**Possible Causes:**
1. Large drift
2. Slow slew rate
3. High poll interval

**Resolution:**
```bash
# Check slew rate (if accessible)
# Consider stepping time instead
ntpd -gq  # Step time once, then exit

# Or restart NTP to allow step
systemctl restart ntp
```

---

#### Issue 3: Clock Jumping Backward

**Symptoms:**
- Time goes backward
- Applications fail
- Logs show time reversal

**Cause:**
- NTP stepping time instead of slewing
- Large negative offset

**Resolution:**
- This is sometimes necessary
- Some applications may need restart
- NTP configured to step for large offsets

### Notes

- **Klish Mode**: Configuration commands executed in klish mode via "sonic-cli"
- **Development Status**: Some klish show commands under development
- **Test Duration**: Allow 30-60 minutes for complete test
- **Drift Range**: ±5 minutes is recommended test range
- **Panic Threshold**: Typically 1000 seconds; drift > this may not correct
- **Slew Rate**: Typically 0.5ms/s; varies by implementation
- **Step vs Slew**: Large drifts may be stepped instead of slewed
- **Monitoring Interval**: Check every 1-2 minutes for good observation
- **Baseline**: Always establish synchronized baseline first

### Cleanup

After test completion:
```
# NTP will auto-correct, no cleanup needed
# If testing is complete:
no ntp server <server-addr>
no ntp enable
```

### Success Criteria Summary

✅ **Test Passes If:**
- NTP detects manual clock drift
- Large offset appears immediately after drift
- NTP automatically begins correction without intervention
- Offset gradually decreases over time
- Clock returns to accurate time within reasonable period (10-60 minutes)
- System remains stable during correction
- Synchronization is re-established
- `*` marker returns after correction
- Final offset is small (< 5 seconds)
- `show clock` displays accurate time after correction

❌ **Test Fails If:**
- NTP doesn't detect drift
- Offset doesn't decrease
- Clock remains incorrect indefinitely
- NTP service crashes during correction
- System becomes unstable
- Synchronization cannot be re-established
- Manual intervention required for correction

### Additional Validation

#### Drift Correction Rate Calculation

```bash
# Calculate slew rate
initial_offset=-300  # seconds
final_offset=-2      # seconds
time_elapsed=1800    # seconds (30 minutes)

correction_amount=$((initial_offset - final_offset))  # 298 seconds
correction_rate=$(echo "scale=6; $correction_amount / $time_elapsed" | bc)  # ~0.165 s/s

echo "Correction rate: $correction_rate seconds per second"
# Expected: around 0.5 ms/s = 0.0005 s/s for slewing
# Actual may be higher due to other factors
```

#### Verify Monotonic Time

```bash
# Ensure time never goes backward during slew
prev_time=$(date +%s)
for i in {1..60}; do
    curr_time=$(date +%s)
    if [ $curr_time -lt $prev_time ]; then
        echo "ERROR: Time went backward!"
        echo "Previous: $prev_time, Current: $curr_time"
    fi
    prev_time=$curr_time
    sleep 10
done
echo "Time monotonicity verified"
```

### Related Test Cases

- **2.1.1**: Basic NTP synchronization (establishes baseline)
- **2.1.7**: Clock drift detection and correction (THIS TEST)
- Together these verify NTP's ability to establish and maintain accurate time

This test is critical for validating NTP's core purpose: maintaining accurate system time despite clock drift or manual changes.
