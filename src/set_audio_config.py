import os
# Enable ASIO support in sounddevice (must be set before importing sounddevice)
os.environ["SD_ENABLE_ASIO"] = "1"

import sounddevice as sd
import yaml
import platform
from typing import List, Tuple, Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../conf/autosamplerT_config.yaml')

def clear_screen():
    """Clear the terminal screen."""
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')


def get_available_driver_types() -> List[Tuple[int, str]]:
    """Get list of available audio driver types (host APIs)."""
    host_apis = sd.query_hostapis()
    driver_types = []
    for idx, api in enumerate(host_apis):
        # Check if this host API has any devices
        devices = sd.query_devices()
        has_devices = any(dev['hostapi'] == idx for dev in devices)
        if has_devices:
            driver_types.append((idx, api['name']))
    return driver_types


def select_driver_type() -> Tuple[int, str]:
    """Let user select audio driver type."""
    driver_types = get_available_driver_types()

    print("\n" + "="*70)
    print("AUDIO DRIVER SELECTION")
    print("="*70)
    print("\nAvailable audio driver types:")
    for idx, (api_idx, name) in enumerate(driver_types, 1):
        print(f"  {idx}. {name}")

    while True:
        try:
            choice = input(f"\nSelect driver type (1-{len(driver_types)}): ").strip()
            if not choice:
                continue
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(driver_types):
                api_idx, api_name = driver_types[choice_idx]
                print(f"\nSelected: {api_name}")
                return api_idx, api_name
            else:
                print(f"Invalid selection. Please enter 1-{len(driver_types)}.")
        except ValueError:
            print("Please enter a valid number.")


def get_asio_channel_pairs(device_idx: int) -> List[Tuple[int, str]]:
    """
    Get list of stereo channel pairs for an ASIO device.

    Returns list of (offset, description) tuples.
    """
    device_info = sd.query_devices(device_idx)
    max_channels = device_info['max_input_channels']

    pairs = []
    for offset in range(0, max_channels, 2):
        if offset + 1 < max_channels:
            # Full stereo pair
            desc = f"Channels {offset}-{offset+1}"
            # Try to give friendly names based on common device layouts
            if max_channels == 4:
                if offset == 0:
                    desc += " (Ch A / In 1|2)"
                elif offset == 2:
                    desc += " (Ch B / In 3|4)"
            elif max_channels == 6:
                desc += f" (Pair {offset//2 + 1})"
            elif max_channels == 8:
                desc += f" (Pair {offset//2 + 1})"
            pairs.append((offset, desc))
        elif offset < max_channels:
            # Single channel (odd number of channels)
            pairs.append((offset, f"Channel {offset} (mono)"))

    return pairs


def test_available_blocksizes(device_idx: int, samplerate: int = 44100) -> List[Tuple[int, float]]:
    """
    Test which buffer sizes are available for an ASIO device.
    
    Returns list of (blocksize, latency_ms) tuples for working buffer sizes.
    """
    import numpy as np
    
    blocksizes_to_test = [64, 128, 256, 512, 1024, 2048, 4096]
    available = []
    
    for blocksize in blocksizes_to_test:
        try:
            # Quick test - just open and close the stream
            stream = sd.InputStream(
                device=device_idx,
                channels=2,
                samplerate=samplerate,
                blocksize=blocksize,
                dtype='float32'
            )
            stream.close()
            latency_ms = blocksize / samplerate * 1000
            available.append((blocksize, latency_ms))
        except Exception:
            # This blocksize doesn't work
            pass
    
    return available


def select_blocksize(device_idx: int, samplerate: int = 44100) -> Optional[int]:
    """
    Let user select buffer size for ASIO device.
    
    Returns selected blocksize or None for driver default.
    """
    print("\n" + "="*70)
    print("BUFFER SIZE SELECTION")
    print("="*70)
    
    # Get current device latency to determine current buffer size
    device_info = sd.query_devices(device_idx)
    current_latency = device_info.get('default_low_input_latency', 0)
    current_blocksize = int(round(current_latency * samplerate))
    # Round to nearest power of 2 for cleaner display
    if current_blocksize > 0:
        import math
        current_blocksize = 2 ** round(math.log2(current_blocksize))
    
    print(f"\nCurrent device buffer size: {current_blocksize} samples ({current_latency*1000:.1f} ms)")
    print("\nTesting available buffer sizes...")
    
    available = test_available_blocksizes(device_idx, samplerate)
    
    if not available:
        print("Could not determine available buffer sizes. Using driver default.")
        return None
    
    # Find which option matches current blocksize
    current_option = 0  # Default to "driver default"
    for idx, (blocksize, _) in enumerate(available, 1):
        if blocksize == current_blocksize:
            current_option = idx
            break
    
    print("\nAvailable buffer sizes:")
    print(f"  0. Use driver default (recommended)")
    for idx, (blocksize, latency_ms) in enumerate(available, 1):
        stability = ""
        if blocksize <= 128:
            stability = " (lowest latency, may cause glitches)"
        elif blocksize <= 256:
            stability = " (low latency)"
        elif blocksize <= 512:
            stability = " (balanced)"
        elif blocksize <= 1024:
            stability = " (stable)"
        else:
            stability = " (very stable, higher latency)"
        
        # Mark current setting
        current_marker = " <-- CURRENT" if blocksize == current_blocksize else ""
        print(f"  {idx}. {blocksize} samples ({latency_ms:.1f} ms){stability}{current_marker}")
    
    print("\nTip: Larger buffer = more stable but higher latency")
    print("     If you hear clicks/pops, try a larger buffer size")
    
    while True:
        try:
            choice = input(f"\nSelect buffer size (0-{len(available)}) [{current_option}]: ").strip()
            if not choice:
                choice = str(current_option)
            if choice == "0":
                print("Using driver default buffer size")
                return None
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(available):
                blocksize, latency_ms = available[choice_idx]
                print(f"Selected: {blocksize} samples ({latency_ms:.1f} ms)")
                return blocksize
            else:
                print(f"Invalid selection. Please enter 0-{len(available)}.")
        except ValueError:
            print("Please enter a valid number.")


def select_asio_device_and_channels(api_idx: int) -> Tuple[Optional[int], Optional[int], Optional[int], Optional[int]]:
    """
    Select ASIO device and channel pairs.

    Returns: (device_idx, input_channel_offset, device_idx, output_channel_offset)
    """
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()

    # Find ASIO devices
    asio_devices = []
    for idx, dev in enumerate(devices):
        if dev['hostapi'] == api_idx:
            asio_devices.append((idx, dev['name'], dev['max_input_channels'], dev['max_output_channels']))

    if not asio_devices:
        print("\n⚠️  No ASIO devices found!")
        return None, None, None, None

    # Show ASIO devices
    print("\n" + "="*70)
    print("ASIO DEVICE SELECTION")
    print("="*70)
    print("\nAvailable ASIO devices:")
    for list_idx, (dev_idx, name, in_ch, out_ch) in enumerate(asio_devices, 1):
        print(f"  {list_idx}. {name}")
        print(f"     Input channels: {in_ch}, Output channels: {out_ch}")

    # Select device
    while True:
        try:
            choice = input(f"\nSelect ASIO device (1-{len(asio_devices)}): ").strip()
            if not choice:
                continue
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(asio_devices):
                device_idx, device_name, in_channels, out_channels = asio_devices[choice_idx]
                print(f"\nSelected: {device_name}")
                break
            else:
                print(f"Invalid selection. Please enter 1-{len(asio_devices)}.")
        except ValueError:
            print("Please enter a valid number.")

    # Select input channel pair
    input_offset = 0
    if in_channels > 2:
        print("\n" + "="*70)
        print("INPUT CHANNEL PAIR SELECTION")
        print("="*70)
        input_pairs = get_asio_channel_pairs(device_idx)
        print(f"\nDevice has {in_channels} input channels")
        print("Available input channel pairs:")
        for list_idx, (offset, desc) in enumerate(input_pairs, 1):
            print(f"  {list_idx}. {desc}")

        while True:
            try:
                choice = input(f"\nSelect input channel pair (1-{len(input_pairs)}) [1]: ").strip()
                if not choice:
                    choice = "1"
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(input_pairs):
                    input_offset, input_desc = input_pairs[choice_idx]
                    print(f"Selected input: {input_desc}")
                    break
                else:
                    print(f"Invalid selection. Please enter 1-{len(input_pairs)}.")
            except ValueError:
                print("Please enter a valid number.")
    else:
        print(f"\nInput: Using default channels 0-1 (device has {in_channels} input channels)")

    # Select monitoring output channel pair
    monitor_offset = input_offset  # Default to same as input
    if out_channels > 2:
        print("\n" + "="*70)
        print("MONITORING OUTPUT CHANNEL PAIR SELECTION")
        print("="*70)
        print("Select which output channels to use for real-time monitoring.")
        print("(This is where you'll hear what you're recording)")
        
        # For output, we need to create pairs based on max_output_channels
        output_pairs = []
        for offset in range(0, out_channels, 2):
            if offset + 1 < out_channels:
                desc = f"Channels {offset}-{offset+1}"
                if out_channels == 4:
                    if offset == 0:
                        desc += " (Ch A / Out 1|2)"
                    elif offset == 2:
                        desc += " (Ch B / Out 3|4)"
                output_pairs.append((offset, desc))

        print(f"\nDevice has {out_channels} output channels")
        print("Available monitoring output channel pairs:")
        for list_idx, (offset, desc) in enumerate(output_pairs, 1):
            # Mark the input channel pair as default
            default_marker = " [DEFAULT - same as input]" if offset == input_offset else ""
            print(f"  {list_idx}. {desc}{default_marker}")

        # Calculate default choice (same as input offset)
        default_choice = None
        for idx, (offset, _) in enumerate(output_pairs):
            if offset == input_offset:
                default_choice = idx + 1
                break
        if default_choice is None:
            default_choice = 1

        while True:
            try:
                choice = input(f"\nSelect monitoring output channel pair (1-{len(output_pairs)}) [{default_choice}]: ").strip()
                if not choice:
                    choice = str(default_choice)
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(output_pairs):
                    monitor_offset, monitor_desc = output_pairs[choice_idx]
                    print(f"Selected monitoring output: {monitor_desc}")
                    break
                else:
                    print(f"Invalid selection. Please enter 1-{len(output_pairs)}.")
            except ValueError:
                print("Please enter a valid number.")
    else:
        print(f"\nMonitoring output: Using default channels 0-1 (device has {out_channels} output channels)")

    return device_idx, input_offset, device_idx, monitor_offset


def select_standard_devices(api_idx: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Select devices for standard (non-ASIO) drivers.

    Returns: (input_device_idx, output_device_idx)
    """
    devices = sd.query_devices()
    host_apis = sd.query_hostapis()

    # Filter devices by selected host API
    filtered_output = []
    filtered_input = []

    for idx, dev in enumerate(devices):
        if dev['hostapi'] == api_idx:
            if dev['max_output_channels'] > 0:
                filtered_output.append((idx, dev['name'], dev['max_output_channels']))
            if dev['max_input_channels'] > 0:
                filtered_input.append((idx, dev['name'], dev['max_input_channels']))

    # Select output device
    output_idx = None
    if filtered_output:
        print("\n" + "="*70)
        print("OUTPUT DEVICE SELECTION")
        print("="*70)
        print("\nAvailable output devices:")
        for list_idx, (dev_idx, name, channels) in enumerate(filtered_output, 1):
            print(f"  {list_idx}. {name} (channels: {channels})")

        while True:
            try:
                choice = input(f"\nSelect output device (1-{len(filtered_output)}): ").strip()
                if not choice:
                    continue
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(filtered_output):
                    output_idx, output_name, _ = filtered_output[choice_idx]
                    print(f"Selected: {output_name}")
                    break
                else:
                    print(f"Invalid selection. Please enter 1-{len(filtered_output)}.")
            except ValueError:
                print("Please enter a valid number.")

    # Select input device
    input_idx = None
    if filtered_input:
        clear_screen()
        print("\n" + "="*70)
        print("INPUT DEVICE SELECTION")
        print("="*70)
        print("\nAvailable input devices:")
        for list_idx, (dev_idx, name, channels) in enumerate(filtered_input, 1):
            print(f"  {list_idx}. {name} (channels: {channels})")

        while True:
            try:
                choice = input(f"\nSelect input device (1-{len(filtered_input)}): ").strip()
                if not choice:
                    continue
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(filtered_input):
                    input_idx, input_name, _ = filtered_input[choice_idx]
                    print(f"Selected: {input_name}")
                    break
                else:
                    print(f"Invalid selection. Please enter 1-{len(filtered_input)}.")
            except ValueError:
                print("Please enter a valid number.")

    return input_idx, output_idx


def configure_audio_parameters(input_idx: Optional[int]) -> Tuple[int, int]:
    """
    Configure sample rate and bit depth.

    Returns: (samplerate, bitdepth)
    """
    # Get default sample rate from device
    if input_idx is not None:
        input_info = sd.query_devices(input_idx)
        default_samplerate = int(input_info.get('default_samplerate', 44100))
    else:
        default_samplerate = 44100

    print("\n" + "="*70)
    print("AUDIO PARAMETERS")
    print("="*70)

    # Sample rate
    supported_samplerates = [44100, 48000, 88200, 96000, 192000]
    print(f"\nSupported sample rates: {supported_samplerates}")
    print(f"Device default: {default_samplerate} Hz")
    samplerate_in = input(f"Enter sample rate [{default_samplerate}]: ").strip()
    samplerate = int(samplerate_in) if samplerate_in else default_samplerate

    # Bit depth
    supported_bitdepths = [16, 24, 32]
    default_bitdepth = 24
    print(f"\nSupported bit depths: {supported_bitdepths}")
    bitdepth_in = input(f"Enter bit depth [{default_bitdepth}]: ").strip()
    bitdepth = int(bitdepth_in) if bitdepth_in else default_bitdepth

    return samplerate, bitdepth


def main():
    """Main audio configuration wizard."""
    clear_screen()
    print("="*70)
    print("AUDIO INTERFACE CONFIGURATION WIZARD")
    print("="*70)

    # Step 1: Select driver type
    api_idx, api_name = select_driver_type()

    # Step 2: Select devices (different flow for ASIO vs others)
    is_asio = 'ASIO' in api_name.upper()

    if is_asio:
        # ASIO: Select device and channel pairs
        device_idx, input_offset, _, output_offset = select_asio_device_and_channels(api_idx)
        if device_idx is None:
            print("\nConfiguration cancelled.")
            return
        input_idx = device_idx
        output_idx = device_idx
    else:
        # Standard drivers: Select separate input/output devices
        input_idx, output_idx = select_standard_devices(api_idx)
        input_offset = 0
        output_offset = 0

    # Step 3: Configure audio parameters
    samplerate, bitdepth = configure_audio_parameters(input_idx)

    # Step 4: Select buffer size (ASIO only)
    blocksize = None
    if is_asio and input_idx is not None:
        blocksize = select_blocksize(input_idx, samplerate)

    # Step 5: Save configuration
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f) or {}

    config['audio_interface'] = {
        'input_device_index': input_idx,
        'output_device_index': output_idx,
        'samplerate': samplerate,
        'bitdepth': bitdepth
    }

    # Add blocksize if specified
    if blocksize is not None:
        config['audio_interface']['blocksize'] = blocksize

    # Add input_channels and monitor_channels for ASIO devices (user-friendly format)
    if is_asio and input_offset is not None:
        # Convert offset to channel pair description (e.g., 0 -> "1-2", 2 -> "3-4")
        first_channel = input_offset + 1
        second_channel = input_offset + 2
        config['audio_interface']['input_channels'] = f"{first_channel}-{second_channel}"
        
        # Add monitor channels (where you hear the recording)
        if output_offset is not None:
            first_monitor = output_offset + 1
            second_monitor = output_offset + 2
            config['audio_interface']['monitor_channels'] = f"{first_monitor}-{second_monitor}"

    if 'midi_interface' not in config:
        config['midi_interface'] = {'midi_input_name': None, 'midi_output_name': None}

    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f)

    # Summary
    print("\n" + "="*70)
    print("CONFIGURATION SUMMARY")
    print("="*70)
    print(f"\nDriver type: {api_name}")
    if input_idx is not None:
        input_info = sd.query_devices(input_idx)
        print(f"Input device: {input_info['name']} (index {input_idx})")
        if is_asio and input_offset >= 0:
            print(f"  Input channels: {input_offset}-{input_offset+1} (user format: {input_offset+1}-{input_offset+2})")
    if output_idx is not None:
        output_info = sd.query_devices(output_idx)
        print(f"Output device: {output_info['name']} (index {output_idx})")
        if is_asio and output_offset >= 0:
            print(f"  Monitor channels: {output_offset}-{output_offset+1} (user format: {output_offset+1}-{output_offset+2})")
    print(f"Sample rate: {samplerate} Hz")
    print(f"Bit depth: {bitdepth} bit")
    if blocksize is not None:
        latency_ms = blocksize / samplerate * 1000
        print(f"Buffer size: {blocksize} samples ({latency_ms:.1f} ms)")
    else:
        print(f"Buffer size: Driver default")
    print(f"\nConfiguration saved to: {CONFIG_FILE}")

if __name__ == "__main__":
	main()
