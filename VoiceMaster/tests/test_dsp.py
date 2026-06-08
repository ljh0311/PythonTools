import unittest
import numpy as np
from dsp.pipeline import DSPPipeline

class TestDSP(unittest.TestCase):
    def setUp(self):
        self.pipeline = DSPPipeline(sr=44100)
        self.duration = 1.0
        self.sr = 44100
        # Create a simple sine wave
        t = np.linspace(0, self.duration, int(self.sr * self.duration))
        self.test_audio = 0.5 * np.sin(2 * np.pi * 440 * t)

    def test_pipeline_passthrough(self):
        # By default, all effects are disabled
        processed = self.pipeline.process(self.test_audio)
        self.assertEqual(len(processed), len(self.test_audio))
        # It should be identical if everything is disabled
        np.testing.assert_array_almost_equal(processed, self.test_audio)

    def test_noise_reduction(self):
        self.pipeline.update_setting('noise_reduction', 'enabled', True)
        processed = self.pipeline.process(self.test_audio)
        self.assertEqual(len(processed), len(self.test_audio))

    def test_reverb(self):
        self.pipeline.update_setting('reverb', 'enabled', True)
        processed = self.pipeline.process(self.test_audio)
        self.assertEqual(len(processed), len(self.test_audio))
        # Reverb should change the audio
        self.assertFalse(np.array_equal(processed, self.test_audio))

if __name__ == '__main__':
    unittest.main()
