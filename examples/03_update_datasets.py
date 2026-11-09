#!/usr/bin/env python3
"""Preview configured sites; add --run for a live update, optionally with --only LCFR."""
import argparse
from pathlib import Path
from calvaldataset import ensure_workspace, load_sites
from calvaldataset.cli import main as calval_main


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--config')
    parser.add_argument('--personal-sites', type=Path)
    args = parser.parse_args()
    root = ensure_workspace(args.data_dir)
    sites = [s for s in load_sites(root, personal_path=args.personal_sites) if not args.only or args.only.casefold() in (s.name.casefold(), s.location.casefold())]
    if not sites:
        parser.error('Unknown site name or code')
    if not args.run:
        for site in sites:
            print(f'{site.location}: {site.name} -> {", ".join(site.categories)}')
        print('Preview only. Add --run to query Insula and update the catalogues.')
        return 0
    command = ['update', '--site', args.only] if args.only else ['update', '--all']
    command.extend(['--data-dir', str(root)])
    if args.config:
        command.extend(['--config', args.config])
    if args.personal_sites is not None:
        command.extend(['--personal-sites', str(args.personal_sites)])
    return calval_main(command)


if __name__ == '__main__':
    raise SystemExit(main())
