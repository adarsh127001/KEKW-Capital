# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary operators:** Twitch streamers and their moderators, running the overlay in OBS during live streams. After one-time setup, operation is faceless and keyboard-driven so the streamer can perform while the market runs.
- **Participants:** Twitch chatters and live-booth attendees. They do not register or use real money. They earn Tendies, the game's coins, by watching and trade with chat commands. A new chatter should be able to place a first trade within 10 seconds of learning the commands.
- **Secondary audience:** Hackathon judges and TwitchCon attendees watching a three-minute demo video or booth run. The experience must read at 100 feet, land its beats with audio off, and visibly prove that the AI is live through the message counter, wall clock, named user trades, and typewriter headlines.

## Product Purpose

KEKW CAPITAL turns Twitch emotes and chat activity into a deterministic virtual stock market hosted by Oddity, an AI-narrated newsroom character. Chat participation moves emote tickers; the market ends in shareable MARKET CLOSE cards, portfolio P&L cards with roasts, and a recap page. Success means chatters become traders, the event is legible and entertaining from the stream floor, and each stream produces artifacts participants want to share.

## Positioning

KEKW CAPITAL combines a transparent market formula with one AI desk that explains market events without setting prices. Chat-driven virtual markets exist; this product adds a live AI newsroom, visible named trades, PRIME TIME in-game contracts, Oddity's host arc, and recap artifacts. The interface must make the separation between deterministic pricing and AI narration visible.

## Operating Context

- The operator runs the web terminal as an OBS browser source and keeps the dashboard on a separate display or control surface.
- LIVE chat enters through Twitch IRC. PIT, SHOWCASE, and RED-KEY are operator fallbacks; the demo is designed around a three-minute stage or booth run.
- The show should proceed hands-free after one-time setup, with keyboard controls for its beats and a visible recovery ladder.
- Audience trust and the story must survive audio being unavailable: market shocks, model activity, and operator state are communicated on screen.

## Capabilities and Constraints

- Emotes can become tickers; users can trade with `!buy` and `!sell`, inspect wallets and portfolios, and join mod-opened PRIME TIME contracts.
- Prices come from the documented deterministic EMA, trade-skew, and bounded-move formula. The LLM narrates but never prices assets.
- Tendies are game coins only: no purchases, cash-outs, prizes paid by the software, or real-money betting. No registration and no DMs.
- IRC is the live ingress. EventSub and an OAuth callback server are not part of this build. The operator provides a long-lived Twitch token and moderator access for LIVE use.
- Chat messages, Twitch user IDs, wallets, and ledgers are stored locally in SQLite. If OpenAI headlines are enabled, only the market context and recent public chat lines needed by the headline request are sent to the API.
- Success criteria: lurkers become traders and chat visibly moves prices within about two seconds; each shock is accompanied by a headline, sound, and Oddity reaction; the formula is displayed; ingress mode, message count, and named-trade headlines stay visible; all numbers carry their ticker and contrast is at least 7:1; type remains at least 24px effective; the experience ends with shareable recaps; LIVE → PIT → SHOWCASE → RED-KEY remains reachable from one keyboard.

## Brand Commitments

The product is KEKW CAPITAL. Oddity is a faceless, perma-bull host who loses often and delivers “I CALLED THE LINE.” ironically. The user supplied this binding visual direction verbatim:

Deranged CRT newsroom: monospace only, palette exactly #061017 ink, #12f6ff cyan, #ff365f crimson, #FFB53D amber-for-breaking (4 max), 1px neon borders with corner brackets, scanlines + vignette overlay, 200ms glitch-jitter on breaker and REKT events, marquee ticker with duplicated content, type floors: headers 40px, wire 44px, prices 56px, blotter 28px; motion budget exactly 3 animations: glitch-jitter, marquee-scroll, pulse-glow; forbidden: sans-serif body, glassmorphism, purple/blue gradients, rounded cards, emoji icons, AI-sparkle motifs. Legibility: every number labeled with its ticker, contrast ≥ 7:1, must read at 100ft.

## Evidence on Hand

- Product rules and stage direction: `STRATEGY.md` and `docs/DEMO_SCRIPT.md`.
- Existing interface and market implementation: `kekw/web/static/terminal.html`, `kekw/web/static/dash.html`, and `kekw/market/`.
- A deterministic file-backed demo exists under `kekw/mock/demos/` and is exercised by the test suite.
- The repository contains no verified live-stream results, judge feedback, user research, or audience-performance measurements. Do not invent them.

## Product Principles

- **The market is honest:** deterministic code prices assets; the AI explains events.
- **Participation has no toll:** chatters need no registration, purchase, affiliate status, or real-money stake.
- **Trust stays on screen:** show ingress, message activity, named trades, the formula, and ticker labels.
- **The host does not take the operator's hands:** setup is one-time and the show remains keyboard-driven.
- **The demo survives failure:** move down the documented fallback ladder and preserve the visible story.
