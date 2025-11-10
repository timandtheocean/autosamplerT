#!/usr/bin/env python3
"""
test_all.py - Comprehensive regression test suite for AutosamplerT

Runs all major sampling scenarios to verify functionality after code changes.
Tests are organized by feature area: basic sampling, velocity layers, round-robin, etc.

Usage:
    python test_all.py              # Run all tests
    python test_all.py --quick      # Run quick tests only (faster)
    python test_all.py --group basic   # Run specific test group
    
Test groups:
    - basic: Single note and note range tests
    - velocity: Velocity layer tests
    - roundrobin: Round-robin layer tests
    - combined: Combined velocity + round-robin tests
    - audio: Audio configuration (mono/stereo)
    - metadata: WAV metadata verification
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import argparse


class TestResult:
    """Store results of a single test"""
    def __init__(self, name, group, passed=False, duration=0, error_msg=""):
        self.name = name
        self.group = group
        self.passed = passed
        self.duration = duration
        self.error_msg = error_msg


class TestRunner:
    """Execute AutosamplerT tests and track results"""
    
    def __init__(self, quick_mode=False):
        self.results = []
        self.quick_mode = quick_mode
        self.base_cmd = [sys.executable, "autosamplerT.py"]
        
    def run_test(self, name, group, args, expected_samples=None):
        """Run a single test command"""
        print(f"\n{'='*60}")
        print(f"Test: {name}")
        print(f"Group: {group}")
        print(f"{'='*60}")
        
        # Clean up output directory if multisample_name is specified
        name_idx = None
        for i, arg in enumerate(args):
            if arg == "--multisample_name" and i + 1 < len(args):
                name_idx = i + 1
                break
        
        if name_idx:
            output_dir = Path("output") / args[name_idx]
            if output_dir.exists():
                import shutil
                try:
                    shutil.rmtree(output_dir)
                    print(f"Cleaned up existing: {output_dir}")
                except Exception as e:
                    print(f"Warning: Could not clean {output_dir}: {e}")
        
        cmd = self.base_cmd + args
        print(f"Command: {' '.join(cmd)}")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            duration = time.time() - start_time
            
            # Check for success
            passed = result.returncode == 0
            
            if passed and expected_samples:
                # Verify expected number of WAV files were created
                # Extract multisample_name from args
                name_idx = None
                for i, arg in enumerate(args):
                    if arg == "--multisample_name" and i + 1 < len(args):
                        name_idx = i + 1
                        break
                
                if name_idx:
                    sample_dir = Path("output") / args[name_idx] / "samples"
                    if sample_dir.exists():
                        wav_count = len(list(sample_dir.glob("*.wav")))
                        if wav_count != expected_samples:
                            passed = False
                            error_msg = f"Expected {expected_samples} samples, found {wav_count}"
                        else:
                            error_msg = f"Created {wav_count} samples as expected"
                    else:
                        passed = False
                        error_msg = f"Sample directory not found: {sample_dir}"
                else:
                    error_msg = "Success"
            else:
                error_msg = "Success" if passed else result.stderr
            
            # Print output
            if result.stdout:
                print(result.stdout)
            if not passed and result.stderr:
                print(f"ERROR: {result.stderr}", file=sys.stderr)
            
            test_result = TestResult(name, group, passed, duration, error_msg)
            self.results.append(test_result)
            
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"\n{status} ({duration:.1f}s)")
            
            return passed
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            test_result = TestResult(name, group, False, duration, "Timeout (>5 min)")
            self.results.append(test_result)
            print(f"\n✗ FAILED - Timeout after {duration:.1f}s")
            return False
            
        except Exception as e:
            duration = time.time() - start_time
            test_result = TestResult(name, group, False, duration, str(e))
            self.results.append(test_result)
            print(f"\n✗ FAILED - Exception: {e}")
            return False
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        total_time = sum(r.duration for r in self.results)
        
        print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed}")
        print(f"Total time: {total_time:.1f}s")
        
        if failed > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  ✗ {result.name} ({result.group})")
                    if result.error_msg and result.error_msg != "Success":
                        print(f"    Error: {result.error_msg}")
        
        print("\nTest groups summary:")
        groups = {}
        for result in self.results:
            if result.group not in groups:
                groups[result.group] = {"total": 0, "passed": 0}
            groups[result.group]["total"] += 1
            if result.passed:
                groups[result.group]["passed"] += 1
        
        for group, stats in sorted(groups.items()):
            status = "✓" if stats["passed"] == stats["total"] else "✗"
            print(f"  {status} {group}: {stats['passed']}/{stats['total']}")
        
        print("="*60)
        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="AutosamplerT regression test suite")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--group", choices=["basic", "velocity", "roundrobin", "combined", "audio", "metadata", "all"],
                       default="all", help="Run specific test group")
    args = parser.parse_args()
    
    runner = TestRunner(quick_mode=args.quick)
    
    # Test configuration
    base_args = [
        "--hold_time", "1.0",
        "--release_time", "0.5", 
        "--pause_time", "0.5"
    ]
    
    # Group: Basic Sampling Tests
    if args.group in ["basic", "all"]:
        print("\n" + "="*60)
        print("GROUP: Basic Sampling")
        print("="*60)
        
        # Test 1: Single note (CLI, note name)
        runner.run_test(
            name="Single note C4 (note name)",
            group="basic",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--multisample_name", "test_single_C4_cli"
            ],
            expected_samples=1
        )
        
        # Test 2: Single note (CLI, MIDI number)
        runner.run_test(
            name="Single note 60 (MIDI number)",
            group="basic",
            args=base_args + [
                "--note_range_start", "60",
                "--note_range_end", "60",
                "--note_range_interval", "1",
                "--multisample_name", "test_single_60_cli"
            ],
            expected_samples=1
        )
        
        # Test 3: Four notes octave (CLI, note names)
        runner.run_test(
            name="Four notes C4-C5 octave (note names)",
            group="basic",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C5",
                "--note_range_interval", "12",
                "--multisample_name", "test_four_octave_cli_names"
            ],
            expected_samples=2  # C4, C5
        )
        
        # Test 4: Four notes (CLI, MIDI numbers)
        runner.run_test(
            name="Four notes 48-72 (MIDI numbers)",
            group="basic",
            args=base_args + [
                "--note_range_start", "48",
                "--note_range_end", "72",
                "--note_range_interval", "12",
                "--multisample_name", "test_four_octave_cli_midi"
            ],
            expected_samples=3  # 48, 60, 72
        )
        
        # Test 5: Script file (note name) - skip in quick mode
        if not runner.quick_mode and Path("conf/single_C4_script.yaml").exists():
            runner.run_test(
                name="Single note C4 (script)",
                group="basic",
                args=["--script", "conf/single_C4_script.yaml"],
                expected_samples=1
            )
        
        # Test 6: Script file (MIDI number) - skip in quick mode
        if not runner.quick_mode and Path("conf/single_60_script.yaml").exists():
            runner.run_test(
                name="Single note 60 (script)",
                group="basic",
                args=["--script", "conf/single_60_script.yaml"],
                expected_samples=1
            )
    
    # Group: Velocity Layer Tests
    if args.group in ["velocity", "all"]:
        print("\n" + "="*60)
        print("GROUP: Velocity Layers")
        print("="*60)
        
        # Test 7: Default velocity layers (4 layers, automatic distribution)
        runner.run_test(
            name="Velocity layers: 4 layers (default auto)",
            group="velocity",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--velocity_layers", "4",
                "--multisample_name", "test_vel_auto_default"
            ],
            expected_samples=4
        )
        
        # Test 8: Velocity layers with minimum
        runner.run_test(
            name="Velocity layers: 4 layers with minimum 45",
            group="velocity",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--velocity_layers", "4",
                "--velocity_minimum", "45",
                "--multisample_name", "test_vel_auto_min45"
            ],
            expected_samples=4
        )
        
        # Test 9: Custom velocity splits
        runner.run_test(
            name="Velocity layers: 3 layers custom splits",
            group="velocity",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--velocity_layers", "3",
                "--velocity_layers_split", "50,90",
                "--multisample_name", "test_vel_custom_splits"
            ],
            expected_samples=3
        )
        
        # Test 10: Single velocity layer
        runner.run_test(
            name="Velocity layers: 1 layer (velocity 100)",
            group="velocity",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--velocity_layers", "1",
                "--velocity_minimum", "100",
                "--multisample_name", "test_vel_single"
            ],
            expected_samples=1
        )
        
        # Test 11: Velocity + note range
        runner.run_test(
            name="Velocity layers: 3 layers × 4 notes",
            group="velocity",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C5",
                "--note_range_interval", "5",
                "--velocity_layers", "3",
                "--multisample_name", "test_vel_noterange"
            ],
            expected_samples=9  # 3 velocities × 3 notes (C4, F4, A#4)
        )
    
    # Group: Round-Robin Tests
    if args.group in ["roundrobin", "all"]:
        print("\n" + "="*60)
        print("GROUP: Round-Robin Layers")
        print("="*60)
        
        # Test 12: Basic round-robin
        runner.run_test(
            name="Round-robin: 2 layers, single note",
            group="roundrobin",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--roundrobin_layers", "2",
                "--multisample_name", "test_rr_basic"
            ],
            expected_samples=2
        )
        
        # Test 13: Round-robin with note range
        runner.run_test(
            name="Round-robin: 2 layers × 4 notes",
            group="roundrobin",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C5",
                "--note_range_interval", "12",
                "--roundrobin_layers", "2",
                "--multisample_name", "test_rr_noterange"
            ],
            expected_samples=4  # 2 RR × 2 notes (C4, C5)
        )
    
    # Group: Combined Tests (velocity + round-robin)
    if args.group in ["combined", "all"] and not args.quick:
        print("\n" + "="*60)
        print("GROUP: Combined Velocity + Round-Robin")
        print("="*60)
        
        # Test 14: Velocity + round-robin
        runner.run_test(
            name="Combined: 3 velocity × 2 RR, single note",
            group="combined",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--velocity_layers", "3",
                "--roundrobin_layers", "2",
                "--multisample_name", "test_vel_rr_combined"
            ],
            expected_samples=6  # 3 vel × 2 RR
        )
        
        # Test 15: Full combo (velocity + RR + note range)
        runner.run_test(
            name="Combined: 2 velocity × 2 RR × 3 notes",
            group="combined",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "E4",
                "--note_range_interval", "2",
                "--velocity_layers", "2",
                "--roundrobin_layers", "2",
                "--multisample_name", "test_full_combo"
            ],
            expected_samples=12  # 2 vel × 2 RR × 3 notes (C4, D4, E4)
        )
    
    # Group: Audio Configuration Tests
    if args.group in ["audio", "all"] and not args.quick:
        print("\n" + "="*60)
        print("GROUP: Audio Configuration")
        print("="*60)
        
        # Test 16: Mono left channel
        runner.run_test(
            name="Audio: Mono left channel",
            group="audio",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--mono_stereo", "mono",
                "--mono_channel", "0",
                "--multisample_name", "test_mono_left"
            ],
            expected_samples=1
        )
        
        # Test 17: Mono right channel
        runner.run_test(
            name="Audio: Mono right channel",
            group="audio",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--mono_stereo", "mono",
                "--mono_channel", "1",
                "--multisample_name", "test_mono_right"
            ],
            expected_samples=1
        )
        
        # Test 18: Stereo recording
        runner.run_test(
            name="Audio: Stereo recording",
            group="audio",
            args=base_args + [
                "--note_range_start", "C4",
                "--note_range_end", "C4",
                "--note_range_interval", "1",
                "--mono_stereo", "stereo",
                "--multisample_name", "test_stereo"
            ],
            expected_samples=1
        )
    
    # Group: Metadata Verification
    if args.group in ["metadata", "all"] and not args.quick:
        print("\n" + "="*60)
        print("GROUP: WAV Metadata Verification")
        print("="*60)
        
        # Test 16: Verify WAV metadata format
        test_dir = Path("output/test_single_C4_cli/samples")
        if test_dir.exists():
            wav_files = list(test_dir.glob("*.wav"))
            if wav_files:
                print(f"\nVerifying WAV metadata for: {wav_files[0].name}")
                verify_cmd = [sys.executable, "verify_wav_metadata.py", str(wav_files[0])]
                try:
                    result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and "Note Chunk Found" in result.stdout:
                        print(result.stdout)
                        runner.results.append(TestResult("WAV metadata format", "metadata", True, 0, "3-byte format verified"))
                        print("✓ PASSED - WAV metadata verified")
                    else:
                        print(result.stdout)
                        print(result.stderr)
                        runner.results.append(TestResult("WAV metadata format", "metadata", False, 0, "Metadata verification failed"))
                        print("✗ FAILED - WAV metadata verification")
                except Exception as e:
                    runner.results.append(TestResult("WAV metadata format", "metadata", False, 0, str(e)))
                    print(f"✗ FAILED - Exception: {e}")
            else:
                print("⊘ SKIPPED - No WAV files found")
                runner.results.append(TestResult("WAV metadata format", "metadata", False, 0, "No WAV files to verify"))
        else:
            print("⊘ SKIPPED - Test output directory not found")
            runner.results.append(TestResult("WAV metadata format", "metadata", False, 0, "No test samples found"))
    
    # Print summary and exit with appropriate code
    success = runner.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
