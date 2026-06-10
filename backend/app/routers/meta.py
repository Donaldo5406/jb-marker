"""[meta] /health · GET/PUT /entitlement (spec §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import entitlement
from ..schemas import AUTH_RESPONSES, EntitlementOut, HealthOut
from .deps import get_user_id

router = APIRouter(tags=["meta"])


class EntitlementPut(BaseModel):
    marker: bool


@router.get("/health", response_model=HealthOut, summary="헬스 체크")
def health() -> dict:
    return {"status": "ok"}


@router.get("/entitlement", response_model=EntitlementOut,
            summary="현재 사용자의 Marker 권한 조회",
            responses=AUTH_RESPONSES)
def get_entitlement(user_id: str = Depends(get_user_id)) -> dict:
    return {"marker": entitlement.is_entitled(user_id)}


@router.put("/entitlement", response_model=EntitlementOut,
            summary="Marker 권한 토글(dev pass 부여/해제)",
            responses=AUTH_RESPONSES)
def put_entitlement(body: EntitlementPut, user_id: str = Depends(get_user_id)) -> dict:
    if body.marker:
        entitlement.set_dev_pass(user_id)
    else:
        entitlement.reset(user_id)
    return {"marker": entitlement.is_entitled(user_id)}
