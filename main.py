from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv
from loguru import logger
from google import genai

from bot import BrowserManager, ChatService, CommandHandler, MessageFilter, SessionManager


@dataclass(slots=True)
class BotConfig:
  command_prefix: str
  session_path: Optional[str]
  log_level: str
  simulation_mode: bool
  google_api_key: Optional[str]
  poll_interval: float = 2.0


def load_config() -> BotConfig:
  return BotConfig(
    command_prefix = os.getenv("BOT_COMMAND_PREFIX", "/bot"),
    session_path = os.getenv("SESSION_PATH") or None,
    log_level = os.getenv("LOG_LEVEL", "INFO").upper(),
    simulation_mode= _to_bool(os.getenv("SIMULATION_MODE", "false")),
    google_api_key= os.getenv("GOOGLE_API_KEY"),
    poll_interval= float(os.getenv("POLL_INTERVAL", "2")),
  )


def configure_logging(level: str) -> None:
  logger.remove()
  normalized = level.upper()
  try:
    logger.add(sys.stderr, level=normalized, format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}")
  except ValueError:
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}")
    logger.warning("Invalid log level '{level_name}'; defaulting to INFO", level_name=level)

def _to_bool(value: str) -> bool:
  return value.strip().lower() in {"1", "true", "yes", "on"}

def run_bot(config: BotConfig) -> None:
  logger.info("🚀 Starting WhatsApp Web Bot")
  logger.info(f"  Command prefix: {config.command_prefix}")
  logger.info(f"  Simulation mode: {config.simulation_mode}")
  logger.info(f"  Log level: {config.log_level}")
  
  with BrowserManager(session_path=config.session_path, headless=False) as browser:
    logger.info("🌐 Opening WhatsApp Web...")
    page = browser.goto_whatsapp()
    
    logger.info("🔐 Verifying session...")
    session = SessionManager(page)
    session.ensure_session()
    browser.save_storage_state()

    chat_service = ChatService(page, simulation_mode=config.simulation_mode)
    message_filter = MessageFilter(config.command_prefix)
    handler = CommandHandler(config.command_prefix)

    # Initialize Gemini Client
    if not config.google_api_key:
      logger.warning("⚠️ GOOGLE_API_KEY not found in .env. AI features will be disabled.")
      ai_client = None
    else:
      ai_client = genai.Client(api_key=config.google_api_key)

    def call_ai(query: str) -> str:
      """Calls Google Gemini AI."""
      if not ai_client:
        return "Error: AI client not configured (missing API key)."
      try:
        logger.info(f"🤖 Querying Gemini: {query}")
        response = ai_client.models.generate_content(
          model="gemini-2.5-flash-lite",
          contents=query,
        )
        return response.text or "No response from AI."
      except Exception as e:
        if "429" in str(e):
          logger.error("❌ AI Error: Quota exceeded (429). Try again in a few seconds.")
          return "Lo siento, he alcanzado mi límite de mensajes por ahora. Por favor, inténtalo de nuevo en unos segundos."
        logger.error(f"❌ AI Error: {e}")
        return f"Sorry, I encountered an error processing that: {e}"

    logger.info(f"✅ Bot ready! Listening for messages with prefix '{config.command_prefix}'")
    logger.info("=" * 60)
    poll_count = 0
    try:
      while True:
        poll_count += 1
        logger.debug(f"\n🔄 Poll cycle #{poll_count}")
        messages = chat_service.poll_new_messages()
        for message in messages:
          logger.info(f"\n📨 NEW MESSAGE: {message.text[:80]}..." if len(message.text) > 80 else f"\n📨 NEW MESSAGE: {message.text}")
          
          parsed = message_filter.parse(message)
          if not parsed:
            continue

          if parsed.is_command and parsed.command:
            logger.info(f"🔥 Command accepted: {parsed.command.name}")
            response = handler.handle(parsed.command)
          else:
            response = call_ai(parsed.query or "")

          if response:
            logger.info(f"\n📤 Responding with:\n{response}")
            chat_service.send_message(response)
        time.sleep(config.poll_interval)
    except KeyboardInterrupt:
      logger.info("\n" + "=" * 60)
      logger.info("✋ Interrupted by user; shutting down")
    finally:
      browser.save_storage_state()


def main() -> int:
  load_dotenv()
  config = load_config()
  configure_logging(config.log_level)
  try:
    run_bot(config)
  except Exception as exc:
    logger.exception("Bot terminated due to unexpected error: {exc}", exc=exc)
    return 1
  return 0


if __name__ == "__main__":
  sys.exit(main())
