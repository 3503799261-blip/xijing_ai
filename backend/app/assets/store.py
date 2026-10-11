"""Private SQLite asset catalog. Short atomic mutations never span network work."""
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from ..errors import ServiceError
from .visual_prompt import prompt_hash


def now():
    return datetime.now(timezone.utc).isoformat()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


class AssetStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'catalog.sqlite3'
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS character_assets (
              asset_id TEXT PRIMARY KEY, signature TEXT UNIQUE NOT NULL,
              content_json TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS asset_images (
              image_id TEXT PRIMARY KEY, asset_id TEXT NOT NULL REFERENCES character_assets(asset_id),
              content_json TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS asset_models (
              model_id TEXT PRIMARY KEY, asset_id TEXT REFERENCES character_assets(asset_id),
              content_json TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS images_by_asset ON asset_images(asset_id);
            CREATE INDEX IF NOT EXISTS models_by_asset ON asset_models(asset_id);
            CREATE UNIQUE INDEX IF NOT EXISTS model_provider_task_unique
              ON asset_models(json_extract(content_json,'$.providerTaskId'))
              WHERE json_extract(content_json,'$.providerTaskId') IS NOT NULL;
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, asset_id):
        with self.connect() as db:
            row = db.execute('SELECT content_json FROM character_assets WHERE asset_id=?', (asset_id,)).fetchone()
        if row is None:
            raise ServiceError('ASSET_NOT_FOUND', '未找到角色资产。', 404)
        return json.loads(row[0])

    def list(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT content_json FROM character_assets ORDER BY created_at DESC,asset_id DESC LIMIT 100')]

    def create(self, content, signature):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT content_json FROM character_assets WHERE signature=?', (signature,)).fetchone()
            if row:
                return json.loads(row[0])
            # Allocate revision under the same transaction as insertion. This
            # prevents simultaneous prompt edits from claiming the same version.
            if content.get('parentAssetId'):
                revisions = []
                for record in db.execute('SELECT content_json FROM character_assets'):
                    old = json.loads(record[0])
                    if (old.get('sourceTaskId') == content['sourceTaskId']
                            and old.get('sourceResultHash') == content['sourceResultHash']
                            and old.get('styleMode', 'realistic') == content['styleMode']
                            and old.get('mode') == content['mode'] and old.get('purpose') == content['purpose']
                            and old.get('enterpriseBrief') == content.get('enterpriseBrief')):
                        revisions.append(max(old.get('version', 1), old.get('styleVersion', 1)))
                revision = max(revisions, default=1) + 1
                content = {**content, 'version': revision, 'styleVersion': revision,
                           'visualPrompt': {**content['visualPrompt'], 'styleVersion': revision}}
                content['visualPrompt']['promptHash'] = prompt_hash(content['visualPrompt'])
            content = {**content, 'assetId': str(uuid.uuid4()), 'createdAt': now()}
            db.execute('INSERT INTO character_assets VALUES (?,?,?,?)', (content['assetId'], signature, encode(content), content['createdAt']))
        return content

    def approve_visual(self, asset_id, expected_hash):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT content_json FROM character_assets WHERE asset_id=?', (asset_id,)).fetchone()
            if not row:
                raise ServiceError('ASSET_NOT_FOUND', '未找到角色资产。', 404)
            content = json.loads(row[0])
            if content.get('culturalReviewRequired', False):
                raise ServiceError('CULTURAL_REVIEW_REQUIRED', '自由编辑草稿须重新完成Agent文化审校，不能直接批准。', 409)
            if content['visualPrompt']['promptHash'] != expected_hash:
                raise ServiceError('ASSET_STALE_PROMPT', '视觉Prompt已变化，请重新查看后确认。', 409)
            if not content['visualPrompt']['approved']:
                content['visualPrompt'].update(approved=True, approvedAt=now())
                db.execute('UPDATE character_assets SET content_json=? WHERE asset_id=?', (encode(content), asset_id))
        return content

    def add_file(self, kind, asset_id, metadata):
        table, key = {'image': ('asset_images', 'imageId'), 'model': ('asset_models', 'modelId')}[kind]
        if asset_id is not None:
            self.get(asset_id)
        metadata = {**metadata, key: str(uuid.uuid4()), 'assetId': asset_id, 'createdAt': now()}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if kind == 'model' and metadata.get('providerTaskId'):
                row = db.execute("SELECT content_json FROM asset_models WHERE json_extract(content_json,'$.providerTaskId')=?", (metadata['providerTaskId'],)).fetchone()
                if row:
                    old = json.loads(row[0])
                    if (old.get('assetId') != asset_id or old.get('hash') != metadata.get('hash')
                            or old.get('imageHash') != metadata.get('imageHash') or old.get('origin') != metadata.get('origin')):
                        raise ServiceError('MODEL_RESULT_CONFLICT', '同一供应商任务返回不同资产结果，请人工核查。', 409)
                    return old
            db.execute(f'INSERT INTO {table} VALUES (?,?,?,?)', (metadata[key], asset_id, encode(metadata), metadata['createdAt']))
        return metadata

    def file(self, kind, file_id):
        table, key = {'image': ('asset_images', 'image_id'), 'model': ('asset_models', 'model_id')}[kind]
        with self.connect() as db:
            row = db.execute(f'SELECT content_json FROM {table} WHERE {key}=?', (file_id,)).fetchone()
        if not row:
            raise ServiceError('ASSET_FILE_NOT_FOUND', '未找到已登记的资产文件。', 404)
        return json.loads(row[0])

    def files(self, kind, asset_id=None):
        table = {'image': 'asset_images', 'model': 'asset_models'}[kind]
        with self.connect() as db:
            sql = f'SELECT content_json FROM {table}'
            args = ()
            if asset_id is not None:
                sql += ' WHERE asset_id=?'
                args = (asset_id,)
            sql += ' ORDER BY created_at DESC LIMIT 100'
            return [json.loads(row[0]) for row in db.execute(sql, args)]

    def accept_image(self, image_id, expected_hash):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT content_json FROM asset_images WHERE image_id=?', (image_id,)).fetchone()
            if not row:
                raise ServiceError('ASSET_FILE_NOT_FOUND', '未找到概念图。', 404)
            content = json.loads(row[0])
            asset = json.loads(db.execute('SELECT content_json FROM character_assets WHERE asset_id=?', (content['assetId'],)).fetchone()[0])
            if asset.get('culturalReviewRequired', False):
                raise ServiceError('CULTURAL_REVIEW_REQUIRED', '自由编辑草稿的文化审校尚未完成，不能接受概念图。', 409)
            if content['hash'] != expected_hash or content['promptHash'] != asset['visualPrompt']['promptHash']:
                raise ServiceError('ASSET_STALE_IMAGE', '概念图或Prompt版本不一致，请重新确认。', 409)
            if not asset['visualPrompt']['approved']:
                raise ServiceError('VISUAL_APPROVAL_REQUIRED', '请先明确确认这份视觉Prompt。', 409)
            if not content['accepted']:
                content.update(accepted=True, acceptedAt=now())
                db.execute('UPDATE asset_images SET content_json=? WHERE image_id=?', (encode(content), image_id))
        return content
