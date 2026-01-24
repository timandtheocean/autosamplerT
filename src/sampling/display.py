"""
Terminal display and logging utilities for sampling progress.

This module provides:
- LogBufferHandler: Logging handler that keeps recent log messages in a buffer
- SamplingDisplay: Terminal UI for real-time sampling progress display
"""

import logging
import sys
import io
import traceback
from typing import Optional, List, Dict, Any, Union

# Force UTF-8 encoding for stdout on Windows to support Unicode characters
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # If reconfiguration fails, continue with default encoding


class LogBufferHandler(logging.Handler):
    """Logging handler that keeps the last N log messages in a buffer."""

    def __init__(self, max_lines=10):
        super().__init__()
        self.log_buffer = []
        self.max_lines = max_lines

    def emit(self, record):
        try:
            msg = self.format(record)
            # Validate and parse log message
            parsed_msg = self._parse_log_message(msg)
            self.log_buffer.append(parsed_msg)
            if len(self.log_buffer) > self.max_lines:
                self.log_buffer.pop(0)
        except Exception as e:
            # Enhanced error logging
            self._log_parse_error("Failed to process log message", e, record)
            self.handleError(record)

    def _parse_log_message(self, msg: str) -> str:
        """Parse and validate log message format."""
        try:
            if not isinstance(msg, str):
                raise ValueError(f"Log message must be string, got {type(msg)}")
            
            # Truncate overly long messages
            max_length = 1000
            if len(msg) > max_length:
                msg = msg[:max_length - 3] + "..."
                logging.debug(f"Truncated log message to {max_length} characters")
            
            # Remove any control characters that might break display
            msg = ''.join(char for char in msg if ord(char) >= 32 or char in '\t\n')
            
            return msg
        except Exception as e:
            logging.error(f"Log message parsing failed: {e}")
            return f"[PARSE ERROR] {str(msg)[:50]}..."
    
    def _log_parse_error(self, context: str, error: Exception, record=None):
        """Log parsing errors with full context."""
        error_msg = f"{context}: {error}"
        if record:
            error_msg += f" | Record: {record.getMessage()[:100]}"
        logging.error(error_msg, exc_info=True)

    def get_logs(self):
        return list(self.log_buffer)


class SamplingDisplay:
    """
    Manages the static terminal display during sampling.
    Provides progress bars and real-time statistics without scrolling.
    """

    def __init__(self, total_notes: int, velocity_layers: int, roundrobin_layers: int,
                 hold_time: float, release_time: float, pause_time: float, log_handler=None):
        """
        Initialize the sampling display.

        Args:
            total_notes: Total number of notes to sample
            velocity_layers: Number of velocity layers
            roundrobin_layers: Number of round-robin layers
            hold_time: Note hold time in seconds
            release_time: Release time in seconds
            pause_time: Pause between samples in seconds
            log_handler: LogBufferHandler instance for displaying recent logs
        """
        try:
            # Parse and validate all parameters
            self.total_notes = self._parse_int_parameter('total_notes', total_notes, min_val=1, max_val=10000)
            self.velocity_layers = self._parse_int_parameter('velocity_layers', velocity_layers, min_val=1, max_val=127)
            self.roundrobin_layers = self._parse_int_parameter('roundrobin_layers', roundrobin_layers, min_val=1, max_val=100)
            self.hold_time = self._parse_float_parameter('hold_time', hold_time, min_val=0.1, max_val=60.0)
            self.release_time = self._parse_float_parameter('release_time', release_time, min_val=0.1, max_val=60.0)
            self.pause_time = self._parse_float_parameter('pause_time', pause_time, min_val=0.0, max_val=10.0)
            
            # Calculate derived values
            self.samples_per_note = self.velocity_layers * self.roundrobin_layers
            self.total_samples = self.total_notes * self.samples_per_note
            
            # Validate log handler
            self.log_handler = self._validate_log_handler(log_handler)
            
            logging.info(f"SamplingDisplay initialized: {self.total_notes} notes, "
                        f"{self.velocity_layers} vel layers, {self.roundrobin_layers} RR layers, "
                        f"total {self.total_samples} samples")
                        
        except Exception as e:
            logging.error(f"SamplingDisplay initialization failed: {e}", exc_info=True)
            raise ValueError(f"Invalid display parameters: {e}")

        self.current_note_index = 0
        self.current_sample_index = 0
        self.current_note = 60
        self.current_velocity = 127
        self.current_rr = 0
        self.current_phase = "Idle"
        self.midi_messages = []

        # Interactive pause state
        self.is_paused = False
        self.pause_message = ""
        self.pause_progress = 0.0
        self.pause_remaining = 0.0
        
        # Monitoring display state
        self.monitoring_data = None

        # Get terminal width
        self.terminal_width = self._get_terminal_width()

        # ANSI codes
        self.CLEAR_SCREEN = '\033[2J\033[H'
        self.HIDE_CURSOR = '\033[?25l'
        self.SHOW_CURSOR = '\033[?25h'

        # Unicode/ASCII fallback characters
        self._use_unicode = self._check_unicode_support()
        if self._use_unicode:
            self.FILLED_CHAR = '█'
            self.EMPTY_CHAR = '░'
            self.PAUSE_ICON = '⏸'
        else:
            self.FILLED_CHAR = '#'
            self.EMPTY_CHAR = '-'
            self.PAUSE_ICON = '||'
        
    def _parse_int_parameter(self, name: str, value: Any, min_val: int = None, max_val: int = None) -> int:
        """Parse and validate integer parameter."""
        try:
            if isinstance(value, str):
                parsed_val = int(value)
            elif isinstance(value, (int, float)):
                parsed_val = int(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to int")
            
            if min_val is not None and parsed_val < min_val:
                raise ValueError(f"{name} must be >= {min_val}, got {parsed_val}")
            if max_val is not None and parsed_val > max_val:
                raise ValueError(f"{name} must be <= {max_val}, got {parsed_val}")
                
            logging.debug(f"Parsed {name}: {parsed_val}")
            return parsed_val
            
        except Exception as e:
            logging.error(f"Failed to parse {name} parameter '{value}': {e}")
            raise ValueError(f"Invalid {name}: {e}")
    
    def _parse_float_parameter(self, name: str, value: Any, min_val: float = None, max_val: float = None) -> float:
        """Parse and validate float parameter."""
        try:
            if isinstance(value, str):
                parsed_val = float(value)
            elif isinstance(value, (int, float)):
                parsed_val = float(value)
            else:
                raise ValueError(f"Cannot convert {type(value)} to float")
            
            if min_val is not None and parsed_val < min_val:
                raise ValueError(f"{name} must be >= {min_val}, got {parsed_val}")
            if max_val is not None and parsed_val > max_val:
                raise ValueError(f"{name} must be <= {max_val}, got {parsed_val}")
                
            logging.debug(f"Parsed {name}: {parsed_val}")
            return parsed_val
            
        except Exception as e:
            logging.error(f"Failed to parse {name} parameter '{value}': {e}")
            raise ValueError(f"Invalid {name}: {e}")
    
    def _validate_log_handler(self, log_handler) -> Optional[LogBufferHandler]:
        """Validate log handler parameter."""
        if log_handler is None:
            return None
        if not isinstance(log_handler, LogBufferHandler):
            logging.warning(f"Invalid log handler type {type(log_handler)}, ignoring")
            return None
        return log_handler

    def _check_unicode_support(self) -> bool:
        """Check if terminal supports Unicode characters."""
        try:
            # Try to encode Unicode characters with the current encoding
            '█░⏸'.encode(sys.stdout.encoding or 'utf-8')
            return True
        except (UnicodeEncodeError, AttributeError, LookupError):
            return False

    def _get_terminal_width(self) -> int:
        """Get the current terminal width."""
        try:
            import shutil
            width = shutil.get_terminal_size().columns
            # Minimum width of 80, maximum of 200 for readability
            return max(80, min(200, width))
        except Exception:
            return 80  # Default fallback

    def start(self):
        """Start the display (clear screen and hide cursor)."""
        print(self.CLEAR_SCREEN + self.HIDE_CURSOR, end='', flush=True)
        # Do an initial render to show the display
        self._render()

    def stop(self):
        """Stop the display (show cursor)."""
        print(self.SHOW_CURSOR, end='', flush=True)

    def update(self, note: int, velocity: int, rr_index: int, vel_layer: int,
               phase: str = "Sampling", midi_msgs: list = None):
        """
        Update the display with current sampling information.

        Args:
            note: Current MIDI note number
            velocity: Current velocity
            rr_index: Round-robin index
            vel_layer: Velocity layer index
            phase: Current phase (e.g., "Sampling", "Recording", "Processing")
            midi_msgs: List of recent MIDI messages sent
        """
        try:
            # Parse and validate all input parameters
            parsed_data = self._parse_update_parameters(
                note, velocity, rr_index, vel_layer, phase, midi_msgs
            )
            
            # Update current state with validated data
            self.current_note = parsed_data['note']
            self.current_velocity = parsed_data['velocity']
            self.current_rr = parsed_data['rr_index']
            self.current_phase = parsed_data['phase']

            # Calculate sample index within current note
            sample_in_note = parsed_data['vel_layer'] * self.roundrobin_layers + parsed_data['rr_index']

            # Calculate overall progress with bounds checking
            self.current_sample_index = min(
                self.current_note_index * self.samples_per_note + sample_in_note,
                self.total_samples
            )

            # Parse and validate MIDI messages
            if parsed_data['midi_msgs']:
                self.midi_messages = self._parse_midi_messages(parsed_data['midi_msgs'])

            self._render()
            
        except Exception as e:
            logging.error(f"Display update failed: {e}", exc_info=True)
            # Continue with safe defaults to avoid breaking the display
            self.current_phase = "Error"
            try:
                self._render()
            except Exception as render_error:
                logging.error(f"Display render failed after update error: {render_error}")
    
    def _parse_update_parameters(self, note: int, velocity: int, rr_index: int, 
                                vel_layer: int, phase: str, midi_msgs: list) -> Dict[str, Any]:
        """Parse and validate update parameters."""
        try:
            parsed = {
                'note': self._parse_int_parameter('note', note, min_val=0, max_val=127),
                'velocity': self._parse_int_parameter('velocity', velocity, min_val=1, max_val=127),
                'rr_index': self._parse_int_parameter('rr_index', rr_index, min_val=0, max_val=self.roundrobin_layers-1),
                'vel_layer': self._parse_int_parameter('vel_layer', vel_layer, min_val=0, max_val=self.velocity_layers-1),
                'phase': self._parse_phase_parameter(phase),
                'midi_msgs': midi_msgs  # Will be validated separately
            }
            
            logging.debug(f"Parsed update parameters: {parsed}")
            return parsed
            
        except Exception as e:
            logging.error(f"Parameter parsing failed in update: {e}")
            raise ValueError(f"Invalid update parameters: {e}")
    
    def _parse_phase_parameter(self, phase: str) -> str:
        """Parse and validate phase parameter."""
        if not isinstance(phase, str):
            raise ValueError(f"Phase must be string, got {type(phase)}")
        
        # Accept any reasonable string as a phase, just limit length
        return phase[:50]  # Limit length to prevent display issues
    
    def _parse_midi_messages(self, midi_msgs: List[Any]) -> List[str]:
        """Parse and validate MIDI messages list."""
        try:
            if not isinstance(midi_msgs, list):
                logging.warning(f"MIDI messages should be list, got {type(midi_msgs)}")
                return []
            
            parsed_msgs = []
            for i, msg in enumerate(midi_msgs[-10:]):  # Limit to last 10 messages
                try:
                    if isinstance(msg, str):
                        # Validate and sanitize string message
                        cleaned_msg = ''.join(char for char in msg if ord(char) >= 32 or char in '\t\n')
                        parsed_msgs.append(cleaned_msg[:200])  # Limit length
                    elif hasattr(msg, '__str__'):
                        parsed_msgs.append(str(msg)[:200])
                    else:
                        parsed_msgs.append(f"[{type(msg).__name__}]")
                except Exception as e:
                    logging.warning(f"Failed to parse MIDI message {i}: {e}")
                    parsed_msgs.append(f"[PARSE ERROR: {str(msg)[:20]}]")
            
            return parsed_msgs[-5:]  # Keep only last 5
            
        except Exception as e:
            logging.error(f"MIDI messages parsing failed: {e}")
            return []

    def increment_note(self):
        """Increment the note counter."""
        self.current_note_index += 1

    def set_pause_state(self, paused: bool, message: str = "", progress: float = 0.0,
                       remaining: float = 0.0):
        """
        Set the pause state and update display.

        Args:
            paused: Whether sampling is paused
            message: Pause message to display
            progress: Pause progress (0.0 to 1.0)
            remaining: Remaining time in seconds
        """
        self.is_paused = paused
        self.pause_message = message
        self.pause_progress = progress
        self.pause_remaining = remaining
        self._render()
    
    def update_monitoring(self, monitor_dict: dict):
        """
        Update monitoring data for display.
        
        Args:
            monitor_dict: Dictionary containing monitoring data (levels, pitch, etc.)
        """
        self.monitoring_data = monitor_dict
        # Render immediately to show real-time monitoring updates
        self._render()

    def _render(self):
        """Render the complete display with error handling."""
        try:
            # Update terminal width (in case window was resized)
            self.terminal_width = self._get_terminal_width()
            
            # Validate current state before rendering
            self._validate_render_state()

            # Move cursor to top-left and clear to end of screen
            print('\033[H\033[J', end='')
            
            # Header
            print("=" * self.terminal_width)
            print("AUTOSAMPLERT - SAMPLING IN PROGRESS".center(self.terminal_width))
            print("=" * self.terminal_width)
            print()

            # Current sample info
            note_name = self._get_note_name(self.current_note)
            print(f"  Current Note:  {note_name} (MIDI {self.current_note})")
            print(f"  Velocity:      {self.current_velocity} "
                  f"(Layer {self._get_vel_layer() + 1}/{self.velocity_layers})")
            print(f"  Round-Robin:   {self.current_rr + 1}/{self.roundrobin_layers}")
            print(f"  Phase:         {self.current_phase}")
            print()

            # Timing info
            print(f"  Hold: {self.hold_time:.1f}s  |  Release: {self.release_time:.1f}s  |  "
                  f"Pause: {self.pause_time:.1f}s")
            print()

            # Progress bars
            progress_bar_width = max(20, int((self.terminal_width * 0.75) - 20))

            # Overall progress
            overall_progress = self._calculate_safe_progress(
                self.current_sample_index, self.total_samples, "overall")
            overall_bar = self._draw_progress_bar(
                overall_progress, progress_bar_width,
                f"Total Progress: {self.current_sample_index}/{self.total_samples} samples")
            print(overall_bar)
            print()

            # Notes progress
            notes_progress = self._calculate_safe_progress(
                self.current_note_index, self.total_notes, "notes")
            notes_bar = self._draw_progress_bar(
                notes_progress, progress_bar_width,
                f"Notes: {self.current_note_index}/{self.total_notes}")
            print(notes_bar)
            print()

            # Interactive pause status (if paused)
            if self.is_paused:
                print("=" * self.terminal_width)
                print(f"  {self.PAUSE_ICON}  INTERACTIVE PAUSE")
                print("=" * self.terminal_width)
                print(f"  {self.pause_message}")
                if self.pause_remaining > 0:
                    bar_width = progress_bar_width
                    filled = int(bar_width * self.pause_progress)
                    bar = self.FILLED_CHAR * filled + self.EMPTY_CHAR * (bar_width - filled)
                    print(f"  [{bar}] {self.pause_remaining:.1f}s")
                print("=" * self.terminal_width)
                print()

            # MIDI messages (last 5)
            if self.midi_messages:
                print("-" * self.terminal_width)
                print("  Recent MIDI Messages:")
                for msg in self.midi_messages:
                    max_msg_len = self.terminal_width - 6
                    if len(msg) > max_msg_len:
                        msg = msg[:max_msg_len - 3] + "..."
                    print(f"    {msg}")
                print("-" * self.terminal_width)

            # Log messages (last 10 lines) - only if there are logs
            if self.log_handler:
                log_lines = self.log_handler.get_logs()
                if log_lines:  # Only show section if there are actual logs
                    print()
                    print("=" * self.terminal_width)
                    print("  Recent Log Messages:")
                    print("=" * self.terminal_width)
                    for log_line in log_lines:
                        max_log_len = self.terminal_width - 4
                        if len(log_line) > max_log_len:
                            log_line = log_line[:max_log_len - 3] + "..."
                        print(f"  {log_line}")
                    print("=" * self.terminal_width)

            # Flush to ensure immediate update
            sys.stdout.flush()
            
        except Exception as e:
            logging.error(f"Display render initialization failed: {e}")
            try:
                print('\033[H\033[J', end='')
                print(f"DISPLAY ERROR: {e}")
                return
            except Exception:
                logging.error("Complete display failure - cannot render anything")
                return
    
    def _validate_render_state(self):
        """Validate current display state before rendering."""
        # Check for reasonable values
        if self.current_note < 0 or self.current_note > 127:
            logging.warning(f"Invalid note value: {self.current_note}, clamping to 0-127")
            self.current_note = max(0, min(127, self.current_note))
        
        if self.current_velocity < 1 or self.current_velocity > 127:
            logging.warning(f"Invalid velocity value: {self.current_velocity}, clamping to 1-127")
            self.current_velocity = max(1, min(127, self.current_velocity))
        
        if self.current_sample_index < 0 or self.current_sample_index > self.total_samples:
            logging.warning(f"Sample index {self.current_sample_index} out of range, clamping")
            self.current_sample_index = max(0, min(self.total_samples, self.current_sample_index))
        
        if self.current_note_index < 0 or self.current_note_index > self.total_notes:
            logging.warning(f"Note index {self.current_note_index} out of range, clamping")
            self.current_note_index = max(0, min(self.total_notes, self.current_note_index))
    
    def _calculate_safe_progress(self, current: int, total: int, context: str) -> float:
        """Calculate progress with error handling and validation."""
        try:
            if total <= 0:
                logging.warning(f"Invalid total for {context} progress: {total}")
                return 0.0
            if current < 0:
                logging.warning(f"Invalid current value for {context} progress: {current}")
                current = 0
            progress = min(1.0, current / total)
            return progress
        except Exception as e:
            logging.error(f"Progress calculation failed for {context}: {e}")
            return 0.0

    def _get_vel_layer(self) -> int:
        """Calculate current velocity layer from sample index."""
        sample_in_note = self._get_sample_in_note()
        return sample_in_note // self.roundrobin_layers

    def _get_sample_in_note(self) -> int:
        """Calculate current sample index within the current note."""
        return self.current_sample_index % self.samples_per_note

    def _draw_progress_bar(self, progress: float, width: int, label: str) -> str:
        """
        Draw a progress bar.

        Args:
            progress: Progress value (0.0 to 1.0)
            width: Width of the progress bar in characters
            label: Label to display above the bar

        Returns:
            Formatted progress bar string
        """
        filled = int(width * progress)
        bar = self.FILLED_CHAR * filled + self.EMPTY_CHAR * (width - filled)
        percentage = int(progress * 100)

        return f"  {label}\n  [{bar}] {percentage}%"

    def _get_note_name(self, note: int) -> str:
        """Convert MIDI note number to note name with error handling."""
        try:
            # Validate note range
            if not isinstance(note, int):
                logging.warning(f"Note must be integer, got {type(note)}: {note}")
                note = int(note)
            
            if note < 0 or note > 127:
                logging.warning(f"MIDI note {note} out of range 0-127, clamping")
                note = max(0, min(127, note))
            
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = (note // 12) - 1
            note_name = note_names[note % 12]
            
            result = f"{note_name}{octave}"
            logging.debug(f"Converted note {note} to {result}")
            return result
            
        except Exception as e:
            logging.error(f"Note name conversion failed for note {note}: {e}")
            return f"NOTE{note}"  # Fallback format
