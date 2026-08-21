from __future__ import annotations

from pathlib import Path

from glucose_widget.state import StateStore, WindowState


def test_state_round_trip(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state.json")
    store.save(WindowState(x=10, y=20, locked=True))
    assert store.load() == WindowState(x=10, y=20, locked=True)
