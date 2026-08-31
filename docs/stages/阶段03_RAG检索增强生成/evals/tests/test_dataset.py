from __future__ import annotations

import sys
import unittest
from pathlib import Path


EVALS_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = EVALS_ROOT / "tools"
for path in (EVALS_ROOT, TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from compile_dataset import DATASET_ID, default_dataset_dir, derive_id  # noqa: E402
from validate_dataset import REQUIRED_CATEGORIES, validate_dataset  # noqa: E402


class DatasetContractTests(unittest.TestCase):
    def test_release_is_complete_and_current(self) -> None:
        report = validate_dataset(default_dataset_dir())
        self.assertEqual(report.dataset, f"{DATASET_ID}@1.0.0")
        self.assertEqual(report.cases, 48)
        self.assertEqual(report.sources, 16)
        self.assertEqual(report.chunks, 40)
        self.assertGreaterEqual(report.labels, 48)

    def test_required_distributions_are_present(self) -> None:
        report = validate_dataset(default_dataset_dir())
        self.assertEqual(set(report.categories), REQUIRED_CATEGORIES)
        self.assertEqual(report.splits, {"dev": 16, "test": 24, "train": 8})
        self.assertEqual(set(report.difficulties), {"easy", "medium", "hard"})
        self.assertEqual(set(report.diagnostic_stages), {"retrieval", "context", "generation"})

    def test_case_identity_is_deterministic_and_input_sensitive(self) -> None:
        first = derive_id("case_", DATASET_ID, "fact-001")
        self.assertEqual(first, derive_id("case_", DATASET_ID, "fact-001"))
        self.assertNotEqual(first, derive_id("case_", DATASET_ID, "fact-002"))
        self.assertRegex(first, r"^case_[0-9a-f]{32}$")


if __name__ == "__main__":
    unittest.main()
