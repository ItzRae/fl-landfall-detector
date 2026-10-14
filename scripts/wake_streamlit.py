"""Visit the public dashboard, wake it if necessary, and verify it renders."""
import os
import re
import time


APP_URL = "https://us-landfall-detector.streamlit.app/"


def wait_for_dashboard(page, timeout=240):
    deadline = time.monotonic() + timeout
    wake_clicked = False
    while time.monotonic() < deadline:
        if "/errors/not_found" in page.url:
            raise RuntimeError("App URL is unavailable or requires sign-in; verify the public Streamlit URL.")
        for frame in page.frames:
            error = frame.locator('[data-testid="stException"]')
            if error.count() and error.first.is_visible():
                raise RuntimeError("Streamlit loaded but reported an application exception. Check Cloud logs.")
            table = frame.locator('[data-testid="stDataFrame"]')
            if table.count() and table.first.is_visible():
                return
            button = frame.get_by_role('button', name=re.compile('Yes, get this app back up', re.I))
            if not wake_clicked and button.count() and button.first.is_visible():
                button.first.click(timeout=10000)
                wake_clicked = True
                print("Requested Streamlit wake-up.", flush=True)
        page.wait_for_timeout(2000)
    raise TimeoutError("Dashboard did not render within the wake-up timeout.")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        options = {"headless": True}
        # Optional local browser override; Actions uses Playwright's Chromium.
        if os.environ.get("WAKE_BROWSER_PATH"):
            options["executable_path"] = os.environ["WAKE_BROWSER_PATH"]
        browser = playwright.chromium.launch(**options)
        try:
            page = browser.new_page()
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
            wait_for_dashboard(page)
            print("Streamlit is awake and the landfall results table rendered.")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
