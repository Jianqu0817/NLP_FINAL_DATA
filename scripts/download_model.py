import json
import os
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download

root = Path(__file__).resolve().parents[1]
model_id = 'Qwen/Qwen3-4B-Instruct-2507'
info = HfApi().model_info(model_id)
revision = info.sha
path = snapshot_download(model_id, revision=revision,
                         allow_patterns=['*.json', '*.safetensors', '*.model', '*.txt', '*.jinja'],
                         max_workers=4)
record = {'model_id': model_id, 'revision': revision, 'local_path': path,
          'endpoint': os.getenv('HF_ENDPOINT', 'https://huggingface.co')}
(root / 'model_manifest.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record), flush=True)
