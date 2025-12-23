from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .chat import ChatMessage
from loguru import logger


@dataclass(slots=True)
class ParsedCommand:
  name: str
  args: List[str]


@dataclass(slots=True)
class ParsedMessage:
  is_command: bool
  command: Optional[ParsedCommand] = None
  query: Optional[str] = None


class MessageFilter:
  """Filter messages by command prefix and distinguish between commands and queries."""

  def __init__(self, prefix: str) -> None:
    if not prefix:
      raise ValueError("Command prefix must not be empty")
    self._prefix = prefix

  def parse(self, message: ChatMessage) -> Optional[ParsedMessage]:
    if not message.text.startswith(self._prefix):
      logger.debug("Ignoring message without prefix: {text}", text=message.text)
      return None

    payload = message.text[len(self._prefix) :].strip()
    if not payload:
      logger.debug("Prefix-only message; ignoring")
      return None

    parts = payload.split()
    first_word = parts[0]

    if first_word.startswith("-"):
      # It's a command (e.g., /bot -help)
      command_name = first_word[1:].lower()  # Strip the '-'
      args = parts[1:]
      logger.debug("Parsed command={command} args={args}", command=command_name, args=args)
      return ParsedMessage(
        is_command=True, 
        command=ParsedCommand(name=command_name, args=args)
      )
    else:
      # It's a general query (e.g., /bot hola)
      logger.debug("Parsed query={query}", query=payload)
      return ParsedMessage(is_command=False, query=payload)
