"""Download the Crop Recommendation dataset (2,200 rows, 22 crops).

    python scripts/download_crop_data.py

The original is on Kaggle ("Crop Recommendation Dataset" by Atharva Ingle).
This script fetches a public copy from GitHub so no Kaggle account is needed.
If you download it from Kaggle yourself, save it as data/crop/Crop_recommendation.csv.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv"
TARGET = Path(__file__).resolve().parents[1] / "data" / "crop" / "Crop_recommendation.csv"
EXPECTED_COLUMNS = "N,P,K,temperature,humidity,ph,rainfall,label"


def main() -> int:
    if TARGET.exists():
        print(f"{TARGET} already exists.")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(URL, timeout=60) as response:
        content = response.read()
    header = content.splitlines()[0].decode("utf-8").strip()
    if header != EXPECTED_COLUMNS:
        print(f"Unexpected columns in the downloaded file: {header}")
        return 1
    TARGET.write_bytes(content)
    print(f"Saved {len(content.splitlines()) - 1} rows to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
