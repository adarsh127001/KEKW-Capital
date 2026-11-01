from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass(frozen=True)
class ChatMessage:
    user_id: str
    display_name: str
    text: str
    first_msg: bool = False
    tokens: tuple[str, ...] = field(default_factory=tuple)
    is_mod: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
