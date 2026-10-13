import json
from unittest.mock import patch

import pytest

from src import data_sources
from update_data import update_published_data

HTML = b'<a href="/data/hurdat/hurdat2-1851-2025-092326.txt">Atlantic</a>'
DATA = b'AL012025, TEST, 1,\n20250801, 0000, , HU, 25.0N, 80.0W, 80,\n'


def test_changed_data_published_and_identical_check_is_noop(tmp_path):
    with patch('update_data.fetch', side_effect=[HTML, DATA, HTML, DATA]):
        assert update_published_data(tmp_path)
        metadata = (tmp_path / 'source.json').read_bytes()
        assert not update_published_data(tmp_path)
    assert (tmp_path / 'hurdat2.txt').read_bytes() == DATA
    assert (tmp_path / 'source.json').read_bytes() == metadata
    assert json.loads(metadata)['source_url'].endswith('092326.txt')


def test_same_url_revision_is_detected(tmp_path):
    with patch('update_data.fetch', side_effect=[HTML, DATA, HTML, DATA.replace(b'80,', b'90,')]):
        assert update_published_data(tmp_path)
        assert update_published_data(tmp_path)
    assert b'90,' in (tmp_path / 'hurdat2.txt').read_bytes()


def test_invalid_download_preserves_published_files(tmp_path):
    with patch('update_data.fetch', side_effect=[HTML, DATA, HTML, b'<html>error</html>']):
        update_published_data(tmp_path)
        metadata = (tmp_path / 'source.json').read_bytes()
        with pytest.raises(ValueError):
            update_published_data(tmp_path)
    assert (tmp_path / 'hurdat2.txt').read_bytes() == DATA
    assert (tmp_path / 'source.json').read_bytes() == metadata


def test_published_snapshot_takes_precedence_over_local_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(data_sources, 'ROOT', tmp_path)
    published = tmp_path / 'data/current'
    published.mkdir(parents=True)
    (published / 'hurdat2.txt').write_bytes(DATA)
    assert data_sources.input_paths() == (
        published / 'hurdat2.txt', tmp_path / 'data/boundaries/cb_2025_us_state_500k.shp',
    )
