"""Pruebas nuevas: modelo ausente no debe aparentar estar disponible."""

import httpx
import pytest

from backend.app.integrations.ollama_http import Ollama


@pytest.mark.asyncio
async def test_ollama_model_missing_even_if_http_responds():
    def responder(request):
        assert request.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "mistral:latest"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
        status = await Ollama(
            {"enabled": True, "model": "llama3.2", "base_url": "http://127.0.0.1:11434"}, client
        ).status()
    assert status["status"] == "MODEL_MISSING"
    assert "ollama pull llama3.2" in status["hint"]


@pytest.mark.asyncio
async def test_ollama_generates_when_model_installed():
    def responder(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})
        if request.url.path == "/api/chat":
            assert b"NO" in request.content  # prompt recibe límites de evidencia
            return httpx.Response(
                200, json={"message": {"content": "Sin despacho BESS verificado."}}
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(responder)) as client:
        result = await Ollama(
            {"enabled": True, "model": "llama3.2", "base_url": "http://127.0.0.1:11434"}, client
        ).explain({"run_id": "case1", "note": "NO VERIFICADO"}, "explica")
    assert result["status"] == "GENERATED_NOT_VALIDATED"
    assert "BESS" in result["answer"]


@pytest.mark.asyncio
async def test_ollama_rejects_remote_address():
    status = await Ollama(
        {"enabled": True, "model": "x", "base_url": "http://example.org:11434"}
    ).status()
    assert status["status"] == "BLOCKED"
