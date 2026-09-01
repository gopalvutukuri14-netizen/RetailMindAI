"""
Phase 1 - Data Preprocessing (continuation)
Cleans and normalizes products.csv:
  1. Converts price from USD to INR (dataset prices are historical Amazon USD)
  2. Parses ram/storage/camera/battery text fields into clean numeric columns
  3. Fixes/flags implausible spec values (e.g. "512 GB" RAM, which is impossible)

Input:  products.csv  (as provided by teammate)
Output: products_clean.csv  (adds *_numeric columns, keeps originals for reference)
"""

import re
import pandas as pd

INPUT_PATH = "data/reviews.csv"
OUTPUT_PATH = "data/reviews_sentiment.csv"

# Amazon prices in this dataset are USD. Update this to whatever rate you want
# to present with (a fixed rate is fine for a project demo -- just document it,
# don't pretend it's live/accurate).
USD_TO_INR = 83.0

# Anything above this is not a real phone RAM value for this dataset's era.
# Rows exceeding it get ram_gb_numeric set to null instead of a bogus number.
MAX_PLAUSIBLE_RAM_GB = 16.0
MAX_PLAUSIBLE_STORAGE_GB = 1024.0  # 1TB ceiling, generous


def parse_size_to_gb(value):
    """
    Parses strings like '8 GB', '512 MB', '1.5 GB' into a float number of GB.
    Returns None if the value is missing or doesn't match the expected pattern
    (rather than guessing -- an unparseable value should stay null, not become
    a silently wrong number).
    """
    if pd.isna(value):
        return None
    match = re.match(r"^\s*([\d.]+)\s*(GB|MB)\s*$", str(value).strip(), re.IGNORECASE)
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2).upper()
    return number if unit == "GB" else number / 1024.0


def parse_camera_mp(value):
    """Parses strings like '13 MP', '8MP' into a float megapixel count."""
    if pd.isna(value):
        return None
    match = re.match(r"^\s*([\d.]+)\s*MP\s*$", str(value).strip(), re.IGNORECASE)
    return float(match.group(1)) if match else None


def parse_battery_mah(value):
    """Parses strings like '2000 mAh', '2000mah' into a float mAh count."""
    if pd.isna(value):
        return None
    match = re.match(r"^\s*([\d.]+)\s*mAh\s*$", str(value).strip(), re.IGNORECASE)
    return float(match.group(1)) if match else None


def main():
    df = pd.read_csv(INPUT_PATH)
    before = len(df)

    # --- Price: USD -> INR ---
    df["price_inr"] = (df["price"] * USD_TO_INR).round(2)

    # --- RAM / storage: text -> numeric GB, with a plausibility guard ---
    df["ram_gb_numeric"] = df["ram"].apply(parse_size_to_gb)
    df["storage_gb_numeric"] = df["storage"].apply(parse_size_to_gb)

    bad_ram_mask = df["ram_gb_numeric"] > MAX_PLAUSIBLE_RAM_GB
    bad_storage_mask = df["storage_gb_numeric"] > MAX_PLAUSIBLE_STORAGE_GB
    n_bad_ram = bad_ram_mask.sum()
    n_bad_storage = bad_storage_mask.sum()

    # Don't silently keep an impossible value -- null it out and flag the row
    # so it's visible in the output, rather than letting Retrieval later
    # treat a "512 GB RAM" phone as satisfying every RAM filter a user asks for.
    df.loc[bad_ram_mask, "ram_gb_numeric"] = None
    df.loc[bad_storage_mask, "storage_gb_numeric"] = None
    df["ram_flagged_implausible"] = bad_ram_mask
    df["storage_flagged_implausible"] = bad_storage_mask

    # --- Camera / battery: text -> numeric ---
    df["camera_mp_numeric"] = df["camera"].apply(parse_camera_mp)
    df["battery_mah_numeric"] = df["battery"].apply(parse_battery_mah)

    df.to_csv(OUTPUT_PATH, index=False)

    # --- Summary so you can see exactly what happened, not just trust it ran ---
    print(f"Rows in:  {before}")
    print(f"Rows out: {len(df)}")
    print()
    print(f"Price converted USD -> INR at rate {USD_TO_INR}")
    print(f"  price present: {df['price_inr'].notna().sum()} / {len(df)}")
    print()
    print(f"RAM values flagged implausible (>{MAX_PLAUSIBLE_RAM_GB}GB) and nulled: {n_bad_ram}")
    print(f"Storage values flagged implausible (>{MAX_PLAUSIBLE_STORAGE_GB}GB) and nulled: {n_bad_storage}")
    print()
    print("Numeric field coverage after cleaning:")
    for col in ["ram_gb_numeric", "storage_gb_numeric", "camera_mp_numeric", "battery_mah_numeric"]:
        present = df[col].notna().sum()
        print(f"  {col:24s}: {present} / {len(df)} ({present/len(df)*100:.1f}%)")

    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
