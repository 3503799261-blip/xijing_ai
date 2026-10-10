"""Export safe measured token counts and conservative estimates, never config/key."""
import json
from pathlib import Path
from datetime import datetime, timezone
from backend.app.config import Settings
from backend.app.providers.budget import BudgetLedger

def export():
    settings = Settings()
    ledger = BudgetLedger(settings.rag_data_dir / 'api-budget.sqlite3', settings.rag_test_budget_cny)
    records = ledger.records()
    return {'exportedAt': datetime.now(timezone.utc).isoformat(), 'summary': ledger.summary(), 'records': records, 'measuredTotals': {key: sum((record['usage'] or {}).get(key, 0) for record in records) for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}, 'scope': 'actual backend ledger, failed/unknown reservations included; estimate is not official billing'}

if __name__ == '__main__':
    result = export()
    Path('docs/evidence/test-results/phase-02-api-usage.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['summary'], ensure_ascii=True))
