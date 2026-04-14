#!/bin/bash
# NTP Server Validation Script
# Validates that NTP server is reachable before running tests
# Usage: ./validate_ntp_server.sh [ntp_server_ip]

set -e

# Default to Google Public NTP if not provided
NTP_SERVER="${1:-216.239.35.0}"
TIMEOUT=5

echo "========================================="
echo "NTP Server Validation"
echo "========================================="
echo "NTP Server: $NTP_SERVER"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Test 1: Network reachability (ping)
echo "[Test 1/3] Testing network reachability..."
if ping -c 2 -W "$TIMEOUT" "$NTP_SERVER" >/dev/null 2>&1; then
    echo "✓ NTP server $NTP_SERVER is reachable via ICMP"
else
    echo "⚠ WARNING: Cannot ping $NTP_SERVER (may be blocked by firewall)"
    echo "  Continuing with NTP protocol test..."
fi

# Test 2: NTP port reachability (UDP 123)
echo ""
echo "[Test 2/3] Testing NTP port accessibility..."
if command -v nc >/dev/null 2>&1; then
    # Using netcat to test UDP port 123
    if timeout "$TIMEOUT" nc -u -z -w 2 "$NTP_SERVER" 123 2>/dev/null; then
        echo "✓ NTP port 123 is accessible on $NTP_SERVER"
    else
        echo "⚠ WARNING: Cannot connect to UDP port 123 on $NTP_SERVER"
    fi
else
    echo "  ⓘ netcat (nc) not installed, skipping port test"
fi

# Test 3: NTP query (actual NTP protocol test)
echo ""
echo "[Test 3/3] Testing NTP protocol query..."
if command -v ntpdate >/dev/null 2>&1; then
    if timeout "$TIMEOUT" ntpdate -q "$NTP_SERVER" >/dev/null 2>&1; then
        echo "✓ NTP server $NTP_SERVER responds to NTP queries"
        echo ""
        echo "NTP Query Details:"
        ntpdate -q "$NTP_SERVER" 2>&1 | grep -E "(server|offset|delay)" | head -5
        NTP_VALID=true
    else
        echo "✗ NTP server $NTP_SERVER does NOT respond to NTP queries"
        NTP_VALID=false
    fi
elif command -v chronyc >/dev/null 2>&1; then
    # Try using chronyc for NTP query
    echo "  Using chronyc for NTP validation..."
    if timeout "$TIMEOUT" chronyc -h "$NTP_SERVER" tracking >/dev/null 2>&1; then
        echo "✓ NTP server $NTP_SERVER is responding"
        NTP_VALID=true
    else
        echo "⚠ chronyc remote query may not work (trying ntpdate alternative)"
        NTP_VALID=unknown
    fi
else
    echo "✗ Neither ntpdate nor chronyc is installed"
    echo "  Install with: sudo apt-get install ntpdate"
    NTP_VALID=unknown
fi

# Summary
echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo "NTP Server: $NTP_SERVER"

if [ "$NTP_VALID" = "true" ]; then
    echo "Status: ✓ VALID - Server is reachable and responding"
    echo ""
    echo "You can use this server in your tests:"
    echo "  test_server: \"$NTP_SERVER\""
    exit 0
elif [ "$NTP_VALID" = "false" ]; then
    echo "Status: ✗ INVALID - Server is not responding to NTP queries"
    echo ""
    echo "Recommended public NTP servers to try:"
    echo "  - 216.239.35.0 (time.google.com)"
    echo "  - 216.239.35.4 (time2.google.com)"
    echo "  - 216.239.35.8 (time3.google.com)"
    echo "  - 216.239.35.12 (time4.google.com)"
    echo ""
    echo "Or use hostname: time.google.com"
    exit 1
else
    echo "Status: ⚠ UNKNOWN - Could not verify (missing tools)"
    echo ""
    echo "Install validation tools:"
    echo "  sudo apt-get install ntpdate netcat-openbsd"
    echo ""
    echo "Proceeding anyway (server may still work)"
    exit 0
fi
