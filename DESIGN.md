---
name: KEKW CAPITAL
description: Deranged CRT newsroom for a transparent, AI-narrated Twitch emote market.
colors:
  ink: "#061017"
  cyan: "#12f6ff"
  crimson: "#ff365f"
  amber: "#FFB53D"
typography:
  body:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "24px"
  headers:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "40px"
  wire:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "44px"
  prices:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "56px"
  blotter:
    fontFamily: "JetBrains Mono, monospace"
    fontSize: "28px"
rounded:
  card: "0px"
components:
  terminal-panel:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.cyan}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
    padding: "14px"
  ticker-chip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.cyan}"
    typography: "{typography.body}"
    rounded: "{rounded.card}"
---

# Design System: KEKW CAPITAL

## Overview

**Creative North Star: “Deranged CRT Newsroom”**

The stream terminal is an instrument panel for a live financial farce. It must remain readable from the floor while making the market's real state visible: the formula sets prices, chat activity changes the tape, and the AI desk narrates. The operator works by keyboard after setup; the audience should understand the proof and story even with sound off.

The locked direction is normative for future UI. The current HTML is a partial prototype and visibly diverges: it uses a sans-serif face, extra interface colors, text below the size floor, and more than three motion effects; the duplicated marquee, scanlines, vignette, and corner brackets are not yet present. These are implementation gaps, not alternate design tokens.

**Key Characteristics:**
- Monospace broadcast typography with hard size floors.
- Four named colors only, with ticker labels and redundant market-state cues.
- Square, flat panels with neon borders and CRT overlays.
- Exactly three named animations.
- Broadcast-scale legibility and visible evidence of live ingress and AI activity.

Deranged CRT newsroom: monospace incl. bundled JetBrains Mono woff2 (no network); palette ONLY #061017 ink / #12f6ff cyan / #ff365f crimson / #FFB53D amber; 1px neon borders + corner brackets; scanlines + vignette; 200ms glitch-jitter on breaker/REKT; marquee ticker with duplicated content; motion budget = exactly marquee, 300ms ease, 120ms flash + glitch-jitter; type floors 40/44/56/28px; forbidden: sans-serif body, glassmorphism, purple/blue gradients, rounded cards, emoji icons, sparkle motifs.

## Colors

The palette is exactly four named colors. The CSS source already contains the locked ink, cyan, and crimson; amber is the reserved breaking accent. Other colors still present in the prototype are drift and must not become design tokens.

### Primary
- **CRT Cyan** (`{colors.cyan}`): headlines, prices, active controls, upward market marks, and the primary readable text color.

### Secondary
- **Circuit Crimson** (`{colors.crimson}`): down-market and breaker signals. Pair color with a text label or shape so meaning never depends on color alone. Keep functional text at the 7:1 contrast requirement.

### Tertiary
- **Breaking Amber** (`{colors.amber}`): breaking-news emphasis only; show no more than four amber highlights at once.

### Neutral
- **CRT Ink** (`{colors.ink}`): the single base surface behind the terminal, panels, and controls.

## Typography

**Display Font:** JetBrains Mono (bundled WOFF2; monospace fallback)
**Body Font:** JetBrains Mono (bundled WOFF2; monospace fallback)
**Label/Mono Font:** JetBrains Mono (bundled WOFF2; monospace fallback)

**Character:** Mechanical, broadcast-dense, and stable at distance. All body copy, labels, controls, and figures use bundled JetBrains Mono WOFF2 with a monospace fallback; do not introduce a contrasting face.

### Hierarchy
- **Header** (40px minimum): terminal identity and primary section headers.
- **Wire** (44px minimum): the typewriter headline and analyst readout.
- **Price** (56px minimum): ticker prices and other hero market values; include the ticker on every value.
- **Blotter** (28px minimum): order activity, trader name, action, and ticker.
- **Body and labels** (24px minimum): controls, captions, secondary facts, and every remaining textual value.

## Layout

The main terminal keeps the ticker tape at the top, the chart and headline wire in the dominant reading area, and the blotter and Oddity pod in a supporting column. PRIME TIME and captions occupy clear, separately labeled regions. The current desktop implementation uses a two-column chart-to-support layout and expects a 1920×1080 OBS browser source; preserve the hierarchy while ensuring the core figures remain legible at 100 feet. The ticker marquee duplicates its content so the loop has no blank seam. The operator dashboard remains a distinct control surface.

## Elevation & Depth

Keep the interface flat: no glass, layered shadows, or ornamental depth. Establish separation with the ink ground, 1px neon borders, corner brackets, scanlines, and a vignette. The prototype's additional surface tones and effects are not approved depth tokens.

### Named Rules
**The Broadcast Contrast Rule.** Functional text and numbers must meet 7:1 contrast; every number is paired with its ticker. Crimson and state shapes never carry meaning by color alone.

## Shapes

Cards and panels have square corners (0px radius). Use 1px neon borders with corner brackets; no pills, rounded cards, emoji icons, or decorative glyphs. Keep the tape and control shapes crisp and rectangular.

## Components

### Terminal Panel
- **Shape:** square, framed by a 1px cyan line and corner brackets.
- **Surface:** ink only, with no glass or shadow treatment.
- **Content:** one clear label followed by ticker-labeled values or a single live function.

### Ticker Tape and Tabs
- **Style:** cyan monospace ticker labels on ink; each price includes its ticker.
- **Behavior:** duplicate the tape content for a continuous marquee. Clicking a tape item selects the matching chart ticker.

### Candle Chart and Prices
- **Style:** cyan for upward movement and crimson for downward movement, with explicit ticker labels and redundant direction cues.
- **Hierarchy:** price text uses the 56px floor; do not rely on color alone to communicate a move.

### Headline Wire
- **Style:** breaking copy may use amber, limited to four amber highlights at once; the wire uses the 44px floor.
- **Behavior:** typewriter delivery remains readable with audio off.

### Order Blotter
- **Style:** use the 28px floor. A readable row names the trader, action, quantity, and ticker; BOOTH labels remain visible where present.

### PRIME TIME
- **Style:** square panel with labeled YES/NO ticker bars, a clear countdown, and settlement rows that name each winner and payout.
- **States:** breaker and REKT feedback use the 200ms glitch-jitter; the verdict must remain understandable without sound.

### Operator Controls
- **Style:** square, 1px neon-bordered controls with monospace text at least 24px effective size.
- **Behavior:** mode, stake, probe, and RED-KEY remain available through the keyboard macros; focus and selected state must be visible.

### Oddity Pod
- **Style:** inline vector character inside the framed terminal system; state names and captions stay legible at the body floor.
- **Behavior:** use only the documented pulse-glow and glitch-jitter states; keep the pod secondary to market proof.

## Do's and Don'ts

### Do:
- **Do** use only ink, cyan, crimson, and amber; reserve amber for breaking and cap it at four simultaneous highlights.
- **Do** label every number with its ticker and keep functional contrast at or above 7:1.
- **Do** maintain the 24px effective floor and the larger header, wire, price, and blotter floors.
- **Do** use exactly glitch-jitter, marquee-scroll, and pulse-glow; glitch-jitter lasts 200ms on breakers and REKT.
- **Do** keep live ingress, message counts, named trades, and AI typewriter output visible without implying a false LIVE state.

### Don't:
- **Don't** use sans-serif body text, glassmorphism, purple/blue gradients, rounded cards, emoji icons, or AI-sparkle motifs.
- **Don't** introduce a fifth color, another animation, or a number without its ticker label.
- **Don't** imply real-money betting or hide that deterministic code—not AI—sets prices.
- **Don't** copy the prototype's noncompliant type sizes, extra colors, gradients, or incidental motion into new surfaces.
