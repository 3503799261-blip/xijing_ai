"""Trusted one-time CLI reconciliation; never execute without verified user history."""
import argparse
import json
from ..app.config import WORKSPACE_ROOT
from ..app.assets.usage import UsageManager


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--used-attempts', type=int, choices=range(4), required=True)
    parser.add_argument('--note', required=True, help='Actual user/supplier reconciliation evidence, no keys.')
    parser.add_argument('--acknowledge-project-history', action='store_true', required=True)
    args = parser.parse_args()
    manager = UsageManager(WORKSPACE_ROOT / '.runtime/neural4d-usage.sqlite3')
    print(json.dumps(manager.initialize_history(args.used_attempts, args.note), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
