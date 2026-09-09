import unittest

from src.job_search_ai.domain.research_eval import (
    BenchmarkCase,
    BenchmarkDataset,
    compare_reports,
    evaluate_benchmark,
)


class ResearchEvaluationTests(unittest.TestCase):
    def make_dataset(self, policy: str) -> BenchmarkDataset:
        cases = (
            BenchmarkCase("c1", "j1", policy, 90, 1, "apply_priority", True, True),
            BenchmarkCase("c2", "j2", policy, 80, 2, "apply_priority", False, False),
            BenchmarkCase("c3", "j3", policy, 70, 3, "apply_review", True, True),
            BenchmarkCase("c4", "j4", policy, 40, 4, "stretch_review", False, None),
            BenchmarkCase("c5", "j5", policy, 20, 5, "do_not_prioritize", None, None, duplicate=True),
        )
        return BenchmarkDataset("benchmark-v1", cases, "Fixed test set")

    def test_dataset_validation_rejects_invalid_score(self):
        dataset = BenchmarkDataset("v1", (BenchmarkCase("c1", "j1", "p1", 101, 1, "apply", True),), "bad")
        self.assertTrue(dataset.validate())
        with self.assertRaises(ValueError):
            evaluate_benchmark(dataset)

    def test_benchmark_reports_ranking_and_quality_metrics(self):
        report = evaluate_benchmark(self.make_dataset("p1"), top_k=3)

        self.assertEqual(report.sample_size, 5)
        self.assertEqual(report.labeled_cases, 4)
        self.assertEqual(report.metrics["top_k_precision"], 0.6667)
        self.assertGreater(report.metrics["mean_reciprocal_rank"], 0)
        self.assertTrue(report.limitations)

    def test_unknown_outcomes_are_not_counted_as_negative(self):
        dataset = BenchmarkDataset("v1", (BenchmarkCase("c1", "j1", "p1", 90, 1, "apply", None),), "unknown")
        report = evaluate_benchmark(dataset)

        self.assertEqual(report.labeled_cases, 0)
        self.assertEqual(report.metrics["brier_score"], 0.0)
        self.assertTrue(any("no known outcome" in item.lower() for item in report.limitations))

    def test_report_comparison_returns_deltas(self):
        champion = evaluate_benchmark(self.make_dataset("p1"))
        challenger = evaluate_benchmark(self.make_dataset("p2"))
        comparison = compare_reports(champion, challenger)

        self.assertEqual(comparison["champion_policy_id"], "p1")
        self.assertIn("top_k_precision_delta", comparison)


if __name__ == "__main__":
    unittest.main()
