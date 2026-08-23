#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from arena_common import harness_self_test, load_world


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("world", type=Path)
    args = parser.parse_args()
    print(json.dumps(harness_self_test(load_world(args.world)), indent=2))


if __name__ == "__main__":
    main()
