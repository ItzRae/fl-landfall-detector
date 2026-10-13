"""Download official inputs; publish only a fully validated pair of files."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "downloads"
NHC_URL = "https://www.nhc.noaa.gov/data/"
BOUNDARY_URL = "https://www2.census.gov/geo/tiger/GENZ2025/shp/cb_2025_us_state_500k.zip"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.urls.extend(value for key, value in attrs if key == "href" and value)


def discover_hurdat_url(html: str) -> str:
    """Select the latest Atlantic coverage year and revision date."""
    parser = Links()
    parser.feed(html)
    candidates = []
    for href in parser.urls:
        url = urljoin(NHC_URL, href)
        parsed = urlparse(url)
        match = re.fullmatch(r"hurdat2-1851-(\d{4})-(\d{6,8})\.txt", Path(parsed.path).name)
        if parsed.scheme == "https" and parsed.hostname == "www.nhc.noaa.gov" and match:
            revision = datetime.strptime(match[2], "%m%d%y" if len(match[2]) == 6 else "%m%d%Y")
            candidates.append((int(match[1]), revision, url))
    if not candidates:
        raise ValueError("No Atlantic HURDAT2 download found on NOAA's data page.")
    return max(candidates)[2]


def fetch(url: str) -> bytes:
    response = requests.get(
        url, headers={"User-Agent": "fl-landfall-detector/1.0"}, timeout=60,
    )
    response.raise_for_status()
    return response.content


def input_paths() -> tuple[Path, Path]:
    """Prefer the published snapshot, then local downloads, then bundled inputs."""
    published = ROOT / "data/current/hurdat2.txt"
    if published.exists():
        return published, ROOT / "data/boundaries/cb_2025_us_state_500k.shp"
    manifest = CACHE / "current.json"
    if manifest.exists():
        data = json.loads(manifest.read_text())
        return CACHE / data["hurdat_path"], CACHE / data["boundary_path"]
    return (ROOT / "data/hurdat2-1851-2022-042723.txt",
            ROOT / "data/boundaries/cb_2025_us_state_500k.shp")


def download_inputs() -> dict[str, str]:
    """Validate both sources before atomically switching the active manifest."""
    import geopandas as gpd
    from src.parser import parse_hurdat

    url = discover_hurdat_url(fetch(NHC_URL).decode("utf-8"))
    CACHE.mkdir(parents=True, exist_ok=True)
    # Unique directories also keep concurrent refreshes from mixing datasets.
    with tempfile.TemporaryDirectory(dir=CACHE) as staging:
        stage = Path(staging)
        hurdat = stage / "hurdat2.txt"
        boundary = stage / "states.zip"
        hurdat.write_bytes(fetch(url))
        boundary.write_bytes(fetch(BOUNDARY_URL))
        storms = parse_hurdat(hurdat.read_text().splitlines())
        if not storms:
            raise ValueError("Downloaded HURDAT2 file has no storms.")
        states = gpd.read_file(boundary).to_crs("EPSG:4326")
        if not {"Florida", "Alabama", "Georgia"}.issubset(set(states["NAME"])):
            raise ValueError("Boundary download is missing required states.")
        if states.geometry.is_empty.any() or not states.geometry.is_valid.all():
            raise ValueError("Boundary download contains invalid geometry.")
        destination = Path(tempfile.mkdtemp(prefix="snapshot-", dir=CACHE))
        hurdat.replace(destination / hurdat.name)
        boundary.replace(destination / boundary.name)
        metadata = {
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "hurdat_url": url, "boundary_url": BOUNDARY_URL,
            "hurdat_path": f"{destination.name}/{hurdat.name}",
            "boundary_path": f"{destination.name}/{boundary.name}",
        }
        pending = stage / "current.json"
        pending.write_text(json.dumps(metadata, indent=2) + "\n")
        pending.replace(CACHE / "current.json")
    return metadata
