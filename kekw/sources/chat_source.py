import asyncio, json, random, re, time
from typing import AsyncIterator, Protocol, runtime_checkable
from ..models import ChatMessage

TOKEN_RE = re.compile(r"(?<!\w)(?:\$?[A-Za-z0-9_]{2,}|[\U0001F300-\U0001FAFF])")

def extract_tokens(text: str) -> tuple[str, ...]:
    return tuple(t.upper().lstrip("$") for t in TOKEN_RE.findall(text))

@runtime_checkable
class ChatSource(Protocol):
    def __aiter__(self) -> AsyncIterator[ChatMessage]: ...

class FileAdapter:
    """Replay one JSONL file; each row uses ChatMessage field names."""
    def __init__(self, path: str, delay: float = 0): self.path, self.delay = path, delay
    async def __aiter__(self):
        with open(self.path, encoding="utf-8") as stream:
            for line in stream:
                if not line.strip(): continue
                row = json.loads(line)
                if "tokens" not in row: row["tokens"] = extract_tokens(row.get("text", ""))
                if "timestamp" in row and isinstance(row["timestamp"], str):
                    from datetime import datetime
                    row["timestamp"] = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
                yield ChatMessage(**row)
                await asyncio.sleep(self.delay)

class IRCAdapter:
    URL = "wss://irc-ws.chat.twitch.tv:443"
    def __init__(self, channel: str, token: str, client_id: str = "", username: str = "", reconnect_max: float = 30, on_status=None):
        self.anonymous = not token
        self.channel, self.token, self.client_id, self.username, self.reconnect_max = channel.lstrip("#"), (token or "").removeprefix("oauth:"), client_id, (f"justinfan{random.randint(10000, 99999)}" if self.anonymous else username), reconnect_max
        self.on_status=on_status
        self._closed = False
        self._ws=None; self._writes=asyncio.Queue(); self._writer=None
    async def SendMessage(self,text):
        """Queue a Twitch chat reply; delivery failures are intentionally ignored."""
        if self.anonymous: return
        if not self._ws: return
        await self._writes.put(f"PRIVMSG #{self.channel} :{text}")
    async def _write_loop(self,ws):
        while ws is self._ws:
            line=await self._writes.get()
            try: await ws.send(line)
            except Exception: pass
    def close(self): self._closed = True
    async def __aiter__(self):
        import websockets
        delay = 1.0
        while not self._closed:
            try:
                async with websockets.connect(self.URL) as ws:
                    self._ws=ws; self._writer=asyncio.create_task(self._write_loop(ws))
                    await ws.send("PASS justinfan" if self.anonymous else f"PASS oauth:{self.token}")
                    await ws.send(f"NICK {self.username}")
                    await ws.send("CAP REQ :twitch.tv/tags twitch.tv/commands")
                    await ws.send(f"JOIN #{self.channel}")
                    delay = 1.0
                    async for raw in ws:
                        if raw.startswith("PING "):
                            await self._writes.put(raw.replace("PING", "PONG", 1)); continue
                        message = self._parse(raw)
                        if message: yield message
                    self._ws=None
                    if self._writer: self._writer.cancel(); self._writer=None
            except asyncio.CancelledError: raise
            except Exception:
                self._ws=None
                if self._writer: self._writer.cancel(); self._writer=None
                if not self._closed:
                    if self.on_status:
                        result=self.on_status("RECONNECTING")
                        if asyncio.iscoroutine(result): await result
                    await asyncio.sleep(delay); delay = min(delay * 2, self.reconnect_max)
    @staticmethod
    def _parse(raw: str):
        if " PRIVMSG " not in raw: return None
        tags, rest = ({}, raw)
        if raw.startswith("@"):
            tagpart, rest = raw.split(" ", 1)
            for item in tagpart[1:].split(";"):
                if "=" in item:
                    k,v=item.split("=",1); tags[k]=v
        try: trailing = rest.split(" :", 1)[1]
        except IndexError: return None
        prefix = rest.split("!",1)[0].lstrip(":")
        display = tags.get("display-name") or prefix
        user_id = tags.get("user-id") or prefix
        return ChatMessage(user_id, display, trailing, tags.get("first-msg")=="1", () if trailing.lstrip().startswith("!") else extract_tokens(trailing),tags.get("mod")=="1" or tags.get("user-type")=="mod")
