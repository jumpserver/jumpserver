"""Shared command lifecycle for modern and compatibility clients."""

import logging
from typing import Any, Callable

from .models import CommandResult

logger = logging.getLogger(__name__)


def report_failure(report, command_id: str) -> None:
    """Try to report failure without replacing the handler's original exception."""
    try:
        report(command_id=command_id, status="failed", error_code="execution_failed")
    except Exception as error:
        logger.warning("Could not report command failure: %s", type(error).__name__)


def execute_command(
    event: dict[str, Any],
    handler: Callable[[dict[str, Any]], Any],
    report: Callable[..., CommandResult],
) -> CommandResult:
    command_id = event["command_id"]
    claim = report(command_id=command_id, status="running")
    if not claim.accepted:
        return claim
    try:
        handler(event)
    except Exception:
        report_failure(report, command_id)
        raise
    return report(command_id=command_id, status="success")
