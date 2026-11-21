"""Package-level guarantees: public API, version, and no tkinter on import."""

import subprocess
import sys
from importlib import metadata
from pathlib import Path

import pytest

import pdfcore

SRC = str(Path(__file__).resolve().parent.parent / "src")


def _run_python(code: str) -> subprocess.CompletedProcess:
    """Run ``code`` in a fresh interpreter (so sys.modules starts clean),
    with this checkout's src/ importable."""
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True,
        env={"PYTHONPATH": SRC, "PATH": "/usr/bin:/bin"},
    )


@pytest.mark.parametrize("module", ["pdfcore", "pdfcore.frozen"])
def test_importing_does_not_import_tkinter(module):
    """configure_bundled_tcl_tk() must run before tkinter is imported, so
    neither the package nor pdfcore.frozen may pull tkinter in."""
    result = _run_python(
        f"import sys, {module}; "
        "print('tkinter' in sys.modules or '_tkinter' in sys.modules)"
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_public_api_is_exported():
    for name in pdfcore.__all__:
        assert hasattr(pdfcore, name), name


def test_version_looks_like_semver():
    parts = pdfcore.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)


def test_installed_metadata_matches_version():
    try:
        installed = metadata.version("pdfcore")
    except metadata.PackageNotFoundError:
        pytest.skip("pdfcore isn't pip-installed in this environment")
    assert installed == pdfcore.__version__
