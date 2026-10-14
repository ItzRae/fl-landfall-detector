from unittest.mock import Mock, patch

import pytest

from scripts.wake_streamlit import wait_for_dashboard


def make_page(error=False, ready=False):
    page, frame = Mock(), Mock()
    page.url = "https://example.streamlit.app/"
    page.frames = [frame]
    exception, table, button = Mock(), Mock(), Mock()
    exception.count.return_value = int(error)
    exception.first.is_visible.return_value = error
    table.count.return_value = int(ready)
    table.first.is_visible.return_value = ready
    button.count.return_value = 1
    button.first.is_visible.return_value = True
    frame.locator.side_effect = lambda selector: exception if 'stException' in selector else table
    frame.get_by_role.return_value = button
    return page, table, button


def test_awake_dashboard_needs_no_wake_click():
    page, _, button = make_page(ready=True)
    wait_for_dashboard(page)
    button.first.click.assert_not_called()


def test_sleeping_dashboard_is_woken_and_verified():
    page, table, button = make_page()
    def wake(**kwargs):
        table.count.return_value = 1
        table.first.is_visible.return_value = True
    button.first.click.side_effect = wake
    wait_for_dashboard(page)
    button.first.click.assert_called_once()


def test_application_error_is_not_reported_as_success():
    page, _, _ = make_page(error=True)
    with pytest.raises(RuntimeError, match='application exception'):
        wait_for_dashboard(page)


def test_unresponsive_dashboard_times_out():
    page, _, button = make_page()
    with patch('scripts.wake_streamlit.time.monotonic', side_effect=[0, 0, 241]):
        with pytest.raises(TimeoutError):
            wait_for_dashboard(page)
    button.first.click.assert_called_once()


def test_inaccessible_app_fails_without_waiting():
    page, _, _ = make_page()
    page.url = "https://share.streamlit.io/errors/not_found"
    with pytest.raises(RuntimeError, match="requires sign-in"):
        wait_for_dashboard(page)
    page.wait_for_timeout.assert_not_called()
