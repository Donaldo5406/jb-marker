import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ArchFlowDiagram } from "@/components/architecture/ArchFlowDiagram";
import { AgentLoopSection } from "@/components/architecture/AgentLoopSection";
import { StackSection } from "@/components/architecture/StackSection";

describe("ArchFlowDiagram", () => {
  it("4개 존 라벨과 첫 단계 캡션이 렌더된다", () => {
    render(<ArchFlowDiagram />);
    expect(screen.getByText("사용자 화면 · VERCEL")).toBeInTheDocument();
    expect(screen.getByText("중앙 서버 · HUGGING FACE")).toBeInTheDocument();
    expect(screen.getByText("외부 AI 모델")).toBeInTheDocument();
    expect(screen.getByText("데이터 보관소 · SUPABASE")).toBeInTheDocument();
    // 초기 단계는 1번 "작업 시작"
    expect(screen.getByText("작업 시작")).toBeInTheDocument();
  });

  it("재생 콘솔 컨트롤이 있고, 다음 단계로 이동한다", () => {
    render(<ArchFlowDiagram />);
    expect(screen.getByLabelText("일시정지")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("다음 단계"));
    // "권한 확인"은 SVG 노드에도 있으므로 콘솔 제목(heading)으로 좁힌다
    expect(screen.getByRole("heading", { name: "권한 확인" })).toBeInTheDocument();
  });

  it("단계 도트 8개가 각 단계로 점프한다", () => {
    render(<ArchFlowDiagram />);
    fireEvent.click(screen.getByLabelText("단계 4: AI 작업 수행"));
    expect(screen.getByText("Gemini 이미지")).toBeInTheDocument();
  });
});

describe("AgentLoopSection", () => {
  it("에이전트 루프 6단계와 4종 하네스가 렌더된다", () => {
    render(<AgentLoopSection />);
    expect(screen.getByText("에이전트 루프")).toBeInTheDocument();
    expect(screen.getByText("① 상태 읽기")).toBeInTheDocument();
    expect(screen.getByText("⑥ 상태 기록")).toBeInTheDocument();
    expect(screen.getByText("기획 하네스")).toBeInTheDocument();
    expect(screen.getByText("이미지 하네스")).toBeInTheDocument();
    expect(screen.getByText("영상 하네스")).toBeInTheDocument();
    expect(screen.getByText("검토 하네스")).toBeInTheDocument();
  });

  it("사용자 게이트 3분기(승인·다시·건너뛰기)가 명시된다", () => {
    render(<AgentLoopSection />);
    expect(screen.getByText("사용자 게이트의 세 갈래")).toBeInTheDocument();
    expect(screen.getByText("승인")).toBeInTheDocument();
    expect(screen.getByText("다시")).toBeInTheDocument();
    expect(screen.getByText("건너뛰기")).toBeInTheDocument();
  });
});

describe("StackSection", () => {
  it("스택 표에 6개 구성 요소가 렌더된다", () => {
    render(<StackSection />);
    for (const area of ["사용자 화면", "에디터", "중앙 서버", "AI 모델", "데이터 보관", "배포·운영"]) {
      expect(screen.getByText(area)).toBeInTheDocument();
    }
    expect(screen.getByText("Supabase")).toBeInTheDocument();
  });
});
