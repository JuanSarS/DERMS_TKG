"""Rutas de proyecto y credenciales exclusivamente servidor."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    host: str = os.getenv("DERMS_BIND_HOST", "127.0.0.1")
    port: int = int(os.getenv("DERMS_PORT", "8088"))
    app_token: str = os.getenv("DERMS_APP_TOKEN", "")

    def remote(self) -> dict:
        local = self.root / "secrets/opendss.local.json"
        data = (
            read_json(local)
            if local.exists()
            else read_json(self.root / "secrets/opendss.example.json")
        )
        if os.getenv("DERMS_OPENDSS_URL"):
            data["base_url"] = os.environ["DERMS_OPENDSS_URL"]
        if os.getenv("DERMS_OPENDSS_USERNAME"):
            data["username"] = os.environ["DERMS_OPENDSS_USERNAME"]
        if os.getenv("DERMS_OPENDSS_PASSWORD"):
            data["password"] = os.environ["DERMS_OPENDSS_PASSWORD"]
        if not data["base_url"].startswith("https://") and not data["base_url"].startswith(
            "http://127.0.0.1"
        ):
            raise ValueError("Solo HTTPS remoto o localhost HTTP")
        return data

    def ollama(self) -> dict:
        local = self.root / "secrets/ollama.local.json"
        return (
            read_json(local)
            if local.exists()
            else read_json(self.root / "secrets/ollama.example.json")
        )


settings = Settings()
