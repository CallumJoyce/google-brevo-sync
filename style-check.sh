#!/usr/bin/env bash

set -eufo pipefail

script_dir="$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)"

. "${script_dir}/env/bin/activate"

flake8 --max-line-length 120 "${script_dir}/google_brevo_sync.py"
