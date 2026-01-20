"""
Interactive Sampling Handler for AutosamplerT.

Handles interactive pause/resume functionality during sampling.
"""

import logging
import time
import sys


class InteractiveSamplingHandler:
    """
    Manages interactive pauses during sampling.

    Allows user to pause sampling at intervals for manual adjustments
    (e.g., patch changes, filter adjustments on hardware synth).
    """

    def __init__(self, pause_interval: int = 0, auto_resume: float = 0.0,
                 prompt: str = "Paused. Press Enter to continue...",
                 velocity_layers: int = 1, roundrobin_layers: int = 1):
        """
        Initialize interactive sampling handler.

        Args:
            pause_interval: Pause after every N notes (0 = disabled)
            auto_resume: Auto-resume after N seconds (0 = wait for Enter)
            prompt: Prompt message to display when paused
            velocity_layers: Number of velocity layers
            roundrobin_layers: Number of round-robin layers
        """
        self.pause_interval = pause_interval
        self.auto_resume = auto_resume
        self.prompt = prompt
        self.velocity_layers = velocity_layers
        self.roundrobin_layers = roundrobin_layers
        self.notes_sampled = 0

    def check_pause(self, display=None) -> None:
        """
        Check if pause is needed and handle user interaction.

        Args:
            display: SamplingDisplay instance to show pause status
        """
        if self.pause_interval <= 0:
            return

        self.notes_sampled += 1

        if self.notes_sampled % self.pause_interval == 0:
            total_samples = self.notes_sampled * self.velocity_layers * self.roundrobin_layers
            message = f"{self.prompt} (Press Enter to continue"
            if self.auto_resume > 0:
                message += f" or wait {self.auto_resume:.0f}s)"
            else:
                message += ")"

            if self.auto_resume > 0:
                self._handle_auto_resume(display, message)
            else:
                self._handle_manual_resume(display, message)

    def _handle_auto_resume(self, display, message: str) -> None:
        """Handle auto-resume with timeout."""
        if display:
            if sys.platform == 'win32':
                self._auto_resume_windows(display, message)
            else:
                self._auto_resume_unix(display, message)
        else:
            logging.warning("Interactive pause without display - using simple wait")
            time.sleep(self.auto_resume)

    def _auto_resume_windows(self, display, message: str) -> None:
        """Auto-resume implementation for Windows."""
        import msvcrt
        start_time = time.time()
        last_update = 0

        while True:
            elapsed = time.time() - start_time
            remaining = self.auto_resume - elapsed

            if remaining <= 0:
                break

            if msvcrt.kbhit():
                msvcrt.getch()
                display.set_pause_state(False)
                logging.info("User pressed key - resuming...")
                return

            if elapsed - last_update >= 0.5:
                progress = elapsed / self.auto_resume
                display.set_pause_state(True, message, progress, remaining)
                last_update = elapsed

            time.sleep(0.1)

        display.set_pause_state(False)
        logging.info("Auto-resuming after timeout")

    def _auto_resume_unix(self, display, message: str) -> None:
        """Auto-resume implementation for Unix/Linux/Mac."""
        import termios
        import tty
        import select

        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            start_time = time.time()
            last_update = 0

            while True:
                elapsed = time.time() - start_time
                remaining = self.auto_resume - elapsed

                if remaining <= 0:
                    break

                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)
                    display.set_pause_state(False)
                    logging.info("User pressed key - resuming...")
                    return

                if elapsed - last_update >= 0.5:
                    progress = elapsed / self.auto_resume
                    display.set_pause_state(True, message, progress, remaining)
                    last_update = elapsed

                time.sleep(0.1)

            display.set_pause_state(False)
            logging.info("Auto-resuming after timeout")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    def _handle_manual_resume(self, display, message: str) -> None:
        """Handle manual resume (wait for Enter)."""
        if display:
            display.set_pause_state(True, message, 0.0, 0.0)
            input()
            display.set_pause_state(False)
            logging.info("User pressed Enter - resuming...")
        else:
            print(f"\n{message}")
            input()
            print("Resuming sampling...")

    def reset(self) -> None:
        """Reset the notes counter."""
        self.notes_sampled = 0
