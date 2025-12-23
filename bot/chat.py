from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from loguru import logger

# Selectors tuned against WhatsApp Web DOM (Dec 2025)
UNREAD_CHAT_SELECTOR = "div[role='row']:has(span[aria-label*='mensaje no leído']), div[role='row']:has(span[aria-label*='unread message'])"
MESSAGE_INPUT_SELECTOR = "div[contenteditable='true'][data-tab='10']"
SEND_BUTTON_SELECTOR = "button[aria-label*='Enviar'], button[aria-label*='Send'], span[data-testid='send']"
LAST_MESSAGE_TEXT = "div[role='region'][aria-label*='mensaje'], div[role='region'][aria-label*='message']"


@dataclass(slots=True)
class ChatMessage:
  text: str
  chat_name: str = ""
  sender: Optional[str] = None
  from_me: bool = False


class ChatService:
  """Read incoming messages and send responses."""

  def __init__(self, page: Page, *, simulation_mode: bool = False, read_timeout: float = 1.0) -> None:
    self._page = page
    self._simulation_mode = simulation_mode
    self._read_timeout = read_timeout
    self._last_seen: dict[str, str] = {}

  def poll_new_messages(self) -> List[ChatMessage]:
    """Return unread messages and mark them as read by visiting the chat."""
    messages: List[ChatMessage] = []
    unread_chats = self._collect_unread_chats()
    if not unread_chats:
      logger.debug("🗑️  No unread chats")
      # Even if no unread chats, still inspect current chat for outgoing/self commands
      self._collect_active_chat_message(messages)
      return messages
    logger.info(f"📨 Found {len(unread_chats)} unread chat(s)")
    for idx, chat in enumerate(unread_chats, 1):
      logger.info(f"  [{idx}/{len(unread_chats)}] Processing chat...")
      try:
        chat.click()
        logger.debug("    ✓ Chat clicked")
        # Nudge the chat to bottom and give DOM a moment
        try:
          self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception:
          pass
        time.sleep(self._read_timeout)

        # Explicitly wait for any bubble to be present
        try:
          self._page.wait_for_selector(
            "div.message-in span.selectable-text, div.message-out span.selectable-text, span[data-lexical-text]",
            timeout=5_000,
          )
        except PlaywrightTimeoutError:
          logger.debug("    ⚠️  No bubbles detected after wait; will attempt fallback read")

        # Log counts per selector to aid debugging
        counts = {
          "message-in": self._page.locator("div.message-in span.selectable-text").count(),
          "message-out": self._page.locator("div.message-out span.selectable-text").count(),
          "lexical": self._page.locator("span[data-lexical-text]").count(),
        }
        logger.debug(f"    🔢 Bubble counts: {counts}")

        result = self._last_message_text()
        if not result:
          logger.debug("    ⚠️  Could not read message text; skipping")
          continue
        
        text, from_me = result
        logger.debug(f"    📝 Message: {text[:50]}..." if len(text) > 50 else f"    📝 Message: {text}")
        self._push_if_new(messages, text, from_me=from_me)
      except Exception as e:
        logger.error(f"    ❌ Error processing chat: {e}")
    logger.info(f"✅ Polled {len(messages)} message(s)")
    # Also inspect current active chat for self-sent commands
    self._collect_active_chat_message(messages)
    return messages

  def send_message(self, text: str) -> bool:
    """Send a message to the currently open chat."""
    if self._simulation_mode:
      logger.info("🔄 [SIMULATION MODE] Would send: {text}", text=text)
      return False
    logger.info(f"📤 Sending message: {text[:50]}..." if len(text) > 50 else f"\ud83d\udce4 Sending message: {text}")
    try:
      input_box = self._page.wait_for_selector(MESSAGE_INPUT_SELECTOR, timeout=5_000)
      logger.debug("  ✓ Message input found")
    except PlaywrightTimeoutError:
      logger.warning("  ❌ Message input not found")
      return False
    input_box.fill("")
    input_box.type(text)
    logger.debug("  ✓ Text entered")
    try:
      send_button = self._page.wait_for_selector(SEND_BUTTON_SELECTOR, timeout=2_000)
      logger.debug("  ✓ Send button found")
      send_button.click()
    except PlaywrightTimeoutError:
      logger.debug("  ⚠️  Send button not found; using Enter key")
      input_box.press("Enter")
    logger.info("  ✅ Message sent")
    return True

  def _collect_unread_chats(self) -> List[Locator]:
    try:
      logger.debug("🔍 Searching for unread chats...")
      self._page.wait_for_selector(UNREAD_CHAT_SELECTOR, timeout=2_000)
    except PlaywrightTimeoutError:
      logger.debug("  ⚠️  No unread badge found")
      return []
    chats = self._page.locator(UNREAD_CHAT_SELECTOR).all()
    logger.debug(f"  ✓ Found {len(chats)} unread chat(s)")
    return chats


  def _last_message_text(self) -> Optional[Tuple[str, bool]]:
    """Returns (text, is_from_me) for the absolute last message in the active chat."""
    
    conversation_selector = "main#main, #main, [role='main'], main"
    try:
      container = self._page.locator(conversation_selector).first
      if not container or container.count() == 0:
        # Fallback to a region that looks like a message list
        container = self._page.locator(LAST_MESSAGE_TEXT).first
        if not container or container.count() == 0:
          return None

      # Scroll to bottom of the message list to ensure latest is loaded
      try:
        scrollable = self._page.locator(f"{LAST_MESSAGE_TEXT}, div.copyable-area").first
        if scrollable.count() > 0:
          scrollable.evaluate("el => el.scrollTop = el.scrollHeight")
      except:
        pass
      # Find all message bubbles
      bubble_selector = "div.message-in, div.message-out, div[data-testid='msg-container']"
      bubbles = container.locator(bubble_selector)
      count = bubbles.count()
      
      if count == 0:
        return None

      # Get the very last bubble
      last_bubble = bubbles.nth(count - 1)
      
      # Determine if it's from me
      html_class = last_bubble.get_attribute("class") or ""
      is_from_me = "message-out" in html_class

      # Find the text inside this specific bubble
      text_selectors = [
        "span.selectable-text",
        "span[data-testid='selectable-text']",
        "span.copyable-text",
        "span[data-lexical-text]",
      ]
      
      for ts in text_selectors:
        text_el = last_bubble.locator(ts).first
        if text_el.count() > 0:
          text = text_el.inner_text().strip()
          # Ignore timestamps
          if text and len(text) > 1:
            return text, is_from_me

    except Exception as exc:
      logger.debug(f"    ⚠️ Error reading last message: {exc}")

    return None

  def _debug_dump_message_area(self) -> None:
    """Dump limited info about the conversation area to aid selector tuning."""
    try:
      # Focus on the conversation region
      container = self._page.locator("main#main, #main, [role='main'], main").first
      if container.count() > 0:
        # Get some text samples from inside the container
        texts = container.locator("span").all_text_contents()
        sample = [t.strip() for t in texts if t.strip()][-15:]
        logger.debug(f"    🔤 Conversation area last texts: {sample}")
        
        # Check for specific bubble classes
        in_bubbles = container.locator("div.message-in").count()
        out_bubbles = container.locator("div.message-out").count()
        logger.debug(f"    📊 Bubbles found: In={in_bubbles}, Out={out_bubbles}")
      else:
        logger.debug("    ⛔ Conversation container not found for debug dump")
    except Exception as e:
      logger.debug(f"    ⚠️ Debug dump failed: {e}")

  def _push_if_new(self, bucket: List[ChatMessage], text: str, *, from_me: bool) -> None:
    # Simple deduplication: check if this exact text was just seen
    if self._last_seen.get("last") == text:
      logger.debug("    ↩️  Skipping duplicate message")
      return
    self._last_seen["last"] = text
    bucket.append(ChatMessage(text=text, from_me=from_me))

  def _collect_active_chat_message(self, bucket: List[ChatMessage]) -> None:
    """Inspect currently open chat for the latest message (including self-sent)."""
    result = self._last_message_text()
    if not result:
      return
    
    text, from_me = result
    logger.debug(f"👀 Active chat latest message: {text[:50]}..." if len(text) > 50 else f"👀 Active chat latest message: {text}")
    self._push_if_new(bucket, text, from_me=from_me)
