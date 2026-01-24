#!/usr/bin/env python3
"""
DEBUG: Wavetable Recording Diagnostics

This script diagnoses why wavetable recording fails while main sampler works.
Run this to identify exactly where the failure occurs.
"""

import os
# CRITICAL: Enable ASIO before importing sounddevice
os.environ["SD_ENABLE_ASIO"] = "1"

import sys
import time
import traceback
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import sounddevice as sd
import yaml


def print_header(title):
    """Print section header."""
    print()
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_success(msg):
    """Print success message."""
    print(f"  [OK] {msg}")


def print_fail(msg):
    """Print failure message."""
    print(f"  [FAIL] {msg}")


def print_info(msg):
    """Print info message."""
    print(f"  [INFO] {msg}")


def load_config():
    """Load audio configuration from autosamplerT_config.yaml."""
    config_path = Path(__file__).parent.parent / "conf" / "autosamplerT_config.yaml"
    if not config_path.exists():
        print_fail(f"Config file not found: {config_path}")
        return None
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def test_1_environment():
    """Test 1: Verify SD_ENABLE_ASIO is set in all modules."""
    print_header("TEST 1: Environment Variables & Imports")
    
    results = {}
    
    # Check environment
    asio_env = os.environ.get("SD_ENABLE_ASIO", None)
    if asio_env == "1":
        print_success(f"SD_ENABLE_ASIO={asio_env}")
        results['env'] = True
    else:
        print_fail(f"SD_ENABLE_ASIO not set or wrong value: {asio_env}")
        results['env'] = False
    
    # Check host APIs
    host_apis = sd.query_hostapis()
    asio_found = False
    for i, api in enumerate(host_apis):
        if 'ASIO' in api['name']:
            print_success(f"ASIO Host API found at index {i}: {api['name']}")
            asio_found = True
    
    if not asio_found:
        print_fail("No ASIO Host API found - SD_ENABLE_ASIO may not be working")
    
    results['asio_api'] = asio_found
    
    # Test module imports
    modules_to_test = [
        "src.sampling.audio_engine",
        "src.realtime_monitor",
        "src.sampling.sample_processor",
        "src.sampler",
    ]
    
    print_info("Checking SD_ENABLE_ASIO in module source files...")
    for module_path in modules_to_test:
        # Convert module path to file path
        file_path = Path(__file__).parent.parent / (module_path.replace(".", "/") + ".py")
        if file_path.exists():
            with open(file_path, 'r') as f:
                content = f.read(2000)  # Read first 2000 chars
            
            if 'SD_ENABLE_ASIO' in content:
                print_success(f"{module_path}: Has SD_ENABLE_ASIO")
            else:
                print_fail(f"{module_path}: MISSING SD_ENABLE_ASIO")
        else:
            print_info(f"{module_path}: File not found at {file_path}")
    
    return results


def test_2_config():
    """Test 2: Check configuration."""
    print_header("TEST 2: Configuration Check")
    
    config = load_config()
    if not config:
        return {'config_loaded': False}
    
    results = {'config_loaded': True}
    
    audio = config.get('audio_interface', {})
    print_info(f"Input device index: {audio.get('input_device_index', 'NOT SET')}")
    print_info(f"Output device index: {audio.get('output_device_index', 'NOT SET')}")
    print_info(f"Input channels: {audio.get('input_channels', 'NOT SET')}")
    print_info(f"Monitor channels: {audio.get('monitor_channels', 'NOT SET')}")
    print_info(f"Enable monitoring: {audio.get('enable_monitoring', 'NOT SET')}")
    print_info(f"Sample rate: {audio.get('samplerate', 'NOT SET')}")
    print_info(f"Bit depth: {audio.get('bitdepth', 'NOT SET')}")
    print_info(f"Block size: {audio.get('blocksize', 'NOT SET (use driver default)')}")
    
    results['input_device'] = audio.get('input_device_index')
    results['monitoring_enabled'] = audio.get('enable_monitoring', True)
    
    return results


def test_3_device_info():
    """Test 3: Get detailed device information."""
    print_header("TEST 3: Audio Device Details")
    
    config = load_config()
    if not config:
        return {'device_found': False}
    
    device_idx = config.get('audio_interface', {}).get('input_device_index')
    if device_idx is None:
        print_fail("No input device configured")
        return {'device_found': False}
    
    try:
        device_info = sd.query_devices(device_idx)
        host_apis = sd.query_hostapis()
        
        print_success(f"Device {device_idx}: {device_info['name']}")
        print_info(f"  Host API: {host_apis[device_info['hostapi']]['name']}")
        print_info(f"  Input channels: {device_info['max_input_channels']}")
        print_info(f"  Output channels: {device_info['max_output_channels']}")
        print_info(f"  Default samplerate: {device_info['default_samplerate']}")
        
        is_asio = 'ASIO' in host_apis[device_info['hostapi']]['name']
        print_info(f"  Is ASIO: {is_asio}")
        
        return {
            'device_found': True,
            'is_asio': is_asio,
            'input_channels': device_info['max_input_channels'],
            'output_channels': device_info['max_output_channels'],
        }
    except Exception as e:
        print_fail(f"Could not query device {device_idx}: {e}")
        return {'device_found': False}


def test_4_simple_recording():
    """Test 4: Simple sd.rec() - this is what main sampler uses."""
    print_header("TEST 4: Simple Recording (sd.rec) - Main Thread")
    
    config = load_config()
    if not config:
        return {'simple_record': False}
    
    audio = config.get('audio_interface', {})
    device_idx = audio.get('input_device_index')
    
    if device_idx is None:
        print_fail("No input device configured")
        return {'simple_record': False}
    
    try:
        # Get device info
        device_info = sd.query_devices(device_idx)
        host_apis = sd.query_hostapis()
        is_asio = 'ASIO' in host_apis[device_info['hostapi']]['name']
        
        # Parse input_channels
        input_channels = audio.get('input_channels', '1-2')
        if isinstance(input_channels, str) and '-' in input_channels:
            first_channel = int(input_channels.split('-')[0])
            channel_offset = first_channel - 1
        else:
            channel_offset = 0
        
        print_info(f"Device: {device_idx}, Channel offset: {channel_offset}")
        print_info(f"Is ASIO: {is_asio}")
        
        # Setup ASIO channel selectors if needed
        extra_settings = None
        if is_asio and device_info['max_input_channels'] > 2:
            channel_selectors = [channel_offset, channel_offset + 1]
            extra_settings = sd.AsioSettings(channel_selectors=channel_selectors)
            print_info(f"ASIO channel selectors: {channel_selectors}")
        
        # Record!
        duration = 1.0
        samplerate = audio.get('samplerate', 44100)
        frames = int(duration * samplerate)
        
        print_info(f"Recording {duration}s at {samplerate}Hz...")
        
        recording = sd.rec(
            frames,
            samplerate=samplerate,
            channels=2,
            dtype='float32',
            device=device_idx,
            extra_settings=extra_settings,
            blocking=True
        )
        
        rms = np.sqrt(np.mean(recording ** 2))
        peak = np.max(np.abs(recording))
        
        print_success(f"Recording successful!")
        print_info(f"  Shape: {recording.shape}")
        print_info(f"  RMS: {rms:.6f} ({20*np.log10(rms+1e-10):.1f} dB)")
        print_info(f"  Peak: {peak:.6f} ({20*np.log10(peak+1e-10):.1f} dB)")
        
        return {'simple_record': True, 'shape': recording.shape}
        
    except Exception as e:
        print_fail(f"Recording failed: {e}")
        traceback.print_exc()
        return {'simple_record': False, 'error': str(e)}


def test_5_threaded_recording():
    """Test 5: Recording from a thread (ASIO usually fails here)."""
    print_header("TEST 5: Threaded Recording - Like Wavetable Does")
    
    config = load_config()
    if not config:
        return {'threaded_record': False}
    
    audio = config.get('audio_interface', {})
    device_idx = audio.get('input_device_index')
    
    if device_idx is None:
        print_fail("No input device configured")
        return {'threaded_record': False}
    
    result = {'recording': None, 'error': None}
    
    def record_in_thread():
        """Record audio in a worker thread."""
        try:
            device_info = sd.query_devices(device_idx)
            host_apis = sd.query_hostapis()
            is_asio = 'ASIO' in host_apis[device_info['hostapi']]['name']
            
            # Parse input_channels
            input_channels = audio.get('input_channels', '1-2')
            if isinstance(input_channels, str) and '-' in input_channels:
                first_channel = int(input_channels.split('-')[0])
                channel_offset = first_channel - 1
            else:
                channel_offset = 0
            
            # Setup ASIO channel selectors if needed
            extra_settings = None
            if is_asio and device_info['max_input_channels'] > 2:
                channel_selectors = [channel_offset, channel_offset + 1]
                extra_settings = sd.AsioSettings(channel_selectors=channel_selectors)
                print_info(f"  Thread: ASIO channel selectors: {channel_selectors}")
            
            duration = 1.0
            samplerate = audio.get('samplerate', 44100)
            frames = int(duration * samplerate)
            
            print_info(f"  Thread: Recording {duration}s...")
            
            recording = sd.rec(
                frames,
                samplerate=samplerate,
                channels=2,
                dtype='float32',
                device=device_idx,
                extra_settings=extra_settings,
                blocking=False
            )
            
            sd.wait()
            
            result['recording'] = recording
            print_info(f"  Thread: Recording complete, shape: {recording.shape}")
            
        except Exception as e:
            result['error'] = str(e)
            print_fail(f"  Thread: Recording failed: {e}")
            traceback.print_exc()
    
    print_info("Starting recording thread...")
    thread = threading.Thread(target=record_in_thread)
    thread.start()
    thread.join(timeout=10.0)
    
    if result['recording'] is not None:
        print_success("Threaded recording successful!")
        return {'threaded_record': True}
    else:
        print_fail(f"Threaded recording failed: {result['error']}")
        print_info("This is EXPECTED for ASIO - recording must be on main thread")
        return {'threaded_record': False, 'error': result['error']}


def test_6_duplex_stream():
    """Test 6: Duplex stream for monitoring (most likely failure point)."""
    print_header("TEST 6: Duplex Stream (sd.Stream) - Monitoring Mode")
    
    config = load_config()
    if not config:
        return {'duplex_stream': False}
    
    audio = config.get('audio_interface', {})
    device_idx = audio.get('input_device_index')
    output_device_idx = audio.get('output_device_index', device_idx)
    
    if device_idx is None:
        print_fail("No input device configured")
        return {'duplex_stream': False}
    
    try:
        device_info = sd.query_devices(device_idx)
        host_apis = sd.query_hostapis()
        is_asio = 'ASIO' in host_apis[device_info['hostapi']]['name']
        
        # Parse input_channels
        input_channels = audio.get('input_channels', '1-2')
        if isinstance(input_channels, str) and '-' in input_channels:
            first_channel = int(input_channels.split('-')[0])
            input_offset = first_channel - 1
        else:
            input_offset = 0
        
        # Parse monitor_channels
        monitor_channels = audio.get('monitor_channels', '1-2')
        if isinstance(monitor_channels, str) and '-' in monitor_channels:
            first_channel = int(monitor_channels.split('-')[0])
            output_offset = first_channel - 1
        else:
            output_offset = 0
        
        print_info(f"Input device: {device_idx}, Output device: {output_device_idx}")
        print_info(f"Input offset: {input_offset}, Output offset: {output_offset}")
        print_info(f"Is ASIO: {is_asio}")
        
        # Setup ASIO channel selectors for duplex
        if is_asio:
            input_selectors = [input_offset, input_offset + 1]
            output_selectors = [output_offset, output_offset + 1]
            
            print_info(f"ASIO input selectors: {input_selectors}")
            print_info(f"ASIO output selectors: {output_selectors}")
            
            input_asio_settings = sd.AsioSettings(channel_selectors=input_selectors)
            output_asio_settings = sd.AsioSettings(channel_selectors=output_selectors)
            
            print_info("Creating duplex stream with separate ASIO settings...")
            print_info("  This is the configuration that likely fails in wavetable mode...")
            
            recording = []
            samplerate = audio.get('samplerate', 44100)
            
            def callback(indata, outdata, frames, time_info, status):
                if status:
                    print(f"  Callback status: {status}")
                recording.append(indata.copy())
                outdata[:] = indata * 0.5  # Pass through at lower volume
            
            print_info("Creating sd.Stream with duplex ASIO settings...")
            
            stream = sd.Stream(
                samplerate=samplerate,
                channels=(2, 2),  # (input, output)
                dtype='float32',
                callback=callback,
                device=(device_idx, output_device_idx),
                extra_settings=(input_asio_settings, output_asio_settings),
            )
            
            print_info("Starting stream...")
            stream.start()
            
            print_info("Recording for 2 seconds...")
            time.sleep(2.0)
            
            print_info("Stopping stream...")
            stream.stop()
            stream.close()
            
            total_frames = sum(len(r) for r in recording)
            print_success(f"Duplex stream successful!")
            print_info(f"  Recorded {total_frames} frames in {len(recording)} callbacks")
            
            return {'duplex_stream': True, 'frames': total_frames}
            
        else:
            print_info("Non-ASIO device - skipping duplex test")
            return {'duplex_stream': 'skipped'}
            
    except Exception as e:
        print_fail(f"Duplex stream failed: {e}")
        traceback.print_exc()
        return {'duplex_stream': False, 'error': str(e)}


def test_7_wavetable_sampler():
    """Test 7: Actually test the WavetableSampler recording."""
    print_header("TEST 7: WavetableSampler Record Method")
    
    try:
        from src.sampler import AutoSampler
        
        config = load_config()
        if not config:
            return {'wavetable_record': False}
        
        print_info("Creating AutoSampler instance...")
        sampler = AutoSampler(config)
        
        print_info("Setting up audio...")
        if not sampler.setup_audio():
            print_fail("Audio setup failed")
            return {'wavetable_record': False, 'error': 'audio_setup'}
        
        print_success("Audio setup successful")
        
        # Test simple recording via sampler
        print_info("Testing sampler.record_audio(1.0)...")
        recording = sampler.record_audio(1.0)
        
        if recording is not None:
            rms = np.sqrt(np.mean(recording ** 2))
            print_success(f"sampler.record_audio() successful!")
            print_info(f"  Shape: {recording.shape}")
            print_info(f"  RMS: {rms:.6f}")
            return {'wavetable_record': True}
        else:
            print_fail("sampler.record_audio() returned None")
            return {'wavetable_record': False, 'error': 'returned_none'}
        
    except Exception as e:
        print_fail(f"WavetableSampler test failed: {e}")
        traceback.print_exc()
        return {'wavetable_record': False, 'error': str(e)}


def test_8_audio_engine_record_with_monitoring():
    """Test 8: Test AudioEngine.record_with_monitoring() directly."""
    print_header("TEST 8: AudioEngine.record_with_monitoring()")
    
    try:
        from src.sampling.audio_engine import AudioEngine
        
        config = load_config()
        if not config:
            return {'record_with_monitoring': False}
        
        audio_config = config.get('audio_interface', {})
        
        print_info("Creating AudioEngine...")
        engine = AudioEngine(audio_config, test_mode=False)
        
        print_info("Setting up engine...")
        if not engine.setup():
            print_fail("AudioEngine setup failed")
            return {'record_with_monitoring': False, 'error': 'setup'}
        
        print_success("AudioEngine setup successful")
        
        # Check if monitoring is enabled
        monitoring_enabled = audio_config.get('enable_monitoring', True)
        print_info(f"Monitoring enabled in config: {monitoring_enabled}")
        
        # Test regular record first
        print_info("Testing engine.record(1.0)...")
        recording = engine.record(1.0)
        
        if recording is not None:
            rms = np.sqrt(np.mean(recording ** 2))
            print_success(f"engine.record() successful!")
            print_info(f"  Shape: {recording.shape}")
            print_info(f"  RMS: {rms:.6f}")
        else:
            print_fail("engine.record() returned None")
            return {'record_with_monitoring': False, 'error': 'record_failed'}
        
        # Test record_with_monitoring if available
        if hasattr(engine, 'record_with_monitoring'):
            print_info("")
            print_info("Testing engine.record_with_monitoring(1.0)...")
            print_info("This is what wavetable mode uses when enable_monitoring=true")
            
            try:
                recording_mon = engine.record_with_monitoring(1.0)
                
                if recording_mon is not None:
                    rms = np.sqrt(np.mean(recording_mon ** 2))
                    print_success(f"engine.record_with_monitoring() successful!")
                    print_info(f"  Shape: {recording_mon.shape}")
                    print_info(f"  RMS: {rms:.6f}")
                    return {'record_with_monitoring': True}
                else:
                    print_fail("engine.record_with_monitoring() returned None")
                    return {'record_with_monitoring': False, 'error': 'returned_none'}
                    
            except Exception as e:
                print_fail(f"engine.record_with_monitoring() exception: {e}")
                traceback.print_exc()
                return {'record_with_monitoring': False, 'error': str(e)}
        else:
            print_info("engine.record_with_monitoring() not available")
            return {'record_with_monitoring': 'not_available'}
        
    except Exception as e:
        print_fail(f"AudioEngine test failed: {e}")
        traceback.print_exc()
        return {'record_with_monitoring': False, 'error': str(e)}


def main():
    """Run all diagnostics."""
    print()
    print("=" * 70)
    print(" WAVETABLE RECORDING DIAGNOSTICS")
    print(" Comparing local vs main branch behavior")
    print("=" * 70)
    
    results = {}
    
    results['env'] = test_1_environment()
    results['config'] = test_2_config()
    results['device'] = test_3_device_info()
    results['simple'] = test_4_simple_recording()
    results['threaded'] = test_5_threaded_recording()
    results['duplex'] = test_6_duplex_stream()
    results['wavetable'] = test_7_wavetable_sampler()
    results['monitoring'] = test_8_audio_engine_record_with_monitoring()
    
    # Summary
    print_header("SUMMARY")
    
    print()
    print("Test Results:")
    print("-" * 50)
    
    tests = [
        ('Environment/ASIO', results.get('env', {}).get('asio_api', False)),
        ('Config Loaded', results.get('config', {}).get('config_loaded', False)),
        ('Device Found', results.get('device', {}).get('device_found', False)),
        ('Simple Recording', results.get('simple', {}).get('simple_record', False)),
        ('Threaded Recording', results.get('threaded', {}).get('threaded_record', False)),
        ('Duplex Stream', results.get('duplex', {}).get('duplex_stream', False)),
        ('Wavetable Sampler', results.get('wavetable', {}).get('wavetable_record', False)),
        ('Record w/ Monitoring', results.get('monitoring', {}).get('record_with_monitoring', False)),
    ]
    
    for name, passed in tests:
        status = "[OK]" if passed else "[FAIL]" if passed is False else "[SKIP]"
        print(f"  {status:8s} {name}")
    
    print()
    print("-" * 50)
    
    # Diagnosis
    print()
    print("DIAGNOSIS:")
    print()
    
    if results.get('simple', {}).get('simple_record') and \
       not results.get('threaded', {}).get('threaded_record'):
        print("  [!] ASIO works on main thread but fails in threads.")
        print("      This is expected ASIO behavior.")
        print()
    
    if results.get('simple', {}).get('simple_record') and \
       not results.get('duplex', {}).get('duplex_stream'):
        print("  [!] Simple recording works but duplex stream fails.")
        print("      The duplex/monitoring mode is broken for ASIO.")
        print()
        print("  SOLUTION: Disable monitoring in wavetable mode for ASIO devices,")
        print("            or use a different monitoring approach.")
        print()
        print("  To disable monitoring, set in conf/autosamplerT_config.yaml:")
        print("    audio_interface:")
        print("      enable_monitoring: false")
        print()
    
    if results.get('wavetable', {}).get('wavetable_record'):
        print("  [OK] Wavetable recording works!")
        print("       The issue may be elsewhere (MIDI, timing, etc.)")
    else:
        wavetable_error = results.get('wavetable', {}).get('error', 'unknown')
        print(f"  [!] Wavetable recording failed: {wavetable_error}")
        print()
        
        if 'ASIO' in str(wavetable_error).upper() or 'driver' in str(wavetable_error).lower():
            print("  This appears to be an ASIO driver issue.")
            print("  The wavetable code may be using threading or duplex mode")
            print("  which doesn't work with ASIO.")
    
    print()
    
    return 0 if results.get('simple', {}).get('simple_record') else 1


if __name__ == "__main__":
    sys.exit(main())
