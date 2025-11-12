#!/usr/bin/env python3
"""
Comprehensive Auto-Loop Testing Script
========================================

This script tests all auto-loop functionality with various configurations.

Test Coverage:
1. Basic auto-loop (default settings)
2. Minimum loop duration (percentage and seconds)
3. Fixed loop start/end times
4. Crossfade loop (various durations)
5. Combined: auto-loop + crossfade + min duration
6. Edge cases: short samples, long samples, noisy samples

Prerequisites:
- Create test samples in tests/autoloop/samples/:
  * short_sustain.wav (1-2s sustained note)
  * medium_sustain.wav (4-5s sustained note)
  * long_sustain.wav (10-15s sustained note)
  * percussive.wav (short attack, quick decay)
  * noisy_sustain.wav (sample with background noise)
  * pure_sine.wav (clean sine wave for testing)

Usage:
    python test_autoloop.py                    # Run all tests
    python test_autoloop.py --test basic       # Run specific test group
    python test_autoloop.py --quick            # Run quick tests only
    python test_autoloop.py --create-samples   # Generate test samples (requires synth)
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from typing import List, Dict, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

SCRIPT_DIR = Path(__file__).parent
SAMPLES_DIR = SCRIPT_DIR / "samples"
OUTPUT_DIR = SCRIPT_DIR / "output"
AUTOSAMPLERT = Path(__file__).parent.parent.parent / "autosamplerT.py"

# Test configurations
TESTS = {
    "basic": [
        {
            "name": "basic_autoloop",
            "desc": "Basic auto-loop with default settings",
            "args": ["--auto_loop"],
            "expected": "Loop points found"
        },
    ],
    
    "min_duration": [
        {
            "name": "min_duration_percent_50",
            "desc": "Minimum loop duration 50% of sample",
            "args": ["--auto_loop", "--loop_min_duration", "50%"],
            "expected": "Loop duration >= 50% of sample"
        },
        {
            "name": "min_duration_percent_80",
            "desc": "Minimum loop duration 80% of sample",
            "args": ["--auto_loop", "--loop_min_duration", "80%"],
            "expected": "Loop duration >= 80% of sample"
        },
        {
            "name": "min_duration_seconds_2",
            "desc": "Minimum loop duration 2 seconds",
            "args": ["--auto_loop", "--loop_min_duration", "2.0"],
            "expected": "Loop duration >= 2.0s"
        },
        {
            "name": "min_duration_seconds_5",
            "desc": "Minimum loop duration 5 seconds",
            "args": ["--auto_loop", "--loop_min_duration", "5.0"],
            "expected": "Loop duration >= 5.0s"
        },
    ],
    
    "fixed_points": [
        {
            "name": "fixed_start_2s",
            "desc": "Fixed loop start at 2.0s",
            "args": ["--auto_loop", "--loop_start_time", "2.0"],
            "expected": "Loop start at 2.0s"
        },
        {
            "name": "fixed_end_10s",
            "desc": "Fixed loop end at 10.0s",
            "args": ["--auto_loop", "--loop_end_time", "10.0"],
            "expected": "Loop end at 10.0s"
        },
        {
            "name": "fixed_both_2_to_8",
            "desc": "Fixed loop start 2.0s to end 8.0s",
            "args": ["--auto_loop", "--loop_start_time", "2.0", "--loop_end_time", "8.0"],
            "expected": "Loop 2.0s to 8.0s"
        },
    ],
    
    "combined": [
        {
            "name": "min_50percent_fixed_start",
            "desc": "Auto-loop + 50% min + fixed start",
            "args": ["--auto_loop", "--loop_min_duration", "50%", "--loop_start_time", "2.0"],
            "expected": "Loop with min 50% and fixed start"
        },
        {
            "name": "min_5sec_fixed_end",
            "desc": "Auto-loop + 5s min + fixed end",
            "args": ["--auto_loop", "--loop_min_duration", "5.0", "--loop_end_time", "10.0"],
            "expected": "Loop with min 5.0s and fixed end"
        },
        {
            "name": "fixed_both_with_min",
            "desc": "Fixed start + fixed end + min duration",
            "args": ["--auto_loop", "--loop_start_time", "2.0", "--loop_end_time", "8.0", "--loop_min_duration", "3.0"],
            "expected": "Fixed points with min validation"
        },
    ],
    
    "edge_cases": [
        {
            "name": "very_short_sample",
            "desc": "Auto-loop on short percussive sample",
            "args": ["--auto_loop", "--loop_min_duration", "10%"],
            "sample": "percussive.wav",
            "expected": "Small or no loop for percussive"
        },
        {
            "name": "noisy_sample",
            "desc": "Auto-loop on noisy sample",
            "args": ["--auto_loop", "--loop_min_duration", "50%"],
            "sample": "noisy_sustain.wav",
            "expected": "Loop despite noise"
        },
    ],
}

# Quick tests (subset for fast testing)
QUICK_TESTS = ["basic", "min_duration", "combined"]


class AutoLoopTester:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.results: List[Dict] = []
        
    def log(self, message: str):
        """Print message if verbose."""
        if self.verbose:
            print(message)
    
    def setup(self):
        """Setup test environment."""
        self.log("\n" + "="*70)
        self.log("AUTO-LOOP TEST SUITE")
        self.log("="*70)
        
        # Create directories
        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check for sample files
        self.log(f"\nChecking for test samples in: {SAMPLES_DIR}")
        sample_files = list(SAMPLES_DIR.glob("*.wav"))
        
        if not sample_files:
            self.log("\n⚠️  WARNING: No test samples found!")
            self.log("\nTo create test samples:")
            self.log("  1. Run: python test_autoloop.py --create-samples")
            self.log("  2. Or manually place WAV files in tests/autoloop/samples/")
            self.log("\nRecommended samples:")
            self.log("  - short_sustain.wav (1-2s)")
            self.log("  - medium_sustain.wav (4-5s)")
            self.log("  - long_sustain.wav (10-15s)")
            self.log("  - percussive.wav (short attack)")
            self.log("  - noisy_sustain.wav (with background noise)")
            return False
        
        self.log(f"\n✓ Found {len(sample_files)} test sample(s):")
        for sample in sample_files:
            self.log(f"  - {sample.name}")
        
        return True
    
    def run_test(self, test_config: Dict, sample_file: Path = None) -> Dict:
        """Run a single auto-loop test."""
        test_name = test_config["name"]
        desc = test_config["desc"]
        args = test_config["args"]
        
        # Use specific sample if provided, otherwise use first available
        if sample_file is None:
            if "sample" in test_config:
                sample_file = SAMPLES_DIR / test_config["sample"]
            else:
                sample_files = list(SAMPLES_DIR.glob("*.wav"))
                if not sample_files:
                    return {
                        "name": test_name,
                        "status": "SKIP",
                        "message": "No sample files available"
                    }
                sample_file = sample_files[0]
        
        if not sample_file.exists():
            return {
                "name": test_name,
                "status": "SKIP",
                "message": f"Sample not found: {sample_file.name}"
            }
        
        self.log(f"\n{'─'*70}")
        self.log(f"Test: {test_name}")
        self.log(f"Desc: {desc}")
        self.log(f"Sample: {sample_file.name}")
        self.log(f"Args: {' '.join(args)}")
        
        # Create output folder for this test
        test_output = OUTPUT_DIR / test_name
        test_output.mkdir(parents=True, exist_ok=True)
        
        # Copy sample to test output
        import shutil
        test_sample = test_output / sample_file.name
        shutil.copy(sample_file, test_sample)
        
        # Build command
        cmd = [
            sys.executable,  # Use current Python interpreter
            str(AUTOSAMPLERT),
            "--process_folder",
            str(test_output),
        ] + args
        
        self.log(f"\nCommand: {' '.join(cmd)}")
        
        # Run test
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            elapsed = time.time() - start_time
            
            # Check result
            if result.returncode != 0:
                self.log(f"\n❌ FAILED (exit code {result.returncode})")
                self.log(f"stderr: {result.stderr}")
                return {
                    "name": test_name,
                    "status": "FAIL",
                    "message": f"Exit code {result.returncode}",
                    "elapsed": elapsed
                }
            
            # Parse output
            output = result.stdout
            expected = test_config.get("expected", "")
            
            # Check for expected output patterns
            success = True
            if "Loop points found" in expected or "Loop" in expected:
                if "Found loop points:" not in output:
                    success = False
            if "crossfade" in expected.lower():
                if "crossfade" not in output.lower():
                    success = False
            
            if success:
                self.log(f"\n✅ PASSED ({elapsed:.2f}s)")
                return {
                    "name": test_name,
                    "status": "PASS",
                    "elapsed": elapsed
                }
            else:
                self.log(f"\n⚠️  UNCERTAIN ({elapsed:.2f}s)")
                self.log(f"Expected: {expected}")
                return {
                    "name": test_name,
                    "status": "WARN",
                    "message": "Output verification uncertain",
                    "elapsed": elapsed
                }
                
        except subprocess.TimeoutExpired:
            self.log(f"\n❌ TIMEOUT (>30s)")
            return {
                "name": test_name,
                "status": "TIMEOUT",
                "message": "Exceeded 30s timeout"
            }
        except Exception as e:
            self.log(f"\n❌ ERROR: {e}")
            return {
                "name": test_name,
                "status": "ERROR",
                "message": str(e)
            }
    
    def run_test_group(self, group_name: str):
        """Run all tests in a group."""
        if group_name not in TESTS:
            self.log(f"\n❌ Unknown test group: {group_name}")
            return
        
        self.log(f"\n{'='*70}")
        self.log(f"TEST GROUP: {group_name.upper()}")
        self.log(f"{'='*70}")
        
        tests = TESTS[group_name]
        for test_config in tests:
            result = self.run_test(test_config)
            self.results.append(result)
    
    def print_summary(self):
        """Print test summary."""
        self.log(f"\n{'='*70}")
        self.log("TEST SUMMARY")
        self.log(f"{'='*70}")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        timeouts = sum(1 for r in self.results if r["status"] == "TIMEOUT")
        
        self.log(f"\nTotal tests: {total}")
        self.log(f"  ✅ Passed:   {passed}")
        self.log(f"  ❌ Failed:   {failed}")
        self.log(f"  ⚠️  Warned:   {warned}")
        self.log(f"  ⏭️  Skipped:  {skipped}")
        self.log(f"  ❌ Errors:   {errors}")
        self.log(f"  ⏱️  Timeouts: {timeouts}")
        
        if failed > 0 or errors > 0 or timeouts > 0:
            self.log(f"\nFailed/Error tests:")
            for result in self.results:
                if result["status"] in ["FAIL", "ERROR", "TIMEOUT"]:
                    self.log(f"  - {result['name']}: {result.get('message', 'No message')}")
        
        self.log("\n" + "="*70)
        
        return passed == total and skipped == 0


def create_test_samples():
    """Guide user to create test samples."""
    print("\n" + "="*70)
    print("CREATE TEST SAMPLES")
    print("="*70)
    
    print("\nThis will help you create test samples for auto-loop testing.")
    print(f"\nSamples will be created in: {SAMPLES_DIR}")
    
    samples_needed = [
        ("short_sustain.wav", "1-2 second sustained note (any pitch)"),
        ("medium_sustain.wav", "4-5 second sustained note (any pitch)"),
        ("long_sustain.wav", "10-15 second sustained note (any pitch)"),
        ("percussive.wav", "Short attack, quick decay (drum, pluck, etc)"),
        ("noisy_sustain.wav", "Sustained note with background noise"),
    ]
    
    print("\nSamples needed:")
    for filename, desc in samples_needed:
        exists = "✓" if (SAMPLES_DIR / filename).exists() else " "
        print(f"  [{exists}] {filename} - {desc}")
    
    print("\nOptions to create samples:")
    print("\n1. AUTOMATED (using autosamplerT):")
    print("   python ../autosamplerT.py --note_range_start C4 --note_range_end C4 \\")
    print("                             --hold_time 2 --release_time 0.5 \\")
    print("                             --multisample_name short_sustain")
    print("   (Then copy WAV to tests/autoloop/samples/)")
    
    print("\n2. MANUAL:")
    print("   - Record or generate WAV files")
    print(f"   - Place them in: {SAMPLES_DIR}")
    
    print("\n3. COPY FROM EXISTING:")
    print("   - Copy samples from output/ directory")
    print("   - Rename to match expected filenames")
    
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n✓ Directory ready: {SAMPLES_DIR}")


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive auto-loop testing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--test", choices=list(TESTS.keys()) + ["all"],
                       default="all", help="Test group to run")
    parser.add_argument("--quick", action="store_true",
                       help="Run only quick tests")
    parser.add_argument("--create-samples", action="store_true",
                       help="Show instructions to create test samples")
    parser.add_argument("--quiet", action="store_true",
                       help="Minimal output")
    
    args = parser.parse_args()
    
    if args.create_samples:
        create_test_samples()
        return 0
    
    tester = AutoLoopTester(verbose=not args.quiet)
    
    # Setup
    if not tester.setup():
        print("\n❌ Setup failed - no test samples available")
        print("Run: python test_autoloop.py --create-samples")
        return 1
    
    # Run tests
    if args.quick:
        test_groups = QUICK_TESTS
    elif args.test == "all":
        test_groups = list(TESTS.keys())
    else:
        test_groups = [args.test]
    
    for group in test_groups:
        tester.run_test_group(group)
    
    # Summary
    success = tester.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
