from __future__ import annotations

import unittest

from biomedical_extractor.hunflair2_training import HunFlair2TrainingConfig


class HunFlair2TrainingConfigTests(unittest.TestCase):
    def test_defaults_are_explicit_and_conservative(self):
        config = HunFlair2TrainingConfig()
        self.assertEqual(config.base_model, "hunflair/hunflair2-ner")
        self.assertEqual(config.learning_rate, 5e-5)
        self.assertEqual(config.mini_batch_size, 4)
        self.assertFalse(config.mixed_precision)
        self.assertEqual(config.gradient_accumulation_steps, 1)
        self.assertTrue(config.output_model_location.endswith("final-model.pt"))

    def test_unknown_fields_and_invalid_values_are_rejected(self):
        with self.assertRaises(ValueError):
            HunFlair2TrainingConfig.from_mapping({"not_a_setting": True})
        with self.assertRaises(ValueError):
            HunFlair2TrainingConfig.from_mapping({"mini_batch_size": 0})
        with self.assertRaises(ValueError):
            HunFlair2TrainingConfig.from_mapping({"device": "mps"})


if __name__ == "__main__":
    unittest.main()
