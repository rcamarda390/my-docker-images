#!/usr/bin/env python3
"""Read-only Debian tracker lookup for the shared security ledger."""
import argparse
import json
from pathlib import Path
from urllib.request import urlopen


def review(findings, tracker):
    for finding in findings:
        if all(image['scan_status'] == 'cleared' for image in finding['images'].values()):
            continue
        advisory = tracker.get(finding['source_package'], {}).get(finding['cve'], {})
        release = advisory.get('releases', {}).get(finding['suite'], {})
        yield {
            'cve': finding['cve'],
            'source_package': finding['source_package'],
            'suite': finding['suite'],
            'status': release.get('status', 'UNKNOWN') if finding['suite'] else 'UPSTREAM_REVIEW',
            'fixed_version': release.get('fixed_version'),
            'urgency': release.get('urgency'),
            'no_dsa': release.get('nodsa'),
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tracker-json', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    ledger = json.loads((root / 'docs/security/findings.json').read_text())
    if args.tracker_json:
        tracker = json.loads(args.tracker_json.read_text())
    else:
        with urlopen('https://security-tracker.debian.org/tracker/data/json', timeout=60) as response:
            tracker = json.load(response)
    for row in review(ledger['findings'], tracker):
        print(json.dumps(row, sort_keys=True))


if __name__ == '__main__':
    main()
