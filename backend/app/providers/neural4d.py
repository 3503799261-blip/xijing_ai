"""One-attempt transport. Creation is possible ONLY after durable quota reservation.

Official current multipart contract, checked 2026-10-11. No legacy JSON/fileKey
fallback, redirects, automatic polling, SDK retries or alternative create paths.
"""
import hashlib
import ipaddress
import json
import socket
import time
from urllib.parse import urlsplit
import httpx
from ..config import WORKSPACE_ROOT
from ..errors import ServiceError

BASE = 'https://alb.neural4d.com:3000/api'
CANONICAL_USAGE_LEDGER = WORKSPACE_ROOT / '.runtime' / 'neural4d-usage.sqlite3'


def parameters_for_style(style_mode):
    """Server-only whitelist, same documented image-to-3D endpoint for both.

    Geometry density is a technical preset, not a guarantee of artistic style;
    the separately confirmed concept image controls the visual interpretation.
    This does not use the special multi-candidate chibi endpoint.
    """
    if not isinstance(style_mode, str) or style_mode not in ('chibi', 'realistic'):
        raise ServiceError('NEURAL4D_STYLE_INVALID', '请选择已支持的Q版或写实风格。', 422)
    return {'modelCount': '1', 'mesh_quality': 'standard',
            'faceNum': '100000' if style_mode == 'chibi' else '500000',
            'disablePbr': '0', 'onlyGenerateMesh': 'false', 'enableImageEnhancement': 'false'}


# Backwards-compatible read-only-by-convention export; real sends always obtain
# a fresh server-selected dictionary rather than trusting a caller's parameters.
PARAMETERS = parameters_for_style('realistic')


class Neural4DProvider:
    def __init__(self, settings, usage, transport=None):
        self.settings, self.usage, self.transport = settings, usage, transport
        self.validate_ledger()

    def validate_ledger(self):
        # Only explicitly offline MockTransport may isolate a fixture ledger.
        # A different real/custom HTTP transport cannot reset the project cap by
        # selecting another data directory or constructing a fresh UsageManager.
        if not isinstance(self.transport, httpx.MockTransport) and self.usage.path.resolve() != CANONICAL_USAGE_LEDGER.resolve():
            raise ServiceError('NEURAL4D_LEDGER_PATH_INVALID', '真实供应商服务只能使用全项目固定额度账本，禁止切换账本重置次数。', 503)

    @property
    def configured(self):
        return bool(self.settings.neural4d_api_key.get_secret_value())

    def headers(self):
        if not self.configured:
            raise ServiceError('NEURAL4D_KEY_MISSING', '请在本地私有配置中填写Neural4D密钥。', 503)
        return {'Authorization': 'Bearer ' + self.settings.neural4d_api_key.get_secret_value()}

    def client(self, timeout=None):
        return httpx.AsyncClient(transport=self.transport, timeout=timeout or self.settings.neural4d_timeout_seconds,
                                 follow_redirects=False, trust_env=False)

    async def read_operation(self, path, body, operation, *, attempt_id=None):
        if path not in ('queryPointsInfo', 'retrieveModel'):
            raise ServiceError('NEURAL4D_OPERATION_BLOCKED', '未开放该供应商操作。', 403)
        started = time.perf_counter()
        status = None
        error = None
        try:
            async with self.client() as client:
                response = await client.post(BASE + '/' + path, headers=self.headers(), json=body)
            status = response.status_code
            if not response.is_success:
                raise self.error(status)
            try:
                data = response.json()
            except (ValueError, UnicodeDecodeError):
                raise ServiceError('NEURAL4D_RESPONSE_INVALID', '供应商响应格式异常。', 502) from None
            if not isinstance(data, dict):
                raise ServiceError('NEURAL4D_RESPONSE_INVALID', '供应商响应格式异常。', 502)
            return data
        except httpx.HTTPError:
            error = 'NEURAL4D_NETWORK_ERROR'
            raise ServiceError(error, '供应商查询失败，未自动重试。', 504) from None
        except ServiceError as exc:
            error = exc.code
            raise
        finally:
            self.usage.record_request(operation, attempt_id=attempt_id, http_status=status, duration_ms=(time.perf_counter()-started)*1000,
                                      error_code=error, is_mock=self.transport is not None)

    @staticmethod
    def error(status):
        messages = {401: ('NEURAL4D_AUTH_FAILED', 'Neural4D鉴权失败，请检查本地配置。'),
                    402: ('NEURAL4D_BALANCE_LOW', 'Neural4D余额不足或账户受限。'),
                    429: ('NEURAL4D_RATE_LIMIT', 'Neural4D请求受限，未自动重发。')}
        code, message = messages.get(status, ('NEURAL4D_PROVIDER_ERROR', 'Neural4D返回错误，未自动重发。'))
        return ServiceError(code, message, 502)

    async def create_once(self, attempt_id, image, mime='image/png'):
        self.validate_ledger()
        if not self.settings.neural4d_generation_enabled or not self.settings.neural4d_protocol_verified:
            raise ServiceError('NEURAL4D_GENERATION_DISABLED', '真实建模未获单次授权或协议尚未核验。', 403)
        headers = self.headers()
        payload = self.usage.frozen_payload(attempt_id)
        parameters = parameters_for_style(payload.get('styleMode'))
        if (type(payload.get('styleVersion')) is not int or payload['styleVersion'] < 1
                or not isinstance(payload.get('characterId'), str) or not payload['characterId'].strip()
                or type(payload.get('modelCount')) is not int or payload['modelCount'] != 1
                or payload.get('imageHash') != hashlib.sha256(image).hexdigest() or payload.get('parameters') != parameters):
            raise ServiceError('NEURAL4D_INPUT_CHANGED', '冻结的建模图片或参数发生变化。', 409)
        # Durable winner before any network operation; duplicate invocation cannot send.
        self.usage.mark_started(attempt_id)
        started, status, error = time.perf_counter(), None, None
        try:
            async with self.client() as client:
                response = await client.post(BASE + '/generateModelWithImage', headers=headers,
                                             data=parameters, files={'image': ('concept.png', image, mime)})
            status = response.status_code
            if not response.is_success:
                # HTTP failure does not refund a creation attempt.
                self.usage.finish(attempt_id, 'FAILED' if status in (400, 401, 402, 403, 422, 429) else 'UNKNOWN', http_status=status, error_code='NEURAL4D_PROVIDER_ERROR')
                raise self.error(status)
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError('Invalid provider response')
            ids = data.get('uuids') or ([data['uuid']] if data.get('uuid') else [])
            if (not isinstance(ids, list) or len(ids) != 1 or not isinstance(ids[0], str) or not 1 <= len(ids[0]) <= 200
                    or (data.get('uuid') is not None and data['uuid'] != ids[0])):
                self.usage.halt('UNEXPECTED_MODEL_COUNT_OR_RESULT')
                self.usage.finish(attempt_id, 'UNKNOWN', http_status=status, error_code='NEURAL4D_RESPONSE_INVALID')
                raise ServiceError('NEURAL4D_RESPONSE_INVALID', '建模响应无法确认唯一模型，已锁定创建，需人工核查。', 502)
            self.usage.finish(attempt_id, 'SUBMITTED', provider_task_id=ids[0], http_status=status)
            return self.usage.get_attempt(attempt_id)
        except ServiceError as exc:
            error = exc.code
            # Local persistence failures are not known supplier rejections.
            if error.startswith('NEURAL4D_LEDGER'):
                try:
                    self.usage.halt('SAVE_FAILED_AFTER_SEND')
                except Exception:
                    self.settings.neural4d_generation_enabled = False
            raise
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            error = 'NEURAL4D_SUBMISSION_UNKNOWN'
            self.usage.finish(attempt_id, 'UNKNOWN', http_status=status, error_code=error)
            raise ServiceError(error, '创建请求结果未知，次数不返还；请先人工核查，不能自动重建。', 504) from None
        except BaseException:
            # Includes cancellation/save failure after potentially successful submission.
            try:
                self.usage.finish(attempt_id, 'UNKNOWN', http_status=status, error_code='NEURAL4D_SAVE_OR_CANCEL_UNKNOWN')
            except Exception:
                self.usage.halt('SAVE_FAILED_AFTER_SEND')
            raise
        finally:
            self.usage.record_request('create_model', attempt_id=attempt_id, is_mock=self.transport is not None,
                                      http_status=status, duration_ms=(time.perf_counter()-started)*1000, error_code=error)

    async def download(self, url):
        parsed = urlsplit(url)
        host = parsed.hostname
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password or parsed.port not in (None, 443) or host not in self.settings.neural4d_download_hosts:
            raise ServiceError('MODEL_DOWNLOAD_BLOCKED', '模型下载域名尚未人工核验，不允许任意外链。', 403)
        if self.transport is None:
            for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
                if not ipaddress.ip_address(info[4][0]).is_global:
                    raise ServiceError('MODEL_DOWNLOAD_BLOCKED', '模型下载地址不是公开资源。', 403)
        # New client: NO Authorization on signed object-store URL or redirects.
        started, status, error = time.perf_counter(), None, None
        try:
            async with self.client(90) as client:
                async with client.stream('GET', url) as response:
                    status = response.status_code
                    if not response.is_success:
                        raise ServiceError('MODEL_DOWNLOAD_FAILED', '模型下载失败，未自动跟随跳转。', 502)
                    data = bytearray()
                    async for block in response.aiter_bytes():
                        if len(data) + len(block) > 50 * 1024 * 1024:
                            raise ServiceError('MODEL_DOWNLOAD_TOO_LARGE', '模型超过50MB，停止下载。', 413)
                        data.extend(block)
            return bytes(data)
        except httpx.HTTPError:
            error = 'MODEL_DOWNLOAD_TIMEOUT'
            raise ServiceError(error, '模型下载超时或网络异常，未自动重试。', 504) from None
        except ServiceError as exc:
            error = exc.code
            raise
        finally:
            self.usage.record_request('download', is_mock=self.transport is not None, http_status=status,
                                      duration_ms=(time.perf_counter()-started)*1000, error_code=error)
