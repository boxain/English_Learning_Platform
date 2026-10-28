import pytest


@pytest.fixture(autouse=True)
def hide_openai_key(monkeypatch):
    """Unit tests must not call OpenAI, even if a key is present in the environment."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
