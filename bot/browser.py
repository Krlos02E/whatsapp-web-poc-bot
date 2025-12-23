from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright
from loguru import logger

WAPP_URL = "https://web.whatsapp.com"

class BrowserManager:
  """Manage Playwright lifecycle and exposes the primary page."""

  def __init__(
    self,
    *,
    session_path: Optional[str] = None,
    headless: bool = False,
    slow_mo: int = 0,
  ) -> None:
    self._session_path = Path(session_path) if session_path else None
    self._headless = headless
    self._slow_mo = slow_mo
    self._playwright: Optional[Playwright] = None
    self.browser: Optional[Browser] = None
    self.context: Optional[BrowserContext] = None
    self.page: Optional[Page] = None

  def __enter__(self) -> "BrowserManager":
    self._start()
    return self

  def __exit__(self, exc_type, exc, tb) -> None:
    self.close()

  def _start(self) -> None:
    logger.info("🚀 Starting Playwright browser manager")
    logger.debug(f"  headless={self._headless}, slow_mo={self._slow_mo}ms")
    self._playwright = sync_playwright().start()
    logger.info("✓ Playwright started")
    
    self.browser = self._playwright.chromium.launch(headless=self._headless, slow_mo=self._slow_mo)
    logger.info("✓ Chromium browser launched")
    
    storage_state = None
    if self._session_path:
      logger.info(f"📂 Session path: {self._session_path}")
      if self._session_path.exists():
        logger.info("♻️  Re-using stored WhatsApp session")
        storage_state = str(self._session_path)
      else:
        logger.info("⚠️  No existing session found; will require QR scan")
    else:
      logger.debug("No session path configured; starting fresh")
    
    self.context = self.browser.new_context(storage_state=storage_state)
    logger.info("✓ Browser context created")
    
    self.page = self.context.new_page()
    logger.info("✓ Page initialized")

  def goto_whatsapp(self) -> Page:
    if not self.page:
      raise RuntimeError("Browser page not initialized")
    logger.info(f"🌐 Navigating to {WAPP_URL}")
    self.page.goto(WAPP_URL, wait_until="domcontentloaded")
    logger.info("✓ Page loaded")
    return self.page

  def save_storage_state(self) -> None:
    if not self.context or not self._session_path:
      logger.debug("Session save skipped (no context or no path configured)")
      return
    logger.info(f"💾 Saving session to {self._session_path}")
    self._session_path.parent.mkdir(parents=True, exist_ok=True)
    self.context.storage_state(path=str(self._session_path))
    logger.info("✓ Session saved")

  def close(self) -> None:
    logger.info("🛑 Closing browser and Playwright resources")
    try:
      if self.context:
        self.context.close()
        logger.debug("  ✓ Context closed")
    finally:
      try:
        if self.browser:
          self.browser.close()
          logger.debug("  ✓ Browser closed")
      finally:
        if self._playwright:
          self._playwright.stop()
          logger.debug("  ✓ Playwright stopped")
    logger.info("✓ Shutdown complete")
