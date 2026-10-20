"""Request bodies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=120)
    aliases: list[str] = Field(default_factory=list)
    category: str = Field(min_length=1, max_length=40)
    description: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)
    source: str = "user"


class SkillUpdate(BaseModel):
    canonical_name: str | None = Field(default=None, min_length=1, max_length=120)
    aliases: list[str] | None = None
    category: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class RelationCreate(BaseModel):
    source_skill_id: int
    target_skill_id: int
    relation_type: Literal["prerequisite", "related", "broader", "narrower"]
    weight: float = Field(gt=0, le=1)
    provenance: str = Field(default="user", max_length=120)


class RequirementCreate(BaseModel):
    skill_id: int
    target_level: int = Field(ge=0, le=5)
    importance: float = Field(gt=0, le=5)
    mandatory: bool = False


class RoleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    family: str = Field(min_length=1, max_length=80)
    summary: str = ""
    requirements: list[RequirementCreate] = Field(default_factory=list)


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    summary: str = ""


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    summary: str | None = None


class ProfileSkillWrite(BaseModel):
    skill_id: int
    self_assessed_level: int | None = Field(default=None, ge=0, le=5)
    asserted_label: str | None = Field(default=None, max_length=120)


class RecommendRequest(BaseModel):
    profile_id: int
    role_id: int
    weights: dict[str, float] | None = None


class CompareRequest(BaseModel):
    profile_id: int
    role_a_id: int
    role_b_id: int


class PathRequest(BaseModel):
    profile_id: int
    role_id: int
