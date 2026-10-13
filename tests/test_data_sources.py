import json
from unittest.mock import patch

import pytest

from src import data_sources


def test_discovery_ignores_other_basins_and_external_hosts():
    html = '''<a href="/data/hurdat/hurdat2-1851-2024-040425.txt">old</a>
    <a href="/data/hurdat/hurdat2-1851-2025-040426.txt">current</a>
    <a href="https://example.com/hurdat2-1851-2099-010199.txt">external</a>
    <a href="/data/hurdat/hurdat2-nepac-1949-2025-040426.txt">Pacific</a>'''
    assert data_sources.discover_hurdat_url(html).endswith('hurdat2-1851-2025-040426.txt')


def test_discovery_fails_when_no_atlantic_file():
    with pytest.raises(ValueError, match="No Atlantic"):
        data_sources.discover_hurdat_url('<html>Error</html>')


def test_failed_download_preserves_current_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(data_sources, 'CACHE', tmp_path)
    manifest = tmp_path / 'current.json'
    original = json.dumps({'hurdat_path': 'old.txt', 'boundary_path': 'old.zip'})
    manifest.write_text(original)
    html = b'<a href="/data/hurdat/hurdat2-1851-2025-040426.txt">data</a>'
    with patch.object(data_sources, 'fetch', side_effect=[html, OSError('offline')]):
        with pytest.raises(OSError, match='offline'):
            data_sources.download_inputs()
    assert manifest.read_text() == original
    assert data_sources.input_paths() == (tmp_path / 'old.txt', tmp_path / 'old.zip')


def test_discovery_orders_revisions_by_date_not_filename():
    html = '''<a href="/data/hurdat/hurdat2-1851-2025-123125.txt">older</a>
    <a href="/data/hurdat/hurdat2-1851-2025-010126.txt">newer</a>'''
    assert data_sources.discover_hurdat_url(html).endswith('010126.txt')
