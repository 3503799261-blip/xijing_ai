"""Strict model output contracts, separate from persisted HTTP task state."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Short = Annotated[str, Field(min_length=1, max_length=160)]
EvidenceId = Annotated[str, Field(min_length=1, max_length=200)]


class StrictArtifact(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_strip_whitespace=True)

    @field_validator('*', mode='after')
    @classmethod
    def text_controls(cls, value):
        def check(item):
            if isinstance(item, str):
                if not item.strip() or any(ord(char) < 32 and char not in '\n\t' for char in item):
                    raise ValueError('Empty or invalid artifact text')
                item.encode('utf-8')
            elif isinstance(item, list):
                for nested in item:
                    check(nested)
        check(value)
        return value


class Requirement(StrictArtifact):
    id: str = Field(pattern=r'^R[1-6]$')
    text: Short


class TaskPlan(StrictArtifact):
    theme: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)
    style: Literal['京剧写意', '国风幻想', '舞台角色']
    requirements: list[Requirement] = Field(min_length=1, max_length=6)
    researchQueries: list[Annotated[str, Field(min_length=1, max_length=180)]] = Field(max_length=3)
    clarificationQuestions: list[Short] = Field(max_length=3)
    requiredEntities: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(default_factory=list, max_length=3)

    @model_validator(mode='after')
    def queries_or_clarification(self):
        if not self.clarificationQuestions and not self.researchQueries:
            raise ValueError('Research is required unless awaiting clarification')
        return self


class DesignElement(StrictArtifact):
    description: str = Field(min_length=1, max_length=120)
    interpretation: Literal['evidence_based', 'creative']
    evidenceIds: list[EvidenceId] = Field(max_length=5)


class CharacterDesign(StrictArtifact):
    schemaVersion: Literal['1.0']
    name: str = Field(min_length=1, max_length=24)
    positioning: str = Field(min_length=1, max_length=120)
    costume: list[DesignElement] = Field(min_length=1, max_length=3)
    colors: list[DesignElement] = Field(min_length=1, max_length=3)
    visualElements: list[DesignElement] = Field(min_length=1, max_length=3)
    creativeElements: list[Short] = Field(max_length=3)
    visualPrompt: str = Field(min_length=1, max_length=320)
    usedEvidenceIds: list[EvidenceId] = Field(min_length=1, max_length=5)
    limitations: list[Short] = Field(max_length=3)


class ReviewIssue(StrictArtifact):
    field: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=1, max_length=180)
    evidenceIds: list[EvidenceId] = Field(max_length=5)


class CultureReview(StrictArtifact):
    verdict: Literal['pass', 'needs_revision', 'insufficient_evidence']
    issues: list[ReviewIssue] = Field(max_length=4)
    suggestions: list[Short] = Field(max_length=4)
    checkedEvidenceIds: list[EvidenceId] = Field(max_length=5)
    needsHumanReview: Literal[True]


def evidence_aliases(evidence: list[dict]) -> dict[str, str]:
    return {f'E{index}': item['id'] for index, item in enumerate(evidence, 1)}


def model_evidence(evidence: list[dict]) -> list[dict]:
    return [{'id': f'E{index}', 'excerpt': item['excerpt'],
             'title': item['title'], 'locator': item['locator'],
             'contentKind': item['contentKind']}
            for index, item in enumerate(evidence, 1)]


def canonical_ids(ids: list[str], aliases: dict[str, str]) -> list[str]:
    if len(set(ids)) != len(ids) or any(item not in aliases for item in ids):
        raise ValueError('Unknown or duplicate evidence aliases')
    return [aliases[item] for item in ids]


def public_citations(evidence: list[dict], ids: list[str]) -> list[dict]:
    by_id = {item['id']: item for item in evidence}
    if any(item not in by_id for item in ids):
        raise ValueError('Evidence is outside this workflow')
    fields = ('id', 'title', 'sourceId', 'locator', 'url', 'excerpt', 'contentKind')
    return [{key: by_id[cid][key] for key in fields} for cid in dict.fromkeys(ids)]
