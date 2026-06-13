import pytest

from app.vfs.paths import parse_path, validate_path


def test_parse_valid_path():
    run_id, studio, rest = parse_path("/run123/design/rough/layout.json")
    assert run_id == "run123"
    assert studio == "design"
    assert rest == "rough/layout.json"


def test_validate_rejects_missing_studio():
    with pytest.raises(ValueError):
        validate_path("/run123/onlyrun")


def test_validate_rejects_unknown_studio():
    with pytest.raises(ValueError):
        validate_path("/run123/marketing/x.md")


def test_validate_accepts_known_studio():
    validate_path("/run123/brainstorming/spec.md")  # no raise


def test_validate_accepts_video_studio():
    validate_path("/run123/video/storyboard/storyboard.spec.json")  # no raise
