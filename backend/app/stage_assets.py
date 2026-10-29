"""Read-only digital-stage manifest and bounded, local-only asset delivery.

This service never creates a directory, registers an asset, opens a database,
or contacts a model provider. Missing prepared resources remain unavailable.
"""
import hashlib
import json
import math
import re
import stat
import struct
import threading
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from .api.assets import require_local_internal_access
from .errors import ServiceError

ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,79}$')
HASH = re.compile(r'^[a-f0-9]{64}$')
SEGMENT = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$')
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ASSET_BYTES = 256 * 1024 * 1024
MIME = {'.glb': 'model/gltf-binary', '.png': 'image/png',
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp'}
HEADERS = {'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'}


def unavailable():
    return ServiceError('STAGE_RESOURCES_UNAVAILABLE', '数字戏台资源尚未准备好，请按运行说明恢复已有资源后重试。', 503)


def invalid_manifest():
    return ServiceError('STAGE_MANIFEST_INVALID', '数字戏台资源清单无法读取，请检查或恢复对应资源版本。', 503)


def resource_error(code='STAGE_FILE_NOT_FOUND', status=404):
    return ServiceError(code, '该戏台资源暂时不可用，请检查已有资源或重新加载。', status)


def text(value, limit=2000):
    return value[:limit] if isinstance(value, str) else ''


def numeric(value, depth=0):
    """Copy bounded transform/camera data, never arbitrary manifest objects."""
    if depth > 4:
        raise ValueError('Numeric metadata nesting limit')
    if isinstance(value, bool):
        raise ValueError('Boolean is not a transform')
    if isinstance(value, (float, int)) and math.isfinite(value) and abs(value) <= 10_000_000:
        return value
    if isinstance(value, list) and len(value) <= 16:
        return [numeric(item, depth + 1) for item in value]
    if isinstance(value, dict) and len(value) <= 16:
        allowed = {'min', 'max', 'center', 'size', 'position', 'target', 'fov', 'near', 'far',
                   'radius', 'azimuth', 'elevation', 'x', 'y', 'z', 'minDistance', 'maxDistance'}
        if not set(value) <= allowed:
            raise ValueError('Unknown camera metadata')
        return {key: numeric(item, depth + 1) for key, item in value.items()}
    raise ValueError('Invalid numeric metadata')


class StageAssets:
    def __init__(self, root):
        # resolve(strict=False) does not create missing resources.
        self.root = Path(root).absolute()
        self._verified = {}
        self._lock = threading.Lock()

    def _safe_path(self, relative):
        if not isinstance(relative, str) or len(relative) > 512 or '\\' in relative:
            raise invalid_manifest()
        parts = relative.split('/')
        if not parts or any(not SEGMENT.fullmatch(part) or part in ('.', '..') for part in parts):
            raise invalid_manifest()
        if PurePosixPath(relative).is_absolute():
            raise invalid_manifest()
        candidate = self.root.joinpath(*parts)
        resolved_root = self.root.resolve()
        resolved = candidate.resolve()
        if resolved_root not in resolved.parents:
            raise invalid_manifest()
        # Windows junctions/reparse points and ordinary symlinks must not turn a
        # whitelisted relative path into another storage location.
        for item in [self.root, *[self.root.joinpath(*parts[:i]) for i in range(1, len(parts) + 1)]]:
            try:
                metadata = item.lstat()
            except FileNotFoundError:
                continue
            if item.is_symlink() or getattr(metadata, 'st_file_attributes', 0) & 0x400:
                raise invalid_manifest()
        return candidate

    def _read_manifest(self):
        try:
            path = self._safe_path('manifest.json')
            if not path.is_file():
                raise unavailable()
            with path.open('rb') as stream:
                raw = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) > MAX_MANIFEST_BYTES:
                raise invalid_manifest()
            body = json.loads(raw)
            if not isinstance(body, dict) or body.get('schemaVersion') != '1.0':
                raise invalid_manifest()
            if not isinstance(body.get('stage'), dict) or not isinstance(body.get('characters'), list):
                raise invalid_manifest()
            if len(body['characters']) > 32:
                raise invalid_manifest()
            groups = body.get('groups', [])
            media = body.get('media', [])
            if not isinstance(groups, list) or len(groups) > 32 or not isinstance(media, list) or len(media) > 64:
                raise invalid_manifest()
            records = [body['stage'], *body['characters'], *media]
            ids = []
            for record in records:
                if not isinstance(record, dict) or not isinstance(record.get('id'), str) or not ID.fullmatch(record['id']):
                    raise invalid_manifest()
                ids.append(record['id'])
                path = self._safe_path(record.get('file'))
                if path.suffix.lower() not in MIME:
                    raise invalid_manifest()
                if not isinstance(record.get('sha256'), str) or not HASH.fullmatch(record['sha256']):
                    raise invalid_manifest()
                size = record.get('sizeBytes')
                if isinstance(size, bool) or not isinstance(size, int) or not 0 < size <= MAX_ASSET_BYTES:
                    raise invalid_manifest()
            if len(ids) != len(set(ids)):
                raise invalid_manifest()
            for record in [body['stage'], *body['characters']]:
                if Path(record['file']).suffix.lower() != '.glb':
                    raise invalid_manifest()
            seen_groups = set()
            for group in groups:
                if (not isinstance(group, dict) or not isinstance(group.get('id'), str)
                        or not ID.fullmatch(group['id']) or group['id'] in seen_groups):
                    raise invalid_manifest()
                seen_groups.add(group['id'])
            return body
        except ServiceError:
            raise
        except (OSError, ValueError, TypeError, RecursionError):
            raise invalid_manifest() from None

    def _check_file(self, record):
        path = self._safe_path(record['file'])
        try:
            metadata = path.stat()
            if not stat.S_ISREG(metadata.st_mode):
                return path, 'missing'
            if metadata.st_size != record['sizeBytes']:
                return path, 'integrity_error'
            fingerprint = (str(path), record['sha256'], metadata.st_size,
                           metadata.st_mtime_ns, metadata.st_ctime_ns, metadata.st_ino)
            with self._lock:
                if fingerprint in self._verified:
                    return path, self._verified[fingerprint]
            with path.open('rb') as stream:
                header = stream.read(12)
                stream.seek(0)
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            suffix = path.suffix.lower()
            valid_format = ((suffix == '.glb' and len(header) == 12 and
                             struct.unpack('<4sII', header) == (b'glTF', 2, metadata.st_size))
                            or (suffix == '.png' and header.startswith(b'\x89PNG\r\n\x1a\n'))
                            or (suffix in ('.jpg', '.jpeg') and header.startswith(b'\xff\xd8\xff'))
                            or (suffix == '.webp' and header[:4] == b'RIFF' and header[8:12] == b'WEBP'))
            status = 'ready' if digest == record['sha256'] and valid_format else 'integrity_error'
            with self._lock:
                # Bound runtime memory independently of the manifest version count.
                if len(self._verified) >= 256:
                    self._verified.clear()
                self._verified[fingerprint] = status
            return path, status
        except (OSError, ValueError):
            return path, 'missing'

    def _public(self, record):
        _, state = self._check_file(record)
        result = {'id': record['id'], 'name': text(record.get('name'), 120),
                  'fileUrl': '/api/v1/stage/files/' + record['id'],
                  'sha256': record['sha256'], 'sizeBytes': record['sizeBytes'],
                  'available': state == 'ready', 'status': state}
        for key in ('description', 'question', 'groupId', 'purpose', 'attribution', 'licenseNote'):
            if key in record:
                result[key] = text(record[key])
        for key in ('position', 'scale', 'rotation', 'rotationY', 'floorY', 'camera', 'bounds'):
            if key in record:
                result[key] = numeric(record[key])
        if 'facing' in record:
            result['facing'] = text(record['facing'], 30) if isinstance(record['facing'], str) else numeric(record['facing'])
        citations = record.get('citations', [])
        if not isinstance(citations, list) or len(citations) > 20:
            raise invalid_manifest()
        result['citations'] = []
        for item in citations:
            if not isinstance(item, dict):
                raise invalid_manifest()
            value = {key: text(item.get(key), 3000 if key == 'excerpt' else 500)
                     for key in ('id', 'title', 'url', 'excerpt')}
            if value['url'] and not value['url'].startswith(('https://', 'http://')):
                raise invalid_manifest()
            result['citations'].append(value)
        return result

    def catalog(self):
        body = self._read_manifest()
        try:
            return {'schemaVersion': '1.0', 'version': text(body.get('version'), 100),
                    'stage': self._public(body['stage']),
                    'characters': [self._public(record) for record in body['characters']],
                    'groups': [{'id': group['id'], 'name': text(group.get('name'), 120),
                                'description': text(group.get('description'))} for group in body.get('groups', [])],
                    'usage': '仅供比赛使用，非商用；展示已有模型，不生成新任务。'}
        except (ValueError, TypeError, RecursionError):
            raise invalid_manifest() from None

    def file(self, file_id):
        if not isinstance(file_id, str) or not ID.fullmatch(file_id):
            raise resource_error()
        body = self._read_manifest()
        records = [body['stage'], *body['characters'], *body.get('media', [])]
        record = next((item for item in records if item['id'] == file_id), None)
        if record is None:
            raise resource_error()
        path, state = self._check_file(record)
        if state != 'ready':
            raise resource_error('STAGE_FILE_INTEGRITY_ERROR' if state == 'integrity_error' else 'STAGE_FILE_NOT_FOUND',
                                 409 if state == 'integrity_error' else 404)
        return path, record


def register_stage(app, root):
    service = StageAssets(root)
    router = APIRouter(prefix='/api/v1/stage')

    @router.get('/catalog')
    async def catalog(request: Request):
        require_local_internal_access(request)
        body = await run_in_threadpool(service.catalog)
        from fastapi.responses import JSONResponse
        return JSONResponse({**body, 'requestId': getattr(request.state, 'request_id', None)}, headers=HEADERS)

    @router.api_route('/files/{file_id}', methods=['GET', 'HEAD'])
    async def asset_file(file_id: str, request: Request):
        require_local_internal_access(request)
        path, record = await run_in_threadpool(service.file, file_id)
        return FileResponse(path, media_type=MIME[path.suffix.lower()],
                            headers={**HEADERS, 'ETag': '"' + record['sha256'] + '"'})

    app.include_router(router)
    return service
