#!/bin/bash
# Batch B tests
tests_b=(
  'test_bgp_ipv4_neighbor_session_establishment.py'
  'test_bgp_ipv4_route_advertisement.py'
  'test_bgp_ipv6_neighbor_session_establishment.py'
  'test_bgp_ipv6_route_advertisement.py'
  'test_bgp_local_pref.py'
  'test_bgp_md5_authentication.py'
  'test_bgp_med_path_selection.py'
  'test_bgp_multihop_over_loopbacks.py'
  'test_bgp_nexthop_propagation.py'
)

echo 'Batch B - Missing Variable Files:'
for test in "${tests_b[@]}"; do
  var_file=$(echo $test | sed 's/test_/vars_/' | sed 's/.py/.yaml/')
  if [ ! -f "$var_file" ]; then
    echo "  MISSING: $var_file for $test"
  fi
done
