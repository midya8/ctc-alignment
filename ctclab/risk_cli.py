"""Audit supplied candidate token-edit risks; do not prune or renormalize the law."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from .prefix_input import loads
from .risk import audit_risk


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output')
    args = parser.parse_args(argv)
    temporary = None
    try:
        if args.output and args.input != '-' and Path(args.input).resolve() == Path(args.output).resolve():
            raise ValueError('Input and output must differ')
        if args.input == '-':
            raw = sys.stdin.buffer.read(65537)
        else:
            with open(args.input, 'rb') as source:
                raw = source.read(65537)
        if len(raw) > 65536:
            raise ValueError('Input exceeds 64KiB')
        report = audit_risk(loads(raw.decode('utf-8')))
        text = json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False) + '\n'
        if args.output:
            target = Path(args.output)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                             prefix='.ctc-risk-', delete=False) as output:
                temporary = output.name
                output.write(text)
            os.replace(temporary, target)
            temporary = None
        else:
            sys.stdout.write(text)
        return 0
    except (ValueError, TypeError, OSError, UnicodeError, RecursionError, OverflowError) as error:
        print('ctclab-risk: ' + str(error), file=sys.stderr)
        return 2
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


if __name__ == '__main__':
    raise SystemExit(main())
