"""Initial SkillGraph schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-20

"""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_meta",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("canonical_name", sa.String(length=120), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.UniqueConstraint("canonical_name"),
    )
    op.create_index("ix_skills_category", "skills", ["category"])
    op.create_table(
        "skill_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_skill_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("target_skill_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("provenance", sa.String(length=120), nullable=False),
        sa.UniqueConstraint(
            "source_skill_id",
            "target_skill_id",
            "relation_type",
            name="uq_skill_relation",
        ),
    )
    op.create_index("ix_skill_relations_source_skill_id", "skill_relations", ["source_skill_id"])
    op.create_index("ix_skill_relations_target_skill_id", "skill_relations", ["target_skill_id"])
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("family", sa.String(length=80), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.UniqueConstraint("title"),
    )
    op.create_index("ix_roles_family", "roles", ["family"])
    op.create_table(
        "role_requirements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("target_level", sa.Integer(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("mandatory", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("role_id", "skill_id", name="uq_role_requirement"),
    )
    op.create_index("ix_role_requirements_skill_id", "role_requirements", ["skill_id"])
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("consent_metadata", sa.JSON(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "profile_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("self_assessed_level", sa.Integer(), nullable=True),
        sa.Column("asserted_label", sa.String(length=120), nullable=False),
        sa.Column("last_verified", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("profile_id", "skill_id", name="uq_profile_skill"),
    )
    op.create_index("ix_profile_skills_profile_id", "profile_skills", ["profile_id"])
    op.create_index("ix_profile_skills_skill_id", "profile_skills", ["skill_id"])
    op.create_table(
        "learning_resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("target_skill_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=False),
        sa.Column("prerequisite_skill_ids", sa.JSON(), nullable=False),
        sa.Column("duration_hours", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
    )
    op.create_index("ix_learning_resources_target_skill_id", "learning_resources", ["target_skill_id"])
    op.create_table(
        "recommendation_traces",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("graph_version", sa.Integer(), nullable=False),
        sa.Column("method_version", sa.String(length=64), nullable=False),
        sa.Column("weights_version", sa.String(length=64), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    graph_meta = sa.table(
        "graph_meta",
        sa.column("id", sa.Integer),
        sa.column("graph_version", sa.Integer),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        graph_meta,
        [{"id": 1, "graph_version": 0, "updated_at": datetime.now(timezone.utc)}],
    )


def downgrade() -> None:
    op.drop_table("recommendation_traces")
    op.drop_table("learning_resources")
    op.drop_table("profile_skills")
    op.drop_table("profiles")
    op.drop_table("role_requirements")
    op.drop_table("roles")
    op.drop_table("skill_relations")
    op.drop_table("skills")
    op.drop_table("graph_meta")
