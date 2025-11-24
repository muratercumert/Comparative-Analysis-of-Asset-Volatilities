"""requirements_helper
Utilities to parse a requirements.txt, map pip package names to import names,
install missing packages into the running Python interpreter, and export pinned
requirements. Designed to be imported from a notebook or script.

Usage:
    from utils.requirements_helper import ensure_requirements, export_requirements
    ensure_requirements()  # reads ./requirements.txt and installs missing packages
    export_requirements()  # create a pinned requirements.txt for a small set
"""
from __future__ import annotations

import os
import sys
import subprocess
from importlib import import_module
from typing import Iterable, List

# Map pip package names to import names when they differ
NAME_MAP = {
    "beautifulsoup4": "bs4",
    "pillow": "PIL",
    "scikit-learn": "sklearn",
    "opencv-python": "cv2",
    "python-dateutil": "dateutil",
}


def parse_requirements_file(filename: str = "requirements.txt") -> List[str]:
    """Return a list of non-comment, non-empty requirement spec strings.

    Lines starting with `#` are ignored. Inline comments after a `#` are trimmed.
    """
    if not os.path.exists(filename):
        return []
    pkgs: List[str] = []
    with open(filename, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # remove inline comments
            line = line.split("#", 1)[0].strip()
            if line:
                pkgs.append(line)
    return pkgs


def get_import_name(pip_spec: str) -> str:
    """Map a pip spec (like `pkg==1.2.3` or `pkg[extra]>=1.0`) to an importable name.

    Uses NAME_MAP for common exceptions.
    """
    s = pip_spec
    for sep in ("==", ">=", "<=", "~=", ">", "<", "!=", "===", "@"):
        if sep in s:
            s = s.split(sep)[0]
            break
    if "[" in s:
        s = s.split("[")[0]
    name = s.strip()
    return NAME_MAP.get(name, name)


def ensure_requirements(filename: str = "requirements.txt", auto_install: bool = True) -> None:
    """Read `filename`, check imports for each package and install missing ones.

    This installs using the running Python interpreter (`sys.executable -m pip install ...`),
    so it will target the kernel/environment that's executing the code (good for notebooks).
    """
    pkgs = parse_requirements_file(filename)
    if not pkgs:
        print(f"No requirements found in {filename}.")
        return

    for spec in pkgs:
        import_name = get_import_name(spec)
        try:
            import_module(import_name)
            print(f"OK: {import_name} (from '{spec}')")
        except Exception:
            print(f"MISSING: {import_name} — installing '{spec}' using {sys.executable}")
            if auto_install:
                subprocess.check_call([sys.executable, "-m", "pip", "install", spec])
                try:
                    import_module(import_name)
                    print(f"Installed and import OK: {import_name}")
                except Exception as e2:
                    print(f"Installed but import still failing for {import_name}:", e2)
            else:
                print("auto_install is False; skipping installation")


def export_requirements(
    packages: Iterable[str] | None = None,
    filename: str = "requirements.txt",
    use_freeze: bool = False,
) -> None:
    """Write a requirements file.

    - If `use_freeze` is True, writes the full output of `pip freeze`.
    - Otherwise writes pinned versions for `packages` (default: a small useful set).
    """
    if use_freeze:
        with open(filename, "w", encoding="utf-8") as f:
            subprocess.check_call([sys.executable, "-m", "pip", "freeze"], stdout=f)
        print("Wrote", filename, "via pip freeze")
        return

    if packages is None:
        packages = [
            "yfinance",
            "pandas",
            "numpy",
            "matplotlib",
            "seaborn",
            "requests",
            "beautifulsoup4",
            "scipy",
        ]

    lines: List[str] = []
    for pkg in packages:
        try:
            m = import_module(get_import_name(pkg))
            ver = getattr(m, "__version__", None)
            if not ver:
                # fallback to pkg_resources
                try:
                    import pkg_resources

                    ver = pkg_resources.get_distribution(pkg).version
                except Exception:
                    ver = "unknown"
            lines.append(f"{pkg}=={ver}")
        except Exception as e:
            lines.append(f"# {pkg} not installed: {e}")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("Wrote", filename)


__all__ = ["parse_requirements_file", "get_import_name", "ensure_requirements", "export_requirements"]
