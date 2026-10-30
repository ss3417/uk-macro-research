"""Tests for the UK CPI data processing module."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from src import process_cpi


DATE_COLUMN = "Title"
VALUE_COLUMN = "CPI-CT percentage change over 12 months: all items"


def make_raw_data(rows: list[tuple[str, str | None]]) -> pl.DataFrame:
    """Build a small ONS-shaped dataset for isolated cleaning tests."""
    return pl.DataFrame(
        {
            DATE_COLUMN: [date_label for date_label, _ in rows],
            VALUE_COLUMN: [value for _, value in rows],
        },
        schema={DATE_COLUMN: pl.String, VALUE_COLUMN: pl.String},
    )


def test_clean_data_selects_expected_columns_and_parses_dates_chronologically() -> None:
    raw_data = make_raw_data(
        [
            ("2001 MAR", "2.5"),
            ("CDID", "EAD6"),
            ("2000", "1.0"),
            ("2000 Q1", "1.2"),
            ("2001 JAN", "1.5"),
        ]
    )

    cleaned = process_cpi.clean_cpi_data(raw_data)

    assert cleaned.columns == ["date", "cpi_inflation_percent"]
    assert cleaned.get_column("date").to_list() == [
        date(2001, 1, 1),
        date(2001, 3, 1),
    ]
    assert cleaned.get_column("date").to_list() == sorted(
        cleaned.get_column("date").to_list()
    )


def test_clean_data_drops_missing_values_without_filling_them() -> None:
    raw_data = make_raw_data(
        [
            ("2000 JAN", "1.0"),
            ("2000 FEB", None),
            ("2000 MAR", ".."),
            ("2000 APR", "N/A"),
            ("2000 MAY", "1.4"),
        ]
    )

    cleaned = process_cpi.clean_cpi_data(raw_data)

    assert cleaned.get_column("date").to_list() == [
        date(2000, 1, 1),
        date(2000, 5, 1),
    ]
    assert cleaned.get_column("cpi_inflation_percent").to_list() == [1.0, 1.4]


def test_clean_data_rejects_invalid_month_label() -> None:
    raw_data = make_raw_data([("2000 XYZ", "1.0")])

    with pytest.raises(ValueError, match="invalid monthly date label"):
        process_cpi.clean_cpi_data(raw_data)


def test_clean_data_rejects_invalid_inflation_value() -> None:
    raw_data = make_raw_data([("2000 JAN", "not-a-number")])

    with pytest.raises(ValueError, match="Could not parse CPI values"):
        process_cpi.clean_cpi_data(raw_data)


def test_clean_data_rejects_missing_required_columns() -> None:
    raw_data = pl.DataFrame({"date": ["2000 JAN"], "value": ["1.0"]})

    with pytest.raises(ValueError, match="missing required columns"):
        process_cpi.clean_cpi_data(raw_data)


def test_clean_data_values_are_numeric() -> None:
    cleaned = process_cpi.clean_cpi_data(make_raw_data([("2000 JAN", "1.25")]))

    assert cleaned.schema["cpi_inflation_percent"] == pl.Float64
    assert cleaned.get_column("cpi_inflation_percent").to_list() == [1.25]


def test_main_does_not_modify_raw_dataset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = tmp_path
    source_path = project_root / "data" / "raw" / "uk_cpi.csv"
    source_path.parent.mkdir(parents=True)
    original_content = (
        f'"{DATE_COLUMN}","{VALUE_COLUMN}"\n'
        '"2000 FEB","1.2"\n'
        '"2000 JAN","1.0"\n'
    ).encode()
    source_path.write_bytes(original_content)

    fake_module_path = project_root / "src" / "process_cpi.py"
    monkeypatch.setattr(process_cpi, "__file__", str(fake_module_path))

    process_cpi.main()

    output_path = project_root / "data" / "processed" / "uk_cpi_clean.csv"
    output = pl.read_csv(output_path, try_parse_dates=True)
    assert source_path.read_bytes() == original_content
    assert output.get_column("date").to_list() == [date(2000, 1, 1), date(2000, 2, 1)]


def test_load_raw_data_reports_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="Raw CPI dataset not found"):
        process_cpi.load_raw_data(missing_path)


def test_invalid_input_file_schema_is_reported(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.csv"
    invalid_path.write_text('"period","inflation"\n"2000 JAN","1.0"\n', encoding="utf-8")

    raw_data = process_cpi.load_raw_data(invalid_path)

    with pytest.raises(ValueError, match="missing required columns"):
        process_cpi.clean_cpi_data(raw_data)
