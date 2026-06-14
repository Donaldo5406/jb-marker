import os
from huggingface_hub import HfApi

RID = "Doss-8b-instruct/jb-marker"
api = HfApi(token=os.environ["HF_TOKEN"])
# Space는 이미 존재 — create_repo는 첫 생성용 안전망일 뿐이라, 실패(예: /api/repos/create
# 429 레이트리밋)해도 배포(업로드)를 막지 않는다. 비치명적으로 처리해 deploy 견고화.
try:
    api.create_repo(RID, repo_type="space", space_sdk="docker", exist_ok=True)
except Exception as e:  # noqa: BLE001 — 생성 실패는 무시(이미 존재 가정), 업로드로 진행
    print(f"create_repo skipped (space exists or rate-limited): {e}")
api.upload_file(path_or_fileobj="backend/SPACE_README.md", path_in_repo="README.md", repo_id=RID, repo_type="space")
api.upload_file(path_or_fileobj="backend/Dockerfile", path_in_repo="Dockerfile", repo_id=RID, repo_type="space")
api.upload_file(path_or_fileobj="backend/requirements-deploy.txt", path_in_repo="requirements-deploy.txt", repo_id=RID, repo_type="space")
api.upload_folder(folder_path="backend/app", path_in_repo="app", repo_id=RID, repo_type="space", ignore_patterns=["**/__pycache__/*", "*.pyc"])
# Dockerfile의 `COPY assets ./assets`가 의존 — 음악 베드/폰트 등 assets를 Space로 업로드해야
# 빌드 컨텍스트에 /assets가 존재한다(미업로드 시 "/assets: not found"로 BUILD_ERROR).
api.upload_folder(folder_path="backend/assets", path_in_repo="assets", repo_id=RID, repo_type="space", ignore_patterns=["**/__pycache__/*", "*.pyc"])
print("HF Space updated:", RID)
