import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestProxyEndpoint:
    def test_ssrf_localhost_blocked(self, client):
        res = client.post("/v1/proxy", json={"url": "http://localhost:9200/secret"})
        assert res.status_code == 403
        assert "SSRF" in res.json()["detail"]

    def test_ssrf_127_blocked(self, client):
        res = client.post("/v1/proxy", json={"url": "http://127.0.0.1:9200/secret"})
        assert res.status_code == 403

    def test_ssrf_gcp_metadata_blocked(self, client):
        res = client.post("/v1/proxy", json={"url": "http://metadata.google.internal/computeMetadata/v1/"})
        assert res.status_code == 403

    def test_valid_proxy_request(self, client):
        # This hits a real public endpoint - skip in CI if needed
        res = client.post("/v1/proxy", json={
            "url": "https://httpbin.org/get",
            "method": "GET"
        })
        # Should succeed or fail gracefully (network dependent)
        assert res.status_code in (200, 500)
