"""OFFLINE SSRF/rebinding/TLS/logging checks; no provider/API/socket calls."""
import asyncio
import ipaddress
import json
import logging
import socket
import ssl

import httpcore
import httpx
import pytest

from backend.app.errors import ServiceError
from backend.app.providers import safe_model_download as safe

HOST = 'verified-download.example.invalid'
SECOND_HOST = 'verified-cdn.example.invalid'
BODY = b'glTF-offline-byte-fixture'


def run(url, handler, *, hosts=None, metadata=None):
    return asyncio.run(safe.secure_download(
        url, hosts or [HOST], httpx.MockTransport(handler),
        on_metadata=metadata.append if metadata is not None else None))


def test_signed_url_not_logged_at_debug_or_forwarded_as_authorization(caplog):
    caplog.set_level(logging.DEBUG)
    requests, metadata = [], []
    def handler(request):
        requests.append(request)
        # Simulates the actual low-level DEBUG response-header event.
        logging.getLogger('httpcore.http11').debug('Location=%s', 'https://' + HOST + '/result.glb?secret=SIGNED_SECRET')
        logging.getLogger('httpx').info('GET %s', request.url)
        if len(requests) == 1:
            return httpx.Response(302, headers={'location': '/result.glb?secret=SIGNED_SECRET', 'set-cookie': 'session=private'})
        return httpx.Response(200, content=BODY, headers={'content-type': 'model/gltf-binary'})
    result = run('https://' + HOST + '/original.glb?signature=INITIAL_SECRET', handler, metadata=metadata)
    assert result == BODY
    assert len(requests) == 2
    assert all('authorization' not in request.headers and 'cookie' not in request.headers for request in requests)
    assert 'INITIAL_SECRET' not in str(requests[1].url)
    assert requests[1].url.params['secret'] == 'SIGNED_SECRET'
    assert len(metadata) == 2 and metadata[1]['size'] == len(BODY)
    assert metadata[1]['dnsPinned'] is False
    assert all(set(item) == {'host', 'httpStatus', 'contentType', 'size', 'redirectCount', 'dnsPinned'} for item in metadata)
    public = caplog.text + json.dumps(metadata)
    assert 'SIGNED_SECRET' not in public and 'INITIAL_SECRET' not in public
    # The filter scope is reset after completion; other requests keep logging.
    logging.getLogger('httpcore.http11').debug('unrelated-request-is-visible')
    assert 'unrelated-request-is-visible' in caplog.text


@pytest.mark.parametrize('url', [
    'http://' + HOST + '/model.glb', 'https://127.0.0.1/model.glb',
    'https://' + HOST + '.evil.invalid/model.glb', 'https://name:password@' + HOST + '/model.glb',
    'https://@' + HOST + '/model.glb', 'https://' + HOST + ':444/model.glb',
    'https://' + HOST + '/model.glb#private', 'https://' + HOST + './model.glb',
    'https://' + HOST + '/\\evil', 'https://' + HOST + '/model\n.glb',
    'https://' + HOST + ':not-a-port/model.glb', None,
])
def test_invalid_target_is_blocked_before_http(url):
    requests = []
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        run(url, lambda request: requests.append(request))
    assert requests == []


@pytest.mark.parametrize('location', [
    'https://evil.example.invalid/result.glb?secret=bad', 'http://' + HOST + '/model.glb',
    'https://user:password@' + HOST + '/model.glb', 'https://127.0.0.1/model.glb',
    'https://' + HOST + ':444/model.glb',
])
def test_redirect_target_checked_before_second_http(location):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={'location': location})
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        run('https://' + HOST + '/first.glb', handler)
    assert len(requests) == 1


def test_exact_second_allowlisted_host_can_redirect_without_origin_cookie_or_token():
    requests = []
    def handler(request):
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(302, headers={'location': 'https://' + SECOND_HOST + '/final.glb', 'set-cookie': 'private=secret'})
        return httpx.Response(200, content=BODY)
    assert run('https://' + HOST + '/first.glb?original=PRIVATE', handler, hosts=[HOST, SECOND_HOST]) == BODY
    assert requests[1].url.host == SECOND_HOST
    assert 'PRIVATE' not in str(requests[1].url)
    assert 'cookie' not in requests[1].headers and 'authorization' not in requests[1].headers


def test_two_redirects_allowed_but_third_redirect_rejected():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={'location': '/hop' + str(len(requests))})
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        run('https://' + HOST + '/first', handler)
    assert len(requests) == 3


def test_relative_redirect_loop_is_rejected():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={'location': '/first'})
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        run('https://' + HOST + '/first', handler)
    assert len(requests) == 1


@pytest.mark.parametrize('address', ['127.0.0.1', '10.0.0.1', '169.254.169.254', '192.168.1.1', '100.64.0.1', '::1', 'fc00::1', 'fe80::1', '::ffff:8.8.8.8'])
def test_mixed_dns_with_nonpublic_ip_fails_closed(address, monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 443)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, '', (address, 443))])
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(safe._resolve_public_ips(HOST))


class FakeStream(httpcore.AsyncNetworkStream):
    def __init__(self, peer='8.8.8.8'):
        self.peer, self.sent, self.tls, self.closed = peer, [], [], False
        self.response = b'HTTP/1.1 200 OK\r\nContent-Length: 4\r\nContent-Type: model/gltf-binary\r\n\r\nglTF'

    async def read(self, max_bytes, timeout=None):
        value, self.response = self.response, b''
        return value

    async def write(self, buffer, timeout=None):
        self.sent.append(buffer)

    async def aclose(self):
        self.closed = True

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        self.tls.append((ssl_context.check_hostname, ssl_context.verify_mode, server_hostname))
        return self

    def get_extra_info(self, info):
        return (self.peer, 443) if info == 'server_addr' else None


class FakeBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, peer='8.8.8.8'):
        self.calls = []
        self.stream = FakeStream(peer)

    async def connect_tcp(self, host, port, **kwargs):
        # A hostname here would silently introduce a second DNS resolution.
        assert str(ipaddress.ip_address(host)) == host
        self.calls.append((host, port))
        return self.stream

    async def sleep(self, seconds):
        raise AssertionError('Connection retry is not allowed')


def test_pinned_tcp_has_no_second_dns_resolution_and_keeps_host_sni_and_cert_validation(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    dns, metadata = [], []
    def rebinding_dns(host, port, **kwargs):
        dns.append((host, port))
        # Any subsequent resolution would become private: our transport must
        # only use the first verified numeric address, never this second result.
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8' if len(dns) == 1 else '127.0.0.1', 443))]
    monkeypatch.setattr(socket, 'getaddrinfo', rebinding_dns)
    backend = FakeBackend()
    original_transport = safe._PinnedTransport
    monkeypatch.setattr(safe, '_PinnedTransport', lambda host, addresses: original_transport(host, addresses, backend))
    assert asyncio.run(safe.secure_download('https://' + HOST + '/model.glb?signature=HIDDEN', [HOST], on_metadata=metadata.append)) == b'glTF'
    assert dns == [(HOST, 443)]
    assert backend.calls == [('8.8.8.8', 443)]
    assert backend.stream.tls == [(True, ssl.CERT_REQUIRED, HOST)]
    wire = b''.join(backend.stream.sent)
    assert ('Host: ' + HOST + '\r\n').encode() in wire
    assert b'/model.glb?signature=HIDDEN' in wire
    assert b'Authorization:' not in wire
    assert metadata[0]['dnsPinned'] is True
    assert 'HIDDEN' not in caplog.text and HOST not in caplog.text


def test_mismatched_peer_is_rejected_and_closed():
    backend = FakeBackend(peer='1.1.1.1')
    pinned = safe._PinnedBackend(HOST, ['8.8.8.8'], backend)
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(pinned.connect_tcp(HOST, 443))
    assert backend.stream.closed is True


def test_each_real_redirect_re_resolves_and_checks_dns(monkeypatch):
    dns, requests = [], []
    def resolver(host, port, **kwargs):
        dns.append(host)
        ip = '8.8.8.8' if host == HOST else '127.0.0.1'
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]
    monkeypatch.setattr(socket, 'getaddrinfo', resolver)
    class OfflineCheckedTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            requests.append(request)
            return httpx.Response(302, headers={'location': 'https://' + SECOND_HOST + '/final.glb'})
    monkeypatch.setattr(safe, '_PinnedTransport', lambda host, addresses: OfflineCheckedTransport())
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(safe.secure_download('https://' + HOST + '/first', [HOST, SECOND_HOST]))
    assert dns == [HOST, SECOND_HOST] and len(requests) == 1


@pytest.mark.parametrize('headers,body,code', [
    ({'content-length': '100'}, BODY, 'MODEL_DOWNLOAD_TOO_LARGE'),
    ({'content-length': '2'}, BODY, 'MODEL_DOWNLOAD_INVALID_CONTENT'),
    ({'content-length': '-1'}, BODY, 'MODEL_DOWNLOAD_INVALID_CONTENT'),
    ({'content-type': 'text/html'}, BODY, 'MODEL_DOWNLOAD_INVALID_CONTENT'),
    ({'content-encoding': 'gzip'}, BODY, 'MODEL_DOWNLOAD_BLOCKED'),
    ({}, b'', 'MODEL_DOWNLOAD_INVALID_CONTENT'),
])
def test_resource_headers_and_integrity_are_bounded(headers, body, code, monkeypatch):
    monkeypatch.setattr(safe, 'MAX_BYTES', 32)
    with pytest.raises(ServiceError, match=code):
        # A raw response stream lets the downloader inspect Content-Encoding
        # before decoding; content= would eagerly decode invalid gzip fixtures.
        run('https://' + HOST + '/model', lambda request: httpx.Response(200, stream=OfflineBody([body]), headers=headers))


class OfflineBody(httpx.AsyncByteStream):
    def __init__(self, chunks, delay=0):
        self.chunks, self.delay = chunks, delay
    async def __aiter__(self):
        for chunk in self.chunks:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield chunk


def test_stream_without_length_stops_at_byte_limit(monkeypatch):
    monkeypatch.setattr(safe, 'MAX_BYTES', 8)
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_TOO_LARGE'):
        run('https://' + HOST + '/model', lambda request: httpx.Response(200, stream=OfflineBody([b'12345', b'67890'])))


def test_whole_deadline_stops_slow_stream_without_retry(monkeypatch):
    monkeypatch.setattr(safe, 'TOTAL_TIMEOUT_SECONDS', .025)
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=OfflineBody([b'a'] * 10, delay=.01))
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_TIMEOUT'):
        run('https://' + HOST + '/model', handler)
    assert len(requests) == 1


def test_network_exception_with_signed_url_is_sanitized_without_retry():
    requests = []
    def handler(request):
        requests.append(request)
        raise httpx.ReadTimeout('https://' + HOST + '/model?secret=DO_NOT_LOG', request=request)
    with pytest.raises(ServiceError) as error:
        run('https://' + HOST + '/model?secret=DO_NOT_LOG', handler)
    assert error.value.code == 'MODEL_DOWNLOAD_TIMEOUT'
    assert 'DO_NOT_LOG' not in str(error.value) + error.value.message
    assert len(requests) == 1


def test_unknown_transport_cannot_bypass_pin():
    with pytest.raises(ServiceError, match='MODEL_DOWNLOAD_BLOCKED'):
        asyncio.run(safe.secure_download('https://' + HOST + '/model', [HOST], httpx.AsyncHTTPTransport()))


def test_logging_context_is_isolated_between_concurrent_tasks(caplog):
    caplog.set_level(logging.DEBUG)
    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        async def handler(request):
            logging.getLogger('httpcore.http11').debug('SIGNED_DOWNLOAD_SECRET')
            started.set()
            await release.wait()
            return httpx.Response(200, content=BODY)
        task = asyncio.create_task(safe.secure_download('https://' + HOST + '/model', [HOST], httpx.MockTransport(handler)))
        await started.wait()
        logging.getLogger('httpcore.http11').debug('OTHER_CONCURRENT_REQUEST')
        release.set()
        await task
    asyncio.run(scenario())
    assert 'SIGNED_DOWNLOAD_SECRET' not in caplog.text
    assert 'OTHER_CONCURRENT_REQUEST' in caplog.text
