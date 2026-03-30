import pytest

from config.settings import reset_settings_cache
from services.llm_client import LLMClient


def test_llm_client_requires_real_configuration(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ARK_API_KEY", "")
    monkeypatch.setenv("MODEL_NAME", "")
    reset_settings_cache()

    client = LLMClient()

    with pytest.raises(RuntimeError, match="真实模型尚未完成配置"):
        client.generate_report("test", [])


def test_llm_client_real_call_smoke(real_llm_required):
    reset_settings_cache()

    client = LLMClient()
    text = client.generate_report("请只回复“测试通过”。", [])

    assert text.strip()
