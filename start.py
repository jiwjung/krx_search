"""Entry point for running the KRX stock search CLI."""

import importlib.util
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
REQUIRED_MODULES = {
    "prompt_toolkit": "prompt_toolkit",
    "pandas": "pandas",
    "requests": "requests",
    "lxml": "lxml",
}


def main():
    """Check runtime dependencies and start the interactive application."""
    missing = [
        package
        for module, package in REQUIRED_MODULES.items()
        if importlib.util.find_spec(module) is None
    ]
    if missing:
        print("필수 패키지가 설치되어 있지 않습니다: " + ", ".join(missing))
        print(f'다음 명령으로 설치한 뒤 다시 실행하세요: "{sys.executable}" -m pip install -r "{PROJECT_DIR / "requirements.txt"}"')
        return 1

    # Make imports independent of the shell's current working directory.
    sys.path.insert(0, str(PROJECT_DIR))
    from main import main as run_cli

    run_cli()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
