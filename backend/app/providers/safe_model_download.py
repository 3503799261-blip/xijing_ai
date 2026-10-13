"""Bounded, unauthenticated model download with DNS-pinned HTTPS connections.

Only exact manually verified hosts are accepted. The original URL remains the
HTTP/TLS origin; only the TCP destination is replaced with a verified numeric
IP. Each redirect starts a new client/pool and repeats all target checks. This
module never creates a model, retries a download, or stores/logs signed URLs.
"""
import asyncio
import ipaddress
import logging
import re
import socket
from contextvars import ContextVar
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx

from ..errors import ServiceError

MAX_BYTES = 50 * 1024 * 1024
TOTAL_TIMEOUT_SECONDS = 90
MAX_REDIRECTS = 2
REDIRECT_STATUSES = frozenset((301, 302, 303, 307, 308))
CONTENT_TYPES = frozenset((
    'application/octet-stream', 'binary/octet-stream',
    'model/gltf-binary', 'application/gltf-binary',
    'model/gltf+json', 'application/gltf+json',
))
HOST_PATTERN = re.compile(r'(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z')
_DOWNLOAD_LOG_CONTEXT = ContextVar('safe_model_download_logging', default=False)


class _DownloadLogFilter(logging.Filter):
    """Suppress library URL/response-header logging only in this async task."""
    def filter(self, record):
        return not _DOWNLOAD_LOG_CONTEXT.get()


for _logger_name in ('httpx', 'httpcore.connection', 'httpcore.http11', 'httpcore.http2'):
    logging.getLogger(_logger_name).addFilter(_DownloadLogFilter())


def _blocked(message='模型资源目标未通过HTTPS域名及公开地址校验。'):
    return ServiceError('MODEL_DOWNLOAD_BLOCKED', message, 403)


def _checked_host(url, allowed_hosts):
    """Reject ambiguous authority syntax before an HTTP library normalizes it."""
    if (not isinstance(url, str) or not url or len(url) > 16384
            or '\\' in url or any(ord(char) < 33 or ord(char) == 127 for char in url)):
        raise _blocked()
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if (parsed.scheme != 'https' or not host or parsed.username is not None
                or parsed.password is not None or parsed.port not in (None, 443)
                or parsed.fragment or not host.isascii() or not HOST_PATTERN.fullmatch(host)
                or host not in allowed_hosts):
            raise _blocked()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise _blocked()
    except (ValueError, TypeError):
        raise _blocked() from None
    return host


def _public_ip(value):
    try:
        address = ipaddress.ip_address(value)
        # IPv4-mapped IPv6 must also be judged by its embedded address. Scoped,
        # translated and tunnelling forms are unnecessary for this CDN policy.
        if (not address.is_global or getattr(address, 'scope_id', None)
                or getattr(address, 'ipv4_mapped', None) is not None
                or getattr(address, 'sixtofour', None) is not None
                or getattr(address, 'teredo', None) is not None):
            raise _blocked('模型资源DNS包含非公开或不允许的地址。')
        return str(address)
    except (ValueError, TypeError):
        raise _blocked('模型资源DNS地址无效。') from None


async def _resolve_public_ips(host):
    try:
        records = await asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM)
        addresses = tuple(dict.fromkeys(_public_ip(record[4][0]) for record in records))
    except ServiceError:
        raise
    except (OSError, IndexError, TypeError):
        raise _blocked('模型资源DNS解析失败。') from None
    if not addresses:
        raise _blocked('模型资源DNS没有有效公开地址。')
    return addresses


class _PinnedBackend(httpcore.AsyncNetworkBackend):
    """No second DNS lookup: only the checked numeric address reaches TCP."""
    def __init__(self, host, addresses, backend=None):
        self.host = host
        self.addresses = tuple(_public_ip(value) for value in addresses)
        if not self.addresses:
            raise _blocked()
        self.backend = backend if backend is not None else httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        if host != self.host or port != 443 or local_address is not None:
            raise _blocked()
        # No retry or alternate resolution. Failure is returned to the caller.
        address = self.addresses[0]
        stream = await self.backend.connect_tcp(
            address, port, timeout=timeout, local_address=None, socket_options=socket_options)
        peer = stream.get_extra_info('server_addr')
        try:
            if not peer or _public_ip(peer[0]) != address or peer[1] != 443:
                raise _blocked('模型资源连接目标与核验地址不一致。')
        except (IndexError, TypeError):
            await stream.aclose()
            raise _blocked('模型资源连接目标无法核验。') from None
        except ServiceError:
            await stream.aclose()
            raise
        return stream

    async def connect_unix_socket(self, *args, **kwargs):
        raise _blocked()

    async def sleep(self, seconds):
        await self.backend.sleep(seconds)


class _CoreResponseStream(httpx.AsyncByteStream):
    def __init__(self, stream):
        self.stream = stream

    async def __aiter__(self):
        async for part in self.stream:
            yield part

    async def aclose(self):
        await self.stream.aclose()


class _PinnedTransport(httpx.AsyncBaseTransport):
    """Public httpcore pool API; default verified TLS, original Host and SNI."""
    def __init__(self, host, addresses, backend=None):
        self.host = host
        self.pool = httpcore.AsyncConnectionPool(
            ssl_context=httpcore.default_ssl_context(),
            network_backend=_PinnedBackend(host, addresses, backend),
            max_connections=1, max_keepalive_connections=0,
            http1=True, http2=False, retries=0)

    async def handle_async_request(self, request):
        if (request.method != 'GET' or request.url.scheme != 'https'
                or request.url.host != self.host or request.url.port not in (None, 443)
                or 'authorization' in request.headers or 'cookie' in request.headers
                or request.headers.get('host') not in (self.host, self.host + ':443')):
            raise _blocked()
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(scheme=request.url.raw_scheme, host=request.url.raw_host,
                             port=request.url.port, target=request.url.raw_path),
            headers=request.headers.raw, content=request.stream,
            # Do not accept a caller override of TLS SNI or proxy extensions.
            extensions={'timeout': request.extensions.get('timeout', {})})
        response = await self.pool.handle_async_request(core_request)
        return httpx.Response(response.status, headers=response.headers,
                              stream=_CoreResponseStream(response.stream), extensions=response.extensions)

    async def aclose(self):
        await self.pool.aclose()


async def _secure_download(url, allowed_hosts, transport=None, *, on_metadata=None):
    """Return bounded resource bytes or a sanitized ServiceError; never URL data.

    MockTransport is the only injectable transport, for explicit offline tests.
    Production always uses pinned DNS and retains certificate verification.
    File format/GLB semantic validation remains the asset layer's responsibility.
    """
    if transport is not None and not isinstance(transport, httpx.MockTransport):
        raise _blocked('模型下载不能使用未经核验的替代网络传输。')
    if not isinstance(allowed_hosts, (list, tuple, set, frozenset)):
        raise _blocked()
    if any(not isinstance(host, str) or not HOST_PATTERN.fullmatch(host) for host in allowed_hosts):
        raise _blocked()
    allowed_hosts = frozenset(allowed_hosts)
    visited = set()
    current_url = url
    try:
        async with asyncio.timeout(TOTAL_TIMEOUT_SECONDS):
            for hop in range(MAX_REDIRECTS + 1):
                host = _checked_host(current_url, allowed_hosts)
                if current_url in visited:
                    raise _blocked('模型资源跳转循环，下载已停止。')
                visited.add(current_url)
                active_transport = transport
                if active_transport is None:
                    active_transport = _PinnedTransport(host, await _resolve_public_ips(host))
                # Call the transport directly: AsyncClient's INFO logger prints
                # full URLs, including sensitive object-storage signatures. No
                # cookie jar, environment proxy or origin header can carry over.
                response = None
                metadata = None
                try:
                    request = httpx.Request('GET', current_url,
                        headers={'Accept-Encoding': 'identity'},
                        extensions={'timeout': {'connect': 10, 'read': 20, 'write': 20, 'pool': 10}})
                    response = await active_transport.handle_async_request(request)
                    content_type = response.headers.get('content-type', '').split(';', 1)[0].lower().strip()
                    metadata = {'host': host, 'httpStatus': response.status_code,
                                'contentType': content_type if content_type in CONTENT_TYPES else ('missing' if not content_type else 'unsupported'),
                                'size': 0, 'redirectCount': hop, 'dnsPinned': transport is None}
                    if response is not None:
                        if response.status_code in REDIRECT_STATUSES:
                            location = response.headers.get('location')
                            if not location or hop >= MAX_REDIRECTS:
                                raise _blocked('模型资源跳转无效或超过2次限制。')
                            current_url = urljoin(current_url, location)
                            # Validate before a next request, including relative
                            # redirects and newly introduced query credentials.
                            _checked_host(current_url, allowed_hosts)
                            continue
                        if response.status_code != 200:
                            raise ServiceError('MODEL_DOWNLOAD_FAILED', '模型资源响应失败，未自动重试。', 502)
                        encoding = response.headers.get('content-encoding', 'identity').lower().strip()
                        if encoding != 'identity':
                            raise _blocked('模型资源采用未允许的压缩传输。')
                        if content_type and content_type not in CONTENT_TYPES:
                            raise ServiceError('MODEL_DOWNLOAD_INVALID_CONTENT', '模型资源媒体类型不支持。', 502)
                        expected_length = response.headers.get('content-length')
                        if expected_length is not None:
                            if not expected_length.isascii() or not expected_length.isdecimal():
                                raise ServiceError('MODEL_DOWNLOAD_INVALID_CONTENT', '模型资源长度字段无效。', 502)
                            expected_length = int(expected_length)
                            if expected_length > MAX_BYTES:
                                raise ServiceError('MODEL_DOWNLOAD_TOO_LARGE', '模型超过50MB，停止下载。', 413)
                        data = bytearray()
                        async for block in response.stream:
                            if len(data) + len(block) > MAX_BYTES:
                                raise ServiceError('MODEL_DOWNLOAD_TOO_LARGE', '模型超过50MB，停止下载。', 413)
                            data.extend(block)
                            metadata['size'] = len(data)
                        if not data or (expected_length is not None and expected_length != len(data)):
                            raise ServiceError('MODEL_DOWNLOAD_INVALID_CONTENT', '模型资源为空或长度不完整。', 502)
                        return bytes(data)
                finally:
                    if response is not None:
                        await response.aclose()
                    await active_transport.aclose()
                    if on_metadata is not None and metadata is not None:
                        on_metadata(dict(metadata))
    except ServiceError:
        raise
    except (TimeoutError, httpx.TimeoutException, httpcore.TimeoutException):
        raise ServiceError('MODEL_DOWNLOAD_TIMEOUT', '模型下载超时，未自动重试。', 504) from None
    except (httpx.HTTPError, httpcore.NetworkError, httpcore.ProtocolError, OSError, ValueError):
        raise ServiceError('MODEL_DOWNLOAD_FAILED', '模型下载网络或协议异常，未自动重试。', 502) from None
    raise _blocked()


async def secure_download(url, allowed_hosts, transport=None, *, on_metadata=None):
    """Scoped logging guard, without changing global logger levels/handlers."""
    token = _DOWNLOAD_LOG_CONTEXT.set(True)
    try:
        return await _secure_download(url, allowed_hosts, transport, on_metadata=on_metadata)
    finally:
        _DOWNLOAD_LOG_CONTEXT.reset(token)
