"""SQLAlchemy models shared by SQLite and PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:

    return datetime.now(UTC)


class GraphMeta(Base):
    __tablename__ = "graph_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="user")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")


class SkillRelation(Base):
    __tablename__ = "skill_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_skill_id",
            "target_skill_id",
            "relation_type",
            name="uq_skill_relation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    target_skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[str] = mapped_column(String(120), nullable=False, default="user")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    family: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    requirements: Mapped[list[RoleRequirement]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )


class RoleRequirement(Base):
    __tablename__ = "role_requirements"
    __table_args__ = (
        UniqueConstraint("role_id", "skill_id", name="uq_role_requirement"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    role: Mapped[Role] = relationship(back_populates="requirements")


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    consent_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    skills: Mapped[list[ProfileSkill]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )


class ProfileSkill(Base):
    __tablename__ = "profile_skills"
    __table_args__ = (
        UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    self_assessed_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asserted_label: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    last_verified: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile: Mapped[Profile] = relationship(back_populates="skills")


class LearningResource(Base):
    __tablename__ = "learning_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    target_skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), nullable=False, index=True)
    prerequisite_skill_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="synthetic catalog")


class RecommendationTrace(Base):
    __tablename__ = "recommendation_traces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=True,
    )
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    graph_version: Mapped[int] = mapped_column(Integer, nullable=False)
    method_version: Mapped[str] = mapped_column(String(64), nullable=False)
    weights_version: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
