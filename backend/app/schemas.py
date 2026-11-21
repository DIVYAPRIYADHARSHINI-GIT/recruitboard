import re
from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal['admin', 'recruiter', 'interviewer']
StageKey = Literal['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']
Source = Literal['referral', 'job_portal', 'campus', 'website']
Rating = Annotated[int, Field(strict=True, ge=1, le=5)]


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


def normalize_email(value):
    value = value.lower().strip()
    if not re.fullmatch(r'[^\s@]{1,64}@[^\s@]+\.[^\s@]+', value) or len(value) > 254:
        raise ValueError('Enter a valid email address')
    return value


class Login(Input):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128)
    _email = field_validator('email')(normalize_email)


class Demo(Input):
    role: Role


class JobInput(Input):
    title: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=80)
    location: str = Field(min_length=2, max_length=100)
    openings: int = Field(strict=True, ge=1, le=1000)
    status: Literal['open', 'on_hold', 'closed'] = 'open'


class CandidateInput(Input):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    phone: str = Field(default='', max_length=30, pattern=r'^[0-9+() .-]*$')
    source: Source = 'website'
    notes: str = Field(default='', max_length=10000)
    tags: list[Annotated[str, Field(min_length=1, max_length=32, pattern=r'^[\w -]+$')]] = Field(default_factory=list, max_length=12)
    _email = field_validator('email')(normalize_email)


class CandidateCreate(CandidateInput):
    job_id: int = Field(strict=True, gt=0)


class ApplicationInput(Input):
    candidate_id: int = Field(strict=True, gt=0)
    job_id: int = Field(strict=True, gt=0)


class Move(Input):
    stage: StageKey
    version: int = Field(strict=True, gt=0)
    reason_id: int | None = Field(default=None, strict=True, gt=0)


class InterviewInput(Input):
    application_id: int = Field(strict=True, gt=0)
    interviewer_id: int = Field(strict=True, gt=0)
    starts_at: datetime
    mode: Literal['video', 'phone', 'in_person'] = 'video'

    @field_validator('starts_at')
    @classmethod
    def aware_time(cls, value):
        if value.tzinfo is None:
            raise ValueError('Include a time zone')
        if not 2000 <= value.year <= 2100:
            raise ValueError('Date outside supported range')
        return value.astimezone(timezone.utc).replace(tzinfo=None)


class ScoreInput(Input):
    technical: Rating
    communication: Rating
    culture: Rating
    recommendation: Literal['strong_yes', 'yes', 'neutral', 'no', 'strong_no']
    feedback: str = Field(min_length=10, max_length=10000)


class OfferInput(Input):
    status: Literal['draft', 'sent', 'accepted', 'declined']
    amount_minor: int | None = Field(default=None, strict=True, ge=0, le=2000000000)


class UserCreate(Input):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=254)
    password: str = Field(min_length=12, max_length=128)
    role: Role
    _email = field_validator('email')(normalize_email)


class UserUpdate(Input):
    role: Role
    active: bool = Field(strict=True)


class StageInput(Input):
    label: str = Field(min_length=2, max_length=50)
    position: int = Field(strict=True, ge=0, le=5)


class CriterionInput(Input):
    label: str = Field(min_length=2, max_length=80)
    guidance: str = Field(max_length=300)


class ReasonInput(Input):
    label: str = Field(min_length=2, max_length=100)
    active: bool = True


class PrivacyInput(Input):
    action: Literal['anonymize', 'delete']
    confirmation: Literal['CONFIRM']