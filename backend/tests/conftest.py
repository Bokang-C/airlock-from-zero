import os
import shutil
import pytest
from airlock import config

@pytest.fixture(autouse=True)
def local_browser(monkeypatch):
    """Only test process relaxes sandbox. Real public deployment must use proper isolation."""
    monkeypatch.setattr(config, "CHROMIUM_SANDBOX", False)
    # Use the system browser on CI if present, otherwise Playwright's downloaded Chromium.
    executable = os.environ.get('AIRLOCK_CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome')
    monkeypatch.setattr(config, "CHROMIUM_EXECUTABLE", executable)
