"""One official DeepSeek provider. No automatic paid retry or raw error logging."""
import hashlib
import json
import time
from datetime import datetime, timezone
import httpx
from ..errors import ServiceError
from .budget import BudgetLedger

class DeepSeekProvider:
    def __init__(self, settings, transport=None):
        self.settings = settings
        self.transport = transport
        self.ledger = BudgetLedger(settings.rag_data_dir / 'api-budget.sqlite3', settings.rag_test_budget_cny)
        self.probe_path = settings.rag_data_dir / 'provider-readiness.json'

    @property
    def configured(self):
        return bool(self.settings.deepseek_api_key.get_secret_value().strip())

    def fingerprint(self):
        return hashlib.sha256((self.settings.deepseek_model + ':' + self.settings.deepseek_api_key.get_secret_value()).encode()).hexdigest()

    @property
    def verified(self):
        if not self.configured: return False
        try:
            data = json.loads(self.probe_path.read_text(encoding='utf-8'))
            return data.get('success') is True and data.get('configurationFingerprint') == self.fingerprint()
        except (OSError, ValueError): return False

    async def generate(self, messages: list, request_id: str, json_mode=True, max_output=None) -> dict:
        if not self.configured:
            raise ServiceError('LLM_KEY_MISSING', '尚未配置DeepSeek密钥，请在本机私有.env填写后重启后端。')
        limit = self.settings.deepseek_max_output_tokens if max_output is None else max_output
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 800:
            raise ServiceError('LLM_OUTPUT_LIMIT', '模型输出长度超过本阶段允许范围。', 400)
        self.ledger.reserve(request_id, messages, limit)
        payload = {'model': self.settings.deepseek_model, 'messages': messages, 'thinking': {'type': 'disabled'}, 'stream': False, 'max_tokens': limit, 'temperature': 0.2}
        if json_mode: payload['response_format'] = {'type': 'json_object'}
        started = time.perf_counter()
        status, usage = 'transport_unknown', None
        try:
            async with httpx.AsyncClient(timeout=self.settings.deepseek_timeout_seconds, transport=self.transport) as client:
                response = await client.post(self.settings.deepseek_base_url + '/chat/completions', headers={'Authorization': 'Bearer ' + self.settings.deepseek_api_key.get_secret_value()}, json=payload)
            status = f'http_{response.status_code}'
            if response.status_code != 200:
                mapping = {400: ('LLM_PARAMETERS', 'DeepSeek参数不兼容，请检查本机模型配置。'), 401: ('LLM_AUTH_FAILED', 'DeepSeek鉴权失败，请在本机检查密钥。'), 402: ('LLM_BALANCE', 'DeepSeek余额不足，请检查账户。'), 404: ('LLM_MODEL', 'DeepSeek模型或接口不可用。'), 429: ('LLM_RATE_LIMIT', 'DeepSeek请求限流，请稍后手动重试。')}
                code, message = mapping.get(response.status_code, ('LLM_UPSTREAM', 'DeepSeek服务暂不可用，请稍后手动重试。'))
                raise ServiceError(code, message, 429 if response.status_code == 429 else 502, response.status_code in (429, 500, 502, 503))
            try:
                body = response.json()
                if not isinstance(body, dict): raise ValueError('invalid body')
                usage = body.get('usage')
                if not isinstance(usage, dict): raise ValueError('invalid usage')
                if any(type(usage.get(key)) is not int or usage[key] < 0 for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')):
                    usage = None
                    raise ValueError('invalid usage values')
                choice = body['choices'][0]
                content = choice['message']['content']
                if not isinstance(content, str) or not content.strip(): raise ValueError('empty')
                if choice.get('finish_reason') == 'length': raise ValueError('truncated')
            except (ValueError, KeyError, IndexError, TypeError):
                raise ServiceError('LLM_INVALID_RESPONSE', '模型返回内容为空或不完整，请缩短问题后手动重试。', 502, True)
            # Do not retain or expose reasoning_content. Only record whether disabled mode was consistent.
            returned_model = body.get('model')
            if not isinstance(returned_model, str) or not (returned_model == 'deepseek-flash' or returned_model.startswith('deepseek-flash-')):
                status = 'invalid_model'
                raise ServiceError('LLM_MODEL_MISMATCH', '返回模型与本阶段批准的模型不一致，已停止展示。', 502)
            reasoning_present = bool(choice['message'].get('reasoning_content'))
            if reasoning_present:
                status = 'invalid_mode'
                raise ServiceError('LLM_MODE_MISMATCH', '模型返回与非思考配置不一致，已停止展示。', 502)
            status = 'success'
            result = {'content': content.strip(), 'model': body.get('model'), 'usage': usage, 'elapsedSeconds': round(time.perf_counter() - started, 4), 'thinkingRequested': 'disabled', 'reasoningContentPresent': False, 'httpStatus': response.status_code}
            self.probe_path.write_text(json.dumps({'success': True, 'configurationFingerprint': self.fingerprint(), 'checkedAt': datetime.now(timezone.utc).isoformat(), 'model': result['model']}, ensure_ascii=False), encoding='utf-8')
            return result
        except httpx.TimeoutException:
            status = 'timeout_unknown'
            raise ServiceError('LLM_TIMEOUT', 'DeepSeek请求超时，未自动重发；请稍后手动重试。', 504, True)
        except httpx.RequestError:
            raise ServiceError('LLM_NETWORK', '无法连接DeepSeek，请检查网络后手动重试。', 503, True)
        finally:
            self.ledger.finish(request_id, usage, status)
            if status != 'success':
                self.probe_path.write_text(json.dumps({'success': False, 'checkedAt': datetime.now(timezone.utc).isoformat(), 'status': status}), encoding='utf-8')
