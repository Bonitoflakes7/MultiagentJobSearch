"""Resume analysis and no-fabrication tailoring plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import re
from typing import Literal

from .jobs import JobRecord
from .matching import MatchAnalysis


ChangeType = Literal[
    "emphasize_existing_evidence",
    "reorder_existing_evidence",
    "clarify_existing_evidence",
    "add_verified_evidence",
    "unsupported_claim_blocked",
]


@dataclass(frozen=True)
class ResumeChangeProposal:
    change_id: str
    change_type: ChangeType
    target_section: str
    proposed_change: str
    evidence_references: tuple[str, ...]
    supported: bool
    requires_human_review: bool
    reason: str


@dataclass(frozen=True)
class ResumeAnalysis:
    record_id: str
    resume_version: str
    match_score: float
    resume_readiness_score: float
    proposals: tuple[ResumeChangeProposal, ...]
    supported_job_skills: tuple[str, ...]
    unsupported_job_skills: tuple[str, ...]
    blocked_claims: tuple[str, ...]
    warnings: tuple[str, ...]
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _profile_skill_map(profile: dict) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    skills = profile.get("skills", {})
    for category in ("primary", "additional", "secondary_or_contextual"):
        for skill in skills.get(category, []):
            result[skill.casefold()] = (skill, category)
    return result


def _resume_present_projects(profile: dict) -> dict[str, dict]:
    return {
        project.get("name", "").casefold(): project
        for project in profile.get("projects", [])
        if project.get("evidence_class") == "verified_resume"
    }


def _all_projects(profile: dict) -> dict[str, dict]:
    return {project.get("name", "").casefold(): project for project in profile.get("projects", [])}


def analyze_resume(job: JobRecord, match: MatchAnalysis, profile: dict) -> ResumeAnalysis:
    """Create a safe tailoring plan; it never invents candidate evidence."""

    skill_map = _profile_skill_map(profile)
    supported: list[str] = []
    unsupported: list[str] = []
    proposals: list[ResumeChangeProposal] = []
    blocked: list[str] = []

    for skill in job.skills:
        key = skill.casefold()
        if key in skill_map:
            label, category = skill_map[key]
            supported.append(label)
            proposals.append(ResumeChangeProposal(
                change_id=f"emphasize-{_slug(label)}",
                change_type="emphasize_existing_evidence",
                target_section="Technical Skills or relevant project",
                proposed_change=f"Emphasize existing evidence for {label} where it is already demonstrated.",
                evidence_references=(f"candidate.skills.{category}:{label}",),
                supported=True,
                requires_human_review=False,
                reason="The skill is present in the candidate profile and can be highlighted without adding a new claim.",
            ))
        else:
            unsupported.append(skill)
            blocked.append(skill)
            proposals.append(ResumeChangeProposal(
                change_id=f"block-{_slug(skill)}",
                change_type="unsupported_claim_blocked",
                target_section="Technical Skills",
                proposed_change=f"Do not add {skill} as an existing skill; consider learning it or leaving it absent.",
                evidence_references=(),
                supported=False,
                requires_human_review=True,
                reason="No candidate evidence supports claiming this job skill.",
            ))

    # User-supplied projects can inform analysis, but must not be silently
    # inserted into the resume until the candidate confirms the resume wording.
    resume_projects = _resume_present_projects(profile)
    all_projects = _all_projects(profile)
    for project_name, project in all_projects.items():
        technologies = {item.casefold() for item in project.get("technologies", [])}
        if project_name not in resume_projects and technologies.intersection({item.casefold() for item in job.skills}):
            proposals.append(ResumeChangeProposal(
                change_id=f"review-project-{_slug(project.get('name', 'project'))}",
                change_type="add_verified_evidence",
                target_section="Projects",
                proposed_change=f"Review whether to add or reference the project '{project.get('name')}' in the resume.",
                evidence_references=(f"candidate.projects:{project.get('name')}",),
                supported=True,
                requires_human_review=True,
                reason="Project is user-supplied or not present in the resume snapshot; automatic insertion is disabled.",
            ))

    if supported:
        proposals.append(ResumeChangeProposal(
            change_id="reorder-relevant-projects",
            change_type="reorder_existing_evidence",
            target_section="Projects",
            proposed_change="Place the most relevant existing project evidence earlier in the project section.",
            evidence_references=tuple(f"candidate.projects:{name}" for name in resume_projects),
            supported=True,
            requires_human_review=False,
            reason="Reordering existing evidence does not create a new claim.",
        ))

    supported_ratio = len(supported) / len(job.skills) if job.skills else 0.5
    readiness = round(supported_ratio * 100, 2)
    warnings: list[str] = []
    if unsupported:
        warnings.append("Some job skills are unsupported and were blocked from resume claims")
    if match.warnings:
        warnings.extend(match.warnings)
    if any(proposal.requires_human_review for proposal in proposals):
        warnings.append("Human review is required before applying project or resume-content changes")

    return ResumeAnalysis(
        record_id=job.record_id,
        resume_version="profile_v1",
        match_score=match.overall_score,
        resume_readiness_score=readiness,
        proposals=tuple(proposals),
        supported_job_skills=tuple(dict.fromkeys(supported)),
        unsupported_job_skills=tuple(dict.fromkeys(unsupported)),
        blocked_claims=tuple(dict.fromkeys(blocked)),
        warnings=tuple(dict.fromkeys(warnings)),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def validate_tailoring_claims(proposals: tuple[ResumeChangeProposal, ...]) -> tuple[str, ...]:
    """Return claims that must not enter an automatic tailored draft."""

    return tuple(
        proposal.proposed_change
        for proposal in proposals
        if not proposal.supported or proposal.change_type == "unsupported_claim_blocked"
    )

