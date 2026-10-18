"""PRIVATE TEST RUNNER ONLY: never import this from production.

Run in a fresh process. It does not expose a production quota override.
All configuration changes are process-local and precede pytest collection.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import importlib
import io
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

sys.dont_write_bytecode = True
BOOTSTRAP = Path(__file__).resolve()
REPO = Path.cwd().resolve()
WORKSPACE = REPO.parent
REAL_RUNTIME = WORKSPACE / ".runtime"
REAL_PRIVATE = WORKSPACE / ".private-config"


class IsolationViolation(RuntimeError):
    """A fixed message never includes a path, credential, or request URL."""


def within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def parse_arguments():
    parser = argparse.ArgumentParser(description="Private Phase 5 WP1 offline pytest isolation.")
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--junitxml", required=True, type=Path)
    parser.add_argument("--basetemp", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    run_root, junit, basetemp = (p.resolve() for p in (args.run_root, args.junitxml, args.basetemp))
    if not (REPO / "backend/tests/conftest.py").is_file():
        raise IsolationViolation("OFFLINE_REPOSITORY_NOT_FOUND")
    if (not within(run_root, REAL_RUNTIME.resolve()) or run_root == REAL_RUNTIME.resolve()
            or not run_root.name.startswith("phase5-wp1-") or run_root.exists()):
        raise IsolationViolation("OFFLINE_RUN_ROOT_MUST_BE_NEW_PRIVATE_DIRECTORY")
    if not within(basetemp, run_root) or basetemp == run_root:
        raise IsolationViolation("OFFLINE_BASETEMP_MUST_BE_INSIDE_RUN_ROOT")
    if (junit.suffix.lower() != ".xml" or junit.exists()
            or not within(junit, run_root)):
        raise IsolationViolation("OFFLINE_JUNIT_DESTINATION_INVALID")
    if any(name in sys.modules for name in (
        "backend.app.config", "backend.app.main", "backend.app.providers.neural4d"
    )):
        raise IsolationViolation("OFFLINE_FRESH_PROCESS_REQUIRED")

    run_root.mkdir(parents=True, exist_ok=False)
    (run_root / "tmp").mkdir()
    (run_root / "workspace").mkdir()
    junit.parent.mkdir(parents=True, exist_ok=True)
    empty_env = run_root / "empty.env"
    empty_env.write_text("# Offline test runner: intentionally contains no credentials.\n", encoding="utf-8")

    # Delete matching names without reading/copying any inherited secret values.
    prefixes = ("DEEPSEEK_", "NEURAL4D_", "RAG_", "AGENT_", "EMBEDDING_")
    for name in list(os.environ):
        if name.upper().startswith(prefixes) or name.upper() in {
            "ALLOWED_ORIGINS", "REQUEST_TIMEOUT_SECONDS", "RETRIEVAL_MIN_SCORE",
            "RETRIEVAL_TOP_K", "RETRIEVAL_MODE"
        }:
            os.environ.pop(name, None)
    os.environ.update({
        "XIJING_ENV_FILE": str(empty_env),
        "RAG_DATA_DIR": str(run_root / "runtime"),
        "EMBEDDING_MODEL_PATH": str(run_root / "unavailable-local-model"),
        "DEEPSEEK_API_KEY": "",
        "NEURAL4D_API_KEY": "",
        "NEURAL4D_ADMIN_TOKEN": "",
        "NEURAL4D_GENERATION_ENABLED": "false",
        "NEURAL4D_PROTOCOL_VERIFIED": "false",
        "NEURAL4D_DOWNLOAD_HOSTS": "[]",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_DATASETS_OFFLINE": "1",
        "TEMP": str(run_root / "tmp"),
        "TMP": str(run_root / "tmp"),
        "TMPDIR": str(run_root / "tmp"),
    })
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(name, None)
    os.chdir(REPO)
    sys.path.insert(0, str(REPO))

    audit_counts = {"blockedFileAccess": 0, "blockedSqlite": 0, "blockedRealHttp": 0}
    guard_diagnostics = []

    def normal_path(value):
        if isinstance(value, int):
            return None
        try:
            return Path(os.fsdecode(value)).resolve()
        except (TypeError, ValueError, OSError):
            return None

    def permitted_write(path):
        return within(path, run_root) or path == junit

    def safe_label(value):
        value = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", str(value))
        return re.sub(r"[^A-Za-z0-9_.()<> -]", "_", value)[:120]

    def record_guard(event, path=None, writing=False):
        # No values from environment, HTTP headers, URLs or exception text.
        if path is None:
            category, name = "network-transport", "not-recorded"
        elif within(path, REAL_PRIVATE.resolve()):
            category, name = "production-private-config", "<private-file>"
        elif within(path, run_root):
            category, name = "isolated-run-root", safe_label(path.name)
        elif path == BOOTSTRAP:
            category, name = "private-helper", safe_label(path.name)
        elif within(path, REAL_RUNTIME.resolve()):
            category, name = "other-production-runtime", safe_label(path.name)
        elif within(path, REPO):
            category, name = "repository", safe_label(path.name)
        else:
            category, name = "external", safe_label(path.name)
        frames = []
        frame = sys._getframe(1)
        for _ in range(8):
            if frame is None:
                break
            frames.append({
                "file": safe_label(Path(frame.f_code.co_filename).name),
                "function": safe_label(frame.f_code.co_name),
                "line": frame.f_lineno,
            })
            frame = frame.f_back
        if len(guard_diagnostics) < 100:
            guard_diagnostics.append({
                "event": event, "category": category, "basename": name,
                "writing": bool(writing), "frames": frames,
            })

    def guard_file(value, writing=False, event="open"):
        path = normal_path(value)
        if path is None:
            return
        private = within(path, REAL_PRIVATE.resolve())
        other_runtime = within(path, REAL_RUNTIME.resolve()) and not within(path, run_root) and path != BOOTSTRAP
        if private or other_runtime or (writing and not permitted_write(path)):
            audit_counts["blockedFileAccess"] += 1
            record_guard(event, path, writing)
            raise IsolationViolation("OFFLINE_FILE_BOUNDARY_BLOCKED")

    def audit(event, values):
        if event == "open":
            mode = values[1] if len(values) > 1 else None
            flags = values[2] if len(values) > 2 else 0
            writing = bool(isinstance(mode, str) and any(c in mode for c in "wax+"))
            writing |= bool(isinstance(flags, int) and flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            ))
            guard_file(values[0], writing, event)
        elif event == "sqlite3.connect":
            value = values[0]
            if value == ":memory:":
                return
            if isinstance(value, str) and value.startswith("file:"):
                value = unquote(urlsplit(value).path)
                if re.match(r"^/[A-Za-z]:", value):
                    value = value[1:]
            path = normal_path(value)
            if path is None or not within(path, run_root):
                audit_counts["blockedSqlite"] += 1
                record_guard(event, path, True)
                raise IsolationViolation("OFFLINE_SQLITE_BOUNDARY_BLOCKED")
        elif event in ("os.mkdir", "os.remove", "os.rmdir", "os.chmod", "os.utime"):
            guard_file(values[0], True, event)
        elif event in ("os.rename", "os.link"):
            guard_file(values[0], event == "os.rename", event)
            guard_file(values[1], True, event)
        elif event == "os.symlink":
            guard_file(values[1], True, event)

    # JUnit asks platform.platform() at finalization; prime its standard-library
    # metadata cache before the file guard, avoiding subprocess DEVNULL writes.
    # This OS metadata lookup does not load app/config or use any network.
    import platform
    platform.platform()

    sys.addaudithook(audit)

    # This module has no app/DB initialization; env_file is already isolated.
    config = importlib.import_module("backend.app.config")
    if config.PRIVATE_ENV.resolve() != empty_env.resolve():
        raise IsolationViolation("OFFLINE_ENV_REDIRECTION_FAILED")
    config.WORKSPACE_ROOT = (run_root / "workspace").resolve()
    isolated_settings = config.Settings()
    if (isolated_settings.rag_data_dir.resolve() != (run_root / "runtime").resolve()
            or isolated_settings.embedding_model_path.resolve() != (run_root / "unavailable-local-model").resolve()
            or isolated_settings.deepseek_api_key.get_secret_value()
            or isolated_settings.neural4d_api_key.get_secret_value()
            or isolated_settings.neural4d_admin_token.get_secret_value()
            or isolated_settings.neural4d_generation_enabled
            or isolated_settings.neural4d_protocol_verified):
        raise IsolationViolation("OFFLINE_SETTINGS_ISOLATION_FAILED")

    import httpx

    def deny_real_sync(*unused_args, **unused_kwargs):
        audit_counts["blockedRealHttp"] += 1
        record_guard("httpx-real-transport")
        raise IsolationViolation("OFFLINE_REAL_HTTP_TRANSPORT_BLOCKED")

    async def deny_real_async(*unused_args, **unused_kwargs):
        audit_counts["blockedRealHttp"] += 1
        record_guard("httpx-real-transport")
        raise IsolationViolation("OFFLINE_REAL_HTTP_TRANSPORT_BLOCKED")

    # The transport boundaries, not AsyncClient.request, are blocked. Explicit
    # MockTransport/custom no-network test doubles continue to exercise contracts.
    httpx.HTTPTransport.handle_request = deny_real_sync
    httpx.AsyncHTTPTransport.handle_async_request = deny_real_async
    app_module = importlib.import_module("backend.app.main")
    provider_module = importlib.import_module("backend.app.providers.neural4d")
    expected_ledger = config.WORKSPACE_ROOT / ".runtime/neural4d-usage.sqlite3"
    if not (app_module.USAGE_LEDGER_PATH.resolve() == expected_ledger.resolve()
            == provider_module.CANONICAL_USAGE_LEDGER.resolve()
            and within(expected_ledger.resolve(), run_root)):
        raise IsolationViolation("OFFLINE_CANONICAL_PATHS_DISAGREE")

    import pytest

    class Summary:
        def __init__(self):
            self.passed = self.failed = self.skipped = self.collection_errors = 0
            self.failed_nodes = []

        def pytest_runtest_logreport(self, report):
            if report.when == "call" and report.passed:
                self.passed += 1
            if report.failed:
                self.failed += 1
                self.failed_nodes.append(report.nodeid)
            if report.skipped:
                self.skipped += 1

        def pytest_collectreport(self, report):
            if report.failed:
                self.collection_errors += 1
                self.failed_nodes.append(report.nodeid)

    def redact(text):
        for path in (run_root, REPO, WORKSPACE):
            text = text.replace(str(path), "<isolated-path>")
            text = text.replace(str(path).replace("\\", "/"), "<isolated-path>")
        text = re.sub(r"(?i)\b[A-Z]:[\\/][^\r\n<>]*", "<absolute-path>", text)
        text = re.sub(r"\bsk-[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", text)
        return text

    summary = Summary()
    buffer = io.StringIO()
    pytest_exit_code = None
    bootstrap_exit_code = 3
    runner_error = None
    try:
        with redirect_stdout(buffer), redirect_stderr(buffer):
            pytest_exit_code = int(pytest.main([
                str(REPO / "backend/tests"), "-q", "--tb=short",
                "-p", "no:cacheprovider", "-o", f"log_file={run_root / 'pytest.log'}",
                f"--basetemp={basetemp}", f"--junitxml={junit}"
            ], plugins=[summary]))
        bootstrap_exit_code = pytest_exit_code
    except BaseException as error:
        # Pytest/framework cleanup can raise before pytest.main returns. A
        # missing pytest exit code stays null, never rewritten as a pass.
        runner_error = {"type": type(error).__name__,
                        "code": str(error) if isinstance(error, IsolationViolation)
                        else "PYTEST_RUNNER_EXCEPTION"}
        bootstrap_exit_code = 130 if isinstance(error, KeyboardInterrupt) else 3
    finally:
        result = {
            "kind": "OFFLINE_TEST_PROCESS_ISOLATION",
            "pytestReturned": pytest_exit_code is not None,
            "pytestExitCode": pytest_exit_code,
            "bootstrapExitCode": bootstrap_exit_code,
            "runnerError": runner_error,
            "scope": "Explicit test doubles and temporary stores only; not live provider or browser evidence.",
            "isolation": {
                "freshProcess": True,
                "emptyPrivateEnv": True,
                "emptyProviderKeys": True,
                "realGenerationDisabled": True,
                "temporaryRagAndModelPaths": True,
                "moduleLevelAppIsolatedBeforeCollection": True,
                "canonicalLedgerPathsAgreeInsideRunRoot": True,
                "realHttpTransportsDenied": True,
                "mockTransportsPermitted": True,
                "productionFilesAndSqliteGuarded": True,
                "externalPytestPluginAutoloadDisabled": True,
            },
            "passed": summary.passed,
            "failedReports": summary.failed,
            "skippedReports": summary.skipped,
            "collectionErrors": summary.collection_errors,
            "failedNodes": [redact(value) for value in summary.failed_nodes],
            "auditCounts": audit_counts,
            "guardDiagnostics": guard_diagnostics,
            "outputs": {"junit": junit.name, "terminal": "pytest-output.redacted.txt"},
        }
        (run_root / "pytest-output.redacted.txt").write_text(redact(buffer.getvalue()), encoding="utf-8")
        (run_root / "isolation-result.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, ensure_ascii=False))
    return bootstrap_exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IsolationViolation as error:
        print(json.dumps({"kind": "OFFLINE_ISOLATION_FAILED", "code": str(error)}, ensure_ascii=False))
        raise SystemExit(3)
    except Exception as error:
        print(json.dumps({"kind": "OFFLINE_BOOTSTRAP_FAILED", "errorType": type(error).__name__}, ensure_ascii=False))
        raise SystemExit(3)


