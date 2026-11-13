"""Restricted URL fetch. DNS addresses are checked and pinned by aiohttp's resolver.
Never use a regular browser navigation to scan an arbitrary URL.
"""
import asyncio
import ipaddress
import socket
from urllib.parse import urlparse, urljoin
import aiohttp
from aiohttp.abc import AbstractResolver

from .config import MAX_HTML_BYTES


class UnsafeURL(ValueError):
    pass


def validate_url(url: str) -> tuple[str, int]:
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise UnsafeURL("Only public HTTP(S) URLs are accepted")
    if parsed.username or parsed.password:
        raise UnsafeURL("URLs with credentials are not allowed")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise UnsafeURL("Only ports 80 and 443 are allowed")
    return parsed.hostname, port


def public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value.split("%", 1)[0]).is_global
    except ValueError:
        return False


class PublicOnlyResolver(AbstractResolver):
    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET):
        # getaddrinfo returns concrete addresses. aiohttp connects to THESE addresses,
        # avoiding the check-then-use DNS re-resolution bug.
        if public_ip(host):
            addresses = [(socket.AF_INET6 if ":" in host else socket.AF_INET, host)]
        else:
            if host.lower() in {"localhost", "localhost.localdomain"}:
                raise UnsafeURL("Local hostnames are blocked")
            infos = await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(
                host, port, type=socket.SOCK_STREAM
            ), timeout=3)
            addresses = list(dict.fromkeys((item[0], item[4][0]) for item in infos))
        if not addresses or any(not public_ip(ip) for _, ip in addresses):
            raise UnsafeURL("URL resolves to a private or non-public address")
        return [{"hostname": host, "host": ip, "port": port, "family": af,
                 "proto": socket.IPPROTO_TCP, "flags": socket.AI_NUMERICHOST}
                for af, ip in addresses]

    async def close(self):
        return None


async def fetch_public_html(url: str) -> str:
    headers = {"Accept": "text/html", "User-Agent": "AirlockHackathonDemo/0.1"}
    timeout = aiohttp.ClientTimeout(total=8, connect=4, sock_read=4)
    resolver = PublicOnlyResolver()
    connector = aiohttp.TCPConnector(resolver=resolver, use_dns_cache=False, limit=2)
    async with aiohttp.ClientSession(connector=connector, trust_env=False, timeout=timeout,
                                     cookie_jar=aiohttp.DummyCookieJar(), headers=headers) as session:
        for _ in range(4):
            validate_url(url)
            async with session.get(url, allow_redirects=False) as response:
                if 300 <= response.status < 400:
                    location = response.headers.get("Location")
                    if not location:
                        raise UnsafeURL("Redirect without Location")
                    url = urljoin(url, location)
                    continue
                if response.status >= 400:
                    raise UnsafeURL(f"Remote page returned HTTP {response.status}")
                if "text/html" not in response.headers.get("Content-Type", "").lower():
                    raise UnsafeURL("Only HTML responses can be scanned")
                blob = await response.content.read(MAX_HTML_BYTES + 1)
                if len(blob) > MAX_HTML_BYTES:
                    raise UnsafeURL("Remote HTML exceeds maximum size")
                return blob.decode(response.charset or "utf-8", errors="replace")
    raise UnsafeURL("Too many redirects")
