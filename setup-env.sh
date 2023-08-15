#!/usr/bin/env bash

set -eufo pipefail

script_dir="$(cd $(dirname "${BASH_SOURCE[0]}") && pwd)"

python3 -m venv "${script_dir}/env"
. "${script_dir}/env/bin/activate"

pip install -r "${script_dir}/requirements.txt"
