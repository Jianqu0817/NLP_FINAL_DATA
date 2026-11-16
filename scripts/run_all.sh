#!/usr/bin/env bash
set -euo pipefail
cd /root/gpufree-data/nlp_final
export HF_HOME=/root/gpufree-data/hf_cache
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
export PYTHONUNBUFFERED=1
.venv/bin/python -u scripts/pilot_queue.py
