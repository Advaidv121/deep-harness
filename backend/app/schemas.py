from datetime import datetime
from typing import Literal, Optional, List
from pydantic import BaseModel, Field, field_validator

class ExtractedFact(BaseModel):
    fact: str = Field(..., description="Atomic declarative fact about the user or relationship.")
    category: Literal["preference", "diet", "career", "relationship", "health", "hobby", "other"] = Field(
        default="other", description="Fact domain category."
    )
    action: Literal["ADD", "UPDATE", "DELETE", "NOOP"] = Field(
        default="ADD", description="ADD for new facts, UPDATE to augment, DELETE for contradictions, NOOP for banter."
    )
    salience_score: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Durable importance (0.0-1.0). Filter if < 0.70."
    )
    supersedes_text: Optional[str] = Field(
        None, description="Exact old text/fact this invalidates or updates."
    )
    temporal_anchor: Optional[str] = Field(
        None, description="ISO-8601 normalized date if a relative date was mentioned."
    )

class ExtractionPayload(BaseModel):
    facts: List[ExtractedFact] = Field(default_factory=list)

class MemoryManageRequest(BaseModel):
    action: Literal["add", "replace", "remove"]
    target: Literal["USER", "MEMORY"]
    content: Optional[str] = None
    old_text: Optional[str] = None
    category: Optional[str] = "other"
    salience_score: Optional[float] = 1.0
    user_id: str = "default_user"

class MemoryOperationResponse(BaseModel):
    success: bool
    message: str
    target: str
    chars_used: int
    char_limit: int

class FactResponse(BaseModel):
    id: str
    user_id: str
    category: str
    content: str
    salience_score: float
    valid_from: datetime
    valid_until: Optional[datetime] = None
    created_at: datetime
    invalidated_at: Optional[datetime] = None
    linked_to: Optional[str] = None
    is_active: bool

class TombstoneResponse(BaseModel):
    id: str
    fact_id: str
    user_id: str
    reason: str
    superseded_by: Optional[str] = None
    created_at: datetime

class MemorySnapshotResponse(BaseModel):
    user_md: str
    memory_md: str
    user_md_chars: int
    user_md_max: int
    memory_md_chars: int
    memory_md_max: int

class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Non-empty user message.")
    user_id: str = "default_user"
    session_id: Optional[str] = "default_session"

    @field_validator("message")
    @classmethod
    def _strip_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v

class ChatMessageResponse(BaseModel):
    response: str
    session_id: str
    retrieved_facts: List[str] = Field(default_factory=list)
    extracted_facts: List[ExtractedFact] = Field(default_factory=list)
    memory_updated: bool = False

class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(default="Software Engineer", max_length=256)
    location: str = Field(default="Remote", max_length=256)
    avatar_bg: str = Field(default="from-amber-500 to-orange-600")

class ProfileResponse(BaseModel):
    id: str
    name: str
    role: str
    location: str
    avatar_bg: str
    created_at: datetime

    model_config = {"from_attributes": True}

class ChatThreadCreate(BaseModel):
    user_id: str
    title: Optional[str] = "New Conversation"
    id: Optional[str] = None

class ChatThreadUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)

class ChatThreadResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class TurnResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}

class UserPreferenceResponse(BaseModel):
    login_username: str
    active_profile_id: Optional[str] = None
    active_thread_id: Optional[str] = None
    updated_at: datetime

    model_config = {"from_attributes": True}

class UserPreferenceUpdate(BaseModel):
    active_profile_id: Optional[str] = None
    active_thread_id: Optional[str] = None
