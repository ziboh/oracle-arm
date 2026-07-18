import argparse
import json
from pathlib import Path

from .instance import InstanceSpec
from .provisioner import Provisioner
from .settings import TaskSettings


def main():
    parser = argparse.ArgumentParser(description="Create an OCI Ampere A1 instance")
    parser.add_argument("instance_file", type=Path)
    args = parser.parse_args()
    values = json.loads(args.instance_file.read_text(encoding="utf-8"))
    Provisioner(InstanceSpec.from_dict(values), TaskSettings.from_env()).run()


if __name__ == "__main__":
    main()
