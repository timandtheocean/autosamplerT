"""
Sweep curve implementations for wavetable creation.

Provides various mathematical curves for parameter sweeping.
"""

import math
import numpy as np
from typing import List


class SweepCurves:
    """Mathematical curves for parameter sweeping during wavetable creation."""
    
    @staticmethod
    def linear(min_val: int, max_val: int, steps: int) -> List[int]:
        """
        Linear sweep curve.
        
        Args:
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            steps: Number of steps in sweep
            
        Returns:
            List of parameter values
        """
        if steps <= 1:
            return [min_val]
            
        values = []
        for i in range(steps):
            progress = i / (steps - 1)
            value = min_val + (max_val - min_val) * progress
            values.append(int(round(value)))
            
        return values
    
    @staticmethod
    def logarithmic(min_val: int, max_val: int, steps: int) -> List[int]:
        """
        Logarithmic sweep curve.
        
        Args:
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            steps: Number of steps in sweep
            
        Returns:
            List of parameter values
        """
        if steps <= 1:
            return [min_val]
            
        # Handle zero/negative values by adding offset
        offset = 1 if min_val <= 0 else 0
        adj_min = min_val + offset
        adj_max = max_val + offset
        
        if adj_min <= 0 or adj_max <= 0:
            # Fallback to linear if logarithmic isn't possible
            return SweepCurves.linear(min_val, max_val, steps)
        
        values = []
        log_min = math.log(adj_min)
        log_max = math.log(adj_max)
        
        for i in range(steps):
            progress = i / (steps - 1)
            log_value = log_min + (log_max - log_min) * progress
            value = math.exp(log_value) - offset
            values.append(int(round(value)))
            
        return values
    
    @staticmethod
    def exponential(min_val: int, max_val: int, steps: int) -> List[int]:
        """
        Exponential sweep curve.
        
        Args:
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            steps: Number of steps in sweep
            
        Returns:
            List of parameter values
        """
        if steps <= 1:
            return [min_val]
            
        values = []
        for i in range(steps):
            progress = i / (steps - 1)
            # Exponential curve: y = x^2
            exp_progress = progress ** 2
            value = min_val + (max_val - min_val) * exp_progress
            values.append(int(round(value)))
            
        return values
    
    @staticmethod
    def log_linear(min_val: int, max_val: int, steps: int) -> List[int]:
        """
        Log-Linear sweep curve (logarithmic first half, linear second half).
        
        Args:
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            steps: Number of steps in sweep
            
        Returns:
            List of parameter values
        """
        if steps <= 1:
            return [min_val]
            
        mid_point = steps // 2
        mid_val = min_val + (max_val - min_val) // 2
        
        # First half: logarithmic
        first_half = SweepCurves.logarithmic(min_val, mid_val, mid_point + 1)
        
        # Second half: linear (skip first point to avoid duplication)
        second_half = SweepCurves.linear(mid_val, max_val, steps - mid_point)
        if len(second_half) > 1:
            second_half = second_half[1:]  # Remove duplicate mid point
            
        return first_half + second_half
    
    @staticmethod
    def linear_log(min_val: int, max_val: int, steps: int) -> List[int]:
        """
        Linear-Log sweep curve (linear first half, logarithmic second half).
        
        Args:
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            steps: Number of steps in sweep
            
        Returns:
            List of parameter values
        """
        if steps <= 1:
            return [min_val]
            
        mid_point = steps // 2
        mid_val = min_val + (max_val - min_val) // 2
        
        # First half: linear
        first_half = SweepCurves.linear(min_val, mid_val, mid_point + 1)
        
        # Second half: logarithmic (skip first point to avoid duplication)
        second_half = SweepCurves.logarithmic(mid_val, max_val, steps - mid_point)
        if len(second_half) > 1:
            second_half = second_half[1:]  # Remove duplicate mid point
            
        return first_half + second_half
    
    @staticmethod
    def get_all_curves() -> List[str]:
        """Get list of all available curve types."""
        return ['lin', 'log', 'exp', 'log-lin', 'lin-log']
    
    @staticmethod
    def generate_curve(curve_type: str, min_val: int, max_val: int, steps: int) -> List[int]:
        """
        Generate sweep curve of specified type.
        
        Args:
            curve_type: Type of curve ('lin', 'log', 'exp', 'log-lin', 'lin-log')
            min_val: Minimum parameter value
            max_val: Maximum parameter value
            steps: Number of steps in sweep
            
        Returns:
            List of parameter values
            
        Raises:
            ValueError: If curve_type is not supported
        """
        curve_functions = {
            'lin': SweepCurves.linear,
            'log': SweepCurves.logarithmic,
            'exp': SweepCurves.exponential,
            'log-lin': SweepCurves.log_linear,
            'lin-log': SweepCurves.linear_log
        }
        
        if curve_type not in curve_functions:
            raise ValueError(f"Unsupported curve type: {curve_type}. Available: {list(curve_functions.keys())}")
            
        return curve_functions[curve_type](min_val, max_val, steps)
    
    @staticmethod
    def preview_curve(curve_type: str, min_val: int, max_val: int, steps: int = 20) -> None:
        """
        Print a preview of the curve values for debugging.
        
        Args:
            curve_type: Type of curve
            min_val: Minimum value
            max_val: Maximum value
            steps: Number of preview steps
        """
        values = SweepCurves.generate_curve(curve_type, min_val, max_val, steps)
        print(f"\\nCurve Preview - {curve_type.upper()} ({min_val} to {max_val}, {steps} steps):")
        for i, value in enumerate(values):
            progress = i / (steps - 1) * 100 if steps > 1 else 0
            print(f"  Step {i:2d}: {value:3d} ({progress:5.1f}%)")
        print()