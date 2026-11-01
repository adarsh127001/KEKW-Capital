import json
from pathlib import Path
import pytest
from kekw.bus import EventBus
from kekw.desk.headlines import HeadlineDesk, SCHEMA
from kekw.market.contracts import PrimeTime, Wager

def test_headline_schema_and_any_emote_fallback():
    assert SCHEMA["additionalProperties"] is False
    assert SCHEMA["properties"]["headlines"]["minItems"] == 1
    assert SCHEMA["properties"]["headlines"]["maxItems"] == 2
    assert SCHEMA["properties"]["headlines"]["items"]["maxLength"] == 90
    async def run():
        desk=HeadlineDesk()
        for emote in ("PogChamp","some custom emote","💀","!!!"):
            result=await desk.prompt(emote)
            assert result.headlines and len(result.headlines[0])<=90
            assert len(result.analyst)<=90 and -1<=result.bias<=1
    import asyncio; asyncio.run(run())

def test_contract_payment_math_exhaustive():
    for yes in range(26):
        for no in range(26):
            bets=[]
            if yes: bets.append(Wager("yes_user","X_YES",yes))
            if no: bets.append(Wager("no_user","X_NO",no))
            for winner in ("X_YES","X_NO"):
                result=PrimeTime.settlement_math(bets,"X_YES","X_NO",winner)
                expected_winner=(yes if winner=="X_YES" else no)*1.9
                expected_loser=no if winner=="X_YES" else yes
                assert sum(result["payouts"].values())==pytest.approx(expected_winner)
                assert result["losing_stake"]==pytest.approx(expected_loser)
                assert result["burned"]==pytest.approx(expected_loser*.1)

def test_showcase_emits_each_stage_beat():
    from kekw.mock.showcase import dry_run
    async def run():
        events=await dry_run()
        timeline=json.loads(Path("kekw/mock/demos/stage_timeline.json").read_text(encoding="utf-8"))
        emitted={e.payload["id"] for e in events if e.kind=="stage_beat"}
        assert emitted=={beat["id"] for beat in timeline["beats"]}
        kinds={e.kind for e in events}
        assert {"ipo","stage_breaking","stake_open","verdict","close_card"}<=kinds
        assert any(e.payload.get("user")=="BOOTH-02" for e in events if e.kind=="stage_breaking")
    import asyncio; asyncio.run(run())

def test_chat_reply_is_queued_and_published():
    import asyncio
    from kekw.main import publish_chat_reply
    from kekw.sources.chat_source import IRCAdapter
    class FakeSource(IRCAdapter):
        def __init__(self): super().__init__("channel","token"); self.sent=[]
        async def SendMessage(self,text): self.sent.append(text)
    async def run():
        bus=EventBus(); queue=bus.subscribe(__import__("kekw.events",fromlist=["MarketEvent"]).MarketEvent); source=FakeSource()
        await publish_chat_reply(bus,source,"Ada","@Ada FILLED 10T $KEKW")
        assert source.sent==["@Ada FILLED 10T $KEKW"]
        event=await queue.get(); assert event.kind=="chat_reply" and event.payload["text"]==source.sent[0]
    asyncio.run(run())
