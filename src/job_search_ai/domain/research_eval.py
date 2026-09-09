"""Research-grade benchmark records and evaluation metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isnan


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    job_id: str
    policy_id: str
    predicted_score: float
    rank: int
    recommendation: str
    useful_outcome: bool | None
    user_approved: bool | None = None
    unsupported_claim: bool = False
    duplicate: bool = False


@dataclass(frozen=True)
class BenchmarkDataset:
    dataset_version: str
    cases: tuple[BenchmarkCase, ...]
    description: str

    def validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            errors.append("case_id values must be unique")
        for case in self.cases:
            if not 0 <= case.predicted_score <= 100:
                errors.append(f"{case.case_id}: predicted_score must be between 0 and 100")
            if case.rank < 1:
                errors.append(f"{case.case_id}: rank must be at least 1")
        return tuple(errors)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkReport:
    dataset_version: str
    policy_id: str
    sample_size: int
    labeled_cases: int
    metrics: dict[str, float]
    limitations: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def evaluate_benchmark(dataset: BenchmarkDataset, *, top_k: int = 5) -> BenchmarkReport:
    """Evaluate a fixed dataset without imputing unknown outcomes."""

    errors = dataset.validate()
    if errors:
        raise ValueError("Invalid benchmark dataset: " + "; ".join(errors))
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    cases = tuple(sorted(dataset.cases, key=lambda case: (case.rank, case.case_id)))
    labeled = tuple(case for case in cases if case.useful_outcome is not None)
    useful = tuple(case for case in labeled if case.useful_outcome)
    top = tuple(case for case in cases if case.rank <= top_k and case.useful_outcome is not None)
    top_useful = sum(1 for case in top if case.useful_outcome)
    brier = sum((case.predicted_score / 100.0 - (1.0 if case.useful_outcome else 0.0)) ** 2 for case in labeled) / len(labeled) if labeled else 0.0
    reciprocal_rank = 0.0
    if useful:
        first_useful = min(case.rank for case in useful)
        reciprocal_rank = 1.0 / first_useful

    approved = tuple(case for case in cases if case.user_approved is not None)
    duplicate_cases = sum(1 for case in cases if case.duplicate)
    unsupported_cases = sum(1 for case in cases if case.unsupported_claim)
    metrics = {
        "top_k_precision": _safe_rate(top_useful, len(top)),
        "top_k_recall": _safe_rate(top_useful, len(useful)),
        "mean_reciprocal_rank": round(reciprocal_rank, 4),
        "brier_score": round(brier, 4),
        "user_approval_rate": _safe_rate(sum(1 for case in approved if case.user_approved), len(approved)),
        "unsupported_claim_rate": _safe_rate(unsupported_cases, len(cases)),
        "duplicate_rate": _safe_rate(duplicate_cases, len(cases)),
    }
    limitations: list[str] = []
    if len(labeled) < len(cases):
        limitations.append("Some cases have no known outcome and were excluded from supervised metrics.")
    if not approved:
        limitations.append("No explicit user approval labels are available.")
    if not useful:
        limitations.append("No useful outcomes are labeled; ranking recall is not informative.")
    limitations.append("Interview probability is not estimated until the dataset contains sufficient real outcomes.")
    return BenchmarkReport(
        dataset_version=dataset.dataset_version,
        policy_id=cases[0].policy_id if cases else "unknown",
        sample_size=len(cases),
        labeled_cases=len(labeled),
        metrics=metrics,
        limitations=tuple(limitations),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def compare_reports(champion: BenchmarkReport, challenger: BenchmarkReport) -> dict[str, float | str]:
    """Return metric deltas; promotion remains governed by Phase 7 policy rules."""

    return {
        "champion_policy_id": champion.policy_id,
        "challenger_policy_id": challenger.policy_id,
        "top_k_precision_delta": round(challenger.metrics.get("top_k_precision", 0.0) - champion.metrics.get("top_k_precision", 0.0), 4),
        "top_k_recall_delta": round(challenger.metrics.get("top_k_recall", 0.0) - champion.metrics.get("top_k_recall", 0.0), 4),
        "brier_score_delta": round(challenger.metrics.get("brier_score", 0.0) - champion.metrics.get("brier_score", 0.0), 4),
        "approval_rate_delta": round(challenger.metrics.get("user_approval_rate", 0.0) - champion.metrics.get("user_approval_rate", 0.0), 4),
        "unsupported_claim_rate_delta": round(challenger.metrics.get("unsupported_claim_rate", 0.0) - champion.metrics.get("unsupported_claim_rate", 0.0), 4),
    }

