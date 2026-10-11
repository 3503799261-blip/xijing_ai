"""Phase 4 metadata lives outside the unchanged Phase 3 CharacterDesign."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class AssetInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, strict=True)

    @field_validator('*', mode='after')
    @classmethod
    def safe_text(cls, value):
        if isinstance(value, str):
            if not value or any(ord(c) < 32 and c not in '\n\t' for c in value):
                raise ValueError('Invalid asset text')
            value.encode('utf-8')
        return value


class EnterpriseBrief(AssetInput):
    organizationType: Literal['game', 'tourism', 'ip_design', 'other']
    audience: str = Field(min_length=1, max_length=160)
    useCase: str = Field(min_length=1, max_length=240)
    designGoal: str = Field(min_length=1, max_length=240)
    culturalBoundaries: str = Field(min_length=1, max_length=240)
    deliveryScope: str = Field(min_length=1, max_length=240)
    licenseStatus: Literal['unverified', 'user_authorized'] = 'unverified'


class CreateAsset(AssetInput):
    # A string UUID accepts ordinary JSON while rejecting arbitrary paths.
    sourceTaskId: str = Field(min_length=36, max_length=36)
    mode: Literal['personal', 'enterprise'] = 'personal'
    purpose: str = Field(min_length=1, max_length=240)
    styleMode: Literal['realistic', 'chibi'] = 'realistic'
    enterpriseBrief: EnterpriseBrief | None = None

    @field_validator('sourceTaskId')
    @classmethod
    def uuid_id(cls, value):
        return str(UUID(value))

    @model_validator(mode='after')
    def enterprise_metadata(self):
        if self.mode == 'enterprise' and self.enterpriseBrief is None:
            raise ValueError('Enterprise mode requires its own brief')
        if self.mode == 'personal' and self.enterpriseBrief is not None:
            raise ValueError('Personal mode cannot carry enterprise metadata')
        return self


class VisualApproval(AssetInput):
    promptHash: str = Field(pattern=r'^[a-f0-9]{64}$')
    action: Literal['accept']


class PromptVersionRequest(AssetInput):
    expectedPromptHash: str = Field(pattern=r'^[a-f0-9]{64}$')
    imagePrompt: str = Field(min_length=1, max_length=3000)
    negativePrompt: str = Field(min_length=1, max_length=1000)
    action: Literal['create_version']


class ImageAcceptance(AssetInput):
    imageHash: str = Field(pattern=r'^[a-f0-9]{64}$')
    action: Literal['accept']


class ModelApprovalRequest(AssetInput):
    assetId: str = Field(min_length=36, max_length=36)
    assetVersion: int = Field(ge=1, strict=True)
    imageId: str = Field(min_length=36, max_length=36)
    imageHash: str = Field(pattern=r'^[a-f0-9]{64}$')
    promptHash: str = Field(pattern=r'^[a-f0-9]{64}$')
    purpose: str = Field(min_length=1, max_length=240)
    modelCount: Literal[1]
    estimatedCredits: int = Field(ge=0, le=1000000, strict=True)
    action: Literal['accept']
    styleMode: Literal['realistic', 'chibi'] | None = None
    styleVersion: int | None = Field(default=None, ge=1, strict=True)
    characterId: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator('modelCount', mode='before')
    @classmethod
    def exactly_one(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('Exactly one model is required')
        return value


class ModelSubmitRequest(AssetInput):
    approvalId: str = Field(min_length=36, max_length=36)
    modelCount: Literal[1]

    @field_validator('modelCount', mode='before')
    @classmethod
    def exactly_one(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError('Exactly one model is required')
        return value
