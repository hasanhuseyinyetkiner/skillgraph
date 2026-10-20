"""HTTP routes for the skill graph."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import GraphMeta, Profile
from app.schemas import (
    CompareRequest,
    PathRequest,
    ProfileCreate,
    ProfileSkillWrite,
    ProfileUpdate,
    RecommendRequest,
    RelationCreate,
    RoleCreate,
    SkillCreate,
    SkillUpdate,
)
from app.services.catalog import (
    GraphCache,
    compare_roles,
    create_profile,
    create_relation,
    create_role,
    create_skill,
    delete_profile,
    delete_profile_skill,
    delete_relation,
    delete_skill,
    export_profile,
    get_role,
    graph_payload,
    heavy_analysis,
    import_csv,
    learning_path,
    list_roles,
    list_skills,
    meta_payload,
    ontology_quality,
    profile_payload,
    profile_summary,
    recommend,
    reset_demo,
    run_evaluation,
    update_profile,
    update_skill,
    upsert_profile_skill,
)

router = APIRouter()
ALLOWED_CSV_TYPES = {
    "",
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}


def _session(request: Request) -> Session:
    return request.app.state.session_factory()


def _cache(request: Request) -> GraphCache:
    return request.app.state.graph_cache


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request) -> JSONResponse:
    def ping() -> int:
        session = _session(request)
        try:
            session.execute(text("SELECT 1"))
            version = session.scalar(select(GraphMeta.graph_version).where(GraphMeta.id == 1))
            if version is None:
                raise RuntimeError("graph_meta missing")
            return int(version)
        finally:
            session.close()

    try:
        version = await run_in_threadpool(ping)
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ready", "graph_version": version})


@router.get("/")
async def root() -> dict[str, str]:
    return {"service": "skillgraph", "health": "/health", "docs": "/docs", "meta": "/api/meta"}


@router.get("/api/meta")
async def meta(request: Request) -> dict[str, object]:
    return meta_payload(request.app.state.settings)


@router.get("/api/skills")
async def skills(request: Request, q: str | None = None, category: str | None = None) -> list[dict[str, object]]:
    def work() -> list[dict[str, object]]:
        session = _session(request)
        try:
            return list_skills(session, q, category)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/skills", status_code=201)
async def post_skill(request: Request, body: SkillCreate) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return create_skill(session, body.model_dump())
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.patch("/api/skills/{skill_id}")
async def patch_skill(request: Request, skill_id: int, body: SkillUpdate) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return update_skill(session, skill_id, body.model_dump(exclude_unset=True))
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.delete("/api/skills/{skill_id}")
async def remove_skill(request: Request, skill_id: int) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return delete_skill(session, skill_id)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/relations", status_code=201)
async def post_relation(request: Request, body: RelationCreate) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return create_relation(session, body.model_dump())
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.delete("/api/relations/{relation_id}")
async def remove_relation(request: Request, relation_id: int) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return delete_relation(session, relation_id)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/roles")
async def roles(request: Request) -> list[dict[str, object]]:
    def work() -> list[dict[str, object]]:
        session = _session(request)
        try:
            return list_roles(session)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/roles/{role_id}")
async def role_detail(request: Request, role_id: int) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            return get_role(session, snapshot, role_id)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/roles", status_code=201)
async def post_role(request: Request, body: RoleCreate) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return create_role(session, body.model_dump())
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/graph")
async def graph(
    request: Request,
    category: str | None = None,
    family: str | None = None,
    relation_type: str | None = None,
    q: str | None = None,
    limit: int = 500,
) -> dict[str, object]:
    bounded = min(max(limit, 1), 1000)

    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            return graph_payload(
                snapshot,
                category=category,
                family=family,
                relation_type=relation_type,
                query=q,
                limit=bounded,
            )
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/ontology/quality")
async def quality(request: Request) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return ontology_quality(_cache(request).get(session))
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/evaluation")
async def evaluation(request: Request) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            return run_evaluation(_cache(request).get(session))
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/analysis/run")
async def analysis(request: Request, delay_ms: int = 0) -> dict[str, object]:
    if delay_ms < 0 or delay_ms > 5000:
        raise HTTPException(status_code=400, detail="delay_ms must be between 0 and 5000")
    if delay_ms and request.app.state.settings.app_env != "test":
        raise HTTPException(status_code=400, detail="delay_ms is only available when APP_ENV=test")
    return await run_in_threadpool(
        heavy_analysis,
        request.app.state.session_factory,
        request.app.state.graph_cache,
        delay_ms,
    )


@router.get("/api/profiles/demo")
async def demo_profile(request: Request) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            profile = session.scalar(select(Profile).where(Profile.slug == "demo"))
            if profile is None:
                from app.errors import DomainError

                raise DomainError("Demo profile not found", 404, "not_found")
            return profile_payload(session, profile, snapshot)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/profiles/demo/reset")
async def demo_reset(request: Request) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            profile = reset_demo(session)
            snapshot = _cache(request).get(session)
            return profile_payload(session, profile, snapshot)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/profiles/{profile_id}")
async def get_profile(request: Request, profile_id: int) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            profile = session.get(Profile, profile_id)
            if profile is None:
                from app.errors import DomainError

                raise DomainError("Profile not found", 404, "not_found")
            return profile_payload(session, profile, snapshot)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/profiles", status_code=201)
async def post_profile(request: Request, body: ProfileCreate) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            profile = create_profile(session, body.display_name, body.summary)
            snapshot = _cache(request).get(session)
            return profile_payload(session, profile, snapshot)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.put("/api/profiles/{profile_id}")
async def put_profile(request: Request, profile_id: int, body: ProfileUpdate) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            profile = update_profile(session, profile_id, body.display_name, body.summary)
            snapshot = _cache(request).get(session)
            return profile_payload(session, profile, snapshot)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.delete("/api/profiles/{profile_id}", status_code=204)
async def remove_profile(request: Request, profile_id: int) -> None:
    def work() -> None:
        session = _session(request)
        try:
            delete_profile(session, profile_id)
        finally:
            session.close()

    await run_in_threadpool(work)


@router.get("/api/profiles/{profile_id}/export")
async def export(request: Request, profile_id: int) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            return export_profile(session, snapshot, profile_id)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.get("/api/profiles/{profile_id}/summary")
async def summary(request: Request, profile_id: int) -> dict[str, object]:
    return await run_in_threadpool(
        profile_summary,
        request.app.state.session_factory,
        request.app.state.graph_cache,
        request.app.state.settings,
        profile_id,
    )


@router.post("/api/profiles/{profile_id}/skills")
async def post_profile_skill(request: Request, profile_id: int, body: ProfileSkillWrite) -> dict[str, object]:
    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            return upsert_profile_skill(
                session,
                snapshot,
                profile_id,
                body.skill_id,
                body.self_assessed_level,
                body.asserted_label,
            )
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.delete("/api/profiles/{profile_id}/skills/{skill_id}", status_code=204)
async def remove_profile_skill(request: Request, profile_id: int, skill_id: int) -> None:
    def work() -> None:
        session = _session(request)
        try:
            delete_profile_skill(session, profile_id, skill_id)
        finally:
            session.close()

    await run_in_threadpool(work)


@router.post("/api/profiles/{profile_id}/import")
async def upload_csv(
    request: Request,
    profile_id: int,
    mode: str = "preview",
    file: UploadFile = File(...),  # noqa: B008
) -> dict[str, object]:
    if mode not in {"preview", "commit"}:
        raise HTTPException(status_code=400, detail="mode must be preview or commit")
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a .csv file")
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in ALLOWED_CSV_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported media type")
    raw = await file.read()

    def work() -> dict[str, object]:
        session = _session(request)
        try:
            snapshot = _cache(request).get(session)
            return import_csv(session, snapshot, profile_id, raw, mode)
        finally:
            session.close()

    return await run_in_threadpool(work)


@router.post("/api/recommendations")
async def recommendations(request: Request, body: RecommendRequest) -> dict[str, object]:
    return await run_in_threadpool(
        recommend,
        request.app.state.session_factory,
        request.app.state.graph_cache,
        request.app.state.settings,
        profile_id=body.profile_id,
        role_id=body.role_id,
        weights_payload=body.weights,
    )


@router.post("/api/recommendations/compare")
async def compare(request: Request, body: CompareRequest) -> dict[str, object]:
    return await run_in_threadpool(
        compare_roles,
        request.app.state.session_factory,
        request.app.state.graph_cache,
        request.app.state.settings,
        profile_id=body.profile_id,
        role_a_id=body.role_a_id,
        role_b_id=body.role_b_id,
    )


@router.post("/api/learning-paths")
async def paths(request: Request, body: PathRequest) -> dict[str, object]:
    return await run_in_threadpool(
        learning_path,
        request.app.state.session_factory,
        request.app.state.graph_cache,
        request.app.state.settings,
        profile_id=body.profile_id,
        role_id=body.role_id,
    )
