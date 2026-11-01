"""Deterministic venue traders. The web layer calls this only while PIT is active."""
from ..events import MarketEvent
from ..market.engine import Candle


PERSONALITIES = [
    ("pit_momentum_1", "Momentum Chaser 01", "momentum"),
    ("pit_momentum_2", "Momentum Chaser 02", "momentum"),
    ("pit_momentum_3", "Momentum Chaser 03", "momentum"),
    ("pit_dip_1", "Dip Buyer 01", "dip"),
    ("pit_dip_2", "Dip Buyer 02", "dip"),
    ("pit_dip_3", "Dip Buyer 03", "dip"),
    ("pit_paperhands_1", "Paperhands 01", "paperhands"),
    ("pit_paperhands_2", "Paperhands 02", "paperhands"),
    ("pit_paperhands_3", "Paperhands 03", "paperhands"),
    ("pit_whale_1", "Whale Walls 01", "whale"),
    ("pit_whale_2", "Whale Walls 02", "whale"),
    ("pit_whale_3", "Whale Walls 03", "whale"),
]


def booth_label(user_id):
    if user_id.startswith("pit_whale_"):
        role = "WHALE"
    elif user_id.startswith("pit_momentum_"):
        role = "MOMO"
    elif user_id.startswith("pit_dip_"):
        role = "DIP"
    else:
        role = "PAPER"
    return f"PIT-{role}-{user_id.rsplit('_', 1)[-1].upper()}"


class PitTraders:
    """Twelve repeatable personalities reacting to price and breaker events."""

    def __init__(self, bus, engine):
        self.bus, self.engine = bus, engine
        self.last_bucket = {}
        self.seen_breakers = set()

    async def _trade(self, user_id, display_name, side, ticker, quantity, strategy):
        filled = await self.engine.trade(user_id, side, ticker, quantity, display_name=display_name)
        if not filled:
            return None
        text = f"!{side} ${ticker} {quantity if quantity is not None else 'all'}"
        event = MarketEvent("pit_trade", {
            "user_id": user_id,
            "display_name": display_name,
            "booth": booth_label(user_id),
            "strategy": strategy,
            "ticker": ticker,
            "side": side,
            "text": text,
            "filled": True,
        })
        await self.bus.publish(event)
        return event

    async def on_event(self, event):
        if isinstance(event, Candle):
            return await self._on_candle(event)
        if isinstance(event, MarketEvent) and event.kind == "circuit_breaker":
            return await self._on_breaker(event)
        return []

    async def _on_candle(self, candle):
        up = candle.close > candle.open
        down = candle.close < candle.open
        made = []
        for user_id, name, strategy in PERSONALITIES:
            if self.last_bucket.get(user_id) == candle.bucket:
                continue
            side = None
            quantity = None
            if strategy == "momentum" and up:
                side, quantity = "buy", 8
            elif strategy == "dip" and down:
                side, quantity = "buy", 8
            elif strategy == "paperhands":
                held = self.engine.positions[user_id, candle.ticker]
                if down and held > 0:
                    side, quantity = "sell", None
                elif up and held <= 0:
                    side, quantity = "buy", 10
            elif strategy == "whale" and candle.bucket % 3 == 0:
                side, quantity = "buy", 25
            if side:
                self.last_bucket[user_id] = candle.bucket
                trade = await self._trade(user_id, name, side, candle.ticker, quantity, strategy)
                if trade:
                    made.append(trade)
        return made

    async def _on_breaker(self, event):
        ticker = str(event.payload.get("ticker", "")).upper()
        if ticker in self.seen_breakers:
            return []
        self.seen_breakers.add(ticker)
        made = []
        for user_id, name, strategy in PERSONALITIES:
            if strategy != "paperhands":
                continue
            for (holder, held_ticker), shares in tuple(self.engine.positions.items()):
                if holder != user_id or shares <= 0 or held_ticker == ticker:
                    continue
                trade = await self._trade(user_id, name, "sell", held_ticker, None, strategy)
                if trade:
                    made.append(trade)
        return made
