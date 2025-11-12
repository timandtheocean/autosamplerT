#!/usr/bin/env python3
"""Test ASIO channel selection with Audio 4 DJ."""

import os
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
import numpy as np
import wave
import tempfile
from pathlib import Path

def test_channel_selection():
    """Test recording from different channel pairs."""
    
    device = 16  # Audio 4 DJ ASIO
    samplerate = 44100
    duration = 2.0  # 2 seconds
    
    print("=" * 80)
    print("ASIO CHANNEL SELECTION TEST - Audio 4 DJ")
    print("=" * 80)
    print(f"\nDevice: {device}")
    print(f"Sample Rate: {samplerate} Hz")
    print(f"Duration: {duration} seconds")
    print(f"\nPlease make sure audio is playing into:")
    print("  - Ch A (In 1|2): Play something in LEFT channel")
    print("  - Ch B (In 3|4): Play something in RIGHT channel")
    print("\n" + "=" * 80)
    
    tests = [
        {
            'name': 'Ch A (0-1) Stereo',
            'channel_selectors': [0, 1],
            'channels': 2,
            'description': 'Recording channels 0-1 (Ch A, In 1|2)'
        },
        {
            'name': 'Ch B (2-3) Stereo',
            'channel_selectors': [2, 3],
            'channels': 2,
            'description': 'Recording channels 2-3 (Ch B, In 3|4)'
        },
        {
            'name': 'Ch A Left (0) Mono',
            'channel_selectors': [0],
            'channels': 1,
            'description': 'Recording channel 0 only (Ch A, In 1)'
        },
        {
            'name': 'Ch A Right (1) Mono',
            'channel_selectors': [1],
            'channels': 1,
            'description': 'Recording channel 1 only (Ch A, In 2)'
        },
        {
            'name': 'Ch B Left (2) Mono',
            'channel_selectors': [2],
            'channels': 1,
            'description': 'Recording channel 2 only (Ch B, In 3)'
        },
        {
            'name': 'Ch B Right (3) Mono',
            'channel_selectors': [3],
            'channels': 1,
            'description': 'Recording channel 3 only (Ch B, In 4)'
        }
    ]
    
    results = []
    temp_dir = Path(tempfile.gettempdir()) / "asio_channel_test"
    temp_dir.mkdir(exist_ok=True)
    
    for test in tests:
        print(f"\n{'='*80}")
        print(f"TEST: {test['name']}")
        print(f"{'='*80}")
        print(f"Description: {test['description']}")
        print(f"Channel selectors: {test['channel_selectors']}")
        print(f"Channels: {test['channels']}")
        
        try:
            # Set up ASIO settings
            asio_settings = sd.AsioSettings(channel_selectors=test['channel_selectors'])
            
            # Record
            print(f"\nRecording...")
            recording = sd.rec(
                int(duration * samplerate),
                samplerate=samplerate,
                channels=test['channels'],
                dtype='float32',
                device=device,
                extra_settings=asio_settings,
                blocking=True
            )
            
            # Analyze recording
            rms = np.sqrt(np.mean(recording ** 2, axis=0))
            peak = np.max(np.abs(recording), axis=0)
            
            print(f"\n✅ Recording successful!")
            print(f"Shape: {recording.shape}")
            
            if test['channels'] == 1:
                print(f"RMS level: {rms[0]:.6f}")
                print(f"Peak level: {peak[0]:.6f}")
                has_signal = rms[0] > 0.001
            else:
                print(f"RMS levels: L={rms[0]:.6f}, R={rms[1]:.6f}")
                print(f"Peak levels: L={peak[0]:.6f}, R={peak[1]:.6f}")
                has_signal = rms[0] > 0.001 or rms[1] > 0.001
            
            # Save to file
            filename = temp_dir / f"{test['name'].replace(' ', '_').replace('(', '').replace(')', '')}.wav"
            print(f"\nSaving to: {filename}")
            
            # Convert to int16 for WAV file
            recording_int = (recording * 32767).astype(np.int16)
            
            with wave.open(str(filename), 'w') as wf:
                wf.setnchannels(test['channels'])
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(samplerate)
                wf.writeframes(recording_int.tobytes())
            
            result = {
                'test': test['name'],
                'status': 'PASS',
                'has_signal': has_signal,
                'rms': rms,
                'peak': peak,
                'filename': str(filename)
            }
            results.append(result)
            
            if not has_signal:
                print(f"⚠️  WARNING: No audio signal detected (RMS too low)")
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            result = {
                'test': test['name'],
                'status': 'FAIL',
                'error': str(e)
            }
            results.append(result)
    
    # Summary
    print(f"\n\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")
    
    for result in results:
        status_icon = '✅' if result['status'] == 'PASS' else '❌'
        print(f"\n{status_icon} {result['test']}: {result['status']}")
        
        if result['status'] == 'PASS':
            print(f"   File: {result['filename']}")
            if 'rms' in result:
                if len(result['rms']) == 1:
                    print(f"   RMS: {result['rms'][0]:.6f}")
                else:
                    print(f"   RMS: L={result['rms'][0]:.6f}, R={result['rms'][1]:.6f}")
            if not result['has_signal']:
                print(f"   ⚠️  WARNING: No audio signal detected")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
    
    print(f"\n\nTest files saved to: {temp_dir}")
    print(f"{'='*80}\n")
    
    # Overall result
    passed = sum(1 for r in results if r['status'] == 'PASS')
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        return 1

if __name__ == "__main__":
    exit(test_channel_selection())
