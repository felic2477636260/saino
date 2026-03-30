import os
import shutil
import uuid
from pathlib import Path

import pytest

from config.settings import get_settings, reset_settings_cache
from services.db import Database


@pytest.fixture()
def work_tmp_dir() -> Path:
    path = Path.cwd() / "test_artifacts" / str(uuid.uuid4())
    path.mkdir(parents=True, exist_ok=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def temp_db(work_tmp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Database:
    monkeypatch.setenv("DATABASE_PATH", str(work_tmp_dir / "test.db"))
    reset_settings_cache()
    database = Database()
    yield database
    reset_settings_cache()


def require_real_llm_configuration() -> None:
    reset_settings_cache()
    settings = get_settings()
    if os.getenv("RUN_REAL_LLM_TESTS") != "1":
        pytest.skip("Set RUN_REAL_LLM_TESTS=1 to execute real API integration tests.")
    if not settings.ark_api_key.strip() or not settings.model_name.strip():
        pytest.skip("Requires ARK_API_KEY and MODEL_NAME for real API calls.")


@pytest.fixture()
def real_llm_required() -> None:
    require_real_llm_configuration()
