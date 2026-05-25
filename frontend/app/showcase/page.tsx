import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { Input } from "@/components/ui/Input";
import { StatusDot } from "@/components/ui/StatusDot";

export default function Showcase() {
  return (
    <main className="mx-auto max-w-container space-y-8 p-margin-x">
      <h1 className="text-h2">디자인 시스템 쇼케이스</h1>
      <div className="flex gap-4">
        <Button>체험해보기</Button>
        <Button variant="secondary">취소</Button>
      </div>
      <Card>
        <h3 className="text-h3">Card</h3>
        <p className="text-body-lg text-on-surface-variant">floated gallery 표면</p>
        <div className="mt-4 flex items-center gap-2">
          <StatusDot status="active" /> <span className="text-caption">ACTIVE</span>
        </div>
      </Card>
      <GlassPanel className="p-6">
        <Input placeholder="검색" />
      </GlassPanel>
    </main>
  );
}
