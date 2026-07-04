#!/usr/bin/env bash
# 음악 베드 생성기 — ffmpeg 사인 합성으로 따뜻한 앰비언트 패드(bed.m4a)를 만든다.
# 절차적 합성이라 서드파티 권리 없음 → CC0 / Public Domain. 재현용으로 커밋.
#
# v2: 정적 드론("뚜-" 단음)을 탈피해 4코드 진행(I-vi-IV-V, C major = 성장·희망 무드)을
#     크로스페이드로 이어 붙인다. 각 코드=3음 사인 믹스, 부드러운 페이드 + 에코(공간)
#     + 트레몰로(호흡) + 하이/로우패스 + 스테레오. 절대 레벨은 렌더 loudnorm이 -18 LUFS 보정.
set -euo pipefail
cd "$(dirname "$0")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 한 코드(3음) = 사인 믹스 + 인/아웃 페이드. 6초.
make_chord () {
  local out="$1" f1="$2" f2="$3" f3="$4"
  ffmpeg -y \
    -f lavfi -i "sine=frequency=$f1:duration=6" \
    -f lavfi -i "sine=frequency=$f2:duration=6" \
    -f lavfi -i "sine=frequency=$f3:duration=6" \
    -filter_complex "[0][1][2]amix=inputs=3:normalize=1,\
afade=t=in:st=0:d=0.6,afade=t=out:st=5.2:d=0.8[a]" \
    -map "[a]" "$out" >/dev/null 2>&1
}
make_chord "$TMP/c1.wav" 130.81 196.00 329.63   # C  (C3·G3·E4)
make_chord "$TMP/c2.wav" 110.00 261.63 329.63   # Am (A2·C4·E4)
make_chord "$TMP/c3.wav"  87.31 220.00 261.63   # F  (F2·A3·C4)
make_chord "$TMP/c4.wav"  98.00 246.94 293.66   # G  (G2·B3·D4)

# 코드들을 크로스페이드(1s)로 이어 진행감 부여 → 공간·따뜻함·스테레오 마감.
ffmpeg -y -i "$TMP/c1.wav" -i "$TMP/c2.wav" -i "$TMP/c3.wav" -i "$TMP/c4.wav" \
  -filter_complex "\
[0][1]acrossfade=d=1:c1=tri:c2=tri[a01];\
[a01][2]acrossfade=d=1:c1=tri:c2=tri[a012];\
[a012][3]acrossfade=d=1:c1=tri:c2=tri[prog];\
[prog]aecho=0.8:0.85:70|130:0.35|0.2,tremolo=f=0.2:d=0.22,\
highpass=f=70,lowpass=f=2600,volume=2.0[a]" \
  -map "[a]" -ac 2 -ar 44100 -c:a aac -b:a 160k bed.m4a

echo "wrote $(pwd)/bed.m4a"
