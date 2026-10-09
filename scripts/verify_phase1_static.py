"""Verify Phase 1 preservation and local references; does not run a browser."""
import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(root):
    result = []
    for folder, directories, names in os.walk(root):
        directories[:] = [name for name in directories if name not in {'.git', 'docs'}]
        result.extend(Path(folder) / name for name in names)
    return sorted(result)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.references = []
        self.idrefs = []
        self.primary_nav = []
        self.in_primary_nav = False
        self.current_link = None

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        line = self.getpos()[0]
        if attributes.get('id'):
            self.ids.append(attributes['id'])
        for attribute in ['href', 'src', 'poster']:
            if attributes.get(attribute):
                self.references.append((attributes[attribute], line, attribute))
        for attribute in ['aria-labelledby', 'aria-describedby', 'for']:
            if attributes.get(attribute):
                for target in attributes[attribute].split():
                    self.idrefs.append((target, line, attribute))
        if tag == 'nav' and attributes.get('aria-label') == '主导航':
            self.in_primary_nav = True
        if tag == 'a' and self.in_primary_nav:
            self.current_link = {'href': attributes.get('href', ''), 'text': '', 'line': line}

    def handle_data(self, text):
        if self.current_link is not None:
            self.current_link['text'] += text

    def handle_endtag(self, tag):
        if tag == 'a' and self.current_link is not None:
            self.current_link['text'] = self.current_link['text'].strip()
            self.primary_nav.append(self.current_link)
            self.current_link = None
        if tag == 'nav':
            self.in_primary_nav = False


def main_bytes(path):
    content = path.read_bytes()
    blocks = re.findall(rb'<main\b[^>]*>.*?</main\s*>', content, re.I | re.S)
    if len(blocks) != 1:
        raise ValueError(f'{path.name}: expected one main, found {len(blocks)}')
    return blocks[0]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('backup', type=Path)
    parser.add_argument('output', type=Path)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    backup = arguments.backup.resolve()
    files = source_files(root)
    checks = []

    preservation = []
    for directory in ['images', 'audio', 'media']:
        original = {path.relative_to(backup).as_posix(): path for path in (backup / directory).rglob('*') if path.is_file()}
        current = {path.relative_to(root).as_posix(): path for path in (root / directory).rglob('*') if path.is_file()}
        compared = []
        for relative in sorted(original.keys() & current.keys()):
            old_hash, new_hash = digest(original[relative]), digest(current[relative])
            compared.append({'file': relative, 'original_sha256': old_hash, 'current_sha256': new_hash, 'identical': old_hash == new_hash})
        missing = sorted(original.keys() - current.keys())
        added = sorted(current.keys() - original.keys())
        preservation.append({'directory': directory, 'original_count': len(original), 'current_count': len(current), 'missing': missing, 'added': added, 'files': compared, 'passed': not missing and not added and all(row['identical'] for row in compared)})
    checks.append({'name': 'all_original_assets_preserved', 'passed': all(row['passed'] for row in preservation)})

    old_css = []
    for path in sorted((backup / 'css').glob('*.css')):
        target = root / 'css' / path.name
        original_hash, current_hash = digest(path), digest(target) if target.is_file() else None
        old_css.append({'file': 'css/' + path.name, 'original_sha256': original_hash, 'current_sha256': current_hash, 'identical': original_hash == current_hash, 'change_allowed': path.name == 'index.css'})
    checks.append({'name': 'old_css_unchanged_except_approved_index_css', 'passed': all(row['identical'] or row['change_allowed'] for row in old_css)})

    allowed = {
        'index.html': [
            ('从历史源流到课程创作，八个主题带你读懂京剧文化。', '从历史源流到智能创作，八个主题带你走近京剧文化。'),
            ('<a class="entry-card" data-no="08" href="about.html">', '<a class="entry-card" data-no="08" href="about.html#ai-workshop">'),
            ('alt="关于梨园风华网站"', 'alt="AI戏韵工坊京剧文化创作入口"'),
            ('<small>课程创作</small><strong>关于我们</strong><em>制作说明与心得</em>', '<small>智能创作</small><strong>AI戏韵工坊</strong><em>探索知识与角色创意</em>'),
        ],
        'facial.html': [
            ('<a class="btn" href="about.html">了解网站制作说明</a>', '<a class="btn" href="about.html#ai-workshop">走进AI戏韵工坊</a>'),
        ],
    }
    body_results = []
    for name in ['index.html', 'history.html', 'roles.html', 'facial.html', 'music.html', 'video.html', 'gallery.html']:
        original, current = main_bytes(backup / name), main_bytes(root / name)
        expected = original
        replacements = []
        for old, new in allowed.get(name, []):
            old_bytes, new_bytes = old.encode('utf-8'), new.encode('utf-8')
            count = expected.count(old_bytes)
            replacements.append({'old': old, 'new': new, 'original_occurrences': count})
            expected = expected.replace(old_bytes, new_bytes)
        passed = expected == current and all(row['original_occurrences'] == 1 for row in replacements)
        body_results.append({'file': name, 'original_main_sha256': hashlib.sha256(original).hexdigest(), 'current_main_sha256': hashlib.sha256(current).hexdigest(), 'byte_identical': original == current, 'allowed_replacements': replacements, 'only_allowed_changes': passed})
    checks.append({'name': 'seven_cultural_page_main_preservation', 'passed': all(row['only_allowed_changes'] for row in body_results)})

    pages = {}
    for path in files:
        if path.suffix.lower() == '.html':
            page = PageParser()
            page.feed(path.read_text(encoding='utf-8-sig'))
            pages[path] = page
    references = []
    external_references = []
    missing = []
    broken_anchors = []
    duplicates = []
    broken_idrefs = []

    def check_reference(path, reference, line, kind):
        url = urlsplit(reference)
        relative = path.relative_to(root).as_posix()
        if url.scheme or url.netloc or reference.startswith('//'):
            external_references.append({'file': relative, 'line': line, 'ref': reference, 'kind': kind})
            return
        target = (root / unquote(url.path).lstrip('/')).resolve() if url.path.startswith('/') else (path.parent / unquote(url.path)).resolve() if url.path else path
        row = {'file': relative, 'line': line, 'ref': reference, 'kind': kind}
        if url.path:
            row['target'] = str(target)
            row['exists'] = target.is_file()
            references.append(row)
            if not target.is_file():
                missing.append(row)
        if kind == 'href' and url.fragment:
            fragment = unquote(url.fragment)
            valid = target in pages and fragment in pages[target].ids
            if not valid:
                broken_anchors.append({**row, 'fragment': fragment})

    for path, page in pages.items():
        relative = path.relative_to(root).as_posix()
        for identifier, count in Counter(page.ids).items():
            if count > 1:
                duplicates.append({'file': relative, 'id': identifier, 'count': count})
        for identifier, line, kind in page.idrefs:
            if identifier not in page.ids:
                broken_idrefs.append({'file': relative, 'line': line, 'id': identifier, 'kind': kind})
        for reference, line, kind in page.references:
            check_reference(path, reference, line, kind)
    for path in files:
        if path.suffix.lower() not in {'.css', '.js', '.mjs'}:
            continue
        source = path.read_text(encoding='utf-8-sig')
        if path.suffix.lower() == '.css':
            for match in re.finditer(r'url\(\s*[\'\"]?([^)\'\"]+)[\'\"]?\s*\)', source):
                check_reference(path, match.group(1).strip(), source.count('\n', 0, match.start()) + 1, 'css-url')
            for match in re.finditer(r'@import\s+[\'\"]([^\'\"]+)[\'\"]', source):
                check_reference(path, match.group(1), source.count('\n', 0, match.start()) + 1, 'css-import')
        else:
            # 删除注释，以免将 JSDoc 类型 import 算作运行时模块依赖。
            executable = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
            executable = re.sub(r'^\s*//.*$', '', executable, flags=re.M)
            imports = list(re.finditer(r'\b(?:import|export)\s+[^;]*?\bfrom\s*[\'\"]([^\'\"]+)[\'\"]', executable))
            imports += list(re.finditer(r'\bimport\s*(?:\(\s*)?[\'\"]([^\'\"]+)[\'\"]', executable))
            for match in imports:
                check_reference(path, match.group(1), executable.count('\n', 0, match.start()) + 1, 'es-module-import')
    checks.append({'name': 'local_resources_and_es_module_imports_exist', 'passed': not missing})
    checks.append({'name': 'ids_and_explicit_fragments_and_accessible_idrefs_valid', 'passed': not duplicates and not broken_anchors and not broken_idrefs})

    navigation = []
    for path, page in sorted(pages.items()):
        workshops = [link for link in page.primary_nav if link['text'] == 'AI戏韵工坊']
        valid = len(workshops) == 1 and workshops[0]['href'] == 'about.html#ai-workshop' and 'ai-workshop' in pages[root / 'about.html'].ids
        navigation.append({'file': path.name, 'workshop_links': workshops, 'passed': valid})
    checks.append({'name': 'all_eight_primary_navigation_workshop_entries_valid', 'passed': len(navigation) == 8 and all(row['passed'] for row in navigation)})

    js_paths = [path for path in files if path.suffix.lower() in {'.js', '.mjs'}]
    unsafe_patterns = {
        'network_operation': r'\b(?:fetch\s*\(|XMLHttpRequest|WebSocket|EventSource|axios)|navigator\s*\.\s*sendBeacon',
        'timer_simulation': r'\bset(?:Timeout|Interval)\s*\(',
        'api_secret_shape': r'\bsk-[A-Za-z0-9_-]{20,}|(?:api[_-]?key|secret|token)\s*[:=]\s*[\'\"][A-Za-z0-9_-]{16,}',
        'unsafe_html_write': r'\.(?:innerHTML|outerHTML)\s*=|\binsertAdjacentHTML\s*\(|\beval\s*\(',
        'assistant_message_creation': r'(?:messageRole\s*=\s*[\'\"]assistant|data-message-role\s*=\s*[\'\"]assistant)',
    }
    findings = []
    for path in js_paths:
        source = path.read_text(encoding='utf-8-sig')
        for name, pattern in unsafe_patterns.items():
            for match in re.finditer(pattern, source, re.I):
                findings.append({'file': path.relative_to(root).as_posix(), 'kind': name, 'line': source.count('\n', 0, match.start()) + 1})
    services = (root / 'js/ai-workshop/services.js').read_text(encoding='utf-8-sig')
    contracts = (root / 'js/ai-workshop/contracts.js').read_text(encoding='utf-8-sig')
    capabilities = re.search(r'export const SERVICE_CAPABILITIES = Object\.freeze\(\{(.*?)\}\);', contracts, re.S)
    unavailable = bool(capabilities) and len(re.findall(r'\w+:\s*false\b', capabilities.group(1))) == 4 and ': true' not in capabilities.group(1)
    adapter_capabilities = re.findall(r"return unavailable\('([^']+)'\);", services)
    strict_adapters = sorted(adapter_capabilities) == sorted(['questionAnswering', 'agentWorkflow', 'conceptImage', 'imageToModel'])
    qa_notice = '京剧AI知识问答正在建设中，将在Phase 2接入私有知识库。' in contracts
    safety = {'javascript_files_reviewed': [path.relative_to(root).as_posix() for path in js_paths], 'pattern_findings': findings, 'all_four_capabilities_false': unavailable, 'all_four_adapters_explicitly_unavailable': strict_adapters, 'exact_qa_notice_present': qa_notice, 'source_review': 'Reviewed main.js, contracts.js and services.js. They render user text/local drafts and unavailable notices only; no assistant answer, citation data, workflow progress or model output is generated. This is static review, not a browser execution claim.'}
    checks.append({'name': 'frontend_ai_service_boundary_and_text_rendering', 'passed': not findings and unavailable and strict_adapters and qa_notice})

    result = {
        'timestamp': datetime.now(timezone(timedelta(hours=8))).isoformat(),
        'scope': 'Static source regression only. No browser, resource decoding or runtime interaction pass is asserted.',
        'source_root': str(root), 'backup_root': str(backup),
        'excluded_directories': ['.git', 'docs'],
        'execution': {'script': str(Path(__file__).resolve()), 'script_sha256': digest(Path(__file__)), 'python': sys.executable, 'arguments': [str(root), str(backup), str(arguments.output.resolve())]},
        'overall_static_passed': all(check['passed'] for check in checks),
        'checks': checks,
        'asset_preservation': preservation,
        'old_css_preservation': old_css,
        'cultural_main_preservation': body_results,
        'reference_audit': {'html_page_count': len(pages), 'local_file_reference_count': len(references), 'es_module_import_count': sum(row['kind'] == 'es-module-import' for row in references), 'references': references, 'external_references': external_references, 'missing_local_files': missing, 'broken_explicit_anchors': broken_anchors, 'duplicate_ids': duplicates, 'broken_accessible_idrefs': broken_idrefs},
        'primary_navigation': navigation,
        'service_safety': safety,
        'source_snapshot': [{'file': path.relative_to(root).as_posix(), 'sha256': digest(path)} for path in files if path.suffix.lower() in {'.html', '.css', '.js', '.mjs'}],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'overall_static_passed': result['overall_static_passed'], 'checks': checks, 'assets_checked': sum(len(row['files']) for row in preservation), 'old_css_checked': len(old_css), 'local_file_references': len(references), 'runtime_es_module_imports': result['reference_audit']['es_module_import_count'], 'missing_resources': missing, 'broken_anchors': broken_anchors, 'duplicate_ids': duplicates, 'broken_idrefs': broken_idrefs, 'output': str(arguments.output.resolve())}, ensure_ascii=False, indent=2))
    return 0 if result['overall_static_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
