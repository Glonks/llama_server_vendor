#!/bin/bash
# Usage: scripts/update_llama_cpp.sh b12000
set -euo pipefail
tag="$1"
cd "$(dirname "$0")/.."
curl -fL -o "vendor/llama.cpp-${tag}.tar.gz" \
  "https://github.com/ggml-org/llama.cpp/archive/refs/tags/${tag}.tar.gz"
find vendor -name 'llama.cpp-*.tar.gz' ! -name "llama.cpp-${tag}.tar.gz" -delete
sed -i "s/^set(LLAMA_CPP_TAG \"[^\"]*\")/set(LLAMA_CPP_TAG \"${tag}\")/" CMakeLists.txt
grep '^set(LLAMA_CPP_TAG' CMakeLists.txt
