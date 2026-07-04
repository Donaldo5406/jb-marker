# 본선 고도화 — 산출물 증빙 (evidence)

> [최적화 변경 보고서](../optimization-report.md)의 실물 증빙. 모두 **실 AI API 또는 실 ffmpeg 렌더**의 결과물이다(Mock 아님).

## 영상 — 렌더 시네마틱화 (보고서 §2)
| 파일 | 무엇 |
| --- | --- |
| `video-cinematic-crossfade.mp4` | **최종 시네마틱 렌더**(실 Veo 2샷 → 실 ffmpeg). h264 1080×1920 / 30fps / AAC / 12→**11.4초**(크로스페이드로 정확히 압축). 자막 스크림·키네틱 페이드·켄번스·컬러그레이드·음악 베드 적용 |
| `video-shot1-headline-body.png` | 샷1 프레임 — 헤드라인 드롭섀도+외곽선, 골드 서브카피, 웜 그레이드·비네팅 |
| `video-crossfade-blend-50pct.png` | 샷1↔샷2 **크로스페이드 중간 프레임**(두 장면 50% 디졸브 블렌드) |
| `video-shot2-cta-disclosure-scrim.png` | 샷2 프레임 — CTA + **법정 고지 박스 스크림**(복잡한 배경 위 100% 가독) |

## 이미지 — 풀베이크 포스터 (보고서 §3, 실 gemini-3-pro-image)
| 파일 | 무엇 |
| --- | --- |
| `image-poster-ko-fullbake.png` | 한국어 4:5 포스터 — 헤드라인/바디/CTA **한글 완벽 베이크** |
| `image-poster-vi-fullbake.png` | 베트남어 4:5 포스터 — **성조부호 포함 완벽 베이크**(풀베이크 확정 근거) |

## 영상 소재 — Veo footage (보고서 §1, 화면회피 프롬프트 적용본)
| 파일 | 무엇 |
| --- | --- |
| `veo-footage-screenless.mp4` | 실 Veo 8초 클립 — 인물·표정·라이프스타일, **기기 화면 노출 회피**(가짜 UI 글씨 footgun 제거본) |

---
*비교용 원본(스모크 전체·frame 다수)은 `docs/eval/smoke-2026-06-30/`(로컬)·세션 스크래치패드에 있으며, 위는 대표 증빙만 큐레이션한 것이다.*
