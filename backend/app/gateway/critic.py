"""CriticVerdict — critic 출력 표준 봉투 (spec §6)."""
from dataclasses import dataclass, field


@dataclass
class CriticVerdict:
    passed: bool
    issues: list[str] = field(default_factory=list)   # 누락 필드·결함 서술
    scores: dict | None = None                        # design 채점 등 도메인 페이로드

    def to_dict(self) -> dict:
        out: dict = {"passed": self.passed, "issues": list(self.issues)}
        if self.scores is not None:
            out["scores"] = self.scores
        return out
