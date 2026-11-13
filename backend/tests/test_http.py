import pytest
import httpx
from airlock.main import app
from airlock.fetch import validate_url, public_ip, UnsafeURL

@pytest.mark.parametrize("bad",[
    "file:///etc/passwd","http://127.0.0.1/a","http://localhost:8080","http://user:pass@example.com/",
    "ftp://example.com/file","http://169.254.169.254/latest/meta-data/","http://example.com:8888/"
])
def test_url_rejection(bad):
    if bad.startswith("http://127.") or bad.startswith("http://169."):
        # Validate_URL checks format; resolver checks public IP. All must be non-global.
        assert not public_ip(bad.split('/')[2])
    else:
        if bad.startswith('http://localhost') and ':8080' in bad:
            with pytest.raises(UnsafeURL): validate_url(bad)
        elif bad.startswith('ftp') or bad.startswith('file') or '@' in bad or ':8888' in bad:
            with pytest.raises(UnsafeURL):validate_url(bad)

@pytest.mark.asyncio
async def test_health_and_scenarios():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://testserver") as client:
        response = await client.get('/api/health')
        assert response.json()['ok']
        resp = await client.get('/api/scenarios')
        assert len(resp.json()) >= 5

@pytest.mark.asyncio
async def test_scan_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://testserver") as client:
        resp = await client.post('/api/scan',json={'content':'<h1>Hello world</h1>'})
        assert resp.status_code == 200, resp.text
        assert resp.json()['verdict'] == 'allow'
        assert 'Hello world' in resp.json()['human_view']

@pytest.mark.asyncio
async def test_api_invalid_payload():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://testserver") as client:
        resp = await client.post('/api/scan',json={'url':'https://example.com','content':'<p>x</p>'})
        assert resp.status_code == 422

@pytest.mark.asyncio
async def test_resolver_blocks_local_network_address():
    from airlock.fetch import PublicOnlyResolver
    resolver = PublicOnlyResolver()
    with pytest.raises(UnsafeURL):
        await resolver.resolve('127.0.0.1', 80)
