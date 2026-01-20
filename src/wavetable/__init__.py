"""
Wavetable Creation Module for AutosamplerT

Provides functionality for creating wavetables by sampling hardware synthesizers
while sweeping control parameters through various curve types.
"""

from .midi_learn import MIDILearn
from .wave_calculator import WaveCalculator
from .sweep_curves import SweepCurves
from .wavetable_sampler import WavetableSampler

__all__ = ['MIDILearn', 'WaveCalculator', 'SweepCurves', 'WavetableSampler']