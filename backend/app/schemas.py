from pydantic import BaseModel, ConfigDict, Field, field_validator

class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    question: str
    conversationId: str | None = Field(default=None, max_length=128)

    @field_validator('question')
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value or len(value.encode('utf-16-le')) // 2 > 600:
            raise ValueError('问题不能为空，最多600个UTF-16字符单位。')
        if any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError('问题包含无效控制字符。')
        return value

class SearchRequest(QuestionRequest):
    topK: int = Field(default=5, ge=1, le=10)
    category: str | None = Field(default=None, min_length=1, max_length=30)

class Citation(BaseModel):
    id: str
    title: str
    sourceId: str
    locator: str
    url: str | None = None
    excerpt: str
    contentKind: str

class QuestionAnswer(BaseModel):
    answer: str
    citations: list[Citation]
    uncertain: bool
    requestId: str

class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    answer: str = Field(min_length=1, max_length=4000)
    usedCitationIds: list[str] = Field(max_length=5)
    uncertain: bool
