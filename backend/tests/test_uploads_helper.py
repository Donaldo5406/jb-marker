"""gateway/uploads — 업로드 소스 헬퍼(캡·정렬·타입 필터·no-op 계약)."""
from app.gateway.uploads import (PER_FILE_CAP, TOTAL_CAP, list_upload_images,
                                 list_upload_texts, uploads_block)
from app.vfs.factory import make_local_store


def _store(tmp_path):
    s = make_local_store(tmp_path)
    s.create_run("r1")
    return s


def test_no_uploads_returns_empty(tmp_path):
    s = _store(tmp_path)
    assert list_upload_texts(s, "r1", "brainstorming") == []
    assert list_upload_images(s, "r1", "review") == []
    assert uploads_block(s, "r1", "design") == ""   # 호출부 no-op 보장(mock 계약)


def test_texts_sorted_truncated_and_images_excluded(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/brainstorming/uploads/b.md", "가" * (PER_FILE_CAP + 100),
          source="user", mime="text/markdown")
    s.put("/r1/brainstorming/uploads/a.txt", "짧은 자료", source="user", mime="text/plain")
    s.put("/r1/brainstorming/uploads/img.png", b"\x89PNG", source="frontend", mime="image/png")
    texts = list_upload_texts(s, "r1", "brainstorming")
    assert [t[0] for t in texts] == ["a.txt", "b.md"]
    assert texts[1][1].endswith("…(잘림)")


def test_total_cap_drops_overflow(tmp_path):
    s = _store(tmp_path)
    for i in range(5):
        s.put(f"/r1/design/uploads/f{i}.md", "나" * PER_FILE_CAP, source="user",
              mime="text/markdown")
    texts = list_upload_texts(s, "r1", "design")
    assert len(texts) == 3                                   # 4000*3 = 12000 캡
    assert sum(len(t[1]) for t in texts) <= TOTAL_CAP


def test_images_listed_with_full_path(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/review/uploads/poster.png", b"\x89PNG\x00", source="frontend", mime="image/png")
    s.put("/r1/review/uploads/photo.jpg", b"\xff\xd8\xff", source="frontend", mime="image/jpeg")
    s.put("/r1/review/uploads/note.md", "메모", source="user", mime="text/markdown")
    assert list_upload_images(s, "r1", "review") == [
        "/r1/review/uploads/photo.jpg", "/r1/review/uploads/poster.png"]


def test_uploads_block_format(tmp_path):
    s = _store(tmp_path)
    s.put("/r1/design/uploads/brand.md", "브랜드 가이드 본문", source="user", mime="text/markdown")
    block = uploads_block(s, "r1", "design")
    assert "[사용자 제공 자료]" in block
    assert "brand.md" in block and "브랜드 가이드 본문" in block
