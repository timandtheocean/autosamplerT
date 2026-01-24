"""
Postprocessing operations for AutosamplerT
Each operation is isolated and applied after sampling is complete.
"""

from .gain import apply_gain
from .normalize import normalize_sample, normalize_patch
from .trim_silence import trim_silence
from .dc_offset import remove_dc_offset
from .auto_loop import find_loop_points
from .bitdepth import convert_bitdepth

__all__ = [
    'apply_gain',
    'normalize_sample',
    'normalize_patch',
    'trim_silence',
    'remove_dc_offset',
    'find_loop_points',
    'convert_bitdepth'
]
