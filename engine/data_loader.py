"""Load and validate the FIN-DOM sample data (entities.csv and exposures.csv).

Main entry point for the rest of the project:

    entities_df, exposures_df = load_data()

Design goals:
  * Report EVERY problem found in one go, not just the first one, with the
    CSV row number (header = line 1) so you can jump straight to the mistake.
  * Return tables sorted by id, so the order of rows in the CSV files can
    never change a result.
  * Contain no model logic: this module only checks and cleans data.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from engine import params

# data/ folder at the repository root (engine/ is one level below the root).
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ENTITIES_FILENAME = "entities.csv"
EXPOSURES_FILENAME = "exposures.csv"

ENTITY_COLUMNS = [
    "entity_id",
    "name",
    "type",
    "region",
    "total_assets_bn",
    "capital_buffer_bn",
]
EXPOSURE_COLUMNS = [
    "exposure_id",
    "creditor_id",
    "debtor_id",
    "exposure_bn",
    "exposure_type",
]
ENTITY_NUMERIC_COLUMNS = ["total_assets_bn", "capital_buffer_bn"]
EXPOSURE_NUMERIC_COLUMNS = ["exposure_bn"]


class DataValidationError(Exception):
    """Raised when the CSV data breaks one or more rules.

    `problems` is a list of plain-English messages, one per problem found.
    """

    def __init__(self, problems):
        self.problems = list(problems)
        lines = "\n".join(f"  - {p}" for p in self.problems)
        super().__init__(f"{len(self.problems)} data problem(s) found:\n{lines}")


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------

def _row_number(index_value) -> int:
    """Convert a 0-based DataFrame index into the CSV line number.

    Line 1 of the file is the header, so the first data row is line 2.
    (Valid when the frame still has its original 0..n-1 index, which is true
    for frames freshly read from a CSV.)
    """
    return int(index_value) + 2


def _missing_columns(df: pd.DataFrame, columns: list[str], filename: str) -> list[str]:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        return [f"{filename}: missing required column(s): {', '.join(missing)}"]
    return []


def _clean(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Keep only the required columns; turn every value into trimmed text.

    Empty or missing cells become "" so later checks can spot them easily.
    """
    out = df[columns].copy()
    for col in columns:
        out[col] = out[col].where(out[col].notna(), "").astype(str).str.strip()
    return out


def _to_number(series: pd.Series) -> pd.Series:
    """Text -> float. Blank, unparseable and infinite values become NaN."""
    num = pd.to_numeric(series.replace("", np.nan), errors="coerce").astype(float)
    return num.where(np.isfinite(num))


def _check_required_values(clean: pd.DataFrame, columns: list[str], filename: str) -> list[str]:
    problems = []
    for idx in clean.index:
        for col in columns:
            if clean.at[idx, col] == "":
                problems.append(f"{filename}, row {_row_number(idx)}: '{col}' is missing")
    return problems


def _check_unique(
    series: pd.Series, col: str, filename: str, ignore_case: bool = False
) -> list[str]:
    """Report every row whose value was already used on an earlier row."""
    problems = []
    first_seen: dict[str, int] = {}
    for idx, value in series.items():
        if value == "":
            continue  # missing values are reported by _check_required_values
        key = value.lower() if ignore_case else value
        if key in first_seen:
            problems.append(
                f"{filename}, row {_row_number(idx)}: {col} '{value}' "
                f"is a duplicate of row {_row_number(first_seen[key])}"
            )
        else:
            first_seen[key] = idx
    return problems


def _check_allowed(series: pd.Series, col: str, allowed: list[str], filename: str) -> list[str]:
    problems = []
    for idx, value in series.items():
        if value != "" and value not in allowed:
            problems.append(
                f"{filename}, row {_row_number(idx)}: {col} '{value}' "
                f"is not allowed (use one of: {', '.join(allowed)})"
            )
    return problems


def _check_numeric(
    clean: pd.DataFrame, col: str, filename: str
) -> tuple[pd.Series, list[str]]:
    """Convert one column to numbers; report cells that are not valid numbers."""
    numbers = _to_number(clean[col])
    problems = []
    for idx in clean.index:
        if clean.at[idx, col] != "" and np.isnan(numbers[idx]):
            problems.append(
                f"{filename}, row {_row_number(idx)}: {col} "
                f"'{clean.at[idx, col]}' is not a valid number"
            )
    return numbers, problems


# ----------------------------------------------------------------------------
# Rule checks (return a list of problems; they never raise)
# ----------------------------------------------------------------------------

def _check_entities(df: pd.DataFrame) -> list[str]:
    f = ENTITIES_FILENAME
    problems = _missing_columns(df, ENTITY_COLUMNS, f)  # E1
    if problems:
        return problems  # cannot check anything else without the columns
    if len(df) == 0:
        return [f"{f}: the file has no data rows"]

    c = _clean(df, ENTITY_COLUMNS)
    problems += _check_required_values(c, ENTITY_COLUMNS, f)                   # E2
    problems += _check_unique(c["entity_id"], "entity_id", f)                  # E3
    problems += _check_unique(c["name"], "name", f, ignore_case=True)          # E4
    problems += _check_allowed(c["type"], "type", params.ENTITY_TYPES, f)      # E5
    problems += _check_allowed(c["region"], "region", params.REGIONS, f)       # E6

    assets, p = _check_numeric(c, "total_assets_bn", f)                        # E7
    problems += p
    buffers, p = _check_numeric(c, "capital_buffer_bn", f)                     # E7
    problems += p

    for idx in c.index:
        a, b = assets[idx], buffers[idx]
        if not np.isnan(a) and a <= 0:                                         # E8
            problems.append(
                f"{f}, row {_row_number(idx)}: total_assets_bn ({a:g}) must be greater than 0"
            )
        if not np.isnan(b):
            if b <= 0:                                                         # E9
                problems.append(
                    f"{f}, row {_row_number(idx)}: capital_buffer_bn ({b:g}) must be greater than 0"
                )
            elif not np.isnan(a) and b >= a:                                   # E9
                problems.append(
                    f"{f}, row {_row_number(idx)}: capital_buffer_bn ({b:g}) "
                    f"must be less than total_assets_bn ({a:g})"
                )
    return problems


def _check_exposures(df: pd.DataFrame, entities_df: pd.DataFrame) -> list[str]:
    f = EXPOSURES_FILENAME
    problems = _missing_columns(df, EXPOSURE_COLUMNS, f)                       # X1
    if problems:
        return problems
    missing_entity_cols = _missing_columns(entities_df, ENTITY_COLUMNS, ENTITIES_FILENAME)
    if missing_entity_cols:
        return [f"{f}: cannot be checked because the entities table is incomplete"]
    if len(df) == 0:
        return [f"{f}: the file has no data rows"]

    c = _clean(df, EXPOSURE_COLUMNS)

    # Look-up tables built from the entities table.
    ent = _clean(entities_df, ENTITY_COLUMNS)
    ent_assets = _to_number(ent["total_assets_bn"])
    known_ids = {i for i in ent["entity_id"] if i != ""}
    assets_by_id = {
        ent.at[i, "entity_id"]: ent_assets[i]
        for i in ent.index
        if ent.at[i, "entity_id"] != ""
    }

    problems += _check_required_values(c, EXPOSURE_COLUMNS, f)                 # X2
    problems += _check_unique(c["exposure_id"], "exposure_id", f)              # X3
    problems += _check_allowed(c["exposure_type"], "exposure_type",
                               params.EXPOSURE_TYPES, f)                       # X9

    amounts, p = _check_numeric(c, "exposure_bn", f)                           # X7
    problems += p

    seen_pairs: dict[tuple[str, str], int] = {}
    for idx in c.index:
        row = _row_number(idx)
        creditor = c.at[idx, "creditor_id"]
        debtor = c.at[idx, "debtor_id"]

        if creditor != "" and creditor not in known_ids:                       # X4
            problems.append(
                f"{f}, row {row}: creditor_id '{creditor}' not found in entities"
            )
        if debtor != "" and debtor not in known_ids:                           # X4
            problems.append(
                f"{f}, row {row}: debtor_id '{debtor}' not found in entities"
            )
        if creditor != "" and creditor == debtor:                              # X5
            problems.append(
                f"{f}, row {row}: creditor_id and debtor_id are both '{creditor}' "
                f"(an entity cannot be exposed to itself)"
            )
        if creditor != "" and debtor != "" and creditor != debtor:             # X6
            pair = (creditor, debtor)
            if pair in seen_pairs:
                problems.append(
                    f"{f}, row {row}: the link {creditor} -> {debtor} "
                    f"already appears on row {_row_number(seen_pairs[pair])}"
                )
            else:
                seen_pairs[pair] = idx

        amount = amounts[idx]
        if not np.isnan(amount):
            if amount <= 0:                                                    # X7
                problems.append(
                    f"{f}, row {row}: exposure_bn ({amount:g}) must be greater than 0"
                )
            else:
                creditor_assets = assets_by_id.get(creditor, np.nan)
                if not np.isnan(creditor_assets) and amount >= creditor_assets:  # X8
                    problems.append(
                        f"{f}, row {row}: exposure_bn ({amount:g}) must be less than "
                        f"the creditor's total_assets_bn ({creditor_assets:g})"
                    )
    return problems


# ----------------------------------------------------------------------------
# Converting validated data into the final tables
# ----------------------------------------------------------------------------

def _finalize_entities(df: pd.DataFrame) -> pd.DataFrame:
    out = _clean(df, ENTITY_COLUMNS)
    for col in ENTITY_NUMERIC_COLUMNS:
        out[col] = _to_number(out[col])
    return out.sort_values("entity_id", kind="mergesort").reset_index(drop=True)


def _finalize_exposures(df: pd.DataFrame) -> pd.DataFrame:
    out = _clean(df, EXPOSURE_COLUMNS)
    for col in EXPOSURE_NUMERIC_COLUMNS:
        out[col] = _to_number(out[col])
    return out.sort_values("exposure_id", kind="mergesort").reset_index(drop=True)


def _read_csv(path, columns: list[str], filename: str) -> tuple[pd.DataFrame | None, list[str]]:
    """Read a CSV as plain text. Returns (table or None, structural problems)."""
    path = Path(path)
    if not path.is_file():
        return None, [f"{filename}: file not found at {path}"]
    try:
        # utf-8-sig quietly removes the invisible marker Excel adds to CSVs.
        raw = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return None, [f"{filename}: the file is empty"]
    except pd.errors.ParserError as err:
        return None, [f"{filename}: could not be read as a CSV file ({err})"]
    raw.columns = [str(col).strip() for col in raw.columns]
    return raw, _missing_columns(raw, columns, filename)


# ----------------------------------------------------------------------------
# Public functions
# ----------------------------------------------------------------------------

def validate_entities(entities_df: pd.DataFrame) -> None:
    """Check an entities table against rules E1-E9. Raises DataValidationError."""
    problems = _check_entities(entities_df)
    if problems:
        raise DataValidationError(problems)


def validate_exposures(exposures_df: pd.DataFrame, entities_df: pd.DataFrame) -> None:
    """Check an exposures table against rules X1-X9. Raises DataValidationError."""
    problems = _check_exposures(exposures_df, entities_df)
    if problems:
        raise DataValidationError(problems)


def load_entities(path=DATA_DIR / ENTITIES_FILENAME) -> pd.DataFrame:
    """Read and validate entities.csv. Returns a table sorted by entity_id."""
    raw, problems = _read_csv(path, ENTITY_COLUMNS, ENTITIES_FILENAME)
    if not problems:
        problems = _check_entities(raw)
    if problems:
        raise DataValidationError(problems)
    return _finalize_entities(raw)


def load_exposures(path=DATA_DIR / EXPOSURES_FILENAME, entities_df=None) -> pd.DataFrame:
    """Read and validate exposures.csv against an entities table.

    `entities_df` is required: every link must point at a known entity.
    Returns a table sorted by exposure_id.
    """
    if entities_df is None:
        raise ValueError("load_exposures needs entities_df to check the links against")
    raw, problems = _read_csv(path, EXPOSURE_COLUMNS, EXPOSURES_FILENAME)
    if not problems:
        problems = _check_exposures(raw, entities_df)
    if problems:
        raise DataValidationError(problems)
    return _finalize_exposures(raw)


def load_data(data_dir=DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load both CSV files, validate them together, and return the clean tables.

    Returns (entities_df, exposures_df). Problems from BOTH files are
    collected and reported together in a single DataValidationError.
    """
    data_dir = Path(data_dir)
    ent_raw, ent_problems = _read_csv(
        data_dir / ENTITIES_FILENAME, ENTITY_COLUMNS, ENTITIES_FILENAME)
    exp_raw, exp_problems = _read_csv(
        data_dir / EXPOSURES_FILENAME, EXPOSURE_COLUMNS, EXPOSURES_FILENAME)

    problems = list(ent_problems) + list(exp_problems)
    if not ent_problems:
        problems += _check_entities(ent_raw)
    if not ent_problems and not exp_problems:
        problems += _check_exposures(exp_raw, ent_raw)
    if problems:
        raise DataValidationError(problems)

    return _finalize_entities(ent_raw), _finalize_exposures(exp_raw)
