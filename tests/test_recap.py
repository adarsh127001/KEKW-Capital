from pathlib import Path
import pytest

def test_html_recap_escapes_input(tmp_path):
    from kekw.cards.recap import html_recap
    output=html_recap(tmp_path/"index.html",{"headlines":["<script>alert(1)</script>"]})
    text=Path(output).read_text(encoding="utf-8")
    assert "&lt;script&gt;" in text and "<script>alert" not in text

def test_card_artifacts_and_oddity_loss(tmp_path):
    pytest.importorskip("PIL")
    from kekw.cards.recap import market_close_png, portfolio_png, oddity_holdings_png
    snapshot={"candles":[{"close":50},{"close":56}],"headlines":["Ticker rockets"],"verdicts":["YES moons"],"top_pnl":[{"display_name":"BOOTH-02","pnl":9}]}
    for output in (market_close_png(tmp_path/"close.png",snapshot),portfolio_png(tmp_path/"user.png","BOOTH-02",[("KEKW",1,55)],5,"Bold entry."),oddity_holdings_png(tmp_path/"oddity.png")):
        assert Path(output).is_file() and Path(output).stat().st_size>1000
