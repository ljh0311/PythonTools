import argparse
import threading
import time
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from inputs import get_gamepad, UnpluggedError


def calculate_fuel_economy(throttle: float, brake: float) -> float:
    fuel_economy = 100 - (throttle * 2) + (brake * 1.5)
    return max(fuel_economy, 0)


class UnifiedDeviceGUI:
    """One GUI with auto device detection and manual tab switching."""

    def __init__(self, root: tk.Tk, initial_mode: str = "auto"):
        self.root = root
        self.initial_mode = initial_mode

        # Shared state
        self.joystick_throttle = 0.0
        self.g27_throttle = 0.0
        self.running = True
        self.input_thread = None
        self.gamepad_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 3
        self.auto_switch_enabled = tk.BooleanVar(value=True)
        self.active_mode = "joystick"
        self.device_score = {"joystick": 0, "g27": 0}

        # Joystick-only state
        self.stick_x = 0.0
        self.stick_y = 0.0
        self.twist = 0.0
        self.buttons = set()

        # G27-only state
        self.brake = 0.0
        self.fig = None
        self.ax = None
        self.line = None
        self.canvas = None

        self._setup_window()
        self._setup_ui()
        if self.initial_mode in ("joystick", "g27"):
            self._select_tab(self.initial_mode)
        self._start_input_thread()
        self.update_gui()

    def _setup_window(self):
        self.root.title("Controller Monitor - Joystick + G27")
        self.root.geometry("540x700")
        self.root.resizable(True, True)
        self.root.configure(bg="#f0f0f0")

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Unified Controller Monitor", font=("Arial", 16, "bold")).pack(
            pady=(0, 12)
        )

        status_frame = ttk.LabelFrame(main_frame, text="Connection Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = ttk.Label(
            status_frame,
            text="🔴 No Controller Detected",
            font=("Arial", 10, "bold"),
            foreground="red",
        )
        self.status_label.pack()

        controls_row = ttk.Frame(status_frame)
        controls_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(controls_row, text="Retry Connection", command=self.retry_connection).pack(
            side=tk.LEFT
        )
        ttk.Checkbutton(
            controls_row,
            text="Auto-switch tabs by detected device",
            variable=self.auto_switch_enabled,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 12))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_manual_tab_change)

        self.joystick_tab = ttk.Frame(self.notebook, padding="10")
        self.g27_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.joystick_tab, text="Joystick")
        self.notebook.add(self.g27_tab, text="G27")

        self._build_joystick_controls(self.joystick_tab)
        self._build_g27_controls(self.g27_tab)

        ttk.Label(
            main_frame,
            text=(
                "Use tabs manually anytime. With auto-switch enabled, the app moves to the most "
                "likely connected device view based on live input patterns."
            ),
            font=("Arial", 9),
            foreground="gray",
            wraplength=500,
        ).pack(pady=(12, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_joystick_controls(self, controls_frame):
        self.stick_x_label, self.stick_x_progress = self._labeled_progress(
            controls_frame, "Stick X:"
        )
        self.stick_y_label, self.stick_y_progress = self._labeled_progress(
            controls_frame, "Stick Y:"
        )
        self.js_throttle_label, self.js_throttle_progress = self._labeled_progress(
            controls_frame, "Throttle:", percent=True
        )
        self.twist_label, self.twist_progress = self._labeled_progress(
            controls_frame, "Twist:"
        )

        btn_frame = ttk.Frame(controls_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Label(btn_frame, text="Buttons:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.buttons_label = ttk.Label(
            btn_frame, text="(none)", font=("Arial", 10), foreground="gray"
        )
        self.buttons_label.pack(anchor=tk.W)

    def _build_g27_controls(self, controls_frame):
        self.g27_throttle_label, self.g27_throttle_progress = self._labeled_progress(
            controls_frame, "Throttle:", percent=True
        )
        self.g27_brake_label, self.g27_brake_progress = self._labeled_progress(
            controls_frame, "Brake:", percent=True
        )

        fuel_frame = ttk.Frame(controls_frame)
        fuel_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fuel_frame, text="Fuel Economy:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.fuel_label = ttk.Label(
            fuel_frame, text="100.0 mpg", font=("Arial", 12, "bold"), foreground="green"
        )
        self.fuel_label.pack(anchor=tk.W)

        self.fig, self.ax = plt.subplots(figsize=(4, 3), dpi=100)
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.ax.set_xlabel("Throttle (%)", fontsize=10)
        self.ax.set_ylabel("Fuel Economy (mpg)", fontsize=10)
        self.ax.set_title("Real-time Fuel Economy", fontsize=12, fontweight="bold")
        self.line, = self.ax.plot([0, 0], [0, 100], marker="o", linewidth=2, markersize=6)
        self.ax.grid(True, alpha=0.3)
        self.ax.set_facecolor("#f8f9fa")

        self.canvas = FigureCanvasTkAgg(self.fig, master=controls_frame)
        self.canvas.get_tk_widget().pack(pady=15, fill=tk.BOTH, expand=True)

    def _labeled_progress(self, parent, label, percent=False):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=label, font=("Arial", 10, "bold")).pack(anchor=tk.W)
        value_label = ttk.Label(frame, text="0.0%" if percent else "0", font=("Arial", 12))
        value_label.pack(anchor=tk.W)
        progress = ttk.Progressbar(frame, length=220, mode="determinate")
        progress.pack(fill=tk.X, pady=(2, 0))
        return value_label, progress

    def _start_input_thread(self):
        self.input_thread = threading.Thread(target=self._read_unified_input, daemon=True)
        self.input_thread.start()

    def retry_connection(self):
        self.connection_attempts = 0
        self.update_connection_status("🔄 Attempting to connect...", "blue")

    def update_connection_status(self, message, color):
        self.status_label.config(text=message, foreground=color)

    def _select_tab(self, mode: str):
        index = 0 if mode == "joystick" else 1
        self.notebook.select(index)
        self.active_mode = mode

    def _on_manual_tab_change(self, _event):
        current_index = self.notebook.index(self.notebook.select())
        self.active_mode = "joystick" if current_index == 0 else "g27"

    def _update_mode_scores(self, event_code: str):
        if event_code in ("ABS_X", "ABS_Y") or event_code.startswith("BTN_"):
            self.device_score["joystick"] += 3
            self.device_score["g27"] = max(0, self.device_score["g27"] - 1)
        elif event_code in ("ABS_Z", "ABS_RZ"):
            self.device_score["g27"] += 1

        if self.device_score["joystick"] >= 4:
            detected_mode = "joystick"
        elif self.device_score["g27"] >= 6 and self.device_score["joystick"] <= 1:
            detected_mode = "g27"
        else:
            return

        if self.auto_switch_enabled.get() and detected_mode != self.active_mode:
            self.root.after(0, lambda m=detected_mode: self._select_tab(m))

    def _read_unified_input(self):
        while self.running:
            try:
                events = get_gamepad()
                if not self.gamepad_connected:
                    self.gamepad_connected = True
                    self.connection_attempts = 0
                    self.root.after(
                        0,
                        lambda: self.update_connection_status(
                            "🟢 Controller Connected (auto-detect active)", "green"
                        ),
                    )

                for event in events:
                    self._update_mode_scores(event.code)
                    if event.ev_type == "Absolute":
                        if event.code == "ABS_X":
                            self.stick_x = max(-100, min(100, event.state / 32767.0 * 100))
                        elif event.code == "ABS_Y":
                            self.stick_y = max(-100, min(100, event.state / 32767.0 * 100))
                        elif event.code == "ABS_Z":
                            # Keep both views updated; mapping semantics differ per device.
                            self.brake = max(0, min(100, event.state / 32767.0 * 100))
                            self.joystick_throttle = max(
                                0, min(100, event.state / 32767.0 * 100)
                            )
                        elif event.code == "ABS_RZ":
                            self.g27_throttle = max(
                                0, min(100, event.state / 32767.0 * 100)
                            )
                            self.twist = max(-100, min(100, event.state / 32767.0 * 100))
                    elif event.ev_type == "Key" and event.code.startswith("BTN_"):
                        if event.state:
                            self.buttons.add(event.code)
                        else:
                            self.buttons.discard(event.code)

            except UnpluggedError:
                if self.gamepad_connected:
                    self.gamepad_connected = False
                    self.root.after(
                        0, lambda: self.update_connection_status("🔴 Controller Disconnected", "red")
                    )
                time.sleep(1)
            except Exception:
                self.connection_attempts += 1
                if self.connection_attempts >= self.max_connection_attempts:
                    self.root.after(
                        0,
                        lambda: self.update_connection_status(
                            f"❌ Connection Failed ({self.connection_attempts}/{self.max_connection_attempts})",
                            "red",
                        ),
                    )
                    time.sleep(5)
                else:
                    self.root.after(
                        0,
                        lambda: self.update_connection_status(
                            f"⚠️ Connection Error ({self.connection_attempts}/{self.max_connection_attempts})",
                            "orange",
                        ),
                    )
                    time.sleep(2)

    def _update_plot(self):
        fuel_economy = calculate_fuel_economy(self.g27_throttle, self.brake)
        self.line.set_data([0, self.g27_throttle], [0, fuel_economy])
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 100)
        self.canvas.draw()

    def _update_joystick_widgets(self):
        self.stick_x_label.config(text=f"{self.stick_x:.0f}")
        self.stick_x_progress["value"] = (self.stick_x + 100) / 2.0
        self.stick_y_label.config(text=f"{self.stick_y:.0f}")
        self.stick_y_progress["value"] = (self.stick_y + 100) / 2.0
        self.js_throttle_label.config(text=f"{self.joystick_throttle:.1f}%")
        self.js_throttle_progress["value"] = self.joystick_throttle
        self.twist_label.config(text=f"{self.twist:.0f}")
        self.twist_progress["value"] = (self.twist + 100) / 2.0
        if self.buttons:
            self.buttons_label.config(text=", ".join(sorted(self.buttons)), foreground="black")
        else:
            self.buttons_label.config(text="(none)", foreground="gray")

    def _update_g27_widgets(self):
        fuel_economy = calculate_fuel_economy(self.g27_throttle, self.brake)
        self.g27_throttle_label.config(text=f"{self.g27_throttle:.1f}%")
        self.g27_brake_label.config(text=f"{self.brake:.1f}%")
        self.fuel_label.config(text=f"{fuel_economy:.1f} mpg")
        self.g27_throttle_progress["value"] = self.g27_throttle
        self.g27_brake_progress["value"] = self.brake
        if fuel_economy >= 80:
            self.fuel_label.config(foreground="green")
        elif fuel_economy >= 60:
            self.fuel_label.config(foreground="orange")
        else:
            self.fuel_label.config(foreground="red")
        self._update_plot()

    def update_gui(self):
        self._update_joystick_widgets()
        self._update_g27_widgets()
        self.root.after(100, self.update_gui)

    def _on_close(self):
        self.running = False
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description="Unified flight/driving controller monitor.")
    parser.add_argument(
        "--initial-tab",
        choices=["auto", "joystick", "g27"],
        default="auto",
        help="Starting tab before auto-detection settles.",
    )
    args = parser.parse_args()

    root = tk.Tk()
    app = UnifiedDeviceGUI(root, initial_mode=args.initial_tab)
    root.mainloop()


if __name__ == "__main__":
    main()
