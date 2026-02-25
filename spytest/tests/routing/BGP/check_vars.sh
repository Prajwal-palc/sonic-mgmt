#!/bin/bash
# Batch A tests
tests_a=(
  'test_bgp_ipv4_basic.py'
  'test_bgp_svi_ipv4.py'
  'test_bgp_portchannel_ipv4.py'
  'test_bgp_loopback_ipv4.py'
  'test_bgp_ipv4_basic_ebgp.py'
  'test_bgp_svi_ipv4_ebgp.py'
  'test_bgp_portchannel_ipv4_ebgp.py'
  'test_bgp_loopback_ipv4_ebgp.py'
  'test_bgp_ebgp_connected_static_redistribution.py'
  'test_bgp_advanced_features.py'
  'test_ipv4_bgp_route_reflector.py'
  'test_bgp_med_weight.py'
)

echo 'Batch A - Missing Variable Files:'
for test in "${tests_a[@]}"; do
  var_file=$(echo $test | sed 's/test_/vars_/' | sed 's/.py/.yaml/')
  if [ ! -f "$var_file" ]; then
    echo "  MISSING: $var_file for $test"
  fi
done
