"use client";
import * as React from "react";
import dynamic from "next/dynamic";

// filerobot가 SSR을 못 하므로(window/konva) 동적 import로 클라이언트에서만 로드.
const DynamicFilerobot = dynamic(() => import("react-filerobot-image-editor"), { ssr: false });

// TABS 문자열 값(react-filerobot-image-editor v5.0.1의 TABS enum). named export를 최상위 import하면
// SSR 시 패키지 본체가 평가되어 깨지므로 값으로 하드코딩한다.
const TAB_IDS = ["Adjust", "Finetune", "Filters", "Watermark", "Annotate", "Resize"];

export type EditedImageObject = {
  imageBase64?: string; fullName?: string; name?: string;
  extension?: string; mimeType?: string; width?: number; height?: number;
};
export type FilerobotProps = {
  source: string;
  onSave?: (img: EditedImageObject, designState: unknown) => void;
  onClose?: (reason: string, unsaved: boolean) => void;
  tabsIds?: string[];
  defaultTabId?: string;
};

/** 활성 이미지를 filerobot로 픽셀 편집. 저장 시 편집본 dataURL을 onApply(dataUrl, fullName)로 넘긴다.
 *  EditorComponent는 테스트 주입용(기본값=동적 filerobot). */
export function RasterEditModal({
  open, source, fileName, onApply, onClose,
  EditorComponent = DynamicFilerobot as unknown as React.ComponentType<FilerobotProps>,
}: {
  open: boolean;
  source: string;
  fileName: string;
  onApply: (dataUrl: string, fullName: string) => void;
  onClose: () => void;
  EditorComponent?: React.ComponentType<FilerobotProps>;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 bg-black/60" role="dialog" aria-label="픽셀 편집">
      <div className="absolute inset-4 overflow-hidden rounded-lg bg-surface shadow-ambient">
        <EditorComponent
          source={source}
          tabsIds={TAB_IDS}
          defaultTabId="Adjust"
          onSave={(img) => {
            if (img?.imageBase64) onApply(img.imageBase64, img.fullName || fileName);
            onClose();
          }}
          onClose={() => onClose()}
        />
      </div>
    </div>
  );
}
