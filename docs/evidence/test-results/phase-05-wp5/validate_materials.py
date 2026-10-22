"""Read-only WP5 documentation gates. Never import/start app or call HTTP.

Private inventories are independently collected with the archived readonly
inventory helper. This script checks their hashes, never writes a database.
"""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
RUNTIME = REPO.parent / '.runtime'
PREFIX = 'phase5-wp5-'
BASE_HEAD = '61064b0842e5f3789c01b107dd0b2a3f45c55adb'
REPORTS = [
    'project-facts', 'requirements-evidence-map', 'competition-submission-brief',
    'demo-script', 'evidence-index', 'deployment-and-recovery',
    'asset-provenance-and-permissions', 'submission-checklist', 'work-package-05',
]
DOCUMENTS = [REPO / 'docs/reports' / f'phase-05-{n}.md' for n in REPORTS]
DOCUMENTS += [REPO / 'docs/prompts/phase-05/README.md', OUT.parent / 'phase-05-wp5-test-report.md']
checks = []


def check(name, condition, details=None):
    item = {'name': name, 'status': 'PASS' if condition else 'FAIL'}
    if details is not None:
        item['details'] = details
    checks.append(item)


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO, encoding='utf8').strip()


def slug(value):
    value = re.sub(r'<[^>]+>', '', value).replace('`', '').strip().lower()
    return re.sub(r'\s', '-', re.sub(r'[^\w\-\s]', '', value))


def nodes(path):
    root = ET.parse(path).getroot()
    return [(n.attrib.get('classname'), n.attrib.get('name')) for n in root.iter('testcase')]


def run(output):
    baseline = read(RUNTIME / (PREFIX + 'baseline-20261022.json'))
    check('clean_start', baseline['initialStatus'] == '' and baseline['head'] == BASE_HEAD)
    check('branch_preserved', git('branch', '--show-current') == baseline['branch'])
    for name, expected in baseline['protectedTrackedFiles'].items():
        path = REPO / name
        if name == 'README.md':
            original = subprocess.check_output(['git', 'show', BASE_HEAD + ':README.md'], cwd=REPO)
            current = path.read_bytes()
            old_lines, new_lines = original.splitlines(), current.splitlines()
            differences = [i for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
            # README has CRLF in the worktree; Git content may use LF. Compare
            # the entire original bytes after restoring its original EOL style.
            original_eol = b'\r\n' if b'\r\n' in current else b'\n'
            expected_original = original_eol.join(old_lines) + (original_eol if current.endswith(original_eol) else b'')
            check('readme_baseline_matches_saved_hash', hashlib.sha256(expected_original).hexdigest() == expected)
            check('readme_only_current_state_line', len(old_lines) == len(new_lines) and differences == [4]
                  and old_lines[4].decode('utf8').startswith('当前状态（2026-10-22）')
                  and 'PHASE_5_WP5_WAITING_ACCEPTANCE' in new_lines[4].decode('utf8')
                  and 'WP1～4已获用户验收' in new_lines[4].decode('utf8'))
            continue
        check('protected_tracked:' + name, path.is_file() and sha(path) == expected)
    changed = set(git('diff', '--name-only', BASE_HEAD).splitlines())
    changed.update(git('ls-files', '--others', '--exclude-standard').splitlines())
    allowed_reports = {p.relative_to(REPO).as_posix() for p in DOCUMENTS}
    allowed_prompts = {
        'docs/prompts/phase-05/18-wp5-delivery-user-request.txt',
        'docs/prompts/phase-05/19-wp5-delivery-public-conversation.jsonl',
        'docs/prompts/phase-05/20-wp5-delivery-export-metadata.json',
    }
    for name in sorted(changed):
        allowed = (name == 'README.md' or name in allowed_reports or name in allowed_prompts or
                   name.startswith('docs/evidence/test-results/phase-05-wp5/'))
        check('allowed_change:' + name, allowed)
        path = REPO / name
        check('text_only:' + name, path.is_file() and path.suffix in {'.md', '.py', '.txt', '.json', '.jsonl'})
        check('size_limit:' + name, path.is_file() and path.stat().st_size < 2_000_000)

    referenced_commits = {BASE_HEAD, 'ae2783e', '452a0c2', '0955d0f', 'f58888b', 'ea0f4fc',
                          '9e3516d', 'f8a1f47', '60e1590', 'e36c1e5', '76dbba0', '45d1dcc', '74b3e6e'}
    links_checked = 0
    for path in DOCUMENTS:
        check('document_exists:' + path.name, path.is_file())
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf8')
        # Code fences are not Markdown hyperlinks; do not interpret regex source or examples.
        prose = re.sub(r'(?ms)^(```|~~~).*?^\1\s*$', '', text)
        for target in re.findall(r'\]\(([^\n)]+)\)', prose):
            target = target.strip('<>')
            parsed = urlsplit(target)
            if parsed.scheme:
                check('safe_link_scheme:' + target, parsed.scheme in {'http', 'https'})
                continue  # Existing local HTTP links are NOT requested during WP5.
            file_part, _, fragment = unquote(target).partition('#')
            destination = (path.parent / file_part).resolve() if file_part else path
            links_checked += 1
            check('local_link:' + path.name + ':' + target, destination.exists())
            if fragment and destination.is_file() and destination.suffix == '.md':
                headings = re.findall(r'^#{1,6}\s+(.+?)\s*$', destination.read_text('utf8'), re.M)
                check('heading_link:' + path.name + ':' + target, fragment in {slug(h) for h in headings})
        referenced_commits.update(re.findall(r'`([0-9a-f]{7,40})`', text))
        check('no_sensitive_signed_links:' + path.name,
              not re.search(r'https?://[^\s<>]+[?&](?:[Xx]-[Aa]mz-|[Xx]-[Cc]os-|signature=|token=)', text))
    # Model Hub revisions are also 40 hex characters, but belong to a different
    # repository. Validate their exact pinned source separately, not as our Git.
    model_revision = '7999e1d3359715c523056ef9478215996d62a620'
    check('model_revision_matches_download_script',
          model_revision in (REPO / 'backend/scripts/download_model.py').read_text('utf8'))
    referenced_commits.discard(model_revision)
    for commit in sorted(referenced_commits):
        valid = subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'], cwd=REPO,
                               capture_output=True).returncode == 0
        ancestor = valid and subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD'],
                                          cwd=REPO, capture_output=True).returncode == 0
        check('actual_commit_ancestor:' + commit, ancestor)

    old = REPO / 'docs/evidence/test-results/phase-05-wp4-db-repair'
    full = nodes(old / 'full-final-pytest.xml')
    targeted = nodes(old / 'targeted-final-pytest.xml')
    for file in ['full-final-pytest.xml', 'targeted-final-pytest.xml']:
        tree = ET.parse(old / file).getroot()
        suites_clean = all(int(n.attrib.get(k, '0')) == 0
                           for n in tree.iter('testsuite') for k in ['failures', 'errors', 'skipped'])
        case_status_clean = not any(list(tree.iter(k)) for k in ['failure', 'error', 'skipped'])
        check('junit_no_failures_errors_skips:' + file, suites_clean and case_status_clean)
    check('full754_actual_nodes', len(full) == 754 and len(set(full)) == 754)
    check('specialized41_in754', len(targeted) == 41 and set(targeted).issubset(set(full)))
    check('full_contains41_database_safety', sum('test_database_safety' in (c or '') for c, _ in full) == 41)
    for file, count in [('full-final-isolation-result.json', 754), ('targeted-final-isolation-result.json', 41)]:
        data = read(old / file)
        check('original_result:' + file, data['passed'] == count and data['failedReports'] == 0
              and data['skippedReports'] == 0 and data['pytestExitCode'] == 0
              and not any(data['auditCounts'].values()))
    cli = read(old / 'explicit-init-cli.json')
    check('separate_cli9', cli['passed'] == 9 and cli['failed'] == 0)
    field = [read(old / f'field-{s}-probe.json') for s in ['corrupt', 'restored', 'misconfigured', 'recovered']]
    check('separate_field42', sum(r['passed'] for r in field) == 42 and all(r['failed'] == 0 for r in field))
    check('field_source80_match', read(old / 'field-final-summary.json')['sourceComparison']['allSame'])
    for item in read(old / 'archive-manifest.json')['files']:
        check('original_evidence_hash:' + item['file'], sha(old / item['file']) == item['archiveSha256'])

    before = read(RUNTIME / (PREFIX + 'physical-before-20261022.json'))
    after = read(RUNTIME / (PREFIX + 'physical-after-20261022.json'))
    integrity = {'scope': 'Read-only actual resource hashes; no rows, credentials or private files copied',
                 'beforeAtUtc': before['checkedAtUtc'], 'afterAtUtc': after['checkedAtUtc'],
                 'baselineComparedToWP4': before['comparison'], 'comparison': {}, 'counts': {}}
    for key in ['databases', 'activeManifestSha256', 'generation', 'generationFiles', 'bgeFiles', 'assetFiles']:
        same = before[key] == after[key]
        integrity['comparison'][key] = same
        check('unchanged_private:' + key, same)
    check('matches_WP4_original_resources', all(before['comparison'].values()))
    safety = read(OUT / 'safety-flags.json')
    check('creation_flags_still_closed', not safety['unknownBoolean'] and not any(safety['flags'].values()))
    integrity['counts'] = {k: len(after[k]) for k in ['databases', 'generationFiles', 'bgeFiles', 'assetFiles']}
    integrity['databases'] = {k: {p: v[p] for p in ['relative', 'bytes', 'sha256']} for k, v in after['databases'].items()}
    integrity['glbFiles'] = {k: v for k, v in after['assetFiles'].items() if k.endswith('.glb')}
    integrity['legacyInventoryClientDate'] = after['clientDate']
    integrity['dateNote'] = 'Reuse of original readonly helper preserves its old clientDate literal; checkedAtUtc is actual execution time.'
    (OUT / 'resource-integrity.json').write_text(json.dumps(integrity, ensure_ascii=False, indent=2) + '\n', encoding='utf8')

    prompts = REPO / 'docs/prompts/phase-05'
    meta = read(prompts / '20-wp5-delivery-export-metadata.json')
    check('exact_user_prompt', sha(prompts / '18-wp5-delivery-user-request.txt') == meta['requestSha256'] and meta['requestExactUtf8Match'])
    check('actual_public_snapshot', sha(prompts / '19-wp5-delivery-public-conversation.jsonl') == meta['publicSnapshotSha256'])
    check('no_hidden_reasoning_export', meta['hiddenReasoningExported'] is False)
    for line in (prompts / '19-wp5-delivery-public-conversation.jsonl').read_text('utf8').splitlines():
        json.loads(line)
    intro = (REPO / 'docs/reports/phase-05-competition-submission-brief.md').read_text('utf8')
    sizes = []
    for title, body in re.findall(r'### ([^\n]+)\n\n(.*?)(?=\n### |\n## |\Z)', intro, re.S):
        sizes.append({'title': title, 'nonWhitespaceCharacters': len(re.sub(r'\s', '', body)),
                      'hanCharacters': len(re.findall(r'[\u4e00-\u9fff]', body))})
    check('three_intro_versions', len(sizes) == 3)

    sys.path.insert(0, str(REPO / 'scripts'))
    from check_public_secrets import scan
    secrets = scan(REPO)
    check('public_secret_patterns', secrets['success'])
    whitespace = subprocess.run(['git', 'diff', '--check'], cwd=REPO, capture_output=True, encoding='utf8')
    check('tracked_diff_whitespace', whitespace.returncode == 0)
    for name in sorted(changed):
        path = REPO / name
        if path.is_file() and path.suffix in {'.md', '.py', '.json', '.jsonl'}:
            text = path.read_text('utf8')
            check('new_text_whitespace:' + name, all(not line.endswith((' ', '\t')) for line in text.splitlines())
                  and not text.endswith('\n\n'))
    result = {'checkedAtUtc': datetime.now(timezone.utc).isoformat(),
              'scope': 'Documentation, local links, prior test evidence, hashes and Git only; not new app/browser tests',
              'branch': git('branch', '--show-current'), 'headAtCheck': git('rev-parse', 'HEAD'),
              'baselineHead': BASE_HEAD, 'passed': sum(c['status'] == 'PASS' for c in checks),
              'failed': sum(c['status'] == 'FAIL' for c in checks), 'skipped': 0,
              'localLinksChecked': links_checked,
              'historical754Includes41': len(full) == 754 and len(targeted) == 41 and set(targeted).issubset(set(full)),
              'introCounts': sizes, 'checks': checks, 'secretScan': secrets,
              'paidApiCalls': 0, 'neural4dRequests': 0, 'appImportedOrStarted': False,
              'newApplicationTestsRun': 0, 'newBrowserRehearsalRun': False,
              'mergePushPerformed': False, 'privateFilesPublished': False}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(json.dumps({k: result[k] for k in ['passed', 'failed', 'skipped', 'localLinksChecked']}, ensure_ascii=False))
    for c in checks:
        if c['status'] == 'FAIL':
            print(json.dumps(c, ensure_ascii=False))
    return 0 if result['failed'] == 0 else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT / 'validation-result.json')
    raise SystemExit(run(parser.parse_args().output))
