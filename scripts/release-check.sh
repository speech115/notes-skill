#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

python3 -m py_compile "$REPO_DIR/scripts/notes-runner"

quick_log="$(mktemp)"
cleanup() {
  rm -f "$quick_log"
}
trap cleanup EXIT

if ! bash "$REPO_DIR/scripts/test-pipeline.sh" --quick 2>&1 | tee "$quick_log"; then
  if grep -Eq '\bSKIP\b' "$quick_log"; then
    echo "release-check failed: quick suite emitted SKIP" >&2
  fi
  exit 1
fi

if grep -Eq '\bSKIP\b' "$quick_log"; then
  echo "release-check failed: quick suite emitted SKIP" >&2
  grep -E '\bSKIP\b' "$quick_log" >&2 || true
  exit 1
fi
