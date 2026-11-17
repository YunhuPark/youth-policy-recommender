"""Keep the legacy suite offline and independent of workstation secrets."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
os.environ["LOG_FORMAT"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("MONGODB_URI", None)

# Historical tests contain localhost smoke calls; exercise the offline suite
# without contacting a workstation service or any provider.
import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import requests
    def deny(*args, **kwargs):
        raise RuntimeError("Network disabled in offline tests")
    monkeypatch.setattr(requests.sessions.Session, "request", deny)
