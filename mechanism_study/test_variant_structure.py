"""CPU structural tests; no model downloads or transformers dependency."""
import ast
import copy
from pathlib import Path

import torch
from torch import nn
from torch.utils.checkpoint import checkpoint

from train_variant import AffineResidual, install_post_attention, post_block


class TinyDecoder(nn.Module):
    """Pinned Qwen3 residual ordering, with small frozen attention/MLP stand-ins."""
    def __init__(self, dtype, explicit=False):
        super().__init__()
        self.input_layernorm = nn.LayerNorm(8, dtype=dtype)
        self.attention = nn.Linear(8, 8, dtype=dtype)
        self.post_attention_layernorm = nn.LayerNorm(8, dtype=dtype)
        self.mlp = nn.Linear(8, 8, dtype=dtype)
        for p in self.parameters():
            p.requires_grad_(False)
        self.task_adapter = AffineResidual(8, 3)
        self.explicit = explicit

    def forward(self, h):
        residual = h
        h = self.attention(self.input_layernorm(h))
        h = residual + h
        if self.explicit:
            h = self.task_adapter(h)
        residual = h
        h = self.post_attention_layernorm(h)
        h = self.mlp(h)
        return residual + h


def test_initialization():
    source = Path(__file__).resolve().parents[1] / 'scripts' / 'experiment.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    definition = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Bottleneck')
    namespace = {'torch': torch, 'nn': nn}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(source), 'exec'), namespace)
    for width in (16, 64):
        torch.manual_seed(42)
        original = namespace['Bottleneck'](8, width)
        torch.manual_seed(42)
        affine = AffineResidual(8, width)
        assert all(torch.equal(a, b) for a, b in zip(original.parameters(), affine.parameters()))
        h = torch.randn(2, 5, 8).bfloat16()
        assert torch.equal(affine(h), h)
    block = nn.Identity()
    block.add_module('task_adapter', AffineResidual(8, 3))
    block.register_forward_hook(post_block)
    h = torch.randn(2, 5, 8)
    assert torch.equal(block(h), h)


def test_e(dtype, recompute):
    torch.manual_seed(117)
    hooked = TinyDecoder(dtype)
    # Test nonzero trained weights, not only the identity initialization.
    nn.init.normal_(hooked.task_adapter.up.weight, std=0.2)
    nn.init.normal_(hooked.task_adapter.up.bias, std=0.1)
    explicit = copy.deepcopy(hooked)
    explicit.explicit = True
    install_post_attention(hooked)
    h1 = torch.randn(2, 5, 8, dtype=dtype, requires_grad=True)
    h2 = h1.detach().clone().requires_grad_(True)
    call = lambda model, h: checkpoint(model, h, use_reentrant=False) if recompute else model(h)
    y1, y2 = call(hooked, h1), call(explicit, h2)
    assert y1.dtype == dtype
    torch.testing.assert_close(y1, y2, rtol=0, atol=0)
    y1.float().square().sum().backward()
    y2.float().square().sum().backward()
    torch.testing.assert_close(h1.grad, h2.grad, rtol=0, atol=0)
    for (name, p), (other_name, q) in zip(hooked.named_parameters(), explicit.named_parameters()):
        assert name == other_name
        if p.requires_grad:
            assert p.grad is not None and torch.isfinite(p.grad).all()
            torch.testing.assert_close(p.grad, q.grad, rtol=0, atol=0)
        else:
            assert p.grad is None and q.grad is None
    # Repeated inference also works without retaining an autograd graph.
    with torch.inference_mode():
        torch.testing.assert_close(hooked(h1.detach()), explicit(h2.detach()), rtol=0, atol=0)


if __name__ == '__main__':
    test_initialization()
    for dtype in (torch.float32, torch.bfloat16):
        for recompute in (False, True):
            test_e(dtype, recompute)
    print('PASS: matched initialization; zero-up identity; E exact output/input/parameter gradients in FP32 and BF16, with/without non-reentrant checkpoint; frozen gradients; inference')
