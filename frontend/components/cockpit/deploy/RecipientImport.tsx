"use client";

import * as React from "react";
import { Upload, FileSpreadsheet, Check, Download, X, AlertTriangle } from "lucide-react";

export type Recipient = Record<string, string>;

/** 따옴표로 감싼 콤마를 보존하는 최소 CSV 행 파서. */
function splitRow(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  let q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (q && line[i + 1] === '"') { cur += '"'; i++; } else q = !q;
    } else if (ch === "," && !q) {
      out.push(cur); cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out;
}

/** 헤더 행 + 데이터 행 → 객체 배열. 헤더는 소문자 정규화. */
export function parseCsv(text: string): Recipient[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
  if (lines.length < 2) return [];
  const headers = splitRow(lines[0]).map((h) => h.trim().toLowerCase());
  return lines.slice(1).map((line) => {
    const cells = splitRow(line);
    const row: Recipient = {};
    headers.forEach((h, i) => { row[h] = (cells[i] ?? "").trim(); });
    return row;
  });
}

const SAMPLE = `id,lang,marketing_consent,opt_out,night_consent
user001@example.com,ko,true,false,false
user002@example.com,en,true,false,true
user003@example.com,vi,false,false,false
user004@example.com,zh,true,true,false`;

const PREVIEW_COLS = ["id", "lang", "marketing_consent", "opt_out", "night_consent"];

/** 발송 명단(CSV) 업로드·미리보기. 적용 시 onApply로 파싱된 수신자 배열을 올린다.
 *  컬럼: id/email · lang · marketing_consent(=consent) · opt_out · night_consent · collected_days_ago.
 *  누락 컬럼은 백엔드(normalize_recipients)가 안전 기본값으로 채운다(동의된 명단 가정). */
export function RecipientImport({ onApply, appliedCount }: {
  onApply: (recipients: Recipient[]) => void;
  appliedCount: number | null;
}) {
  const [rows, setRows] = React.useState<Recipient[]>([]);
  const [fileName, setFileName] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [dragOver, setDragOver] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = async (file: File | undefined | null) => {
    if (!file) return;
    setError(null);
    try {
      const parsed = parseCsv(await file.text());
      if (parsed.length === 0) {
        setError("행을 찾지 못했습니다. 헤더 1줄 + 데이터 1줄 이상이 필요합니다.");
        setRows([]); setFileName(null);
        return;
      }
      setRows(parsed);
      setFileName(file.name);
    } catch {
      setError("파일을 읽지 못했습니다. UTF-8 CSV인지 확인하세요.");
    }
  };

  const downloadSample = () => {
    const blob = new Blob(["﻿" + SAMPLE], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "recipients_sample.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const clear = () => { setRows([]); setFileName(null); setError(null); if (inputRef.current) inputRef.current.value = ""; };

  return (
    <div className="space-y-3" data-testid="recipient-import">
      <input
        ref={inputRef}
        type="file"
        accept=".csv,text/csv,text/plain"
        className="hidden"
        data-testid="recipient-file-input"
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />

      {/* 드롭존 / 업로드 */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); void handleFile(e.dataTransfer.files?.[0]); }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
        className={
          "flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed px-4 py-6 text-center transition-colors " +
          (dragOver ? "border-primary bg-primary/5" : "border-outline-variant bg-surface-container-low hover:bg-surface-container")
        }
      >
        <Upload className="h-5 w-5 text-on-surface-variant" aria-hidden />
        <p className="text-body-sm text-on-surface">CSV 발송 명단을 끌어다 놓거나 클릭해 업로드</p>
        <p className="text-caption text-on-surface-variant">컬럼: id/email · lang · marketing_consent · opt_out · night_consent</p>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={downloadSample}
          className="inline-flex items-center gap-1.5 text-caption font-medium text-primary hover:underline"
        >
          <Download className="h-3.5 w-3.5" aria-hidden />
          샘플 CSV 받기
        </button>
        {appliedCount !== null && (
          <span className="inline-flex items-center gap-1 text-caption text-severity-ok-fg">
            <Check className="h-3.5 w-3.5" aria-hidden />
            명단 {appliedCount}명 적용됨
          </span>
        )}
      </div>

      {error && (
        <p className="inline-flex items-center gap-1.5 text-caption text-severity-critical-fg" role="alert">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden />
          {error}
        </p>
      )}

      {rows.length > 0 && (
        <div className="space-y-2 rounded-xl border border-outline-variant bg-surface-container-low p-3 animate-fade-in-up">
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 text-body-sm font-medium text-on-surface">
              <FileSpreadsheet className="h-4 w-4 text-on-surface-variant" aria-hidden />
              {fileName} · <b className="tabular-nums">{rows.length}</b>명
            </span>
            <button type="button" onClick={clear} aria-label="명단 비우기"
              className="inline-flex h-6 w-6 items-center justify-center rounded-full text-on-surface-variant hover:bg-surface-container-high">
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-caption">
              <thead>
                <tr className="text-left text-on-surface-variant">
                  {PREVIEW_COLS.map((col) => <th key={col} className="px-2 py-1 font-medium">{col}</th>)}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 5).map((r, i) => (
                  <tr key={i} className="border-t border-outline-variant/50 text-on-surface">
                    {PREVIEW_COLS.map((col) => <td key={col} className="px-2 py-1">{r[col] ?? r[col === "marketing_consent" ? "consent" : col] ?? "—"}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 5 && <p className="px-2 pt-1 text-caption text-on-surface-variant">… 외 {rows.length - 5}명</p>}
          </div>
          <button
            type="button"
            data-testid="recipient-apply-btn"
            onClick={() => onApply(rows)}
            className="rounded-lg bg-primary px-3 py-1.5 text-caption font-medium text-on-primary hover:bg-primary-container"
          >
            이 명단으로 적법성 검사
          </button>
        </div>
      )}
    </div>
  );
}
