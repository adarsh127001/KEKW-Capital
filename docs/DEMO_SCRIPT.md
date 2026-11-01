# KEKW CAPITAL stage script

The following run of show is copied verbatim from `STRATEGY.md` §5.

```
0:00  glitch-open + synth RISE; Oddity SASSY: "MARKET. IS. OPEN. I AM THE MARKET." KEY-1 = LIVE(else PIT)
0:05  framing sentence types on screen: "Every emote chat has ever spammed is now a stock — and the AI desk shorted the ghost."
0:15  IPOTIME: $KEKW/$GG/$FAIL list @ 50T w/ 1-line prospectuses; PIT + booth phones flood; ask/bid spread visible; candles build
0:25  NAMED KILL: last booth !buy → BREAKING headline names that user, typewriter, ≤8s  [PROOF: not pre-animated]
0:35  Oddity CALLED_IT wav: "I called it. You're welcome."
0:45  KEY-2 PRIME TIME: "can Oddity beat Snake in 60s?" → $ODDY_WIN/$ODDY_LOSE; orderbook w/ booth names; HUBRIS wav
0:55  PROVE-THE-AI: /headline-prompt <booth emote> → analyst note typewrites live (fallback-templated: can't fail)
1:00  Oddity attempts deterministic Snake minigame; PIT keeps trading
1:20  VERDICT: Oddity LOSES → $ODDY_LOSE moons, klaxon, SULK wav; NO-side wallets flash green
1:35  Oddity: "...I still called the line."
1:50  RECAP: MARKET CLOSE card + Oddity Holdings P&L (−87%): he's the bagholder on his own exchange
2:05  "BUILT WITH CODEX + TWITCH": live !found IPO on a booth-suggested emote + Codex thread screenshot
2:20  Oddity MARKET_CLOSED wav: "MARKET. CLOSED. I am the tape." confetti pop
2:25  QR: repo + RECAP board
2:30–2:40 buffer / Q&A
2:45  RED-KEY reel ONLY if a beat failed
3:00  hard stop
```

## Keys and dashboard

- `KEY-1`: LIVE; switch to PIT when channel ingress is unavailable.
- `KEY-2`: open PRIME TIME for 60 seconds.
- `KEY-3`: probe the emote entered in the dashboard field; `R`: start RED-KEY recording. Click outside form fields before using a key.
- Dashboard: mode selector, stake open, settle key, RED-KEY, and force-crash controls. Use the settle-key field for the verdict.
- `!recap` or the dashboard recap control writes the MARKET CLOSE PNG, Oddity Holdings PNG, and HTML recap.
- Offline voice batch (requires `OPENAI_API_KEY`): `KEKW_GENERATE_VOICES=1 python -m kekw.desk.sfx` renders the six event cues plus the five idle wavs; no TTS runs during the show.

## Fallback lines and recovery

- AI request fails: keep the prewarmed template wire visible; display `TRANSMISSION LOST — AI headline service unavailable; guaranteed template headlines remain on the wire.`
- IRC disconnects: reconnect with backoff; display `RECONNECTING — Twitch IRC dropped; automatic rejoin is in progress.`
- IPO headline: `NEW IPO: chat has priced in pure vibes.`
- Breaker headline: `CIRCUIT BREAKER: the ticker has entered witness protection.`
- Emote probe: `PogChamp: chat attention is the only fundamental.` (same canned template works for any emote.)
- If other live beats fail, move down LIVE → PIT → SHOWCASE → RED-KEY.

## RED-KEY recording and rehearsal

Start `record_png_sequence("recordings/red-key", duration_seconds=120, fps=15)` while OBS displays the best run. It writes numbered PNG frames without invoking a video encoder. Play the PNG sequence as an OBS image slideshow if the live application fails.

- [ ] Run `python -m kekw.mock.showcase` with network disabled.
- [ ] Verify the bot token and moderator status before LIVE mode.
- [ ] Check the named trade, headline fallback, settlement key, and recap outputs.
- [ ] Capture and rehearse the RED-KEY PNG sequence.
- [ ] Keep API/Twitch credentials out of OBS, screenshots, and demo logs.
