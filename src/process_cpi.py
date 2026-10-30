"""Clean the ONS UK CPI time series for analysis."""

from pathlib import Path

import polars as pl

DATE_LABEL_COLUMN = "Title"
CPI_VALUE_COLUMN = "CPI-CT percentage change over 12 months: all items"
MONTH_LABEL_PATTERN = r"^\d{4} [A-Z]{3}$"        # See lecture notes for explanation of this regex #


def load_raw_data(raw_path: Path) -> pl.DataFrame:
    """Load the original ONS CSV without changing the source file."""
    if not raw_path.is_file():
        raise FileNotFoundError(f"Raw CPI dataset not found: {raw_path}")

    return pl.read_csv(
        raw_path,
        infer_schema_length=10_000,
        null_values=["", "..", "NA", "N/A"],     # Can this be extended potentially to include other missing value indicators? #
    )


def clean_cpi_data(raw_data: pl.DataFrame) -> pl.DataFrame:
    """Return monthly CPI observations with parsed dates and numeric values.

    ONS metadata, annual summaries, and quarterly summaries are excluded.
    Rows with missing CPI values are dropped; no observations are filled or
    interpolated.
    """
    required_columns = {DATE_LABEL_COLUMN, CPI_VALUE_COLUMN}
    missing_columns = required_columns.difference(raw_data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Raw CPI dataset is missing required columns: {missing}")

    monthly_rows = raw_data.filter(
        pl.col(DATE_LABEL_COLUMN)
        .cast(pl.String)
        .str.strip_chars()
        .str.contains(MONTH_LABEL_PATTERN)
    )
    if monthly_rows.is_empty():
        raise ValueError("Raw CPI dataset contains no monthly observations")

    date_labels = (
        pl.col(DATE_LABEL_COLUMN)
        .cast(pl.String)
        .str.strip_chars()
        .str.replace(r"$", " 01")
    )
    value_labels = pl.col(CPI_VALUE_COLUMN).cast(pl.String).str.strip_chars()
    value_labels = pl.when(value_labels.is_in(["", "..", "NA", "N/A"])).then(
        None
    ).otherwise(value_labels)

    try:
        cleaned = monthly_rows.select(
            date_labels.str.strptime(
                pl.Date,
                format="%Y %b %d",
                strict=False,
            ).alias("date"),
            value_labels.cast(pl.Float64, strict=True).alias(
                "cpi_inflation_percent"
            ),
        )
    except pl.exceptions.PolarsError as exc:
        raise ValueError("Could not parse CPI values from the raw dataset") from exc

    if cleaned.get_column("date").null_count():
        raise ValueError("Raw CPI dataset contains an invalid monthly date label")

    cleaned = cleaned.drop_nulls(subset=["cpi_inflation_percent"]).sort("date")
    if cleaned.is_empty():
        raise ValueError("Raw CPI dataset contains no complete monthly observations")

    return cleaned


def save_clean_data(clean_data: pl.DataFrame, output_path: Path) -> None:
    """Write cleaned CPI observations to a CSV, creating its parent directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_data.write_csv(output_path)


def main() -> None:
    """Process the repository's raw CPI dataset into its processed location."""
    project_root = Path(__file__).resolve().parents[1]
    raw_path = project_root / "data" / "raw" / "uk_cpi.csv"
    output_path = project_root / "data" / "processed" / "uk_cpi_clean.csv"

    if raw_path.resolve() == output_path.resolve():
        raise ValueError("Raw and processed CPI paths must be different")

    raw_data = load_raw_data(raw_path)
    clean_data = clean_cpi_data(raw_data)
    save_clean_data(clean_data, output_path)


if __name__ == "__main__":
    main()
