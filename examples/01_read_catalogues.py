#!/usr/bin/env python3
"""List local metadata using the installed package: python examples/01_read_catalogues.py --site LCFR."""
import sys
from calvaldataset.cli import main

if __name__ == '__main__':
    raise SystemExit(main(['list', *sys.argv[1:]]))
