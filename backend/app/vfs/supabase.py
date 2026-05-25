"""SupabaseVfsStore — 인터페이스 자리(후속 연결). 로컬-우선 결정으로 미구현."""
from __future__ import annotations

from .base import VfsStore


class SupabaseVfsStore(VfsStore):
    def _todo(self, *_a, **_k):
        raise NotImplementedError("SupabaseVfsStore는 후속 마일스톤에서 구현 (로컬-우선)")

    create_run = get_manifest = patch_manifest = set_step_status = _todo
    put = get = read_meta = list = update = delete = list_runs = _todo
