"""AdvisorHarness — D2 카피 적응 멀티턴 + 도구 화이트리스트 + grounding 출력 검증."""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from app.deploy.advisor.tools import ALLOWED, ToolNotAllowed, TOOL_SCHEMAS, assert_allowed
from app.deploy.advisor.prompt import SYSTEM_PROMPT
from app.deploy.advisor.grounding import check as grounding_check


class AdvisorHarness:
    """카드(packageId) 단위 멀티턴 챗 + write_d2_copy 출력 검증."""

    def __init__(self, *, provider, vfs_store, run_id: str):
        self.provider = provider
        self.vfs = vfs_store
        self.run_id = run_id

    # --- helpers --------------------------------------------------------

    def _state_path(self, package_id: str) -> str:
        return f"/{self.run_id}/deploy/advisor/transcripts/{package_id}.jsonl"

    def _append_event(self, package_id: str, event: dict) -> None:
        path = self._state_path(package_id)
        existing = self.vfs.get_text(path) or ""
        self.vfs.put_text(path, existing + json.dumps(event, ensure_ascii=False) + "\n")

    def _read_review_context(self, package_id: str) -> dict:
        """read_review 도구 구현 — VFS에서 review 통과 텍스트·고지 로드."""
        copy_meta_path = f"/{self.run_id}/deploy/packages/{package_id}/copy.meta.json"
        meta_raw = self.vfs.get_text(copy_meta_path)
        if not meta_raw:
            return {"error": f"package {package_id} not found"}
        return json.loads(meta_raw)

    def _read_eligibility(self) -> dict:
        """read_eligibility 도구 구현 — D1 결과 요약."""
        path = f"/{self.run_id}/deploy/eligibility/recipients.json"
        raw = self.vfs.get_text(path)
        if not raw:
            return {"error": "eligibility not computed yet"}
        recipients = json.loads(raw)
        return {"eligible_count": len(recipients), "languages": list({r["lang"] for r in recipients})}

    # --- main entry -----------------------------------------------------

    def handle_turn(self, *, package_id: str, user_message: str) -> dict:
        """한 턴 처리 — 모델 호출 → 도구 디스패치 → write_d2_copy 시 grounding 검증."""
        self._append_event(package_id, {"role": "user", "content": user_message})

        ctx = self._read_review_context(package_id)
        if "error" in ctx:
            return {"status": "error", "message": ctx["error"]}

        response = self.provider.chat(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            tools=TOOL_SCHEMAS,
        )

        self._append_event(package_id, {"role": "assistant", "content": response.get("text", ""), "tool_calls": response.get("tool_calls", [])})

        result: dict[str, Any] = {"status": "ok", "text": response.get("text", ""), "tool_results": []}

        for call in response.get("tool_calls", []):
            try:
                assert_allowed(call["name"])
            except ToolNotAllowed as e:
                self._append_event(package_id, {"tool_blocked": call["name"], "reason": str(e)})
                result["tool_results"].append({"name": call["name"], "status": "blocked", "reason": str(e)})
                continue

            if call["name"] == "read_review":
                out = self._read_review_context(call["input"]["package_id"])
                result["tool_results"].append({"name": "read_review", "output": out})
            elif call["name"] == "read_eligibility":
                out = self._read_eligibility()
                result["tool_results"].append({"name": "read_eligibility", "output": out})
            elif call["name"] == "write_d2_copy":
                adapted = call["input"]["adapted_text"]
                g = grounding_check(
                    original=ctx.get("original_text", ""),
                    adapted=adapted,
                    disclosures=ctx.get("disclosures", []),
                )
                if g.ok:
                    # 영속 — copy.md + copy.meta.json grounding_check 갱신
                    self.vfs.put_text(
                        f"/{self.run_id}/deploy/packages/{package_id}/copy.md",
                        adapted + "\n\n" + "\n".join(ctx.get("disclosures", [])),
                    )
                    meta = {**ctx, "advisor_used": True, "grounding_check": "ok", "adapted_text": adapted}
                    self.vfs.put_text(
                        f"/{self.run_id}/deploy/packages/{package_id}/copy.meta.json",
                        json.dumps(meta, ensure_ascii=False),
                    )
                    result["tool_results"].append({"name": "write_d2_copy", "status": "ok"})
                else:
                    meta = {**ctx, "advisor_used": True, "grounding_check": "fail", "failures": g.failures}
                    self.vfs.put_text(
                        f"/{self.run_id}/deploy/packages/{package_id}/copy.meta.json",
                        json.dumps(meta, ensure_ascii=False),
                    )
                    result["tool_results"].append({"name": "write_d2_copy", "status": "fail", "failures": g.failures})

        return result
