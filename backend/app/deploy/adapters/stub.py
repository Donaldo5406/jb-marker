"""StubAdapter — 실 dispatch ✗, 로그 + 결과 반환만."""
from __future__ import annotations

from app.deploy.adapters.base import DeployAdapter, Package, ScheduleSpec, DispatchResult


class StubAdapter(DeployAdapter):
    @property
    def status(self):
        return "stub"

    def dispatch(self, channel, package, schedule, recipients):
        return DispatchResult(
            status="ok",
            channel=channel,
            lang=package.lang,
            recipients_count=len(recipients),
            message=f"[STUB] Would dispatch {channel}/{package.lang} to {len(recipients)} recipients at {schedule.send_hour}:00 {schedule.timezone}",
            meta={"visual": package.visual_path, "copy_length": len(package.copy_text)},
        )
