from __future__ import annotations

from typing import Dict

from .filters import ParsedCommand
from loguru import logger


class CommandHandler:
  """Dispatch bot commands."""

  def __init__(self, prefix: str) -> None:
    self._prefix = prefix
    self._commands: Dict[str, str] = {
      "ping": "pong",
    }

  def handle(self, command: ParsedCommand) -> str:
    logger.info("Handling command: {command}", command=command.name)
    if command.name == "help":
      return self._help_message()
    if command.name in self._commands:
      return self._commands[command.name]
    logger.warning("Unknown command: {command}", command=command.name)
    return f"Unknown command '{command.name}'. Try '{self._prefix} help'."

  def _help_message(self) -> str:
    commands = sorted({*self._commands.keys(), "help"})
    items = "\n".join(f"- {self._prefix} {name}" for name in commands)
    return "Available commands:\n" + items
