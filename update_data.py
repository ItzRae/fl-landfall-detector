"""Refresh the Git-tracked HURDAT2 snapshot used by the hosted dashboard."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from src.data_sources import NHC_URL, ROOT, discover_hurdat_url, fetch
from src.parser import parse_hurdat

PUBLISHED = ROOT / "data" / "current"


def update_published_data(destination: Path = PUBLISHED) -> bool:
    """Validate before writing; identical content leaves every file unchanged.

    Fetch the file even when its URL is unchanged to detect in-place NOAA
    revisions. The pinned Census boundary is maintained separately.
    """
    url = discover_hurdat_url(fetch(NHC_URL).decode("utf-8"))
    content = fetch(url)
    target = destination / "hurdat2.txt"
    if target.exists() and target.read_bytes() == content:
        return False
    storms = parse_hurdat(content.decode("utf-8").splitlines())
    if not storms or any(not storm.id.startswith("AL") for storm in storms):
        raise ValueError("Expected a nonempty Atlantic HURDAT2 dataset.")
    metadata = {
        "source_url": url,
        "sha256": hashlib.sha256(content).hexdigest(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "boundary_file": "data/boundaries/cb_2025_us_state_500k.shp",
    }
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as staging:
        stage = Path(staging)
        (stage / "hurdat2.txt").write_bytes(content)
        (stage / "source.json").write_text(json.dumps(metadata, indent=2) + "\n")
        (stage / "hurdat2.txt").replace(target)
        (stage / "source.json").replace(destination / "source.json")
    return True


if __name__ == "__main__":
    changed = update_published_data()
    print("Updated published HURDAT2 data." if changed else "HURDAT2 data is unchanged.")
