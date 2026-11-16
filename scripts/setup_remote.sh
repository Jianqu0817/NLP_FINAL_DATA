#!/usr/bin/env bash
set -euo pipefail
cd /root/gpufree-data/nlp_final
export PATH=/opt/conda/bin:$PATH
export HF_HOME=/root/gpufree-data/hf_cache
python -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip freeze > environment.freeze.txt
.venv/bin/python -u scripts/download_model.py
