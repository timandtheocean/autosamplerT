"""
AutosamplerT - Main Sampling Engine

This module handles the core autosampling functionality:
- MIDI note/CC message transmission
- Audio recording with configurable parameters
- Velocity layers and round-robin sampling
- Silence detection and auto-trimming
- Sample normalization
- WAV metadata writing
- SFZ export generation

Author: AutosamplerT
License: MIT
"""

# Standard library imports
import os
import sys
import time
import logging
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Enable ASIO support in sounddevice (must be set before importing sounddevice)
os.environ["SD_ENABLE_ASIO"] = "1"

# Third-party imports
import mido
import numpy as np
import sounddevice as sd

# Local application imports
from src.sampler_midicontrol import MIDIController
from src.sampling.display import LogBufferHandler, SamplingDisplay
from src.sampling.audio_engine import AudioEngine
from src.sampling.file_manager import FileManager
from src.sampling.midi_engine import MIDINoteEngine
from src.sampling.sample_processor import SampleProcessor
from src.sampling.interactive_handler import InteractiveSamplingHandler
from src.sampling.patch_iterator import PatchIterator
from src.realtime_monitor import show_pre_sampling_monitor

# Set up logging with buffer handler
log_buffer_handler = LogBufferHandler(max_lines=10)
log_buffer_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

# Add the buffer handler to capture logs for display
logging.getLogger().addHandler(log_buffer_handler)

# Store reference to console handler so we can disable it during display
console_handler = None
for handler in logging.getLogger().handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream.name in ('<stdout>', '<stderr>'):
        console_handler = handler
        break


class AutoSampler:
    """
    Main autosampling class that coordinates MIDI and audio operations.

    This class handles:
    - MIDI port management and message sending
    - Audio device configuration and recording
    - Sample processing (normalization, trimming)
    - File management and metadata
    """

    def __init__(self, config: Dict, batch_mode: bool = False):
        """
        Initialize the AutoSampler with configuration.

        Args:
            config: Dictionary containing audio_interface, midi_interface, and sampling settings
            batch_mode: If True, skip user confirmation prompts for automated batch processing
        """
        self.config = config
        self.batch_mode = batch_mode
        self.audio_config = config.get('audio_interface', {})
        self.midi_config = config.get('midi_interface', {})
        self.sampling_midi_config = config.get('sampling_midi', {})
        self.sampling_config = config.get('sampling', {})
        self.interactive_config = config.get('interactive_sampling', {})

        # Merge output settings into sampling_config for backward compatibility
        output_config = config.get('output', {})
        if output_config:
            self.sampling_config.update(output_config)

        # Merge audio settings - script 'audio:' section OVERRIDES config 'audio_interface:'
        audio_settings = config.get('audio', {})
        if audio_settings:
            # Script settings override config settings
            for key, value in audio_settings.items():
                self.audio_config[key] = value

        # Test mode flag
        self.test_mode = self.sampling_config.get('test_mode', False)

        # Initialize modular components
        self.audio_engine = AudioEngine(self.audio_config, self.test_mode)
        self.file_manager = FileManager(self.sampling_config, self.audio_config, self.test_mode)

        # MIDI note engine (will be fully initialized after MIDI port setup)
        self.midi_note_engine = None

        # Sample processor (will be initialized after MIDI engine)
        self.sample_processor = None

        # Interactive sampling handler (will be initialized after reading settings)
        self.interactive_handler = None

        # Patch iterator (for multi-patch sampling)
        self.patch_iterator = None  # Initialized after MIDI setup

        # MIDI ports
        self.midi_input_port: Optional[mido.ports.BaseInput] = None
        self.midi_output_port: Optional[mido.ports.BaseOutput] = None
        self.midi_controller: Optional[MIDIController] = None

        # Sampling settings (kept for backward compatibility and easy access)
        self.hold_time = self.sampling_config.get('hold_time', 2.0)
        self.release_time = self.sampling_config.get('release_time', 1.0)
        self.pause_time = self.sampling_config.get('pause_time', 0.5)
        self.velocity_layers = self.sampling_config.get('velocity_layers', 1)
        self.roundrobin_layers = self.sampling_config.get('roundrobin_layers', 1)

        # Velocity configuration
        self.velocity_minimum = self.midi_config.get('velocity_minimum', 1)
        self.velocity_layers_split = self.sampling_config.get('velocity_layers_split', None)

        # MIDI message delay
        self.midi_message_delay = self.midi_config.get('midi_message_delay', 0.0)

        # Processing settings
        self.patch_normalize = self.audio_config.get('patch_normalize', False)
        
        # Enable real-time monitoring during sampling
        self.enable_monitoring = self.audio_config.get('enable_monitoring', False)

        # Output settings (delegate to FileManager, but keep for backward compatibility)
        self.base_output_folder = self.file_manager.base_output_folder
        self.output_format = self.sampling_config.get('output_format', 'sfz')
        self.multisample_name = self.file_manager.multisample_name
        self.multisample_folder = self.file_manager.multisample_folder
        self.output_folder = self.file_manager.output_folder
        self.lowest_note = self.file_manager.lowest_note
        self.highest_note = self.file_manager.highest_note

        # Interactive sampling settings
        self.interactive_pause_interval = self.interactive_config.get('pause_interval',
                                           self.interactive_config.get('every', 0))
        self.interactive_auto_resume = self.interactive_config.get('auto_resume',
                                        self.interactive_config.get('continue', 0))
        self.interactive_prompt = self.interactive_config.get('prompt',
            "Paused for user intervention. Press Enter to continue...")
        self.interactive_notes_sampled = 0

        # MIDI range mapping for limited-key hardware
        self.interactive_midi_range = self.interactive_config.get('midi_range', None)
        self.interactive_pause_after_range = self.interactive_config.get('pause_after_range', False)

        # Initialize interactive handler after settings are loaded
        self.interactive_handler = InteractiveSamplingHandler(
            pause_interval=self.interactive_pause_interval,
            auto_resume=self.interactive_auto_resume,
            prompt=self.interactive_prompt,
            velocity_layers=self.velocity_layers,
            roundrobin_layers=self.roundrobin_layers
        )

        # Storage for normalization
        self.recorded_samples: List[Tuple[np.ndarray, Dict]] = []

        logging.info("AutoSampler initialized with modular components")

    # Properties for backward compatibility - delegate to audio_engine
    @property
    def samplerate(self):
        """Get sample rate from audio engine."""
        return self.audio_engine.samplerate

    @property
    def bitdepth(self):
        """Get bit depth from audio engine."""
        return self.audio_engine.bitdepth

    @property
    def channels(self):
        """Get channels from audio engine."""
        return self.audio_engine.channels

    @property
    def mono_stereo(self):
        """Get mono/stereo setting from audio engine."""
        return self.audio_engine.mono_stereo

    @property
    def mono_channel(self):
        """Get mono channel from audio engine."""
        return self.audio_engine.mono_channel

    @property
    def channel_offset(self):
        """Get channel offset from audio engine."""
        return self.audio_engine.channel_offset

    @property
    def gain(self):
        """Get gain from audio engine."""
        return self.audio_engine.gain

    @property
    def input_device(self):
        """Get input device from audio engine."""
        return self.audio_engine.input_device

    @property
    def silence_detection(self):
        """Get silence detection setting from audio engine."""
        return self.audio_engine.silence_detection

    @property
    def sample_normalize(self):
        """Get sample normalization setting from audio engine."""
        return self.audio_engine.sample_normalize

    def setup_midi(self) -> bool:
        """
        Open MIDI input/output ports based on configuration.

        Returns:
            True if MIDI setup successful, False otherwise
        """
        midi_success = False
        try:
            midi_input_name = self.midi_config.get('midi_input_name')
            midi_output_name = self.midi_config.get('midi_output_name')

            if midi_input_name:
                self.midi_input_port = mido.open_input(midi_input_name)
                logging.info("MIDI input opened: %s", midi_input_name)
            else:
                logging.warning("No MIDI input configured - MIDI input disabled")

            if midi_output_name:
                self.midi_output_port = mido.open_output(midi_output_name)
                logging.info("MIDI output opened: %s", midi_output_name)
            else:
                logging.warning("No MIDI output configured - MIDI output disabled")

            midi_success = True
        except Exception as e:
            logging.error("MIDI setup failed: %s", e)
            midi_success = False

        # Always initialize MIDI components (even if port setup failed)
        # Initialize MIDI controller
        self.midi_controller = MIDIController(self.midi_output_port, self.test_mode)

        # Initialize MIDI note engine
        self.midi_note_engine = MIDINoteEngine(self.midi_output_port, self.test_mode)

        # Initialize sample processor with MIDI and audio engines
        self.sample_processor = SampleProcessor(
            midi_note_engine=self.midi_note_engine,
            audio_engine=self.audio_engine,
            hold_time=self.hold_time,
            release_time=self.release_time,
            pause_time=self.pause_time,
            input_device=self.audio_engine.input_device,
            test_mode=self.test_mode,
            velocity_minimum=self.velocity_minimum,
            velocity_layers_split=self.velocity_layers_split,
            enable_monitoring=self.enable_monitoring
        )

        # Initialize patch iterator
        self.patch_iterator = PatchIterator(
            midi_controller=self.midi_controller,
            midi_message_delay=self.midi_message_delay,
            test_mode=self.test_mode
        )

        return midi_success

    def setup_audio(self) -> bool:
        """
        Configure audio devices and verify settings.

        Returns:
            True if audio setup successful, False otherwise
        """
        return self.audio_engine.setup()

    def check_interactive_pause(self, display: SamplingDisplay = None) -> None:
        """
        Check if interactive pause is needed.

        Delegates to InteractiveSamplingHandler.

        Args:
            display: SamplingDisplay instance to show pause status
        """
        self.interactive_handler.check_pause(display)

    def send_midi_note(self, note: int, velocity: int, channel: int = 0, duration: float = None) -> None:
        """
        Send a MIDI note on/off sequence.

        Delegates to MIDINoteEngine component.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            channel: MIDI channel (0-15)
            duration: Note duration in seconds (if None, only sends note_on)
        """
        if self.midi_note_engine:
            self.midi_note_engine.send_midi_note(note, velocity, channel, duration)
        else:
            logging.warning("MIDI note engine not initialized - skipping MIDI note")


    def record_audio(self, duration: float) -> Optional[np.ndarray]:
        """Record audio using AudioEngine.

        This method delegates to the AudioEngine component.
        Uses real-time monitoring if enabled in configuration.

        Args:
            duration: Recording duration in seconds

        Returns:
            NumPy array of recorded audio samples, or None if recording failed
        """
        if self.enable_monitoring:
            logging.debug(f"Recording with monitoring enabled (duration={duration}s)")
            return self.audio_engine.record_with_monitoring(duration)
        else:
            logging.debug(f"Recording without monitoring (duration={duration}s)")
            return self.audio_engine.record(duration)

    def sample_noise_floor(self, duration: float = 2.0) -> float:
        """
        Record silence from synth to detect actual noise floor of signal chain.
        
        Args:
            duration: Duration to record silence in seconds
            
        Returns:
            Silence trim threshold in dB (noise floor + 6dB margin)
        """
        import numpy as np
        
        logging.info(f"Recording {duration}s of silence to detect noise floor...")
        
        # Ensure audio engine is properly set up before recording
        if not self.audio_engine.setup():
            logging.error("Audio engine setup failed")
            return -60.0
        
        # Record silence (no MIDI sent - this is the key part)
        silence_audio = self.audio_engine.record(duration)
        
        if silence_audio is None:
            logging.warning("Failed to record noise floor, using default -60dB")
            return -60.0
        
        # Calculate noise floor RMS
        silence_rms = np.sqrt(np.mean(silence_audio ** 2))
        noise_floor_db = 20 * np.log10(silence_rms + 1e-10)
        
        logging.info(f"Detected noise floor: {noise_floor_db:.1f}dB")
        
        # Use raw noise floor + 0.1dB for precise threshold
        threshold = noise_floor_db + 0.1
        logging.info(f"Using precise threshold: {threshold:.1f}dB (noise floor + 0.1dB)")
        
        # Test signal level if MIDI controller is available
        if self.midi_controller and not self.test_mode:
            self._test_signal_level()
        
        return threshold
    
    def _test_signal_level(self) -> None:
        """
        Test signal level by sending a MIDI note and measuring peak amplitude.
        Provides feedback on whether recording levels are optimal.
        """
        import numpy as np
        import time
        
        logging.info("Testing signal levels for optimal recording...")
        print("🔊 Testing signal levels...")
        
        try:
            # Send middle C at moderate velocity for level test
            test_note = 60  # Middle C
            test_velocity = 100  # Moderate velocity
            test_duration = 2.0  # 2 seconds
            
            # Send note on
            if self.midi_controller:
                self.midi_controller.send_note(test_note, test_velocity, 0)
                time.sleep(0.1)  # Brief delay to let note start
            
            # Record test signal
            test_audio = self.audio_engine.record(test_duration)
            
            # Send note off
            if self.midi_controller:
                self.midi_controller.send_note_off(test_note, 0)
            
            if test_audio is None:
                logging.warning("Failed to record test signal")
                return
            
            # Calculate peak amplitude
            peak_linear = np.abs(test_audio).max()
            if peak_linear > 0:
                peak_db = 20 * np.log10(peak_linear)
            else:
                peak_db = -200.0  # Essentially silence
            
            logging.info(f"Test signal peak: {peak_db:.1f}dB")
            
            # Analyze level and provide feedback
            if peak_db >= -3.0:
                status = "⚠️  TOO HIGH"
                recommendation = "REDUCE gain/volume - risk of clipping!"
                color = "🔴"
            elif peak_db >= -6.0:
                status = "✅ OPTIMAL"
                recommendation = "Perfect recording level"
                color = "🟢"
            elif peak_db >= -12.0:
                status = "⚠️  LOW"
                recommendation = "Consider increasing gain for better SNR"
                color = "🟡"
            elif peak_db >= -20.0:
                status = "❌ TOO LOW"
                recommendation = "INCREASE gain significantly"
                color = "🔴"
            else:
                status = "❌ VERY LOW"
                recommendation = "Check connections and gain settings"
                color = "🔴"
            
            print(f"\n{color} Signal Level Test Results:")
            print(f"   Peak Level: {peak_db:.1f}dB")
            print(f"   Status: {status}")
            print(f"   Target Range: -6dB to -3dB")
            print(f"   Recommendation: {recommendation}")
            
            if peak_db < -6.0:
                # Calculate suggested gain increase
                target_db = -4.5  # Middle of optimal range
                gain_needed = target_db - peak_db
                print(f"   Suggested gain increase: +{gain_needed:.1f}dB")
            elif peak_db > -3.0:
                # Calculate suggested gain decrease
                target_db = -4.5  # Middle of optimal range
                gain_reduction = peak_db - target_db
                print(f"   Suggested gain reduction: -{gain_reduction:.1f}dB")
            
            print()
            
        except Exception as e:
            logging.error(f"Signal level test failed: {e}")
            print(f"❌ Signal level test failed: {e}")

    def detect_silence(self, audio: np.ndarray, threshold: float = 0.001) -> Tuple[int, int]:
        """Detect silence using AudioEngine.

        Delegates to AudioEngine component.

        Args:
            audio: Audio data as NumPy array
            threshold: Amplitude threshold for silence detection

        Returns:
            Tuple of (start_sample, end_sample) for trimming
        """
        return self.audio_engine.detect_silence(audio, threshold)

    def normalize_audio(self, audio: np.ndarray, target_level: float = 0.95) -> np.ndarray:
        """Normalize audio using AudioEngine.

        Delegates to AudioEngine component.

        Args:
            audio: Audio data as NumPy array
            target_level: Target peak amplitude (0.0-1.0)

        Returns:
            Normalized audio array
        """
        return self.audio_engine.normalize(audio, target_level)

    def save_wav_file(self, audio: np.ndarray, filepath: Path, metadata: Dict = None) -> bool:
        """
        Save audio to WAV file with optional metadata.

        Delegates to FileManager component.

        Args:
            audio: Audio data as NumPy array
            filepath: Output file path
            metadata: Optional dictionary of metadata (note, velocity, etc.)

        Returns:
            True if save successful, False otherwise
        """
        return self.file_manager.save_wav(audio, filepath, metadata)

    def sample_note(self, note: int, velocity: int, channel: int = 0,
                    rr_index: int = 0, midi_note: Optional[int] = None) -> Optional[np.ndarray]:
        """
        Sample a single note: send MIDI, record audio, process.

        Delegates to SampleProcessor component.

        Args:
            note: SFZ note number (used for filenames, metadata, and SFZ mapping)
            velocity: MIDI velocity
            channel: MIDI channel
            rr_index: Round-robin layer index
            midi_note: MIDI note to send (if different from note due to MIDI range mapping)

        Returns:
            Processed audio array or None
        """
        if self.sample_processor:
            return self.sample_processor.sample_note(note, velocity, channel, rr_index, midi_note)
        else:
            logging.error("Sample processor not initialized")
            return None

    def calculate_velocity_value(self, layer: int, total_layers: int) -> int:
        """
        Calculate MIDI velocity for a given velocity layer.

        Delegates to SampleProcessor component.

        Args:
            layer: Current layer index (0-based)
            total_layers: Total number of velocity layers

        Returns:
            MIDI velocity value (1-127)
        """
        if self.sample_processor:
            return self.sample_processor.calculate_velocity_value(layer, total_layers)
        else:
            logging.warning("Sample processor not initialized - returning default velocity")
            return 127

    def calculate_velocity_range_for_layer(self, layer: int, total_layers: int) -> tuple:
        """
        Calculate the velocity range (min, max) for a given velocity layer.
        
        Args:
            layer: Current layer index (0-based) 
            total_layers: Total number of velocity layers
            
        Returns:
            Tuple of (min_velocity, max_velocity)
        """
        if self.sample_processor and self.sample_processor.velocity_layers_split is not None:
            # Use custom split points
            split_points = self.sample_processor.velocity_layers_split
            
            if layer == 0:
                # First layer: 1 to first split point
                return (1, split_points[0])
            elif layer < len(split_points):
                # Middle layers: previous split + 1 to current split
                return (split_points[layer - 1] + 1, split_points[layer])
            else:
                # Last layer: last split + 1 to 127
                return (split_points[-1] + 1, 127)
        else:
            # Default behavior - calculate even distribution
            if total_layers == 1:
                return (1, 127)
            
            # Even distribution
            range_size = 126 // total_layers  # 126 = 127 - 1
            min_vel = layer * range_size + 1
            max_vel = min(127, (layer + 1) * range_size)
            
            # Last layer gets remainder
            if layer == total_layers - 1:
                max_vel = 127
                
            return (min_vel, max_vel)

    def generate_sample_filename(self, note: int, velocity: int, rr_index: int = 0, velocity_layer: int = None) -> str:
        """Generate sample filename using FileManager.

        This method delegates to the FileManager component.
        Generate standardized sample filename.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            rr_index: Round-robin index
            velocity_layer: Velocity layer index (for range naming)

        Returns:
            Filename string
        """
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note // 12) - 1
        note_name = note_names[note % 12]

        base_name = self.sampling_config.get('sample_name', self.multisample_name)

        # Determine velocity string format
        if velocity_layer is not None and self.velocity_layers > 1:
            # Show velocity range instead of single value
            vel_min, vel_max = self.calculate_velocity_range_for_layer(velocity_layer, self.velocity_layers)
            velocity_str = f"v{vel_min:03d}-{vel_max:03d}"
        else:
            # Show single velocity value
            velocity_str = f"v{velocity:03d}"

        if self.roundrobin_layers > 1:
            filename = f"{base_name}_{note_name}{octave}_{velocity_str}_rr{rr_index+1}.wav"
        else:
            filename = f"{base_name}_{note_name}{octave}_{velocity_str}.wav"

        return filename

    def _perform_warmup_sequence(self, start_note: int, channel: int, display) -> None:
        """
        Perform warm-up sequence to prevent low-level first sample.
        
        Sends MIDI note and records a brief warm-up sample to initialize
        the synth and audio interface before actual sampling begins.
        
        Args:
            start_note: MIDI note to use for warm-up
            channel: MIDI channel for warm-up
            display: Display handler for status updates
        """
        if self.test_mode:
            logging.debug("Warm-up sequence skipped in test mode")
            return
            
        logging.info("Performing warm-up sequence to initialize synth and audio interface...")
        display.update(start_note, 127, 0, 0, "Warming up...", ["Initializing synth/audio"])
        
        try:
            # Send a MIDI note to wake up the synth
            if self.midi_controller and self.midi_controller.midi_output_port:
                # Trigger the starting note at full velocity for warm-up
                self.send_midi_note(start_note, 127, channel, duration=0.5)
                
                # Add extra settling time
                time.sleep(1.0)
                
            # Record a brief warm-up sample (discarded)
            if self.audio_engine:
                _ = self.audio_engine.record(0.5)
                
            # Additional settling time
            time.sleep(0.5)
            
            logging.info("Warm-up sequence completed - synth and audio interface ready")
            
        except Exception as e:
            logging.warning(f"Warm-up sequence failed: {e} - continuing with sampling")

    def sample_range(self, start_note: int, end_note: int, interval: int = 1,
                     channel: int = 0) -> List[Dict]:
        """
        Sample a range of notes with velocity layers and round-robin.

        Args:
            start_note: Starting MIDI note number (SFZ range start)
            end_note: Ending MIDI note number (SFZ range end, inclusive)
            interval: Note interval (1=chromatic, 2=whole tone, etc.)
            channel: MIDI channel

        Returns:
            List of sample metadata dictionaries
        """
        global console_handler
        
        sample_list = []
        
        # Step 1: Handle silence detection based on configuration
        postprocessing_config = self.config.get('postprocessing', {})
        if postprocessing_config.get('trim_silence') and not self.test_mode:
            silence_mode = postprocessing_config.get('silence_detection', 'auto')
            
            if silence_mode == 'auto':
                # Auto mode: detect noise floor from synth
                self.detected_noise_threshold = self.sample_noise_floor(2.0)
            elif silence_mode == 'manual':
                # Manual mode: use specified threshold
                manual_threshold = postprocessing_config.get('silence_threshold', -60.0)
                self.detected_noise_threshold = manual_threshold
                logging.info(f"Using manual silence threshold: {manual_threshold:.1f}dB")
            else:
                logging.warning(f"Unknown silence_detection mode '{silence_mode}', using auto")
                self.detected_noise_threshold = self.sample_noise_floor(2.0)
        else:
            self.detected_noise_threshold = None

        # Calculate total notes (SFZ notes to sample)
        all_notes = list(range(start_note, end_note + 1, interval))
        total_notes = len(all_notes)

        # Check if MIDI range mapping is enabled
        midi_range_enabled = False
        midi_range_start = start_note
        midi_range_end = end_note
        midi_range_size = 0

        if self.interactive_midi_range:
            midi_range_start = self.interactive_midi_range.get('start', start_note)
            midi_range_end = self.interactive_midi_range.get('end', end_note)
            midi_range_size = midi_range_end - midi_range_start + 1

            # Enable MIDI mapping if MIDI range is smaller than SFZ range
            if midi_range_size < total_notes:
                midi_range_enabled = True
                logging.info(
                    "MIDI range mapping enabled: MIDI %s-%s (%s notes) -> SFZ %s-%s (%s notes)",
                    midi_range_start, midi_range_end, midi_range_size, start_note, end_note, total_notes
                )
                logging.info(
                    "MIDI range will repeat %s times (+%s extra notes)",
                    total_notes // midi_range_size, total_notes % midi_range_size
                )

        # Initialize display with log handler
        display = SamplingDisplay(
            total_notes=total_notes,
            velocity_layers=self.velocity_layers,
            roundrobin_layers=self.roundrobin_layers,
            hold_time=self.hold_time,
            release_time=self.release_time,
            pause_time=self.pause_time,
            log_handler=log_buffer_handler
        )

        # Start display
        display.start()
        
        # Pass display to sample processor if monitoring is enabled
        if self.enable_monitoring:
            self.sample_processor.set_sampling_display(display)
        
        # Disable console logging during display to prevent interference
        if console_handler:
            console_handler.setLevel(logging.CRITICAL + 1)  # Disable console output

        try:
            # Get MIDI control configurations
            velocity_midi_config = self.sampling_midi_config.get('velocity_midi_control', [])
            roundrobin_midi_config = self.sampling_midi_config.get('roundrobin_midi_control', [])

            # Send initial MIDI setup messages (from sampling_midi or fallback to midi_interface)
            initial_config = {}
            if self.sampling_midi_config:
                initial_config = self.sampling_midi_config
            else:
                # Fallback to old config structure
                initial_config = self.midi_config

            if self.midi_controller:
                self.midi_controller.send_midi_setup(initial_config, channel)

            # Warm-up sequence to prevent low-level first sample
            self._perform_warmup_sequence(start_note, channel, display)

            # Iterate through notes
            for note_idx, note in enumerate(all_notes):
                # Iterate through velocity layers
                for vel_layer in range(self.velocity_layers):
                    velocity = self.calculate_velocity_value(vel_layer, self.velocity_layers)

                    # Collect MIDI messages for display
                    midi_msgs = []

                    # Apply velocity layer MIDI settings
                    if self.midi_controller and velocity_midi_config:
                        self.midi_controller.apply_velocity_layer_midi(
                            vel_layer, velocity_midi_config, channel, self.midi_message_delay
                        )
                        midi_msgs.append(f"Velocity Layer {vel_layer}: Applied MIDI settings")

                    # Iterate through round-robin layers
                    for rr_layer in range(self.roundrobin_layers):
                        # Update display
                        display.update(note, velocity, rr_layer, vel_layer, "Preparing", midi_msgs)

                        # Apply round-robin layer MIDI settings
                        if self.midi_controller and roundrobin_midi_config:
                            self.midi_controller.apply_roundrobin_layer_midi(
                                rr_layer, roundrobin_midi_config, channel, self.midi_message_delay
                            )
                            midi_msgs.append(f"Round-Robin {rr_layer}: Applied MIDI settings")

                        # Determine which channel to use for this note
                        if self.midi_controller:
                            note_channel = self.midi_controller.get_layer_channel(
                                vel_layer, rr_layer, velocity_midi_config,
                                roundrobin_midi_config, channel
                            )
                        else:
                            note_channel = channel

                        # Calculate MIDI note to send (may be different from SFZ note if MIDI range mapping is enabled)
                        midi_note_to_send = note
                        if midi_range_enabled:
                            # Map SFZ note index to MIDI range
                            # Example: SFZ notes 36-67 (32 notes) -> MIDI 36-67
                            #          SFZ notes 68-99 (32 notes) -> MIDI 36-67 (repeated)
                            notes_into_range = note_idx % midi_range_size
                            midi_note_to_send = midi_range_start + notes_into_range

                        # Get note names for display
                        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                        sfz_octave = (note // 12) - 1
                        sfz_note_name = note_names[note % 12] + str(sfz_octave)

                        # Build MIDI message display
                        if midi_range_enabled and midi_note_to_send != note:
                            midi_octave = (midi_note_to_send // 12) - 1
                            midi_note_name = note_names[midi_note_to_send % 12] + str(midi_octave)
                            midi_msgs.append(f"Note ON: MIDI {midi_note_name} ({midi_note_to_send}) -> SFZ {sfz_note_name} ({note}), "
                                           f"Vel={velocity} (Layer {vel_layer+1}/{self.velocity_layers}), "
                                           f"RR={rr_layer+1}/{self.roundrobin_layers}, Ch={note_channel}")
                        else:
                            midi_msgs.append(f"Note ON: {sfz_note_name} (MIDI {note}), "
                                           f"Vel={velocity} (Layer {vel_layer+1}/{self.velocity_layers}), "
                                           f"RR={rr_layer+1}/{self.roundrobin_layers}, Ch={note_channel}")

                        display.update(note, velocity, rr_layer, vel_layer,
                                     f"Recording ({self.hold_time + self.release_time:.1f}s)", midi_msgs)

                        # Sample the note (pass MIDI note if different)
                        if midi_range_enabled and midi_note_to_send != note:
                            audio = self.sample_note(note, velocity, note_channel, rr_layer, midi_note=midi_note_to_send)
                        else:
                            audio = self.sample_note(note, velocity, note_channel, rr_layer)

                        # Update display for processing
                        display.update(note, velocity, rr_layer, vel_layer, "Processing", midi_msgs)

                        # Generate filename
                        filename = self.generate_sample_filename(note, velocity, rr_layer, velocity_layer=vel_layer)
                        filepath = self.output_folder / filename

                        # Prepare metadata
                        metadata = {
                            'note': note,
                            'velocity': velocity,
                            'velocity_layer': vel_layer,
                            'roundrobin_layer': rr_layer,
                            'samplerate': self.samplerate,
                            'bitdepth': self.bitdepth,
                            'channels': self.channels,
                            'duration': (self.hold_time + self.release_time) if self.test_mode else (len(audio) / self.samplerate if audio is not None else 0)
                        }

                        # In test mode, still add to sample list for SFZ generation
                        if self.test_mode:
                            sample_list.append({'file': str(filepath), **metadata})
                        elif audio is not None:
                            # Store for potential patch normalization
                            self.recorded_samples.append((audio, metadata))

                            # Save immediately if not doing patch normalization
                            if not self.patch_normalize:
                                display.update(note, velocity, rr_layer, vel_layer, "Saving", midi_msgs)
                                self.save_wav_file(audio, filepath, metadata)
                                sample_list.append({'file': str(filepath), **metadata})
                            else:
                                sample_list.append({'audio': audio, 'file': str(filepath), **metadata})

                        # Check for interactive pause (after each note across all velocity/RR layers)
                        # Only check after completing all layers for this note
                        if rr_layer == self.roundrobin_layers - 1 and vel_layer == self.velocity_layers - 1:
                            display.increment_note()

                            # Check for MIDI range cycle completion pause
                            if (midi_range_enabled and self.interactive_pause_after_range and
                                (note_idx + 1) % midi_range_size == 0 and
                                (note_idx + 1) < total_notes):
                                # Pause after completing a full MIDI range cycle
                                logging.info(
                                    "Completed MIDI range cycle (%s notes sampled)", midi_range_size
                                )
                                import sys
                                message = (
                                    f"{self.interactive_prompt} (MIDI range cycle complete - "
                                    f"press Enter to continue"
                                )
                                if self.interactive_auto_resume > 0:
                                    message += f" or wait {self.interactive_auto_resume:.0f}s)"
                                else:
                                    message += ")"

                                if self.interactive_auto_resume > 0:
                                    # Auto-resume pause with countdown
                                    if display:
                                        import time as time_module
                                        if sys.platform == 'win32':
                                            import msvcrt
                                            start_time = time_module.time()
                                            last_update = 0
                                            while True:
                                                elapsed = time_module.time() - start_time
                                                remaining = self.interactive_auto_resume - elapsed
                                                if remaining <= 0:
                                                    break
                                                if msvcrt.kbhit():
                                                    msvcrt.getch()
                                                    display.set_pause_state(False)
                                                    logging.info("User pressed key - resuming...")
                                                    break
                                                if elapsed - last_update >= 0.5:
                                                    progress = elapsed / self.interactive_auto_resume
                                                    display.set_pause_state(True, message, progress, remaining)
                                                    last_update = elapsed
                                                time_module.sleep(0.1)
                                            display.set_pause_state(False)
                                        else:
                                            import termios, tty, select
                                            old_settings = termios.tcgetattr(sys.stdin)
                                            try:
                                                tty.setcbreak(sys.stdin.fileno())
                                                start_time = time_module.time()
                                                last_update = 0
                                                while True:
                                                    elapsed = time_module.time() - start_time
                                                    remaining = self.interactive_auto_resume - elapsed
                                                    if remaining <= 0:
                                                        break
                                                    if select.select([sys.stdin], [], [], 0)[0]:
                                                        sys.stdin.read(1)
                                                        display.set_pause_state(False)
                                                        logging.info("User pressed key - resuming...")
                                                        break
                                                    if elapsed - last_update >= 0.5:
                                                        progress = elapsed / self.interactive_auto_resume
                                                        display.set_pause_state(True, message, progress, remaining)
                                                        last_update = elapsed
                                                    time_module.sleep(0.1)
                                                display.set_pause_state(False)
                                            finally:
                                                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                                else:
                                    # Wait for Enter keypress
                                    if display:
                                        display.set_pause_state(True, message, 0.0, 0.0)
                                        input()
                                        display.set_pause_state(False)
                                        logging.info("User pressed Enter - resuming...")
                            else:
                                # Standard pause_interval check
                                self.check_interactive_pause(display)

                        # Pause between samples
                        if self.pause_time > 0:
                            display.update(note, velocity, rr_layer, vel_layer, "Pausing", midi_msgs)
                            time.sleep(self.pause_time)

        finally:
            # Stop display
            display.stop()
            
            # Re-enable console logging
            if console_handler:
                console_handler.setLevel(logging.INFO)

        # Apply patch normalization if enabled
        if self.patch_normalize and self.recorded_samples:
            self.apply_patch_normalization()

            # Save all normalized samples
            for sample_info in sample_list:
                if 'audio' in sample_info:
                    audio = sample_info.pop('audio')
                    filepath = Path(sample_info['file'])
                    metadata = {k: v for k, v in sample_info.items() if k != 'file'}
                    self.save_wav_file(audio, filepath, metadata)

        return sample_list

    def apply_patch_normalization(self, target_level: float = 0.95) -> None:
        """
        Normalize all recorded samples to the same peak level.

        Args:
            target_level: Target peak amplitude (0.0-1.0)
        """
        if not self.recorded_samples:
            return

        # Find global peak across all samples
        global_peak = max(np.abs(audio).max() for audio, _ in self.recorded_samples)

        if global_peak > 0:
            scale_factor = target_level / global_peak

            # Apply normalization to all samples
            for i, (audio, metadata) in enumerate(self.recorded_samples):
                self.recorded_samples[i] = (audio * scale_factor, metadata)

            logging.info("Patch normalization applied: global peak %.3f -> %s", global_peak, target_level)

    def generate_sfz(self, sample_list: List[Dict], output_path: Path = None) -> bool:
        """
        Generate SFZ mapping file.

        Delegates to FileManager.

        Args:
            sample_list: List of sample metadata dictionaries
            output_path: Output SFZ file path

        Returns:
            True if successful, False otherwise
        """
        return self.file_manager.generate_sfz(sample_list, output_path)

    def _apply_postprocessing(self, sample_list: List[Dict], postprocessing_config: Dict) -> None:
        """
        Apply postprocessing operations to recorded samples.
        
        This runs AFTER all sampling is complete for the patch.

        Args:
            sample_list: List of sample metadata dictionaries
            postprocessing_config: Postprocessing configuration from YAML
        """
        from src.postprocess.processor import PostProcessor

        # Check if any postprocessing is enabled
        has_operations = any([
            postprocessing_config.get('patch_normalize'),
            postprocessing_config.get('sample_normalize'),
            postprocessing_config.get('gain_db', 0.0) != 0.0,
            postprocessing_config.get('trim_silence'),
            postprocessing_config.get('auto_loop'),
            postprocessing_config.get('dc_offset_removal'),
            postprocessing_config.get('convert_bitdepth')
        ])

        if not has_operations:
            logging.info("No postprocessing operations enabled")
            return

        # Collect sample file paths
        sample_paths = []
        for sample_info in sample_list:
            filepath = sample_info.get('file')
            if filepath and Path(filepath).exists():
                sample_paths.append(str(filepath))

        if not sample_paths:
            logging.warning("No sample files found for postprocessing")
            return

        # Build operations dictionary
        operations = {
            'gain_db': postprocessing_config.get('gain_db', 0.0),
            'patch_normalize': postprocessing_config.get('patch_normalize', False),
            'sample_normalize': postprocessing_config.get('sample_normalize', False),
            'trim_silence': postprocessing_config.get('trim_silence', False),
            'silence_threshold': getattr(self, 'detected_noise_threshold', postprocessing_config.get('silence_threshold', -60.0)),
            'dc_offset_removal': postprocessing_config.get('dc_offset_removal', False),
            'auto_loop': postprocessing_config.get('auto_loop', False),
            'convert_bitdepth': postprocessing_config.get('convert_bitdepth'),
            'dither': postprocessing_config.get('dither', False)
        }

        # Run postprocessing (completely isolated from sampling)
        processor = PostProcessor()
        processor.process_patch(sample_paths, operations)

    def _export_formats(self, export_config: Dict) -> None:
        """
        Export multisample to additional sampler formats.

        Args:
            export_config: Export configuration from YAML
        """
        formats = export_config.get('formats', [])
        
        # Remove 'sfz' from formats list since it's already created
        formats = [f for f in formats if f.lower() != 'sfz']
        
        if not formats:
            return

        print("\n" + "="*70)
        print("EXPORTING TO ADDITIONAL FORMATS")
        print("="*70)

        # Find SFZ file
        sfz_file = self.multisample_folder / f'{self.multisample_name}.sfz'
        samples_folder = self.output_folder
        
        if not sfz_file.exists():
            logging.error(f"SFZ file not found: {sfz_file}")
            print(f"[ERROR] SFZ file not found: {sfz_file}")
            return

        for fmt in formats:
            fmt_lower = fmt.lower()
            
            if fmt_lower == 'qpat':
                print(f"\n[EXPORT] Converting to Waldorf QPAT format...")
                try:
                    from src.export.export_qpat import export_to_qpat
                    qpat_config = export_config.get('qpat', {})
                    location = qpat_config.get('location', 2)
                    optimize_audio = qpat_config.get('optimize_audio', False)
                    
                    success = export_to_qpat(
                        output_folder=str(self.multisample_folder),
                        multisample_name=self.multisample_name,
                        sfz_file=str(sfz_file),
                        samples_folder=str(samples_folder),
                        location=location,
                        optimize_audio=optimize_audio
                    )
                    if success:
                        print(f"[SUCCESS] Exported to QPAT: {self.multisample_name}.qpat")
                    else:
                        print(f"[ERROR] Failed to export QPAT")
                except Exception as e:
                    logging.error(f"QPAT export failed: {e}", exc_info=True)
                    print(f"[ERROR] QPAT export failed: {e}")
            
            elif fmt_lower == 'waldorf_map':
                print(f"\n[EXPORT] Converting to Waldorf Sample Map format...")
                try:
                    from src.export.export_waldorf_sample_map import export_to_waldorf_map
                    waldorf_config = export_config.get('waldorf_map', export_config.get('qpat', {}))
                    location = waldorf_config.get('location', 2)
                    
                    success = export_to_waldorf_map(
                        output_folder=str(self.multisample_folder),
                        map_name=self.multisample_name,
                        sfz_file=str(sfz_file),
                        samples_folder=str(samples_folder),
                        location=location
                    )
                    if success:
                        print(f"[SUCCESS] Exported to Waldorf Map: {self.multisample_name}.map")
                    else:
                        print(f"[ERROR] Failed to export Waldorf Map")
                except Exception as e:
                    logging.error(f"Waldorf Map export failed: {e}", exc_info=True)
                    print(f"[ERROR] Waldorf Map export failed: {e}")
            
            elif fmt_lower in ['ableton', 'exs24', 'exs', 'sxt']:
                print(f"[TODO] {fmt.upper()} export not yet implemented")
            else:
                print(f"[ERROR] Unknown export format: {fmt}")

        print("\n" + "="*70)
        print("EXPORT COMPLETE")
        print("="*70 + "\n")

    def cleanup(self) -> None:
        """Close MIDI ports and clean up resources."""
        if self.midi_input_port:
            self.midi_input_port.close()
            logging.debug("MIDI input port closed")

        if self.midi_output_port:
            self.midi_output_port.close()
            logging.debug("MIDI output port closed")
            
        # Cleanup audio engine to release ASIO devices
        if hasattr(self.audio_engine, 'cleanup'):
            self.audio_engine.cleanup()
        else:
            # Fallback for older AudioEngine versions
            try:
                import sounddevice as sd
                sd.stop()
                logging.debug("Audio operations stopped")
            except Exception as e:
                logging.warning(f"Failed to stop audio operations: {e}")

    def check_output_folder(self) -> bool:
        """
        Check if output folder exists and prompt user for action.

        Returns:
            True to continue, False to abort
        """
        if self.multisample_folder.exists():
            # In test mode, just warn
            if self.test_mode:
                logging.warning("Multisample folder already exists: %s", self.multisample_folder)
                logging.info("Test mode: Will overwrite existing files")
                return True

            print(f"\nWARNING: Multisample folder already exists: {self.multisample_folder}")
            print("This folder may contain samples from a previous session.")
            print("\nOptions:")
            print("  1) Delete folder and continue")
            print("  2) Use different name")
            print("  3) Cancel")

            while True:
                choice = input("\nSelect option (1-3): ").strip()

                if choice == '1':
                    # Delete folder
                    import shutil
                    try:
                        shutil.rmtree(self.multisample_folder)
                        logging.info("Deleted existing folder: %s", self.multisample_folder)
                        return True
                    except Exception as e:
                        logging.error("Failed to delete folder: %s", e)
                        print(f"Error deleting folder: {e}")
                        return False

                elif choice == '2':
                    # Ask for new name
                    new_name = input("Enter new multisample name: ").strip()
                    if new_name:
                        self.multisample_name = new_name
                        self.multisample_folder = self.base_output_folder / self.multisample_name
                        self.output_folder = self.multisample_folder / 'samples'
                        
                        # Update FileManager with new name and folders
                        self.file_manager.multisample_name = new_name
                        self.file_manager.multisample_folder = self.multisample_folder
                        self.file_manager.output_folder = self.output_folder
                        
                        logging.info("Changed multisample name to: %s", self.multisample_name)
                        # Check again recursively
                        return self.check_output_folder()
                    else:
                        print("Invalid name. Please try again.")

                elif choice == '3':
                    print("Cancelled by user")
                    return False

                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")

        return True

    def show_sampling_summary(self, start_note: int, end_note: int, interval: int) -> bool:
        """
        Display sampling summary and ask for user confirmation.

        Args:
            start_note: Starting MIDI note
            end_note: Ending MIDI note
            interval: Note interval in semitones

        Returns:
            True to continue, False to abort
        """
        # Calculate sample count
        num_notes = len(range(start_note, end_note + 1, interval))
        total_samples = num_notes * self.velocity_layers * self.roundrobin_layers

        # Calculate duration per sample
        sample_duration = self.hold_time + self.release_time
        total_duration_seconds = total_samples * (sample_duration + self.pause_time)
        total_duration_minutes = total_duration_seconds / 60

        # Calculate file size
        # Formula: samples * samplerate * duration * channels * (bitdepth/8)
        bytes_per_sample = self.channels * (self.bitdepth // 8)
        frames_per_file = int(self.samplerate * sample_duration)
        bytes_per_file = frames_per_file * bytes_per_sample
        total_bytes = total_samples * bytes_per_file
        total_mb = total_bytes / (1024 * 1024)

        # Get MIDI settings summary
        velocity_midi = self.sampling_midi_config.get('velocity_midi_control', [])
        roundrobin_midi = self.sampling_midi_config.get('roundrobin_midi_control', [])

        print("\n" + "="*90)
        print(" "*32 + "SAMPLING SUMMARY")
        print("="*90)
        
        # Show real-time audio monitoring first
        if not self._show_realtime_monitoring_section():
            return False
        
        # Three-column layout
        col_width = 28
        sep = "  │  "
        
        print("\n" + "="*90)
        print(f"{'OUTPUT & SAMPLES':<{col_width}}{sep}{'AUDIO & TIMING':<{col_width}}{sep}{'MIDI & CONTROL':<{col_width}}")
        print("─" * col_width + sep + "─" * col_width + sep + "─" * col_width)
        
        # Column 1: Output & Samples
        col1_lines = []
        col1_lines.append(f"Name: {self.multisample_name}")
        col1_lines.append(f"Location: {os.path.basename(self.multisample_folder)}")
        col1_lines.append(f"Format: {self.output_format.upper()}")
        col1_lines.append("")
        col1_lines.append(f"Note range: {start_note}-{end_note} ({interval})")
        col1_lines.append(f"Notes: {num_notes}")
        col1_lines.append(f"Velocity layers: {self.velocity_layers}")
        col1_lines.append(f"Round-robin: {self.roundrobin_layers}")
        col1_lines.append(f"Total samples: {total_samples}")
        col1_lines.append("")
        col1_lines.append("Estimates:")
        col1_lines.append(f"  Duration: {total_duration_minutes:.1f} min")
        col1_lines.append(f"  Disk space: {total_mb:.1f} MB")
        
        # Column 2: Audio & Timing
        col2_lines = []
        col2_lines.append(f"Sample rate: {self.samplerate} Hz")
        col2_lines.append(f"Bit depth: {self.bitdepth} bit")
        col2_lines.append(f"Channels: {self.channels} ({'stereo' if self.channels == 2 else 'mono'})")
        
        # Audio interface info
        device_info = self._get_audio_device_info()
        col2_lines.append(f"Device: {device_info}")
        
        # Input and monitor channels
        input_channels = self.audio_config.get('input_channels', '')
        monitor_channels = self.audio_config.get('monitor_channels', '')
        if input_channels:
            col2_lines.append(f"Input ch: {input_channels}")
        if monitor_channels:
            col2_lines.append(f"Monitor ch: {monitor_channels}")
        
        # Audio engine settings (gain, blocksize, monitoring)
        gain_db = getattr(self.audio_engine, 'gain_db', 0.0)
        blocksize = getattr(self.audio_engine, 'blocksize', None)
        col2_lines.append(f"Gain: {gain_db:+.1f} dB" if gain_db != 0 else "Gain: 0 dB (unity)")
        if blocksize:
            col2_lines.append(f"Buffer: {blocksize} samples")
        col2_lines.append(f"Monitoring: {'On' if self.enable_monitoring else 'Off'}")
        
        col2_lines.append("")
        col2_lines.append("Timing:")
        col2_lines.append(f"  Hold: {self.hold_time:.2f}s")
        col2_lines.append(f"  Release: {self.release_time:.2f}s")
        col2_lines.append(f"  Pause: {self.pause_time:.2f}s")
        col2_lines.append(f"  Per sample: {sample_duration + self.pause_time:.2f}s")
        
        # Post-processing info
        postprocessing_config = self.config.get('postprocessing', {})
        col2_lines.append("")
        col2_lines.append("Post-processing:")
        auto_loop = postprocessing_config.get('auto_loop', False)
        trim_silence = postprocessing_config.get('trim_silence', False)
        normalize = postprocessing_config.get('normalize', False)
        col2_lines.append(f"  Auto-loop: {'On' if auto_loop else 'Off'}")
        col2_lines.append(f"  Trim silence: {'On' if trim_silence else 'Off'}")
        col2_lines.append(f"  Normalize: {'On' if normalize else 'Off'}")
        
        # Column 3: MIDI & Control
        col3_lines = []
        midi_input_name = self.midi_config.get('midi_input_name', 'None')
        midi_output_name = self.midi_config.get('midi_output_name', 'None')
        midi_channel = self.midi_config.get('midi_channel', 1)
        
        col3_lines.append(f"Input: {self._truncate_text(midi_input_name, 18)}")
        col3_lines.append(f"Output: {self._truncate_text(midi_output_name, 17)}")
        col3_lines.append(f"Channel: {midi_channel}")
        
        if hasattr(self, 'midi_message_delay') and self.midi_message_delay > 0:
            col3_lines.append(f"Delay: {self.midi_message_delay:.3f}s")
        
        col3_lines.append("")
        col3_lines.append("Control:")
        
        # General MIDI control
        general_cc = self.midi_config.get('cc_messages', {})
        general_pc = self.midi_config.get('program_change')
        if general_cc:
            cc_list = [f"{cc}:{val}" for cc, val in list(general_cc.items())[:2]]
            col3_lines.append(f"  CC: {', '.join(cc_list)}")
        if general_pc is not None:
            col3_lines.append(f"  Program: {general_pc}")
        
        # Velocity layers with MIDI control
        if velocity_midi:
            col3_lines.append(f"  Vel layers: {len(velocity_midi)} w/ MIDI")
        elif self.velocity_layers > 1:
            col3_lines.append(f"  Vel layers: {self.velocity_layers}")
        
        # Round-robin with MIDI control
        if roundrobin_midi:
            col3_lines.append(f"  RR layers: {len(roundrobin_midi)} w/ MIDI")
        elif self.roundrobin_layers > 1:
            col3_lines.append(f"  RR layers: {self.roundrobin_layers}")
        
        # Interactive sampling info
        if self.interactive_config:
            col3_lines.append("")
            col3_lines.append("Interactive:")
            pause_interval = self.interactive_config.get('pause_interval', 
                           self.interactive_config.get('every', 0))
            if pause_interval > 0:
                col3_lines.append(f"  Pause every: {pause_interval}")
        
        # Export formats
        export_config = self.config.get('export', {})
        export_formats = export_config.get('formats', ['sfz'])
        col3_lines.append("")
        col3_lines.append("Export:")
        col3_lines.append(f"  Formats: {', '.join(format.upper() for format in export_formats)}")
        
        # Print three columns
        max_lines = max(len(col1_lines), len(col2_lines), len(col3_lines))
        
        for i in range(max_lines):
            col1 = col1_lines[i] if i < len(col1_lines) else ""
            col2 = col2_lines[i] if i < len(col2_lines) else ""
            col3 = col3_lines[i] if i < len(col3_lines) else ""
            
            print(f"{col1:<{col_width}}{sep}{col2:<{col_width}}{sep}{col3:<{col_width}}")

        print("="*90)

        # Skip confirmation in batch mode
        if self.batch_mode:
            logging.info("Batch mode: auto-proceeding with sampling")
            return True

        # Ask for final confirmation
        while True:
            choice = input("\nConfirm: Start sampling now? (y/n): ").strip().lower()
            if choice == 'y':
                return True
            elif choice == 'n':
                print("Sampling cancelled by user")
                return False
            else:
                print("Please enter 'y' or 'n'")

    def _show_realtime_monitoring_section(self):
        """Show the real-time monitoring section integrated into the summary."""
        print("\n" + "="*90)
        print(" "*30 + "REAL-TIME AUDIO MONITORING")
        print("="*90)
        
        try:
            # Get audio settings for monitoring
            device_index = getattr(self.audio_engine, 'input_device', None)
            sample_rate = self.samplerate
            channels = getattr(self.audio_engine, 'device_channels', 2)
            channel_offset = getattr(self.audio_engine, 'channel_offset', 0)
            
            # Check if we can get the actual input channels config
            input_channels_config = self.audio_config.get('input_channels', '')
            if input_channels_config and '-' in input_channels_config:
                # Parse "3-4" format to get offset (3-1=2 for 0-based indexing)
                start_ch = int(input_channels_config.split('-')[0]) - 1
                channel_offset = start_ch
                logging.info(f"Using channel offset {channel_offset} from config '{input_channels_config}'")
                
            # Debug channel configuration
            logging.info(f"Monitor config: device={device_index}, rate={sample_rate}, "
                        f"channels={channels}, offset={channel_offset}")
            
            # Import here to avoid circular dependency
            from .realtime_monitor import show_pre_sampling_monitor
            
            print(f"Audio Device: {self._get_audio_device_info()} | Sample Rate: {sample_rate} Hz | Channels: {channels}")
            
            # Show actual channel names instead of confusing offset
            input_channels_config = self.audio_config.get('input_channels', '')
            if input_channels_config:
                print(f"Input Channels: {input_channels_config} (configured channels)")
            else:
                print(f"Input Channels: Default (system default channels)")
                
            print("Check your audio levels before sampling. Optimal: -6dB to -3dB (yellow/red zone)")
            print()
            
            # Get monitor device/channel info from audio engine
            monitor_channel_offset = getattr(self.audio_engine, 'monitor_channel_offset', channel_offset)
            output_device = getattr(self.audio_engine, 'output_device', device_index)
            
            proceed = show_pre_sampling_monitor(
                device_index=device_index,
                sample_rate=sample_rate,
                channels=channels,
                channel_offset=channel_offset,
                monitor_channel_offset=monitor_channel_offset,
                output_device_index=output_device,
                title="Pre-Sampling Audio Monitor"
            )
            
            if not proceed:
                print("\nSampling cancelled by user")
                return False
                
        except ImportError as e:
            logging.warning(f"Real-time monitoring module not available: {e}")
            print("[WARNING] Real-time monitoring not available - realtime_monitor module missing")
            print("Continuing without audio level monitoring...")
            return True  # Don't block sampling if monitoring unavailable
            
        except Exception as e:
            logging.warning(f"Could not show audio monitoring: {e}")
            print(f"[WARNING] Audio monitoring unavailable: {str(e)}")
            print("Check audio interface settings. Continuing without monitoring...")
            return True  # Don't block sampling if monitoring fails
            
        return True

    def _get_audio_device_info(self):
        """Get compact audio device information for display."""
        try:
            if (hasattr(self.audio_engine, 'input_device') and 
                self.audio_engine.input_device is not None):
                device_index = self.audio_engine.input_device
                try:
                    import sounddevice as sd
                    all_devices = sd.query_devices()
                    if device_index < len(all_devices):
                        input_info = sd.query_devices(device_index)
                        device_name = input_info['name']
                        return self._truncate_text(device_name, 20)
                    else:
                        return f"Device #{device_index} (invalid)"
                except Exception as e:
                    return f"Device #{device_index} (error)"
            else:
                return "Default"
        except Exception:
            return "Unknown"

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to fit in specified length."""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def run(self) -> bool:
        """
        Main sampling workflow: setup, sample, generate output files.

        Returns:
            True if sampling completed successfully, False otherwise
        """
        try:
            # Setup
            logging.info("=== AutosamplerT Starting ===")

            # Check output folder
            if not self.check_output_folder():
                logging.info("Sampling cancelled")
                return False

            if not self.setup_audio():
                logging.error("Audio setup failed - aborting")
                return False

            if not self.setup_midi():
                logging.error("MIDI setup failed - cannot continue without MIDI output")
                logging.error("Please check that your MIDI device is connected and powered on")
                return False

            # Parse note range - support multiple formats:
            # 1. sampling_midi.note_range dict (new preferred location)
            # 2. midi_interface.note_range dict (legacy)
            # 3. sampling.note_range_start/end/interval individual keys (legacy)
            note_range = self.sampling_midi_config.get('note_range', self.midi_config.get('note_range', {}))
            if isinstance(note_range, str):
                try:
                    note_range = json.loads(note_range)
                except:
                    note_range = {}

            # Try dict format first, then fall back to individual keys in sampling config
            start_note = note_range.get('start') or self.sampling_config.get('note_range_start', 36)
            end_note = note_range.get('end') or self.sampling_config.get('note_range_end', 96)
            interval = note_range.get('interval') or self.sampling_config.get('note_range_interval', 1)

            # Get MIDI channel
            channels = self.midi_config.get('midi_channels', [0])
            if isinstance(channels, list):
                channel = channels[0] if channels else 0
            else:
                channel = 0

            logging.info("Sampling range: Note %s-%s, interval %s", start_note, end_note, interval)
            logging.info("Velocity layers: %s, Round-robin: %s", self.velocity_layers, self.roundrobin_layers)
            logging.info(
                "Timing: hold=%.2fs, release=%.2fs, pause=%.2fs",
                self.hold_time, self.release_time, self.pause_time
            )

            # Check if patch iteration is enabled
            patch_iteration = self.sampling_midi_config.get('patch_iteration', {})
            if patch_iteration.get('enabled', False):
                return self._run_with_patch_iteration(start_note, end_note, interval, channel, patch_iteration)

            # Show summary and get confirmation (skip in test mode)
            if not self.test_mode:
                if not self.show_sampling_summary(start_note, end_note, interval):
                    logging.info("Sampling cancelled by user")
                    return False

            # Sample the range
            sample_list = self.sample_range(start_note, end_note, interval, channel)

            logging.info("Sampling complete: %s samples recorded", len(sample_list))

            # Generate SFZ output format (always, even in test mode)
            if self.output_format == 'sfz':
                self.generate_sfz(sample_list)

            # Apply postprocessing if enabled in config
            postprocessing_config = self.config.get('postprocessing', {})
            if postprocessing_config and not self.test_mode:
                self._apply_postprocessing(sample_list, postprocessing_config)

            # Export to additional formats if configured
            export_config = self.config.get('export', {})
            if export_config and not self.test_mode:
                self._export_formats(export_config)

            logging.info("=== AutosamplerT Complete ===")
            return True

        except KeyboardInterrupt:
            logging.info("Sampling interrupted by user")
            return False
        except Exception as e:
            logging.error(f"Sampling failed: {e}", exc_info=True)
            return False
        finally:
            self.cleanup()

    def _run_with_patch_iteration(self, start_note: int, end_note: int, interval: int,
                                   channel: int, patch_iteration: Dict) -> bool:
        """
        Run sampling with patch iteration - sample multiple patches with program changes.

        Args:
            start_note: Starting MIDI note
            end_note: Ending MIDI note
            interval: Note interval
            channel: MIDI channel
            patch_iteration: Patch iteration configuration

        Returns:
            True if all patches sampled successfully
        """
        program_start = patch_iteration.get('program_start', 0)
        program_end = patch_iteration.get('program_end', 0)
        auto_naming = patch_iteration.get('auto_naming', True)
        base_name = patch_iteration.get('name_template', 'Patch')

        # Store original multisample name
        original_name = self.multisample_name

        print("\n" + "="*70)
        print("PATCH ITERATION MODE")
        print("="*70)
        print(f"Sampling {program_end - program_start + 1} patches (program {program_start}-{program_end})")
        print(f"Notes per patch: {start_note} to {end_note} (interval: {interval})")
        print(f"Auto-naming: {'Enabled' if auto_naming else 'Disabled'}")
        print("="*70)

        if not self.test_mode:
            response = input("\nContinue? [y/N]: ")
            if response.lower() != 'y':
                logging.info("Sampling cancelled by user")
                return False

        success_count = 0
        failed_patches = []

        # Iterate through programs
        for program in range(program_start, program_end + 1):
            print(f"\n{'='*70}")
            print(f"Sampling Program {program} ({program - program_start + 1}/{program_end - program_start + 1})")
            print(f"{'='*70}")

            # Generate patch name
            if auto_naming:
                patch_name = f"{base_name}_{program:03d}"
            else:
                patch_name = f"{original_name}_{program:03d}"

            # Update multisample name and folder
            self.multisample_name = patch_name
            self.multisample_folder = self.base_output_folder / self.multisample_name
            self.output_folder = self.multisample_folder / 'samples'

            print(f"Patch name: {patch_name}")

            # Send program change
            if self.midi_controller:
                self.midi_controller.send_program_change(program, channel)
                time.sleep(self.midi_message_delay * 2)  # Extra delay after program change
                print(f"Program change sent: {program}")

            try:
                # Sample the range for this patch
                sample_list = self.sample_range(start_note, end_note, interval, channel)

                logging.info("Program %s complete: %s samples recorded", program, len(sample_list))
                print(f"[SUCCESS] Program {program}: {len(sample_list)} samples")

                # Generate SFZ (always, even in test mode)
                if self.output_format == 'sfz':
                    self.generate_sfz(sample_list)

                # Apply postprocessing if enabled
                postprocessing_config = self.config.get('postprocessing', {})
                if postprocessing_config and not self.test_mode:
                    self._apply_postprocessing(sample_list, postprocessing_config)

                # Export to additional formats
                export_config = self.config.get('export', {})
                if export_config and not self.test_mode:
                    self._export_formats(export_config)

                success_count += 1

            except Exception as e:
                logging.error("Failed to sample program %s: %s", program, e, exc_info=True)
                print(f"[ERROR] Program {program} failed: {e}")
                failed_patches.append(program)

            # Clear recorded samples for next patch
            self.recorded_samples = []

        # Restore original name
        self.multisample_name = original_name
        self.multisample_folder = self.base_output_folder / self.multisample_name
        self.output_folder = self.multisample_folder / 'samples'

        # Summary
        print(f"\n{'='*70}")
        print("PATCH ITERATION COMPLETE")
        print(f"{'='*70}")
        print(f"Successful: {success_count}/{program_end - program_start + 1}")
        if failed_patches:
            print(f"Failed programs: {', '.join(map(str, failed_patches))}")
        print(f"{'='*70}")

        return len(failed_patches) == 0


def main() -> None:
    """Example usage of AutoSampler."""
    import yaml

    # Load config
    config_path = Path(__file__).parent.parent / 'conf' / 'autosamplerT_config.yaml'

    if not config_path.exists():
        logging.error("Config file not found: %s", config_path)
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Create and run sampler
    sampler = AutoSampler(config)
    success = sampler.run()

    if success:
        logging.info("Sampling completed successfully")
    else:
        logging.error("Sampling failed")


if __name__ == "__main__":
    main()
