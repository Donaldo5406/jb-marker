"""DeployAdapter ABC + 타입 정의."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class Package:
    channel: str
    lang: str
    visual_path: str
    copy_text: str
    meta: dict


@dataclass
class ScheduleSpec:
    send_hour: int
    timezone: str = "Asia/Seoul"


@dataclass
class DispatchResult:
    status: Literal["ok", "fail", "skipped"]
    channel: str
    lang: str
    recipients_count: int
    message: str
    meta: dict


class DeployAdapter(ABC):
    @abstractmethod
    def dispatch(self, channel: str, package: Package, schedule: ScheduleSpec, recipients: list[dict]) -> DispatchResult:
        ...

    @property
    @abstractmethod
    def status(self) -> Literal["stub", "live"]:
        ...
