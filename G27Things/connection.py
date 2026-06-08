from inputs import get_gamepad, UnpluggedError
import time
import threading


class Connection:
    def __init__(self):
        self.device_connected = False
        self.gamepad_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.max_retry_duration_seconds = 60
        self.retry_started_at = None
        self.device_name = None
        self._input_reader = None

    def _start_retry_window(self):
        self.retry_started_at = time.time()

    def _clear_retry_window(self):
        self.retry_started_at = None

    def _retry_timed_out(self):
        if self.retry_started_at is None:
            return False
        return (time.time() - self.retry_started_at) >= self.max_retry_duration_seconds

    def _stop_retry_due_to_timeout(self):
        self.running = False
        self._clear_retry_window()
        self.root.after(
            0,
            lambda: self.update_connection_status(
                "⏱️ Retry stopped after 60s. Press Retry Connection to try again.",
                "red",
            ),
        )

    def retry_connection(self):
        """Retry gamepad connection"""
        self.connection_attempts = 0
        self._start_retry_window()
        self.update_connection_status("🔄 Attempting to connect...", "blue")
        # Restart the input thread
        if hasattr(self, 'input_thread') and self.input_thread.is_alive():
            self.running = False
            time.sleep(0.1)
        self.running = True
        reader = self._input_reader or self.read_g27_input
        self.input_thread = threading.Thread(target=reader, daemon=True)
        self.input_thread.start()

    def update_connection_status(self, message, color):
        """Update the connection status display"""
        self.status_label.config(text=message, foreground=color)

    def read_g27_input(self):
        """Read G27 input with proper error handling"""
        while self.running:
            if self._retry_timed_out():
                self._stop_retry_due_to_timeout()
                break
            try:
                events = get_gamepad()
                if not self.gamepad_connected:
                    self.gamepad_connected = True
                    self.connection_attempts = 0
                    self._clear_retry_window()
                    self.root.after(0, lambda: self.update_connection_status("🟢 G27 Connected", "green"))
                
                for event in events:
                    if event.code == "ABS_RZ":
                        self.throttle = max(0, min(100, event.state / 32767.0 * 100))
                    elif event.code == "ABS_Z":
                        self.brake = max(0, min(100, event.state / 32767.0 * 100))
                        
            except UnpluggedError:
                if self.gamepad_connected:
                    self.gamepad_connected = False
                    self.root.after(0, lambda: self.update_connection_status("🔴 G27 Disconnected", "red"))
                time.sleep(1)  # Wait before retrying
                
            except Exception as e:
                self.connection_attempts += 1
                if self.connection_attempts >= self.max_connection_attempts:
                    self.root.after(0, lambda: self.update_connection_status(
                        f"❌ Connection Failed ({self.connection_attempts}/{self.max_connection_attempts})", "red"))
                    time.sleep(5)  # Wait longer before retrying
                else:
                    self.root.after(0, lambda: self.update_connection_status(
                        f"⚠️ Connection Error ({self.connection_attempts}/{self.max_connection_attempts})", "orange"))
                    time.sleep(2)

    def read_joystick_input(self):
        """Read joystick (e.g. Logitech Extreme 3D Pro) input with proper error handling.
        Expects subclass to define: stick_x, stick_y, throttle, twist, buttons (set of pressed BTN_* codes).
        Axis mapping: ABS_X/Y -> -100..100, ABS_Z -> throttle 0..100, ABS_RZ -> twist -100..100.
        """
        while self.running:
            if self._retry_timed_out():
                self._stop_retry_due_to_timeout()
                break
            try:
                events = get_gamepad()
                if not self.gamepad_connected:
                    self.gamepad_connected = True
                    self.connection_attempts = 0
                    self._clear_retry_window()
                    self.root.after(0, lambda: self.update_connection_status("🟢 Joystick Connected", "green"))

                for event in events:
                    if event.ev_type == "Absolute":
                        if event.code == "ABS_X":
                            self.stick_x = max(-100, min(100, event.state / 32767.0 * 100))
                        elif event.code == "ABS_Y":
                            self.stick_y = max(-100, min(100, event.state / 32767.0 * 100))
                        elif event.code == "ABS_Z":
                            self.throttle = max(0, min(100, event.state / 32767.0 * 100))
                        elif event.code == "ABS_RZ":
                            self.twist = max(-100, min(100, event.state / 32767.0 * 100))
                    elif event.ev_type == "Key" and event.code.startswith("BTN_"):
                        if event.state:
                            self.buttons.add(event.code)
                        else:
                            self.buttons.discard(event.code)

            except UnpluggedError:
                if self.gamepad_connected:
                    self.gamepad_connected = False
                    self.root.after(0, lambda: self.update_connection_status("🔴 Joystick Disconnected", "red"))
                time.sleep(1)

            except Exception:
                self.connection_attempts += 1
                if self.connection_attempts >= self.max_connection_attempts:
                    self.root.after(0, lambda: self.update_connection_status(
                        f"❌ Connection Failed ({self.connection_attempts}/{self.max_connection_attempts})", "red"))
                    time.sleep(5)
                else:
                    self.root.after(0, lambda: self.update_connection_status(
                        f"⚠️ Connection Error ({self.connection_attempts}/{self.max_connection_attempts})", "orange"))
                    time.sleep(2)
