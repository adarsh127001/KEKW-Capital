from .engine import BLUE_CHIPS
async def list_ticker(store, ticker, prospectus="Community discovered ticker."):
    await store.add_listing(ticker.upper().lstrip("$"), prospectus, 50)
