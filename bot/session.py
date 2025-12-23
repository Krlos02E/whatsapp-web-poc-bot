from __future__ import annotations

import time

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

# WhatsApp selectors evolve often; keep them easy to update.
CHAT_LIST_READY_SELECTOR = "div[id='pane-side']"
QR_CODE_SELECTOR = "canvas[aria-label*='Scan']"

class SessionManager:
  """Responsible for opening WhatsApp Web and ensuring we stay logged in."""

  def __init__(self, page: Page, poll_interval: float = 2.0, login_timeout: float = 120.0) -> None:
    self._page = page
    self._poll_interval = poll_interval
    self._login_timeout = login_timeout

  def ensure_session(self) -> None:
    logger.info("🔐 Ensuring WhatsApp Web session is active")
    self._page.bring_to_front()
    logger.debug("  ✓ Page brought to front")
    # Ensure the QR or the chat UI is loaded.
    self._wait_for_login()
    if self.is_logged_in():
      logger.info("✅ WhatsApp session ready - chat list detected")
    else:
      raise RuntimeError("Failed to establish WhatsApp Web session")

  def is_logged_in(self) -> bool:
    try:
      self._page.wait_for_selector(CHAT_LIST_READY_SELECTOR, timeout=3_000)
      logger.debug(f"  ✅ Chat list detected")
      return True
    except PlaywrightTimeoutError:
      return False

  def _wait_for_login(self) -> None:
    logger.info(f"⏳ Waiting for login (timeout: {self._login_timeout}s)")
    deadline = time.time() + self._login_timeout
    poll_count = 0
    while time.time() < deadline:
      poll_count += 1
      if self.is_logged_in():
        logger.info(f"✅ Login successful after {poll_count} polls")
        return
      qr_visible = self._qr_visible()
      if qr_visible:
        logger.info(f"📋 QR code visible - awaiting scan (poll #{poll_count})")
      else:
        logger.debug(f"  ⟳ Waiting... (poll #{poll_count}, no QR visible)")
      time.sleep(self._poll_interval)
    raise RuntimeError(f"Login timed out after {poll_count} polls in {self._login_timeout}s")

  def _qr_visible(self) -> bool:
    try:
      self._page.wait_for_selector(QR_CODE_SELECTOR, timeout=1_000)
      return True
    except PlaywrightTimeoutError:
      return False

