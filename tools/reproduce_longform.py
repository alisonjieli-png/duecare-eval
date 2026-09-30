"""Recompute the main report's original-case counts entirely offline."""
import argparse
import json
from pathlib import Path
from duecare_eval.longform_report import reproduce, readable_text

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    findings=reproduce(ROOT)
    path=ROOT/'results/longform_readable_findings_2026-09-30.json'
    if args.check:
        if findings!=json.loads(path.read_text()):
            raise SystemExit('Original-case report counts differ from the recorded review')
    else:
        path.write_text(json.dumps(findings,indent=2)+'\n')
    print(readable_text(findings))


if __name__=='__main__':
    main()
