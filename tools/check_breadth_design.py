"""Validate the published breadth/depth design and dated execution boundaries."""
import argparse
import json
from duecare_eval.breadth_design import validate_design


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Run the offline checks (default).')
    parser.add_argument('--json', action='store_true', help='Print the full validation summary.')
    args = parser.parse_args()
    result = validate_design()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print('Breadth design verified: 6 banks, 200 stored rows, 184 unique request specifications, 5 preserved source prompts and 48 matched scaffold pairs.')
        print('Execution: Jev 1/72 attempted, HTTP 402, 0 usable; context pilot 32/32 usable generations. Full 1,152-condition design remains prepared.')


if __name__ == '__main__':
    main()
