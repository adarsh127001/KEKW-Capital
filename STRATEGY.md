# STRATEGY.md — Codex x TwitchCon Hackathon: Final Build Spec

**CONCEPT (LOCKED): KEKW CAPITAL — the AI-hosted emote stock exchange for Twitch chat.**

Every emote your chat spams becomes a listed ticker. Price moves on real chat momentum +
`!buy`/`!sell` orders through a pinned, legible formula. A Bloomberg-parody overlay shows
candles, a screaming tape, an order blotter, and an AI headline wire — **the market never
moves without a headline**. **Oddity**, a neon CRT ghost, hosts: arrogant, perma-bull on
himself, loses constantly ("I CALLED THE LINE." — always ironic). **PRIME TIME** settles
stakes via duel-ticker event contracts (no affiliate needed). **RECAP cards** end every
stream with take-home artifacts. Faceless by design: the operator is a silent keyboard
pit-boss; three fallback modes + RED-KEY.


---

## 1. Product

### 1.1 Market engine (deterministic; the LLM narrates, never prices)
- **Listings ("IPOs")**: emoji/emote seen ≥3 times becomes a ticker; `!found <emote>`
  lists instantly with a 1-line "prospectus" (AI-desk flavor). Ship 3 universal
  "blue chips" with harm-free prospectuses pre-written: `$KEKW`, `$GG`, `$FAIL`.
- **Formula (pinned, shown on screen — "the market is honest")** [PMA: z-score→EMA,
  no cold-start div-zero]:
  `mom = EMA(tokens/5s, α=0.3) vs EMA(tokens/5s, α=0.01) ratio`
  `price_delta = clamp(k1*log(mom) + k2*buy_sell_skew + shock_bias, ±0.25)`
  Orders batch once/second; 5s OHLC candles per ticker. Circuit breaker: −20%/min →
  "HALTED" + Oddity panic; dead chat → slow market-wide −5% "soft close".
- **Orders**: `!buy $T n` / `!sell $T n|all` / `!balance` / `!portfolio` / `!top` /
  `!ipo` / `!halp`. Market orders only. Rate limit 1 trade/5s/user.
- **Currency: Tendies — the economy (exact rules, locked):**
  - **Wallets**: every chatter starts with **100T granted on first message**; passive
    income **1T/min while live, capped 20T/stream**; **+10T first-trade bonus**.
    Tendies cannot be purchased — wealth = time + skill, no pay-to-win.
  - **IPO anchor**: every listing mints at a fixed **50T** (blue chips and PRIME TIME
    duel tickers included). Same starting line for all assets; price then moves only
    on the pinned momentum formula + trade skew.
  - **Market making**: the exchange is a synthetic maker — **buy fills at ask
    (price×1.01), sell fills at bid (price×0.99): 2% spread**, batched 1Hz, no
    orderbook matching, no counterparties. Spread + spread-reversal of the formula is
    all the liquidity there is, and it is shown on the terminal.
  - **Founder badge**: first 3 traders of any newly listed ticker get the `FOUNDER`
    tag + 10T. Community lore for free.
  - **Prize conversion (streamer-configured, README/dashboard note only — not built
    in 48h)**: streamer can attach real rewards to top wallets (gift sub, VIP nom,
    Discord role, mod tryout). This is the channel-points-reward loop, manually run.
  - Wallets persist cross-stream (SQLite by Twitch `user-id`). No real money, ever.
- **Anti-GIGO**: 1 trade/5s/user, no negative holdings, ±25% per-move clamp, no
  shorting at t=0, breaker halts at −20%/min.
- **PRIME TIME event contracts** [PMA: ONE settle-key; trio = flavor not dependency]:
  mod-only `/stake "title" window=60` mints duel tickers ($X_YES/$X_NO) at 50T; book
  open for the window; settle via dashboard key (button, not an API). **Settlement:
  winning ticker settles to 95T (1.9x), losing to 0T; 10% of the losing side's value
  is burnt (Oddity tax, anti-inflation).** YES moons + confetti; NO crashes + klaxon.
  (Affiliate predictions = documented swap-in plug for later; not built.)

### 1.2 The AI desk (the Codex flex; ONE live LLM path [PMA: deflating TTS out])
- **Headline wire**: every 45–90s (and on breakers/IPOs instantly) → gpt-4.1-mini with
  market-state JSON (movers, breaker flags, last 40 chat lines) + strict json_schema →
  1–2 tabloid headlines ≤90 chars + 1 analyst note + sentiment bias −1..1.
  **Template fallback pre-warmed for every trigger: the wire NEVER goes blank.**
- **Typewriter render**: headlines type onto the wire character-by-character (hides
  latency; makes "live AI" visible at 100ft) [PMD].
- **NAMED KILL** [PMD]: `!buy`/BREAKING headlines may name a real user ("BOOTH-02 dump
  14 $GG — a bold strategy"). Booth attendees become characters.
- **`/headline-prompt <emote>`** [PMD probe beat]: operator keys an emote → desk streams
  an analyst note on it. Always succeeds: canned fallback template ready for ANY emote.
- **Oddity audio**: 6 wavs pre-rendered (tts-1, batch, offline): OPEN, CALLED_IT, HUBRIS,
  PANIC, SULK, MARKET_CLOSED + 5 synth SFX (tape_tick, riser, klaxon, siren, confetti_pop,
  zero-copyright, generated). Played by event/key — **no live audio routing on stage.**
- **Runtime Codex**: `!found` → Codex writes listing JSON/prospectus against a locked
  schema (validated, NEVER executed). Shown in video + optional stage beat.

### 1.3 Identity & overlay (Design criterion)
- **Oddity**: neon-cyan CRT ghost, paperclip nose; 5 SVG states (SASSY/PANIC/FREEZE/
  SCREAMING/SULK) + keyframe glitch-shake; perma-bull; catchphrase "I CALLED THE LINE."
  (ironic). Protagonist arc: hubris → loss → SULK → exposed as biggest bagholder [PMD].
- **Terminal (OBS browser source, vanilla JS/Canvas)**: ticker tape (blue chips +
  top movers), main candle chart, order blotter (BOOTH badge), headline wire
  (typewriter), prospectus strip, Oddity pod, captions line. Cyan=up, crimson=down,
  ≤300ms easing, legible at 100ft [PMD: exhibit A against "cute overlay toy"].

### 1.4 Modes (reliability ladder)
1. **LIVE** — real channel, IRC, attendees on phones. 2. **PIT** — 12 scripted
   personalities trade (venue-no-wifi mode). 3. **SHOWCASE** — JSON timeline, zero
   network, deterministic. 4. **RED-KEY** — prerendered reel (screen recording of the
   best run) = hard kill switch. Operator: 4 dashboard buttons + keys.

### 1.5 Take-home artifacts (THE OUTPUT) [PMA: shrink ffmpeg OUT]
- **RECAP cards**: end-of-stream "MARKET CLOSE" PNG (today's tape: chart, top 3
  headlines, verdicts, top P&L) + per-user portfolio PNGs with Oddity roast lines
  (Pillow text/lines only). **HTML recap page** fallback both ways. Shareable = impact.
  (mp4 "THE TAPE" video = documented stretch, only if hours 28+ are free.)
- **Oddity Holdings card**: the desk's own fictional portfolio at −87% — the 1:50
  punchline beat [PMD].
- **Almanac**: persistent per-channel history page.

## 2. Twitch integration (simplified by pre-mortem — INGRESS IS IRC ONLY)

- **IRC** `wss://irc-ws.chat.twitch.tv:443`: `CAP REQ twitch.tv/tags twitch.tv/commands`,
  PING/PONG, auto-rejoin; tags give `user-id`, `display-name`, `first-msg`.
- **Auth pragmatics [PMA]**: paste a long-lived token from the Twitch dev token
  generator (scopes: `chat:read chat:edit channel:moderate user:read:chat`) into `.env`.
  Bot = second account, moderator of the channel. Full auth-code flow = stretch only.
- **Helix (moderation/nice-to-haves only)**: announce, timeout, get users. Queue w/
  429 respect. NOT on demo critical path.
- **EventSub: NOT in the MVP build** (the pre-mortem gutted the dual-stack). Note in
  README as roadmap. Everything ships on IRC alone: `ChatSource` protocol with **IRC and
  file adapters** so SHOWCASE trades the same code path [PMA spine].
- Non-affiliate facts stay true: no points/predictions/polls/clips needed anywhere.

## 3. Repo layout

```
kekw-capital/
  README.md  .env.example  pyproject.toml
  kekw/
    main.py  config.py
    twitch/ ircbot.py helix.py          # IRC in (tags), Helix out (announce)
    bus.py  store.py                    # pub/sub + sqlite wallets/ledger
    market/ engine.py listings.py orders.py circuits.py contracts.py
    desk/   headlines.py oddity.py sfx.py   # ONE live LLM path + prerecorded audio
    sources/ chat_source.py             # ChatSource protocol: IRC adapter + file adapter
    pit/    traders.py
    web/    server.py static/terminal.html static/dash.html
    mock/   showcase.py demos/stage_timeline.json
    cards/  recap.py                    # Pillow PNG cards + HTML recap
  tests/
```

## 4. Judge-attack prep

- *"Cute overlay toy / pre-animated."* → Typewriter wire + NAMED KILL + /headline-prompt
  beat: live model output, visibly un-pre-bakeable, at 100ft.
- *"Chat economy bots existed."* → They were mute rule engines; ours prices chat and
  *explains it* in real time; PRIME TIME settles stakes with no affiliate gate; RECAP
  cards make chatters come back.
- *"Why no predictions/polls?"* → Affiliate-gated; we serve the 95% every channel can
  use today, with a documented swap-in for when they qualify.
- *"Is this gambling?"* → Game coins, no purchase, no payout, no wagering on outside
  outcomes. Tendies are participation points with market theater.
- *"What does it produce?"* → MARKET CLOSE recap cards + portfolio roasts after every
  stream: an engagement engine that ends in content.
- *"Breaks on stage?"* → LIVE→PIT→SHOWCASE→RED-KEY ladder; deterministic by default.


## 5. Stage script (3:00, keyboard-driven) [PMD]

```
0:00  glitch-open + synth RISE; Oddity SASSY: "MARKET. IS. OPEN. I AM THE MARKET." KEY-1 = LIVE(else PIT)
0:05  framing sentence types on screen: "Every emote chat has ever spammed is now a stock — and the AI desk shorted the ghost."
0:15  IPOTIME: $KEKW/$GG/$FAIL list @ 50T w/ 1-line prospectuses; PIT + booth phones flood; ask/bid spread visible; candles build
0:25  NAMED KILL: last booth !buy → BREAKING headline names that user, typewriter, ≤8s  [PROOF: not pre-animated]
0:35  Oddity CALLED_IT wav: "I called it. You're welcome."
0:45  KEY-2 PRIME TIME: "can Oddity beat Snake in 60s?" → $ODDY_WIN/$ODDY_LOSE; orderbook w/ booth names; HUBRIS wav
0:55  PROVE-THE-AI: /headline-prompt <booth emote> → analyst note typewrites live (fallback-templated: can't fail)
1:00  Oddity attempts deterministic Snake minigame; PIT keeps trading
1:20  VERDICT: Oddity LOSES → $ODDY_LOSE moons, klaxon, SULK wav; NO-side wallets flash green
1:35  Oddity: "...I still called the line."
1:50  RECAP: MARKET CLOSE card + Oddity Holdings P&L (−87%): he's the bagholder on his own exchange
2:05  "BUILT WITH CODEX + TWITCH": live !found IPO on a booth-suggested emote + Codex thread screenshot
2:20  Oddity MARKET_CLOSED wav: "MARKET. CLOSED. I am the tape." confetti pop
2:25  QR: repo + RECAP board
2:30–2:40 buffer / Q&A
2:45  RED-KEY reel ONLY if a beat failed
3:00  hard stop
```