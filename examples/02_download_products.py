#!/usr/bin/env python3
"""Preview the sample session; add --download to download, or --all for the full dataset."""
import argparse
from calvaldataset import CATEGORIES
from calvaldataset.cli import main as calval_main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--category', choices=CATEGORIES, default='image_quality')
    parser.add_argument('--location', default='BAOT')
    parser.add_argument('--session', default='Session1')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--unzip', action='store_true')
    parser.add_argument('--data-dir')
    parser.add_argument('--config')
    args = parser.parse_args()
    command = ['download', '--all'] if args.all else ['download', '--category', args.category, '--site', args.location, '--session', args.session]
    if not args.download:
        command.append('--dry-run')
    if args.unzip:
        command.append('--unzip')
    for option in ('data-dir', 'config'):
        value = getattr(args, option.replace('-', '_'))
        if value:
            command.extend(['--' + option, value])
    return calval_main(command)


if __name__ == '__main__':
    raise SystemExit(main())
