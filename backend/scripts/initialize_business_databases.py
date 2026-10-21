"""Explicit first-install business databases; never recreates missing runtime data.

This command creates only Agent, budget and asset stores. It does not create,
reset or reconcile the project-wide Neural4D ledger, ingest knowledge, download
models, contact suppliers or repair any existing partial/corrupt database.
"""
import argparse
import json
from pathlib import Path

from ..app.agents.store import TaskStore, TASK_TABLES, TASK_DATABASE_MESSAGE
from ..app.assets.store import AssetStore, ASSET_TABLES, ASSET_OBJECTS, ASSET_DATABASE_MESSAGE
from ..app.config import Settings
from ..app.database import validate_database
from ..app.providers.budget import BudgetLedger, BUDGET_TABLES, BUDGET_OBJECTS, BUDGET_DATABASE_MESSAGE


def initialize_business_databases(settings):
    root = Path(settings.rag_data_dir).expanduser().resolve()
    planned = [
        ('agent', root / 'agent-tasks.sqlite3', TASK_TABLES, (), 'AGENT_DATABASE_UNAVAILABLE', TASK_DATABASE_MESSAGE),
        ('budget', root / 'api-budget.sqlite3', BUDGET_TABLES, BUDGET_OBJECTS, 'BUDGET_DATABASE_UNAVAILABLE', BUDGET_DATABASE_MESSAGE),
        ('assets', root / 'assets' / 'catalog.sqlite3', ASSET_TABLES, ASSET_OBJECTS, 'ASSET_DATABASE_UNAVAILABLE', ASSET_DATABASE_MESSAGE),
    ]
    # A bad existing store aborts before creating any other missing store.
    existing = {}
    for name, path, tables, objects, code, message in planned:
        existing[name] = path.exists()
        if path.exists():
            validate_database(path, tables, objects=objects, code=code, message=message)
    TaskStore(root / 'agent-tasks.sqlite3', create=True)
    BudgetLedger(root / 'api-budget.sqlite3', settings.rag_test_budget_cny,
                 scope='phase3', scope_limit=settings.agent_test_budget_cny, create=True)
    AssetStore(root / 'assets', create=True)
    return {'status': 'ready', 'stores': {name: 'validated_existing' if existing[name] else 'initialized_new'
                                        for name in existing},
            'neural4dLedger': 'not_created_or_modified', 'knowledge': 'separate_explicit_ingestion_required'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize-new-installation', action='store_true', required=True,
                        help='Explicit confirmation: create missing stores only for a known fresh installation.')
    args = parser.parse_args()
    if not args.initialize_new_installation:
        parser.error('Explicit first-install confirmation is required.')
    print(json.dumps(initialize_business_databases(Settings()), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
