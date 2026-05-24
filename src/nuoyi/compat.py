"""
NuoYi compatibility layer for transformers 5.x + surya 0.17.x.
Applied at import time before any marker/surya imports.
"""
import sys
import types as _types

# Ensure site-packages surya has priority over any local clones
_site = __import__('site').getsitepackages()[0]
if _site not in sys.path:
    sys.path.insert(0, _site)

import torch
import torch.nn as nn
import torch.nn.functional as F


def apply():
    """Apply all compatibility patches."""
    _patch_onnx()
    _patch_pytorch_utils()
    _patch_tokenization_utils()
    _patch_rope()
    _patch_tied_weights()
    _patch_surya_tie_weights()
    _patch_encoder_meta()


# Patch 0: Fake transformers.onnx (removed in 5.x) + Nougat PretrainedConfig fix
def _patch_onnx():
    try:
        import transformers.onnx
    except ImportError:
        m = _types.ModuleType("transformers.onnx")
        class _OnnxConfig:
            task = "default"
            @property
            def inputs(self):
                from collections import OrderedDict
                return OrderedDict()
        m.OnnxConfig = _OnnxConfig
        sys.modules["transformers.onnx"] = m

    # Fix Nougat: PretrainedConfig moved from modeling_utils to configuration_utils
    try:
        from transformers.configuration_utils import PretrainedConfig
        import transformers.modeling_utils as _mu
        if not hasattr(_mu, "PretrainedConfig"):
            _mu.PretrainedConfig = PretrainedConfig
    except Exception:
        pass


# Patch 1: find_pruneable_heads_and_indices (removed in 5.x)
def _patch_pytorch_utils():
    try:
        from transformers.pytorch_utils import find_pruneable_heads_and_indices
        return
    except ImportError:
        pass
    import transformers.pytorch_utils as _pu
    def _f(heads, n_heads, head_size, layer_heads=None):
        layer_heads = set(heads) if layer_heads is None else layer_heads
        return set(range(n_heads)) - layer_heads, torch.ones(n_heads * head_size)
    _pu.find_pruneable_heads_and_indices = _f


# Patch 2: _is_control, _is_punctuation, _is_whitespace (moved in 5.x)
def _patch_tokenization_utils():
    try:
        from transformers.tokenization_utils import _is_control
        return
    except ImportError:
        pass
    import unicodedata
    import transformers.tokenization_utils as _tu
    _tu._is_control = lambda c: c not in (' ', '\t', '\n', '\r') and unicodedata.category(c).startswith('C')
    _tu._is_punctuation = lambda c: unicodedata.category(c).startswith(('P', 'S'))
    _tu._is_whitespace = lambda c: c in (' ', '\t', '\n', '\r') or unicodedata.category(c) == 'Zs'


# Patch 3: ROPE_INIT_FUNCTIONS['default']
def _patch_rope():
    try:
        from transformers.modeling_rope_utils import ROPE_INIT_FUNCTIONS
        if "default" not in ROPE_INIT_FUNCTIONS and "linear" in ROPE_INIT_FUNCTIONS:
            ROPE_INIT_FUNCTIONS["default"] = ROPE_INIT_FUNCTIONS["linear"]
    except ImportError:
        pass


# Patch 4: all_tied_weights_keys + nn.Module.__setattr__ + pad_token_id
def _patch_tied_weights():
    from transformers import PreTrainedModel
    if not hasattr(PreTrainedModel, "all_tied_weights_keys"):
        PreTrainedModel.all_tied_weights_keys = {}
    _orig = nn.Module.__setattr__
    def _fixed(self, name, value):
        if name == "all_tied_weights_keys" and value is None:
            value = {}
        _orig(self, name, value)
    nn.Module.__setattr__ = _fixed

    try:
        from surya.common.surya.decoder.config import SuryaDecoderConfig
        if not hasattr(SuryaDecoderConfig, "pad_token_id") or SuryaDecoderConfig.pad_token_id is None:
            _orig_init = SuryaDecoderConfig.__init__
            def _new_init(self, *a, **kw):
                _orig_init(self, *a, **kw)
                self.pad_token_id = getattr(self, 'pad_token_id', None) or 0
            SuryaDecoderConfig.__init__ = _new_init
    except ImportError:
        pass


# Patch 5: surya SuryaModel._tie_or_clone_weights + tie_weights(**kwargs)
def _patch_surya_tie_weights():
    try:
        from surya.common.surya import SuryaModel
    except ImportError:
        return
    if not hasattr(SuryaModel, "_tie_or_clone_weights"):
        def _tie_or_clone_weights(self, out, inp):
            out.weight = inp.weight
            if hasattr(out, "bias") and out.bias is not None:
                out.bias.data = F.pad(out.bias.data, (0, out.weight.shape[0] - out.bias.shape[0]), "constant", 0)
        SuryaModel._tie_or_clone_weights = _tie_or_clone_weights
    _orig = SuryaModel.tie_weights
    def _tie_weights(self, **kw):
        return _orig(self)
    SuryaModel.tie_weights = _tie_weights


# Patch 6: fix meta device inv_freq in surya encoder
def _patch_encoder_meta():
    try:
        from surya.common.surya.encoder import Qwen2RotaryEmbedding
    except ImportError:
        return
    _orig = Qwen2RotaryEmbedding.forward
    def _forward(self, seqlen):
        inv = self.inv_freq
        if inv.device.type == "meta":
            dim = inv.shape[-1] * 2
            theta = getattr(self, "theta", 10000.0)
            inv = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=torch.float, device="cpu") / dim))
        seq = torch.arange(seqlen, device=inv.device, dtype=inv.dtype)
        return torch.outer(seq, inv)
    Qwen2RotaryEmbedding.forward = _forward
