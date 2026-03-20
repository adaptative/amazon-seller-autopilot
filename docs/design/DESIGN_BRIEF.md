# Seller Autopilot — Master Design Brief: Mission Control

> **This document is the CONTEXT PREAMBLE for every mockup prompt.**
> Paste this BEFORE your screen-specific prompt when using Stitch, v0, Lovable, or any AI design tool.

---

## 1. Creative North Star: "The High-Density Architect"

This is NOT a generic dashboard. It is a **precision instrument** for high-revenue Amazon sellers. We reject the "bubbly" consumer web in favor of a sophisticated, editorial aesthetic inspired by **aerospace interfaces and high-end IDEs**.

The system breaks the "template" look by rejecting traditional grid-lines in favor of **Tonal Layering** — using the interplay between surface container tiers and Inter typography to create an environment that feels expansive yet structured, like a high-end physical workstation.

### Brand Personality
| Trait | Expression |
|-------|-----------|
| **Authoritative** | Deep navy surfaces, structured layouts, decisive typography |
| **Intelligent** | Subtle agent activity animations, contextual AI insights, data-first hierarchy |
| **Calm** | No visual noise, no flashing alerts, ambient depth instead of hard lines |
| **High-Density** | Data-rich screens — sellers want MORE data, not excessive whitespace |
| **Premium** | Glassmorphism on floating elements, gradient CTAs, ambient shadows, editorial type |

### Visual Benchmarks (Looks Like)
- **Aerospace Mission Control / Bloomberg Terminal** — High-density data, dark surfaces, calm authority
- **Linear.app** — Clean, monochrome, strategic color accents
- **Vercel Dashboard** — Dark mode elegance, surface layering, professional depth
- **Warp Terminal / Fig** — Modern IDE aesthetic, tonal layering, crisp monospace for data

### Anti-Patterns (Must NOT Look Like)
- Amazon Seller Central (dated, orange, anxious, white backgrounds)
- Helium 10 (neon "hacker" aesthetic, overwhelming)
- Generic Bootstrap admin templates (soulless, 1px borders everywhere)
- Material Design dashboards (rounded, bubbly, consumer-grade drop shadows)

---

## 2. Application Context

Seller Autopilot is a **B2B SaaS** for Amazon sellers replacing 7+ disconnected tools with a **single AI-powered command center.** Think "Mission Control for Amazon sellers" — a calm, authoritative interface where AI agents work visibly in the background while the seller makes strategic decisions.

**Users:** Amazon private-label sellers doing $10K-$500K/month, ages 28-55, spending 4-8 hours/day in tools. They're overwhelmed, anxious, exhausted. Our UI transforms them: Overwhelmed → Informed → Confident → In Command.

---

## 3. Colors & Surface Logic

### Surface Hierarchy (Tonal Layering — "Synthetic Obsidian")
```
surface                    #0d1322   Main page background (deepest)
surface_dim                #0d1322   Furthest background, recessed
surface_container_lowest   #111725   Sunken/utility areas
surface_container_low      #151b2b   Sidebar, navigation panels
surface_container          #191f2f   Content cards, primary containers
surface_container_high     #1e2435   Elevated cards, nested containers
surface_container_highest  #2f3445   Popovers, active elements, inner cards
surface_bright             #33394a   "Pop-out" widgets, focused elements
```

### The "No-Line" Rule (CRITICAL)
1px solid borders are PROHIBITED for layout sectioning. Use background color shifts between surface tiers instead. Ghost borders (outline_variant #43474e at 15% opacity) only where accessibility requires them.

### Primary & Semantic Colors
```
primary                #abc9f2   Accents, links, focused states
primary_container      #1b3a5c   Button backgrounds, high-emphasis containers
on_primary             #0e305a   Text on primary surfaces
secondary              #a0caff   Focus rings, secondary interactive
tertiary               #c8bfff   Tertiary accents, tags
on_surface             #e1e2e8   Primary text (light on dark)
on_surface_variant     #c3c6cf   Secondary/muted text
outline                #8d9199   Inactive input borders
outline_variant        #43474e   Ghost borders (at 15% opacity)
```

### Semantic Status Colors
```
success/tertiary_container  #2e4a3e   Positive trends, healthy
warning                     #f59e0b   Low stock, approaching limits
error                       #ffb4ab   Critical alerts
error_container             #93000a   Error badge backgrounds
```

### Agent Colors (Dots + Left-Border Accent Only)
```
Listing #a0caff | Inventory #7dd3a0 | Advertising #f4a261
Pricing #c8bfff | Analytics #5eead4 | Compliance #8d9199 | Orchestrator #f9a8d4
```

### Glassmorphism (Floating Elements)
```css
background: rgba(30, 36, 53, 0.80);
backdrop-filter: blur(12px);
border: 1px solid rgba(67, 71, 78, 0.15);
```

### CTA Gradient
```css
background: linear-gradient(135deg, #abc9f2, #1b3a5c);
```

---

## 4. Typography

```
Inter (Variable):     UI voice — all headings, body, labels
JetBrains Mono:       Data voice — ASINs, SKUs, prices, IDs (signals "immutable data")

Display    3.5rem/600   Inter   -0.02em     Hero revenue/profit numbers
Headline L 2rem/600     Inter   -0.02em     Page titles
Headline M 1.5rem/600   Inter   -0.02em     Section headers
Title      1.125rem/500 Inter   normal      Card headers
Body       0.875rem/400 Inter   normal      Default text
Body Sm    0.8125rem/400 Inter  normal      Table cells, dense data
Label L    0.75rem/500  Inter   0.05em CAPS Column headers, metadata
Label S    0.6875rem/500 Inter  0.05em CAPS Tags, timestamps
Mono       0.8125rem/400 JBMono normal      ASINs, SKUs, $prices
```

---

## 5. Spacing & Layout
```
Sidebar: 256px expanded / 56px collapsed | Top bar: 56px
Card padding: 16px | Between cards: 24px gap
Section separation: 28px or 36px (REPLACES horizontal rules)
Table row gap: 4px vertical (REPLACES dividers)
```

---

## 6. Component Rules

**Cards:** surface_container bg, NO border, 8px radius, p-4. Color difference with surface IS the edge.
**Stat Cards:** Display (3.5rem) hero number + Label CAPS above + trend pill badge + optional sparkline.
**Agent Cards:** 3px left-border in agent color + agent dot + approve/reject buttons.
**Tables:** NO dividers, 4px row gap, hover = surface_container_low, Label CAPS headers, Body Sm content.
**Buttons:** Primary = gradient CTA. Secondary = surface_container_highest, no border. Tertiary = ghost.
**Inputs:** surface_container_high bg, floating label, ghost border, secondary color on focus.
**Chips:** 4px radius (sharp/technical), 24px height.
**Empty States:** Thin-stroke icon (no illustrations), professional language (no "Oops!").
**Shadows:** Ambient only (0 20px 40px rgba(0,0,0,0.4)) on floating elements. Never 100% black.

---

## 7. Do's and Don'ts

**Do:** JetBrains Mono for all data | Spacing 8-10 instead of lines | High density | Tonal layering | Gradient CTAs | Glassmorphism on overlays
**Don't:** 1px borders for layout | Black shadows | Illustrations/playful icons | Primary for backgrounds | Material shadows | Zebra striping | Bubbly corners | "Oops!" language
