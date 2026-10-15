import pytest

from app.data.local import LocalRepo

from .conftest import write_world


def test_live_stock_is_last_day_closing_stock(world):
    assert world.get_stock("S02", "SKU-0001") == 40  # not 999 from the older row
    assert world.get_stock("S01", "SKU-0002") == 8


def test_hero_scenario_starts_with_empty_shelf(world):
    # simulator baseline has 22+ units; the demo scenario forces the shelf empty
    assert world.get_stock("S01", "SKU-0001") == 0


def test_set_stock_and_reset(world):
    world.set_stock("S01", "SKU-0001", 60)
    assert world.get_stock("S01", "SKU-0001") == 60
    world.reset_live_stock()
    assert world.get_stock("S01", "SKU-0001") == 0


def test_set_stock_rejects_unknown_pair_and_clamps_negative(world):
    with pytest.raises(KeyError):
        world.set_stock("S99", "SKU-0001", 1)
    world.set_stock("S02", "SKU-0001", -5)
    assert world.get_stock("S02", "SKU-0001") == 0


def test_unknown_pair_is_none(world):
    assert world.get_stock("S01", "SKU-9999") is None


def test_stock_by_store(world):
    assert world.stock_by_store("SKU-0001") == {"S01": 0, "S02": 40, "S03": 12}


def test_distance_is_symmetric_and_zero_to_self(world):
    assert world.distance_km("S01", "S02") == world.distance_km("S02", "S01") == 21
    assert world.distance_km("S03", "S03") == 0
    assert world.distance_km("S01", "S99") is None


def test_missing_stock_csv_explains_how_to_fix(tmp_path):
    root = write_world(tmp_path)
    (root / "out" / "stock_events.csv").unlink()
    with pytest.raises(FileNotFoundError, match="make sim"):
        LocalRepo(root)
