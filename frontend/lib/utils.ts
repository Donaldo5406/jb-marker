import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// 커스텀 fontSize 토큰(text-h1/h2/h3 · text-body-lg/body-sm · text-caption)이 기본 twMerge에서
// text-color(text-on-primary 등)와 같은 'text-*' 그룹으로 오인돼, cva로 색+크기를 함께 쓰면
// 색 클래스가 드롭되는 버그가 있다(예: primary 버튼 글자색 소실). fontSize 토큰을 font-size
// 그룹에 명시 등록해 색/크기 충돌을 분리한다.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [{ text: ["h1", "h2", "h3", "body-lg", "body-sm", "caption"] }],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
