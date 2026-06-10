"""[meta] /health · GET/PUT /entitlement (spec §8.1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import entitlement
from .deps import get_user_id

router = APIRouter(tags=["meta"])


class EntitlementPut(BaseModel):
    marker: bool


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/entitlement")
def get_entitlement(user_id: str = Depends(get_user_id)) -> dict:
    return {"marker": entitlement.is_entitled(user_id)}


@router.put("/entitlement")
def put_entitlement(body: EntitlementPut, user_id: str = Depends(get_user_id)) -> dict:
    if body.marker:
        entitlement.set_dev_pass(user_id)
    else:
        entitlement.reset(user_id)
    return {"marker": entitlement.is_entitled(user_id)}
