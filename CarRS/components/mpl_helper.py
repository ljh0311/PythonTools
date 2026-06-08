"""Helper for embedding and managing a Matplotlib figure in a Tkinter frame."""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class MplHelper:
    """Helper for embedding and managing a Matplotlib figure in a Tkinter frame."""

    def __init__(self, parent_frame, figsize=(5, 3), dpi=100):
        self.fig, self.ax = plt.subplots(figsize=figsize, dpi=dpi)
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.widget = self.canvas.get_tk_widget()
        self.widget.pack(fill="both", expand=True)

    def clear(self):
        """Clear the axes and redraw the canvas."""
        self.ax.clear()
        self.canvas.draw()

    def plot(self, *args, **kwargs):
        """Plot data on the axes and redraw the canvas."""
        self.ax.plot(*args, **kwargs)
        self.canvas.draw()

    def set_title(self, title, **kwargs):
        """Set the title of the axes."""
        self.ax.set_title(title, **kwargs)
        self.canvas.draw()

    def set_xlabel(self, label, **kwargs):
        """Set the x-axis label."""
        self.ax.set_xlabel(label, **kwargs)
        self.canvas.draw()

    def set_ylabel(self, label, **kwargs):
        """Set the y-axis label."""
        self.ax.set_ylabel(label, **kwargs)
        self.canvas.draw()

    def get_figure(self):
        """Return the underlying Matplotlib figure."""
        return self.fig

    def get_axes(self):
        """Return the underlying Matplotlib axes."""
        return self.ax

    def get_canvas(self):
        """Return the FigureCanvasTkAgg instance."""
        return self.canvas

    def resize_to_widget(self):
        """Resize the figure to match the widget size (for mobile friendliness)."""
        self.widget.update_idletasks()
        width = self.widget.winfo_width()
        height = self.widget.winfo_height()
        if width > 0 and height > 0:
            dpi = self.fig.get_dpi()
            self.fig.set_size_inches(max(2, width / dpi), max(2, height / dpi), forward=True)
            self.canvas.draw()
