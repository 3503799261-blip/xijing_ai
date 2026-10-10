"""Backend-only configuration; private env stays outside the static site."""
from pathlib import Path
import os
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent
PRIVATE_ENV = Path(os.environ.get('XIJING_ENV_FILE', WORKSPACE_ROOT / '.private-config' / '.env'))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PRIVATE_ENV, env_file_encoding='utf-8', extra='ignore')
    deepseek_api_key: SecretStr = SecretStr('')
    deepseek_base_url: str = 'https://api.deepseek.com'
    deepseek_model: str = 'deepseek-flash'
    deepseek_thinking_enabled: bool = False
    deepseek_max_output_tokens: int = Field(default=800, ge=32, le=800)
    deepseek_timeout_seconds: float = Field(default=35, ge=1, le=40)
    rag_test_budget_cny: float = Field(default=3, gt=0, le=3)
    rag_data_dir: Path = WORKSPACE_ROOT / '.runtime' / 'xijing-ai'
    embedding_model: str = 'BAAI/bge-small-zh-v1.5'
    embedding_model_path: Path = WORKSPACE_ROOT / '.runtime' / 'models' / 'bge-small-zh-v1.5'
    allowed_origins: list[str] = ['http://127.0.0.1:8000', 'http://localhost:8000', 'http://127.0.0.1:8877', 'http://localhost:8877']
    request_timeout_seconds: float = Field(default=45, ge=2, le=50)
    retrieval_min_score: float = Field(default=0.62, ge=0, le=1)
    retrieval_top_k: int = Field(default=5, ge=1, le=5)

    @field_validator('deepseek_base_url')
    @classmethod
    def approved_provider(cls, value: str) -> str:
        if value.rstrip('/') != 'https://api.deepseek.com':
            raise ValueError('Only the approved official HTTPS provider is supported.')
        return value.rstrip('/')

    @field_validator('deepseek_model')
    @classmethod
    def approved_model(cls, value: str) -> str:
        if value != 'deepseek-flash':
            raise ValueError('Only the approved budgeted deepseek-flash model is supported.')
        return value

    @field_validator('deepseek_thinking_enabled')
    @classmethod
    def no_thinking(cls, value: bool) -> bool:
        if value:
            raise ValueError('Phase 2 budget configuration requires non-thinking mode.')
        return value

    @field_validator('rag_data_dir', 'embedding_model_path')
    @classmethod
    def outside_static_root(cls, value: Path) -> Path:
        path = value.expanduser().resolve()
        if path == PROJECT_ROOT or PROJECT_ROOT in path.parents:
            raise ValueError('Runtime data and model files must stay outside the website repository.')
        return path

    @field_validator('allowed_origins')
    @classmethod
    def local_origins(cls, values: list[str]) -> list[str]:
        permitted = {f'http://{host}:{port}' for host in ('localhost', '127.0.0.1') for port in (8000, 8877)}
        if not set(values).issubset(permitted):
            raise ValueError('Only explicit approved loopback origins are allowed.')
        return values
