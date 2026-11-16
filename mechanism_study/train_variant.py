"""Matched affine adapter ablations; reuse the frozen pilot's training loop.

B: width 64, post-block; D: width 16, post-block; E: width 16,
post-attention residual (before MLP). All three use Identity, not SiLU.
"""
import argparse
import json
from pathlib import Path
import random
import sys
from types import SimpleNamespace

import torch
from torch import nn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
WIDTHS = {'A': 64, 'B': 64, 'D': 16, 'E': 16}


def experiment():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import experiment as exp
    return exp


def seed_all():
    import numpy as np
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    torch.set_num_threads(8)


class AffineResidual(nn.Module):
    def __init__(self, hidden, width):
        super().__init__()
        # Identical constructor RNG consumption and initialization to pilot A.
        self.down = nn.Linear(hidden, width)
        self.up = nn.Linear(width, hidden)
        nn.init.normal_(self.down.weight, std=0.02)
        nn.init.zeros_(self.down.bias)
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, h):
        return (h.float() + self.up(self.down(h.float()))).to(h.dtype)


def post_block(module, inputs, output):
    if isinstance(output, tuple):
        return (module.task_adapter(output[0]),) + output[1:]
    return module.task_adapter(output)


def install_post_attention(layer):
    # Qwen3DecoderLayer stores `residual = hidden_states` immediately before
    # calling this norm. Returning a replacement input alone misses that residual.
    # Updating the shared tensor updates BOTH paths. Clone is essential: the
    # adapter's linear backward saves its input, which must not then be mutated.
    def update_both_paths(norm, inputs):
        h = inputs[0]
        adapted = layer.task_adapter(h.clone())
        h.copy_(adapted)
    return layer.post_attention_layernorm.register_forward_pre_hook(update_both_paths)


def build_for_eval(variant, checkpoint=None):
    """Return (model, tokenizer, manifest), with exact trainable checkpoint keys.

    A loads the historical SiLU width-64 adapter. B/D/E are affine variants.
    Caller supplies checkpoint explicitly; None means zero-up initialization.
    """
    variant = variant.upper()
    if variant not in WIDTHS:
        raise ValueError(variant)
    exp = experiment()
    if variant == 'A':
        return exp.build(SimpleNamespace(method='adapter', width=64, checkpoint=checkpoint))
    model, tokenizer, manifest = exp.build(SimpleNamespace(method='base', checkpoint=None))
    if model.config.hidden_size != 2560 or len(model.model.layers) != 36:
        raise ValueError('expected original Qwen3-4B architecture: hidden=2560, layers=36')
    for layer in model.model.layers:
        layer.add_module('task_adapter', AffineResidual(model.config.hidden_size, WIDTHS[variant]).to(device='cuda', dtype=torch.float32))
        if variant == 'E':
            install_post_attention(layer)
        else:
            layer.register_forward_hook(post_block)
    trainable = {n: p for n, p in model.named_parameters() if p.requires_grad}
    expected = 36 * (2 * 2560 * WIDTHS[variant] + 2560 + WIDTHS[variant])
    if sum(p.numel() for p in trainable.values()) != expected:
        raise ValueError('trainable parameter budget mismatch')
    if any('.task_adapter.' not in n for n in trainable):
        raise ValueError('backbone parameter unexpectedly trainable')
    if checkpoint is not None:
        state = torch.load(checkpoint, map_location='cpu', weights_only=True)
        if set(state) != set(trainable):
            raise ValueError('checkpoint must contain exactly all trainable parameters')
        if any(state[n].shape != p.shape or state[n].dtype != p.dtype for n, p in trainable.items()):
            raise ValueError('checkpoint shape/dtype mismatch')
        model.load_state_dict(state, strict=False)
    return model, tokenizer, manifest


def smoke(model, tokenizer, variant):
    exp = experiment()
    model.train()
    model.config.use_cache = False
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    ids, labels = exp.encoded_train(tokenizer, exp.read_rows('train', 1), 4096)[0]
    ids = torch.tensor([ids], device='cuda')
    labels = torch.tensor([labels], device='cuda')
    out = model(input_ids=ids, attention_mask=torch.ones_like(ids), labels=labels, use_cache=False)
    if not torch.isfinite(out.loss):
        raise FloatingPointError('smoke loss nonfinite')
    out.loss.backward()
    gradients = {}
    for name, p in model.named_parameters():
        if p.requires_grad:
            if p.dtype != torch.float32 or p.grad is None or not torch.isfinite(p.grad).all():
                raise RuntimeError('invalid adapter dtype/gradient: ' + name)
            gradients[name] = float(p.grad.norm())
        elif p.grad is not None:
            raise RuntimeError('frozen backbone received gradient: ' + name)
    # Zero-up initialization makes down gradients zero on the first step.
    if not any(value > 0 for name, value in gradients.items() if '.up.' in name):
        raise RuntimeError('zero up-projection gradients')
    model.zero_grad(set_to_none=True)
    result = dict(variant=variant, status='smoke_passed', loss=float(out.loss.detach()),
                  gradient_checkpointing=True, adapter_gradients=gradients)
    (HERE / 'preflight').mkdir(exist_ok=True)
    (HERE / 'preflight' / f'{variant}.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('variant', choices=['B', 'D', 'E'])
    parser.add_argument('--smoke', action='store_true')
    cli = parser.parse_args()
    seed_all()
    outdir = HERE / 'runs' / cli.variant
    if not cli.smoke and outdir.exists() and any(outdir.iterdir()):
        raise FileExistsError(f'refusing to overwrite nonempty training directory: {outdir}')
    model, tokenizer, manifest = build_for_eval(cli.variant)
    if cli.smoke:
        print(json.dumps(smoke(model, tokenizer, cli.variant)), flush=True)
        return
    # Exactly the pilot's settings, sample order, optimizer, scheduler,
    # validation population, lexicographic checkpoint rule and frozen probes.
    args = SimpleNamespace(method='adapter', width=WIDTHS[cli.variant], checkpoint=None,
                           lr=1e-4, epochs=3, seed=42, accum=16, limit=0,
                           eval_limit=0, eval_batch=16, max_length=4096,
                           max_new_tokens=2048)
    outdir.mkdir(parents=True, exist_ok=True)
    config = dict(variant=cli.variant, activation='identity', site='post_attention_residual' if cli.variant == 'E' else 'post_block',
                  model_manifest=manifest, torch=torch.__version__, gpu=torch.cuda.get_device_name(),
                  system_prompt=experiment().SYSTEM,
                  data_manifest=json.loads((ROOT / 'data' / 'manifest.json').read_text(encoding='utf-8')),
                  trainable_dtypes=sorted({str(p.dtype) for p in model.parameters() if p.requires_grad}),
                  training_loop='scripts/experiment.py:train', **vars(args))
    (outdir / 'train_config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        result = experiment().train(model, tokenizer, args, outdir)
    except Exception as exc:
        status_path = outdir / 'status.json'
        status = json.loads(status_path.read_text()) if status_path.exists() else {}
        status.update(status='failed', error=str(exc))
        status_path.write_text(json.dumps(status, indent=2), encoding='utf-8')
        raise
    print(json.dumps({'event': 'complete', 'variant': cli.variant, 'result': result}), flush=True)


if __name__ == '__main__':
    main()
