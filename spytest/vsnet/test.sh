#!/bin/bash

set -x

VER=`date +%Y-%m-%d-%H-%M-%S`

pushd /data/work

ARGS=(
  "--logs-level" "debug"
  "--results-prefix=results"
  "--get-tech-support" "none"
  "--fetch-core-files" "none"
  "--syslog-check" "none"
  "--save" "config-db" "module"
  "--topology-check" "module"
  "--logs-path" "logs/$VER"
  "--continue-on-collection-errors"
  "--max-time" "session" "0"
  "--max-time" "module" "0"
  "--max-time" "function" "0"
  "--noop"
  "--tryssh=0"
  "--testbed-file" "testbed.yaml"
  "--env" "SPYTEST_RPS_DEBUG" "0"
  "--tclist-bucket" "1,2,4"
)

if [ -f /scripts/run.args ]; then
  while IFS= read -r -d '' arg; do
    [ -n "$arg" ] && ARGS+=("$arg")
  done < <(xargs -a /scripts/run.args -r printf '%s\0')
fi

if ! printf '%s\n' "${ARGS[@]}" | grep -q -- '--test-suite'; then
  ARGS+=("--test-suite" "community-vs")
fi

resolve_spytest_bin() {
  local default_candidates=(
    "/repo/bin/spytest"
    "/repo/spytest/bin/spytest"
    "/repo/sonic-mgmt/spytest/bin/spytest"
  )

  if [ -n "${REPO:-}" ]; then
    default_candidates+=("$REPO/bin/spytest" "$REPO/spytest/bin/spytest")
  fi

  if [ -n "${SHARE:-}" ]; then
    default_candidates+=(
      "$SHARE/bin/spytest"
      "$SHARE/spytest/bin/spytest"
      "$SHARE/sonic-mgmt/spytest/bin/spytest"
      "$SHARE/images/sonic-mgmt/spytest/bin/spytest"
      "$SHARE/images/vsnet/sonic-mgmt/spytest/bin/spytest"
    )
  fi

  local share_mount_src=""
  if [ -n "${SHARE:-}" ]; then
    share_mount_src=$(awk -v target="$SHARE" '$2==target {print $1}' /proc/self/mounts | head -n 1)
  fi

  local try_path
  for try_path in "${default_candidates[@]}"; do
    if [ -x "$try_path" ]; then
      printf '%s' "$try_path"
      return 0
    fi

    if [ -n "$share_mount_src" ] && [[ "$try_path" == "$share_mount_src"* ]]; then
      local remapped="$SHARE${try_path#$share_mount_src}"
      if [ -x "$remapped" ]; then
        printf '%s' "$remapped"
        return 0
      fi
    fi
  done

  local search_roots=("/repo" "/data")
  if [ -n "${REPO:-}" ]; then
    search_roots+=("$REPO")
  fi
  if [ -n "${SHARE:-}" ]; then
    search_roots+=("$SHARE" "$SHARE/images" "$SHARE/images/vsnet")
  fi

  local root
  for root in "${search_roots[@]}"; do
    if [ -n "$root" ] && [ -d "$root" ]; then
      while IFS= read -r -d '' found; do
        if [ -x "$found" ]; then
          printf '%s' "$found"
          return 0
        fi

        if [ -n "$share_mount_src" ] && [[ "$found" == "$share_mount_src"* ]]; then
          local remap="$SHARE${found#$share_mount_src}"
          if [ -x "$remap" ]; then
            printf '%s' "$remap"
            return 0
          fi
        fi
      done < <(find "$root" -maxdepth 6 -type f -path '*/spytest/bin/spytest' -perm -u+x -print0 2>/dev/null)
    fi
  done

  if command -v spytest >/dev/null 2>&1; then
    command -v spytest
    return 0
  fi

  return 1
}

SPYTEST_BIN=$(resolve_spytest_bin)
if [ -z "$SPYTEST_BIN" ] || [ ! -x "$SPYTEST_BIN" ]; then
  echo "Unable to locate executable spytest binary" >&2
  exit 1
fi

echo "Using spytest binary: $SPYTEST_BIN"

"$SPYTEST_BIN" "${ARGS[@]}" "$@"
