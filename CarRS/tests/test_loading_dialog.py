"""Tests for LoadingDialog main-thread lifecycle."""
import threading
import time
import tkinter as tk
import unittest

from components.loading_dialog import LoadingDialog, run_with_loading


class LoadingDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_show_from_worker_thread_raises(self):
        dialog = LoadingDialog(self.root, "Test", "Wait")
        error = {}

        def worker():
            try:
                dialog.show()
            except RuntimeError as exc:
                error["exc"] = exc

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=2)
        self.assertIn("exc", error)
        self.assertIn("main thread", str(error["exc"]).lower())

    def test_run_with_loading_stays_visible_then_hides(self):
        done = {"ok": False}
        seen = {"shown": False}

        def work():
            time.sleep(0.2)
            return 42

        def on_success(value):
            done["ok"] = value == 42
            self.root.quit()

        loading = run_with_loading(
            self.root,
            work,
            on_success,
            title="Test",
            message="Working",
            min_visible_ms=300,
        )
        self.root.after(50, lambda: seen.update(shown=loading.is_shown))
        self.root.after(5000, self.root.quit)
        self.root.mainloop()
        self.assertTrue(seen["shown"])
        self.assertTrue(done["ok"])
        self.assertFalse(loading.is_shown)


if __name__ == "__main__":
    unittest.main()
