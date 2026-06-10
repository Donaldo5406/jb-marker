"""[runs] POST/GET /runs (spec §8.1)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..schemas import AUTH_RESPONSES, RunCreatedOut, RunListOut
from .deps import get_user_id

router = APIRouter(tags=["runs"])


class RunCreate(BaseModel):
    title: str | None = None
    languages: list[str] = []


@router.post("/runs", response_model=RunCreatedOut, summary="run 생성",
             responses=AUTH_RESPONSES)
def create_run(body: RunCreate, request: Request,
               user_id: str = Depends(get_user_id)) -> dict:
    run_id = uuid.uuid4().hex[:12]
    m = request.app.state.store.create_run(run_id, user_id=user_id,
                                           title=body.title, languages=body.languages)
    return {"run_id": m.run_id, "title": m.title}


@router.get("/runs", response_model=RunListOut, summary="현재 사용자의 run 목록",
            responses=AUTH_RESPONSES)
def list_runs(request: Request, user_id: str = Depends(get_user_id)) -> dict:
    runs = request.app.state.store.list_runs(user_id=user_id)
    return {"runs": [{"run_id": m.run_id, "title": m.title,
                      "created_at": m.created_at,
                      "step_status": m.step_status} for m in runs]}
