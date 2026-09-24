import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "refresh_monitor.py"
SPEC = importlib.util.spec_from_file_location("refresh_monitor", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MonitorSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = MODULE.build_snapshot(MODULE.DEFAULT_CONFIG)
        cls.queries = cls.snapshot["queries"]

    def test_expected_experiment_metrics(self):
        rows = {
            row["experiment_id"]: row
            for row in self.queries["experiment_summaries"]["rows"]
        }
        expected = {
            "baseline": (55, 57, 211, 99, 81, 29, 17),
            "improved": (58, 59, 213, 94, 79, 26, 19),
            "short": (53, 55, 204, 96, 63, 28, 16),
            "next_action": (55, 57, 210, 95, 64, 24, 16),
        }
        for experiment_id, values in expected.items():
            row = rows[experiment_id]
            observed = (
                row["completion_passes"],
                row["db_passes"],
                row["read_correct"],
                row["write_correct"],
                row["cardinality_turns"],
                row["unsafe_write_turns"],
                row["illegal_actions"],
            )
            self.assertEqual(observed, values)

    def test_task_populations_and_exclusion(self):
        rows = self.queries["task_results"]["rows"]
        self.assertEqual(len(rows), 280)
        for experiment_id in {row["experiment_id"] for row in rows}:
            experiment_rows = [row for row in rows if row["experiment_id"] == experiment_id]
            self.assertEqual(len(experiment_rows), 70)
            excluded = [row["task_id"] for row in experiment_rows if row["excluded"]]
            self.assertEqual(excluded, ["105"])

    def test_no_full_trajectory_messages_are_embedded(self):
        rows = self.queries["task_results"]["rows"]
        for row in rows:
            self.assertNotIn("messages", row)
            self.assertNotIn("trajectory", row)

    def test_all_nonbaseline_experiments_have_task_movements(self):
        rows = self.queries["task_movements"]["rows"]
        self.assertEqual(len(rows), 3 * 69)
        self.assertNotIn("105", {row["task_id"] for row in rows})


if __name__ == "__main__":
    unittest.main()
