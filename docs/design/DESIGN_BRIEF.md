# Seller Autopilot — Master Design Brief: Mission Control

> **This document is the CONTEXT PREAMBLE for every mockup prompt.**
> Paste the relevant sections BEFORE your screen-specific prompt in Stitch, v0, or Lovable.

---

## Stitch Output Audit (v1 Failures — What Went Wrong)

Our first Stitch generation ignored every design constraint and produced a consumer-grade, playful, light-mode page. Below are the 13 documented violations and the hardened guardrails added to prevent recurrence:

| # | What Stitch Generated | What We Specified | Guardrail Added |
|---|----------------------|-------------------|-----------------|
| 1 | Light mode bg #f0f9ff | Dark surface #0d1322 | HARD CONSTRAINT: "dark background #0d1322" repeated 3x in prompt |
| 2 | Fredoka whimsical font | Inter + JetBrains Mono only | EXPLICIT: "do NOT use Fredoka, Poppins, or any rounded/playful font" |
| 3 | Cartoon robot with eyes/smile | No illustrations | EXPLICIT: "ZERO illustrations, ZERO characters, ZERO mascots" |
| 4 | "Woohoo!", "login party", "nudge" | Professional language | EXPLICIT: "NEVER use: Woohoo, party, magic, nudge, Oops, yay" |
| 5 | border-4, border-dashed | No-Line Rule | EXPLICIT: "ZERO visible borders on cards or layout sections" |
| 6 | rounded-3xl (24px) | 4-8px max | EXPLICIT: "border-radius: 8px MAXIMUM. Never rounded-2xl or rounded-3xl" |
| 7 | shadow-2xl, 3D button shadow | Ambient shadows only | EXPLICIT: "NEVER shadow-2xl. NEVER 3D push-button shadows" |
| 8 | Gradient blobs, blur-3xl clouds | No decoration | EXPLICIT: "ZERO background blobs, ZERO blur clouds, ZERO mix-blend" |
| 9 | #3b82f6, #f472b6 | Our token palette | INLINE hex values in every element description |
| 10 | No monospace on email | JetBrains Mono for data | EXPLICIT: "email address in monospace font-family" |
| 11 | Flat white/blue | 7-tier surface hierarchy | Surface hex values embedded directly in element specs |
| 12 | 4s infinite float bounce | Purposeful-only animation | EXPLICIT: "ZERO floating/bouncing animations" |
| 13 | Star/celebration icons | Thin-stroke functional only | EXPLICIT: "ZERO decorative icons — star, celebration, sparkle, favorite" |

---

## 1. Creative North Star: "The High-Density Architect"

This is a **precision instrument** for high-revenue Amazon sellers. NOT a consumer app. NOT playful. NOT whimsical. Think **aerospace Mission Control meets Bloomberg Terminal meets Linear.app**.

**Dark-first. Dense. Editorial. Calm. Authoritative.**

---

## 2. HARD CONSTRAINTS (Paste These First in Every Prompt)

These constraints override all AI design tool defaults. Repeat them at the top AND bottom of every prompt.

```
=== HARD CONSTRAINTS — VIOLATING ANY OF THESE REJECTS THE OUTPUT ===

DARK MODE ONLY:
- Page background MUST be #0d1322 (near-black navy). NEVER white, NEVER light blue, NEVER #f0f9ff.
- ALL surfaces are dark. The lightest surface is #33394a. There is NO white background anywhere.
- This is a DARK application. Dark. Dark. Dark. Not light mode. Not white. Dark.

NO ILLUSTRATIONS / NO CHARACTERS:
- ZERO illustrations. ZERO cartoon characters. ZERO mascots. ZERO robots with faces.
- ZERO decorative SVGs. ZERO whimsical drawings. ZERO anthropomorphic elements.
- If the design needs a visual, use a THIN-STROKE (1.5px) geometric ICON only.

NO PLAYFUL LANGUAGE:
- NEVER use: "Woohoo", "yay", "party", "magic", "nudge", "zipped", "Oops", "awesome", "bam"
- Tone is PROFESSIONAL and DIRECT: "Check your email" not "Woohoo! It's on its way!"
- "Back to sign in" not "Back to the login party"
- "Resend link" not "Give it another nudge!"

NO PLAYFUL FONTS:
- Font is Inter (variable) ONLY. NEVER Fredoka, Poppins, Comic Sans, Nunito, or any rounded/bouncy font.
- JetBrains Mono for data identifiers (emails, ASINs, prices) ONLY.

NO HEAVY BORDERS:
- ZERO visible borders on cards or layout blocks. No border-2, No border-4.
- If a border is absolutely needed: #43474e at 15% opacity ONLY.
- No dashed borders. No dotted borders.

BORDER-RADIUS 8px MAXIMUM:
- border-radius: 8px on cards, buttons, inputs.
- NEVER rounded-2xl (16px). NEVER rounded-3xl (24px). NEVER rounded-full on containers.
- 4px on chips/badges (sharp, technical).

NO MATERIAL / 3D SHADOWS:
- NEVER shadow-2xl. NEVER shadow-lg on cards.
- NEVER 3D push-button effects (shadow-[0_10px_0_rgb(...)]).
- ONLY ambient shadow on floating elements: box-shadow: 0 20px 40px rgba(0,0,0,0.4)

NO DECORATIVE BACKGROUNDS:
- ZERO gradient blobs. ZERO blur-3xl clouds. ZERO mix-blend-multiply effects.
- ZERO background animations (drifting, floating).
- Background is FLAT SOLID color #0d1322. Period.

NO DECORATIVE ICONS:
- ZERO star, sparkle, celebration, favorite, rocket, fire emoji-style icons.
- Icons must be thin-stroke (1.5px), functional, monochrome.

NO FLOATING/BOUNCE ANIMATIONS:
- ZERO float, bounce, drift, or pulse animations on page elements.
- Animation is reserved for: agent status dots (subtle pulse), skeleton loaders (shimmer), and micro-interactions (hover, focus).

===
```

---

## 3. Surface Hierarchy (Tonal Layering)

Depth comes from background color shifts between tiers, NOT from borders or shadows.

```
TOKEN                          HEX         USE
surface                        #0d1322     Page background (deepest)
surface_container_lowest       #111725     Sunken/utility areas
surface_container_low          #151b2b     Sidebar, navigation panels
surface_container              #191f2f     Content cards, primary containers
surface_container_high         #1e2435     Elevated cards, inputs background
surface_container_highest      #2f3445     Popovers, active states, inner cards
surface_bright                 #33394a     Focused widgets, hover states
```

Cards (`#191f2f`) sit on page (`#0d1322`). The color difference IS the card edge. No border needed.

---

## 4. Color Tokens

```
primary                 #abc9f2     Text accents, links, focus states
primary_container       #1b3a5c     Gradient button end, high-emphasis
on_primary              #0e305a     Text on primary surfaces
secondary               #a0caff     Focus rings, secondary interactive
tertiary                #c8bfff     Tags, tertiary accents
on_surface              #e1e2e8     Primary text (light on dark)
on_surface_variant      #c3c6cf     Muted text, labels, placeholders
outline                 #8d9199     Inactive borders (when required)
outline_variant         #43474e     Ghost borders (15% opacity only)

Semantic:
success                 #7dd3a0     Positive (with #2e4a3e container)
warning                 #f59e0b     Attention needed
error                   #ffb4ab     Critical (with #93000a container)

CTA gradient:           linear-gradient(135deg, #abc9f2, #1b3a5c)
Glassmorphism:          rgba(30,36,53,0.80) + backdrop-filter: blur(12px)
```

### Agent Colors (Status Dots + Left-Border Only)
```
Listing #a0caff | Inventory #7dd3a0 | Advertising #f4a261
Pricing #c8bfff | Analytics #5eead4 | Compliance #8d9199 | Orchestrator #f9a8d4
```

---

## 5. Typography

```
UI Font:      Inter (variable) — NEVER any other font
Data Font:    JetBrains Mono — emails, ASINs, SKUs, prices, IDs

Display       3.5rem / 600  Inter    -0.02em     Hero numbers
Headline L    2rem / 600    Inter    -0.02em     Page titles
Headline M    1.5rem / 600  Inter    -0.02em     Section/card headings
Title         1.125rem / 500 Inter   normal      Subheadings
Body          0.875rem / 400 Inter   normal      Default text
Body Sm       0.8125rem / 400 Inter  normal      Table cells, dense content
Label L       0.75rem / 500 Inter    0.05em CAPS Column headers, metadata labels
Label S       0.6875rem / 500 Inter  0.05em CAPS Tags, timestamps, micro-labels
Mono Data     0.8125rem / 400 JBMono normal      ASINs, $24.99, B08XYZ, seller@email.com
```

- Headlines use tight letter-spacing (-0.02em) for a "newsroom" compact feel
- Labels are ALL-CAPS with 0.05em tracking in `on_surface_variant` (#c3c6cf)
- Numbers use `font-variant-numeric: tabular-nums`
- Sentence case everywhere EXCEPT labels

---

## 6. Component Patterns

**Cards:** `#191f2f` bg, ZERO border, 8px radius, 16px padding. On `#0d1322` page.
**Stat Cards:** Display 3.5rem hero number + Label CAPS above + trend pill + optional sparkline.
**Agent Cards:** 3px left-border in agent color + dot + approve/reject.
**Buttons:**
- Primary: `linear-gradient(135deg, #abc9f2, #1b3a5c)`, text `#0e305a`, 8px radius, 44px height
- Secondary: `#2f3445` bg, no border, text `#e1e2e8`
- Ghost: transparent, text `#e1e2e8`, bg appears on hover (`#1e2435`)
- NEVER 3D shadows on buttons. NEVER rounded-2xl on buttons.

**Inputs:** 44px height, 8px radius, `#1e2435` bg, floating label, ghost border (`#43474e` at 15%), `#a0caff` on focus.
**Tables:** ZERO dividers, 4px row gap, Label CAPS headers, Body Sm content, hover = `#151b2b`.
**Chips:** 4px radius (sharp), 24px height, token-colored.
**Empty States:** Thin-stroke icon 48px + headline + one sentence + CTA button. ZERO illustrations.

---

## 7. Spacing
```
Card padding:        16px
Between cards:       24px gap
Section separation:  28-36px (REPLACES horizontal rules)
Table row gap:       4px (REPLACES dividers)
Page top margin:     48px below header
Sidebar:             256px / 56px collapsed
Top bar:             56px height
```

---

## 8. Animation
- Agent status: 2s subtle pulse on active dots ONLY
- Skeleton loaders: shimmer sweep 1.5s
- Hover: 150ms opacity/bg transitions
- Modals: 200ms fade + 10px slide-up
- NEVER: float, bounce, drift, cloud, infinite decorative animations
- All respect `prefers-reduced-motion`

---

## 9. Prompt Template

Use this structure for EVERY mockup prompt:

```
[Paste Section 2: HARD CONSTRAINTS — the full block between === markers]

DESIGN SYSTEM TOKENS:
Page background: #0d1322
Card surfaces: #191f2f (no border, sits on #0d1322)
Input backgrounds: #1e2435
Primary text: #e1e2e8 (Inter)
Muted text: #c3c6cf (Inter)
Primary accent: #abc9f2
CTA button: linear-gradient(135deg, #abc9f2, #1b3a5c), text #0e305a
Focus/links: #a0caff
Data font: JetBrains Mono for emails, ASINs, prices
Danger: #ffb4ab with 3px left-border accent (not full-red backgrounds)

[Paste the specific screen description with inline hex values on every element]

FINAL REMINDER — REJECT CRITERIA:
If the output has ANY of these, regenerate:
- White or light background (anything lighter than #33394a)
- Cartoon illustrations, mascots, or characters
- Fredoka, Poppins, or any rounded font
- "Woohoo", "party", "magic", "awesome" or other playful text
- Visible borders (>1px) on cards or layout sections
- rounded-2xl or rounded-3xl on any element
- Shadow-2xl or 3D push-button shadows
- Background gradient blobs or blur clouds
- Decorative star/sparkle/celebration icons
- Floating or bouncing animations
```

---

## 10. Do's and Don'ts (Quick Reference)

### Do
- ✅ Dark surfaces (#0d1322 → #33394a tonal layers) for ALL backgrounds
- ✅ Inter + JetBrains Mono ONLY
- ✅ Gradient CTA button: `linear-gradient(135deg, #abc9f2, #1b3a5c)`
- ✅ Glassmorphism on modals/popovers (blur + 80% opacity surface)
- ✅ 8px max border-radius (4px for chips)
- ✅ Spacing (28-36px) instead of divider lines
- ✅ Thin-stroke (1.5px) monochrome icons
- ✅ Professional, direct language
- ✅ High data density — power users want MORE information

### Don't
- ❌ Light/white backgrounds (NEVER)
- ❌ Illustrations, characters, mascots, cartoon robots (NEVER)
- ❌ Playful fonts: Fredoka, Poppins, Nunito, Comic Sans (NEVER)
- ❌ Playful language: Woohoo, party, magic, nudge, Oops (NEVER)
- ❌ Visible borders (>1px) for layout sectioning (NEVER)
- ❌ rounded-2xl or larger (NEVER)
- ❌ Shadow-2xl, 3D button shadows (NEVER)
- ❌ Gradient blobs, blur clouds, decorative backgrounds (NEVER)
- ❌ Decorative icons: stars, sparkles, celebration, favorite (NEVER)
- ❌ Floating/bouncing/drifting animations (NEVER)
- ❌ Material Design elevation patterns (NEVER)
- ❌ Zebra striping on tables (NEVER)
