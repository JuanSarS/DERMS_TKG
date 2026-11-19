import pytest

from backend.app.integrations.opendss_http import RemoteOpenDSS, UpstreamError


class OfflineClient:
    def __init__(self):
        self.post_count = 0

    async def get(self, *a, **k):
        raise __import__("httpx").ConnectError("offline")

    async def request(self, *a, **k):
        self.post_count += 1


@pytest.mark.asyncio
async def test_offline_blocks_posts():
    fake = OfflineClient()
    remote = RemoteOpenDSS(
        {"base_url": "https://mock.example", "username": "u", "password": "p"}, client=fake
    )
    assert (await remote.health())["state"] == "OFFLINE"
    with pytest.raises(UpstreamError):
        await remote.create("ieee13")
    assert fake.post_count == 0
