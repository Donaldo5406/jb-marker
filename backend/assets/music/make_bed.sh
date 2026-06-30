#!/usr/bin/env bash
# 음악 베드 생성기 — ffmpeg 사인 합성으로 따뜻한 앰비언트 패드(bed.m4a)를 만든다.
# 절차적 합성이라 서드파티 권리 없음 → CC0 / Public Domain. 재현용으로 커밋.
#
# 코드: C3·G3·C4·E4 (Cmaj, 성장·신뢰 무드) + 느린 트레몰로(호흡) + 에코(공간)
#       + 하이/로우패스(클린업) + 인/아웃 페이드. 절대 레벨은 렌더의 loudnorm이 -18 LUFS로 보정.
set -euo pipefail
cd "$(dirname "$0")"

ffmpeg -y \
  -f lavfi -i "sine=frequency=130.81:duration=22" \
  -f lavfi -i "sine=frequency=196.00:duration=22" \
  -f lavfi -i "sine=frequency=261.63:duration=22" \
  -f lavfi -i "sine=frequency=329.63:duration=22" \
  -filter_complex \
  "[0][1][2][3]amix=inputs=4:normalize=1,\
tremolo=f=0.18:d=0.5,\
aecho=0.8:0.85:80|160:0.35|0.2,\
highpass=f=70,lowpass=f=2400,\
afade=t=in:st=0:d=4,afade=t=out:st=18:d=4,\
volume=2.4[a]" \
  -map "[a]" -ac 2 -ar 44100 -c:a aac -b:a 160k bed.m4a

echo "wrote $(pwd)/bed.m4a"
