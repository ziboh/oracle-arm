import argparse
import json
import sys
from pathlib import Path

from .instance import InstanceSpec
from .provisioner import Provisioner
from .settings import TaskSettings


def main():
    parser = argparse.ArgumentParser(description="Create an OCI Ampere A1 instance")
    parser.add_argument("instance_file", type=Path)
    parser.add_argument(
        "--settings-stdin",
        action="store_true",
        help="Read task settings from stdin so notification credentials are not written to disk",
    )
    args = parser.parse_args()
    values = json.loads(args.instance_file.read_text(encoding="utf-8"))
    if not args.settings_stdin:
        parser.error("--settings-stdin is required")
    settings = json.loads(sys.stdin.read())
    Provisioner(InstanceSpec.from_dict(values), TaskSettings.from_dict(settings)).run()


if __name__ == "__main__":
    main()
