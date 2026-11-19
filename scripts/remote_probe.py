"""Prueba remota NO mutante: /health, autenticación y catálogo."""

import asyncio

from backend.app.integrations.opendss_http import RemoteOpenDSS, UpstreamError


async def main():
    remote = RemoteOpenDSS()
    try:
        status = await remote.health()
        print("REMOTE_HEALTH", status)
        if status["state"] != "HEALTHY":
            print("REMOTE_MODE: OFFLINE, sin llamadas que creen o modifiquen sesiones")
            return
        try:
            models = await remote.models()
            print("MODELS", models)
            print("AUTH_SUCCESS")
        except UpstreamError as error:
            print("AUTH_OR_MODELS_ERROR", error.code, str(error))
    finally:
        await remote.aclose()


if __name__ == "__main__":
    asyncio.run(main())
