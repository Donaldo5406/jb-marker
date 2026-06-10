"""PromptSpec — 시스템프롬프트 조립 표준 (spec §5.1).

하네스 6요소(persona·constraints·references·structured_output·studio·step 신호)를
선언적 필드로 들고, assemble()이 결정론적 순서(persona→constraints→output_schema→references)로
결합한다. 각 블록은 자신의 선행 구분자("\n\n" 등)를 포함한다 — 조립 결과가 현행
인라인 f-string과 문자 단위 동일해야 하기 때문(D6 행동 보존).
"""
from dataclasses import dataclass, field


@dataclass
class PromptSpec:
    persona: str                          # 시스템프롬프트 본문(역할·지시)
    constraints: list[str] = field(default_factory=list)   # 스텝 지시·제약 블록
    references: list[str] = field(default_factory=list)    # 컨텍스트/레퍼런스 블록
    output_schema: str | None = None      # 구조화 출력 지시(현행 인라인 JSON 지시문)
    studio: str = ""                      # 명시 신호
    step: str = ""                        # 명시 신호 (예: "stage_a", "S1", "R2")

    def assemble(self) -> str:
        """결정론적 결합. 블록들은 자체 구분자를 포함한다(D6 — 현행 문자열 보존)."""
        parts = [self.persona, *self.constraints]
        if self.output_schema is not None:
            parts.append(self.output_schema)
        parts.extend(self.references)
        return "".join(parts)

    @property
    def meta(self) -> dict:
        return {"studio": self.studio, "step": self.step}
