"""Evaluation and governance primitives for agent outputs and policy versions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Literal

from .matching import MatchAnalysis
from .resume import ResumeAnalysis
from .verification import VerificationResult


Severity = Literal["info", "warning", "error", "critical"]
PolicyStatus = Literal["champion", "challenger", "retired"]
PromotionDecision = Literal["promote_challenger", "retain_champion"]


@dataclass(frozen=True)
class EvaluationFinding:
    code: str
    severity: Severity
    message: str
    evidence: tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentEvaluation:
    output_id: str
    agent_name: str
    agent_version: str
    evaluator_version: str
    input_snapshot_id: str
    rubric_scores: dict[str, float]
    overall_score: float
    passed: bool
    findings: tuple[EvaluationFinding, ...]
    feedback: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PolicyMetrics:
    policy_id: str
    sample_size: int
    overall_quality: float
    safety_error_rate: float
    unsupported_claim_rate: float
    top5_usefulness: float


@dataclass(frozen=True)
class PolicyComparison:
    champion_policy_id: str
    challenger_policy_id: str
    decision: PromotionDecision
    quality_delta: float
    safety_delta: float
    unsupported_claim_delta: float
    top5_usefulness_delta: float
    reasons: tuple[str, ...]
    compared_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", " ", value.casefold()).strip()


def _profile_skills(profile: dict) -> set[str]:
    skills = profile.get("skills", {})
    return {
        _norm(value)
        for group in ("primary", "additional", "secondary_or_contextual")
        for value in skills.get(group, [])
    }


def _evaluate(
    *,
    output_id: str,
    agent_name: str,
    agent_version: str,
    input_snapshot_id: str,
    rubric_scores: dict[str, float],
    findings: list[EvaluationFinding],
    feedback: list[str],
) -> AgentEvaluation:
    overall = round(sum(rubric_scores.values()) / len(rubric_scores), 2) if rubric_scores else 0.0
    passed = not any(item.severity in {"error", "critical"} for item in findings)
    return AgentEvaluation(
        output_id=output_id,
        agent_name=agent_name,
        agent_version=agent_version,
        evaluator_version="1.0",
        input_snapshot_id=input_snapshot_id,
        rubric_scores=rubric_scores,
        overall_score=overall,
        passed=passed,
        findings=tuple(findings),
        feedback=tuple(feedback),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def evaluate_match_output(
    match: MatchAnalysis,
    verification: VerificationResult,
    profile: dict,
    *,
    input_snapshot_id: str,
) -> AgentEvaluation:
    """Evaluate a match result against stored evidence and safety rules."""

    findings: list[EvaluationFinding] = []
    feedback: list[str] = []
    candidate_skills = _profile_skills(profile)
    matched_skills = {_norm(skill) for skill in match.matched_skills}
    unsupported_matches = sorted(matched_skills - candidate_skills)

    schema = 100.0 if match.record_id and match.matching_version and match.recommendation else 0.0
    if schema == 0:
        findings.append(EvaluationFinding("missing_required_fields", "critical", "Match output is missing required identity or recommendation fields."))
    evidence = 100.0
    if unsupported_matches:
        evidence = 0.0
        findings.append(EvaluationFinding(
            "unsupported_match_evidence", "critical",
            "Match output claims skills not supported by the candidate profile.",
            tuple(unsupported_matches),
        ))
        feedback.append("Only mark a skill as matched when candidate evidence contains the normalized skill.")
    elif match.matched_skills:
        feedback.append("Matched-skill evidence is grounded in the candidate profile.")
    else:
        evidence = 60.0
        findings.append(EvaluationFinding("low_evidence_coverage", "warning", "No matched skills were recorded; inspect role and domain evidence."))

    safety = 100.0
    if verification.status == "rejected" and (match.overall_score != 0 or match.recommendation != "blocked"):
        safety = 0.0
        findings.append(EvaluationFinding("rejected_job_not_blocked", "critical", "A rejected verification result received a normal match recommendation."))
        feedback.append("Always block matching when verification rejects a listing.")
    if verification.status == "uncertain" and not match.warnings:
        safety = 30.0
        findings.append(EvaluationFinding("uncertainty_hidden", "error", "Uncertain verification was not surfaced in match warnings."))

    usefulness = 100.0
    if not match.dimensions and verification.status != "rejected":
        usefulness = 0.0
        findings.append(EvaluationFinding("missing_dimensions", "error", "Non-rejected match output has no explainable dimensions."))
    elif not any(d.evidence or d.gaps for d in match.dimensions):
        usefulness = 40.0
        findings.append(EvaluationFinding("weak_explanation", "warning", "Match dimensions do not contain evidence or gaps."))

    calibration = max(0.0, min(100.0, 100.0 - abs(match.confidence * 100 - match.overall_score) * 0.25))
    feedback.append("Calibration remains provisional until application outcomes are available.")
    return _evaluate(
        output_id=match.record_id,
        agent_name="matching",
        agent_version=match.matching_version,
        input_snapshot_id=input_snapshot_id,
        rubric_scores={"schema": schema, "evidence_grounding": evidence, "safety": safety, "usefulness": usefulness, "calibration": round(calibration, 2)},
        findings=findings,
        feedback=feedback,
    )


def evaluate_resume_output(resume: ResumeAnalysis, *, input_snapshot_id: str) -> AgentEvaluation:
    findings: list[EvaluationFinding] = []
    feedback: list[str] = []
    safety = 100.0
    for proposal in resume.proposals:
        if proposal.change_type == "unsupported_claim_blocked" and proposal.supported:
            safety = 0.0
            findings.append(EvaluationFinding("blocked_claim_marked_supported", "critical", "An unsupported claim was incorrectly marked supported.", (proposal.change_id,)))
        if not proposal.evidence_references and proposal.supported and proposal.change_type != "unsupported_claim_blocked":
            findings.append(EvaluationFinding("missing_resume_evidence", "error", "Supported resume change lacks evidence references.", (proposal.change_id,)))
            safety = min(safety, 40.0)
    schema = 100.0 if resume.record_id and resume.resume_version else 0.0
    grounding = 100.0 if not resume.blocked_claims or any(p.change_type == "unsupported_claim_blocked" for p in resume.proposals) else 60.0
    usefulness = 100.0 if resume.proposals else 0.0
    if resume.blocked_claims:
        feedback.append("Unsupported claims were correctly surfaced instead of inserted into the resume.")
    feedback.append("Human approval remains required for new or user-supplied project evidence.")
    return _evaluate(
        output_id=resume.record_id,
        agent_name="resume_analysis",
        agent_version=resume.resume_version,
        input_snapshot_id=input_snapshot_id,
        rubric_scores={"schema": schema, "evidence_grounding": grounding, "safety": safety, "usefulness": usefulness},
        findings=findings,
        feedback=feedback,
    )


def compare_policy_versions(
    champion: PolicyMetrics,
    challenger: PolicyMetrics,
    *,
    minimum_sample_size: int = 10,
    minimum_quality_gain: float = 0.02,
    maximum_safety_regression: float = 0.0,
    maximum_unsupported_claim_regression: float = 0.0,
) -> PolicyComparison:
    """Compare versions without mutating either historical policy."""

    quality_delta = round(challenger.overall_quality - champion.overall_quality, 4)
    safety_delta = round(challenger.safety_error_rate - champion.safety_error_rate, 4)
    unsupported_delta = round(challenger.unsupported_claim_rate - champion.unsupported_claim_rate, 4)
    top5_delta = round(challenger.top5_usefulness - champion.top5_usefulness, 4)
    reasons: list[str] = []
    promote = True
    if challenger.sample_size < minimum_sample_size:
        promote = False
        reasons.append("Challenger does not have enough evaluation samples.")
    if quality_delta < minimum_quality_gain:
        promote = False
        reasons.append("Quality improvement is below the promotion threshold.")
    if safety_delta > maximum_safety_regression:
        promote = False
        reasons.append("Safety error rate regressed beyond the allowed threshold.")
    if unsupported_delta > maximum_unsupported_claim_regression:
        promote = False
        reasons.append("Unsupported-claim rate regressed beyond the allowed threshold.")
    if promote:
        reasons.append("Challenger meets sample, quality, safety, and evidence thresholds.")
    else:
        reasons.append("Champion remains active; both versions are preserved for auditability.")
    return PolicyComparison(
        champion_policy_id=champion.policy_id,
        challenger_policy_id=challenger.policy_id,
        decision="promote_challenger" if promote else "retain_champion",
        quality_delta=quality_delta,
        safety_delta=safety_delta,
        unsupported_claim_delta=unsupported_delta,
        top5_usefulness_delta=top5_delta,
        reasons=tuple(reasons),
        compared_at=datetime.now(timezone.utc).isoformat(),
    )

