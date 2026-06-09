// frontend/lib/editor/exportPng.ts
/** PNG 내보내기 순수 헬퍼. dataURL을 <a download>로 트리거(브라우저 다운로드). doc 주입으로 테스트 가능. */

/** 언어별 파일명. 예: design-ko.png. 위험/경로 문자는 제거(영숫자·_·-만 허용). */
export function exportFilename(lang: string): string {
  const safe = (lang || "").replace(/[^a-z0-9_-]+/gi, "") || "design";
  return `design-${safe}.png`;
}

/** dataURL을 파일 다운로드로 트리거. doc=document(테스트는 스텁 주입). */
export function triggerPngDownload(dataUrl: string, filename: string, doc: Document = document): void {
  const a = doc.createElement("a") as HTMLAnchorElement;
  a.href = dataUrl;
  a.download = filename;
  doc.body.appendChild(a);
  a.click();
  doc.body.removeChild(a);
}
