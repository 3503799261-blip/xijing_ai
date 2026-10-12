"""Offline candidate registration, never character approval or supplier traffic."""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from PIL import Image, ImageChops, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings
from backend.app.assets.service import AssetService
from backend.app.assets.candidates import CandidateCatalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--prompt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text('utf-8'))
    history = json.loads(args.history.read_text('utf-8'))
    prompt = json.loads(args.prompt.read_text('utf-8'))
    # Bind the exact bytes read once, rather than the replaceable source path.
    with args.image.open('rb') as file:
        raw = file.read(10 * 1024 * 1024 + 1)
    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != manifest['expectedSourceHash']:
        raise ValueError('Source image changed since review. Register a new reviewed version.')
    assets = AssetService(Settings(), None)  # Does not construct or mutate TaskStore/UsageManager.
    catalog = CandidateCatalog(assets)
    with assets.store.connect() as db:
        counts_before = {name: db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0]
                         for name in ('character_assets', 'asset_images', 'asset_models')}
    old = catalog.import_history(history, manifest['scope'])
    item = catalog.register(raw, manifest['mimeType'], manifest['scope'], manifest['sourceNote'],
                            manifest['licenseNote'], prompt, str(args.image.resolve()), manifest['styleMode'])
    saved_original = catalog.file_path(item['candidateId'], 'original').read_bytes()
    with Image.open(io.BytesIO(raw)) as original, Image.open(catalog.file_path(item['candidateId'])) as preview:
        source_rgb = ImageOps.exif_transpose(original).convert('RGB')
        normalized_rgb = preview.convert('RGB')
        pixels_identical = (source_rgb.size == normalized_rgb.size
                            and ImageChops.difference(source_rgb, normalized_rgb).getbbox() is None)
    with assets.store.connect() as db:
        counts_after = {name: db.execute('SELECT COUNT(*) FROM ' + name).fetchone()[0]
                        for name in counts_before}
    if saved_original != raw or not pixels_identical or counts_before != counts_after:
        raise ValueError('Candidate snapshot integrity check failed; do not use for modeling.')
    result = {'kind': 'OFFLINE_CANDIDATE_REGISTRATION_NO_SUPPLIER_CALLS',
              'previousCandidate': old, 'candidate': item,
              'proof': {'sourceHashChanged': old['sourceHash'] != item['sourceHash'],
                        'originalBytesIdentical': saved_original == raw,
                        'decodedRgbPixelsIdentical': pixels_identical,
                        'backgroundEdited': False, 'cropApplied': False,
                        'formalAssetCountsBefore': counts_before, 'formalAssetCountsAfter': counts_after,
                        'formalAssetsUnchanged': counts_before == counts_after,
                        'realModelSubmissions': 0, 'supplierApiCalls': 0}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(json.dumps({'candidateId': item['candidateId'], 'version': item['version'],
                      'sourceHash': item['sourceHash'], 'previewHash': item['hash'],
                      'pixelsIdentical': pixels_identical, 'modelEligible': item['modelEligible']}))


if __name__ == '__main__':
    main()
