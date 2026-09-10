from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthContext:
    """Who the agent is acting for. Built from the verified JWT — never from model output.

    ``token`` is only populated for the MCP executor path (``chatbot.py``); the in-process
    ``ServiceToolExecutor`` passes ``customer_id`` / ``role`` straight to the service layer.
    """

    customer_id: int
    role: str  # "customer" | "admin"
    token: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
