"""Tests for configure_bundled_tcl_tk (py2app startup fix-up)."""

from pdfcore.frozen import configure_bundled_tcl_tk


def _make_bundle(tmp_path, tcl=True, tk=True):
    if tcl:
        (tmp_path / "tcl" / "tcl8.6").mkdir(parents=True)
    if tk:
        (tmp_path / "tcl" / "tk8.6").mkdir(parents=True)
    return str(tmp_path)


def test_not_frozen_does_nothing(tmp_path):
    env = {"RESOURCEPATH": _make_bundle(tmp_path)}
    assert configure_bundled_tcl_tk(environ=env, frozen=False) is False
    assert "TCL_LIBRARY" not in env
    assert "TK_LIBRARY" not in env


def test_frozen_without_resourcepath_does_nothing():
    env = {}
    assert configure_bundled_tcl_tk(environ=env, frozen=True) is False
    assert env == {}


def test_frozen_points_at_bundled_libraries(tmp_path):
    resources = _make_bundle(tmp_path)
    env = {"RESOURCEPATH": resources}

    assert configure_bundled_tcl_tk(environ=env, frozen=True) is True

    assert env["TCL_LIBRARY"] == str(tmp_path / "tcl" / "tcl8.6")
    assert env["TK_LIBRARY"] == str(tmp_path / "tcl" / "tk8.6")


def test_frozen_skips_missing_directories(tmp_path):
    env = {"RESOURCEPATH": _make_bundle(tmp_path, tk=False),
           "TK_LIBRARY": "/left/alone"}

    assert configure_bundled_tcl_tk(environ=env, frozen=True) is True

    assert env["TCL_LIBRARY"] == str(tmp_path / "tcl" / "tcl8.6")
    assert env["TK_LIBRARY"] == "/left/alone"


def test_defaults_to_real_environment_when_not_frozen(monkeypatch):
    # The test runner isn't frozen, so with no overrides this is a no-op.
    monkeypatch.delenv("TCL_LIBRARY", raising=False)
    assert configure_bundled_tcl_tk() is False
