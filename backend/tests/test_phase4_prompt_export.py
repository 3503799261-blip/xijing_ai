"""Offline public-evidence redaction; no actual session or credentials read."""
import importlib.util
import json
import sys
from pathlib import Path
import pytest

@pytest.mark.parametrize('host', ['cos.neural4d.com', 'cos.zmkj.com'])
def test_signed_documentation_or_result_url_is_removed_as_a_whole(host, monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('phase4_export_offline', scripts / 'export_phase4_prompt.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    url = f'https://{host}/offline/model.glb?AWSAccessKeyId=OFFLINE_ACCESS&Signature=OFFLINE_SIGNATURE&Expires=100'
    raw = json.dumps({'output': json.dumps({'modelUrl': url, 'codeStatus': 0})})
    cleaned = module.redact(raw)
    assert 'OFFLINE_ACCESS' not in cleaned and 'OFFLINE_SIGNATURE' not in cleaned
    assert '/offline/model.glb' not in cleaned and 'AWSAccessKeyId' not in cleaned
    assert '[signed model resource URL redacted]' in cleaned
    assert json.loads(json.loads(cleaned)['output'])['codeStatus'] == 0

def test_unsigned_public_documentation_link_is_preserved(monkeypatch):
    scripts = Path(__file__).resolve().parents[2] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('phase4_export_offline_public', scripts / 'export_phase4_prompt.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = 'https://docs.neural4d.com/en/quickstart https://cos.neural4d.com/example.glb'
    assert module.redact(value) == value
