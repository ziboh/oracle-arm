# Contributing

Thanks for helping improve A1 Control.

## Development

1. Create a Python 3.10+ virtual environment.
2. Install development dependencies with `pip install -e ".[dev]"`.
3. Run `python -m pytest -q` before opening a pull request.

Please keep changes focused, add regression tests for behavior changes, and do not commit OCI credentials, private keys, `data/`, `.env` files, or generated build artifacts.

## Pull requests

Describe the user-facing change, security impact, and verification performed. UI changes should include a short description of the affected screen; automated UI testing is not required by this project.
