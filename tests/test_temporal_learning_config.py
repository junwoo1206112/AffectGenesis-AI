import json
from pathlib import Path
import tempfile
import unittest

from temporal_learning.config import load_config


class TemporalLearningConfigTests(unittest.TestCase):
    def test_canonical_config_and_duplicate_rejection(self):
        config, digest = load_config(Path("experiments") / "temporal_learning_v1.json")
        self.assertEqual(config["protocol"], "temporal-learning-v1")
        self.assertEqual(len(digest), 64)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"protocol":"temporal-learning-v1","protocol":"temporal-learning-v1"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_config(path)
