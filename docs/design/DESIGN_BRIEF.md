# Seller Autopilot — Master Design Brief

> **This document is the CONTEXT PREAMBLE for every mockup prompt.**  
> Paste this BEFORE your screen-specific prompt when using Stitch, v0, Lovable, or any AI design tool.  
> It gives the AI the full picture: who uses this, how it feels, what it looks like, and what it must NOT look like.

---

## 1. What This Product Is

Seller Autopilot is a **B2B SaaS platform** for Amazon sellers. It replaces 7+ disconnected tools (Helium 10, Jungle Scout, Perpetua, Seller Snap, etc.) with a **single AI-powered command center** where intelligent agents manage listings, pricing, advertising, inventory, analytics, and compliance — while the seller makes strategic decisions.

Think of it as **"Mission Control for Amazon sellers"** — a calm, authoritative interface where complex data is organized into clear action items, and AI agents work visibly in the background like a team of expert employees reporting to the seller.

## 2. Who Uses This

### Primary Users
- **Amazon private-label sellers** doing $10K–$500K/month in revenue
- Ages 28–55, mix of technical and non-technical
- They spend 4-8 hours/day in Seller Central, ad consoles, and spreadsheets
- They're overwhelmed by data, anxious about competitor moves, and exhausted by manual work
- They want to feel **in control without doing the work** — like a CEO with a great team

### Secondary Users
- **Agency managers** overseeing 10-50 client seller accounts
- **Team members** (VAs, ad specialists) who handle specific functions

### User Emotional Journey
```
BEFORE our product: Overwhelmed → Anxious → Reactive → Exhausted
AFTER our product:  Informed → Confident → Strategic → Relieved
```

The UI must facilitate this emotional transformation. Every screen should make the seller feel like they have **superhuman awareness** of their business.

## 3. Visual Identity & Aesthetic Direction

### Brand Personality
| Trait | Expression |
|-------|-----------|
| **Authoritative** | Navy/dark blues for primary UI, structured layouts, decisive typography |
| **Intelligent** | Subtle agent activity animations, smart data highlights, contextual insights |
| **Trustworthy** | Clean forms, clear confirmations, visible audit trails, no hidden actions |
| **Calm** | Generous whitespace, muted backgrounds, no visual noise, no flashing alerts |
| **Premium** | Refined shadows, polished micro-interactions, Apple-level attention to detail |

### What We Look Like (Inspiration Benchmarks)
- **Linear** — Clean, minimal, monochrome with strategic color. The "developer tool that doesn't look like a developer tool" aesthetic.
- **Vercel Dashboard** — Dark mode elegance, clear data hierarchy, professional without being corporate.
- **Stripe Dashboard** — Trustworthy financial data display. Perfect balance of density and breathing room.
- **Notion** — Warm neutrals, readable typography, feels approachable despite being powerful.
- **Arc Browser** — Modern, bold, thoughtful use of color as functional communication.

### What We Do NOT Look Like
- ❌ **Helium 10** — Cluttered, overwhelming, neon-on-dark "hacker" aesthetic, too many features fighting for attention
- ❌ **Jungle Scout** — Generic SaaS, bland, forgettable, no personality
- ❌ **Amazon Seller Central** — Dated, confusing navigation, inconsistent patterns, anxious orange alerts everywhere
- ❌ **Generic Bootstrap admin templates** — Soulless, cookie-cutter, blue-header-white-card repetition
- ❌ **Crypto/fintech dashboards** — Dark neon, gradients, "futuristic" gimmicks, overwhelming chart density

## 4. Color System

### Primary Palette
```
Navy (Primary)      #1B3A5C → Sidebar, headers, primary buttons, key text
                    Used for: authority, trust, professionalism
                    
Slate (Backgrounds) #F8FAFC (light) / #0F172A (dark mode)
                    Used for: page backgrounds, card surfaces
                    
White               #FFFFFF
                    Used for: card surfaces (light mode), text on dark

Blue Accent         #4A90D9 → Links, selected states, focus rings
                    Used for: interactive elements, secondary emphasis
```

### Semantic Colors (used sparingly — only for status communication)
```
Success/Green       #22C55E → Buy Box won, stock healthy, listing active, positive trends
Warning/Amber       #F59E0B → Low stock, approaching limits, attention needed
Danger/Red          #EF4444 → Out of stock, listing suppressed, account health critical, negative trends  
Info/Blue           #3B82F6 → AI suggestions, informational tooltips, neutral updates
```

### Agent Accent Colors (each AI agent has a subtle identity color)
```
Listing Agent       #3B82F6 (Blue)    — content, creativity
Inventory Agent     #22C55E (Green)   — stock, health
Advertising Agent   #F97316 (Orange)  — energy, spend, campaigns
Pricing Agent       #8B5CF6 (Purple)  — strategy, intelligence
Analytics Agent     #14B8A6 (Teal)    — insights, data
Compliance Agent    #6B7280 (Gray)    — rules, structure
Orchestrator        #EC4899 (Pink)    — coordination across agents
```

> Agent colors appear ONLY on: agent status dots, agent icon backgrounds, and the left-border accent on agent action cards. They never dominate a screen.

### Color Application Rules
- **80% of the UI is neutral** (navy, slate, white, gray) — color is reserved for meaning
- **Never use color purely for decoration** — every colored element communicates status, identity, or action
- **Data visualizations** use the agent palette or semantic colors, never random rainbow colors
- **Dark mode** inverts backgrounds but keeps the same accent colors — test every screen in both modes

## 5. Typography

### Font Stack
```
Primary:    Inter (variable, weights 400/500/600)
Monospace:  JetBrains Mono (for ASINs, prices, code, API responses)
```

### Type Scale
```
Display:    36px / 600 weight — Hero numbers (revenue, profit) on dashboard
H1:         30px / 600 weight — Page titles ("Listing Management", "Advertising")
H2:         24px / 600 weight — Section headers ("Campaign Performance", "Buy Box Tracker")
H3:         20px / 500 weight — Card headers, widget titles
H4:         16px / 500 weight — Table headers, form section labels
Body:       14px / 400 weight — Default text, descriptions, table cells
Small:      13px / 400 weight — Helper text, timestamps, secondary info
Caption:    12px / 400 weight — Labels, tags, metadata
Monospace:  13px / 400 weight — ASINs (B08XYZ123), prices ($24.99), SKUs
```

### Typography Rules
- **Numbers are hero elements** — revenue, profit, ACoS should be the largest text on any screen
- **Never bold entire paragraphs** — bold only labels, column headers, and emphasis words
- **Monospace for all Amazon identifiers** — ASINs, SKUs, Order IDs, Campaign IDs get monospace treatment
- **Tabular figures for numbers** — so columns of numbers align vertically in tables (use `font-variant-numeric: tabular-nums`)
- **Sentence case everywhere** — never ALL CAPS except acronyms (ASIN, ACoS, ROAS)

## 6. Layout & Spacing System

### Grid
```
Max content width:  1440px (centered on wide screens)
Column grid:        12-column grid with 24px gutters
Card grid:          CSS Grid with gap-6 (24px) between cards
Sidebar width:      256px expanded, 64px collapsed
Top bar height:     64px
```

### Spacing Scale (8px base unit)
```
2px  — Border radius on small elements (badges, tags)
4px  — Tight spacing within components
8px  — Default padding within compact elements (badges, pills)
12px — Vertical space between related items
16px — Standard padding inside cards and panels
24px — Gap between cards and major sections
32px — Vertical space between page sections
48px — Top margin for page content below header
```

### Layout Principles
- **F-pattern reading flow** — most important data top-left, actions top-right
- **Consistent card patterns** — all cards have: 16px padding, 8px border-radius, subtle border (1px #E2E8F0), no shadow in light mode (1px border is enough), subtle shadow in dark mode
- **Data density is high but organized** — this is a power tool, not a marketing page. Show more data, but with clear visual hierarchy
- **Whitespace is intentional** — breathing room between sections, but not wasteful. Sellers want information density
- **Sticky elements** — sidebar, top bar, and table headers should be sticky on scroll
- **Progressive disclosure** — show summary first, details on click/expand. Don't overwhelm on first glance

## 7. Component Patterns

### Cards
```
Standard Card:     White bg, 1px border #E2E8F0, rounded-lg (8px), p-4 (16px), no shadow
                   Header: H4 bold + optional subtitle muted + optional action button right-aligned
                   Dark mode: bg-slate-900, border-slate-700

Stat Card:         Same as standard card but with:
                   - Hero number (Display size, 36px, font-semibold)
                   - Label below (Caption size, muted)
                   - Trend indicator (↑12.5% green or ↓3.2% red)
                   - Optional sparkline chart (64px tall, right-aligned)

Agent Action Card: Same as standard card but with:
                   - Left border 3px in agent accent color
                   - Agent icon + name badge top-left
                   - Action description (Body)
                   - "View reasoning" expandable section
                   - Approve (green) + Reject (outline) buttons bottom-right
                   - Priority indicator: subtle background tint
```

### Tables
```
Design:            Clean horizontal rules only (no vertical borders, no zebra striping)
                   Header row: uppercase caption (12px), font-medium, muted color, sticky
                   Data rows: 48px min-height, comfortable padding
                   Hover: subtle bg-slate-50 highlight
                   Selected: blue-50 background with blue left border
                   
Key behaviors:     Sortable columns with arrow indicators
                   Inline editing for prices, bids (click to edit, enter to save)
                   Row expansion for detail panels
                   Bulk selection with floating action bar
```

### Charts & Data Visualization
```
Chart style:       Clean, minimal. No 3D effects, no gradients in chart fills.
                   Line charts: 2px stroke, dot markers on hover only
                   Bar charts: rounded-top corners (4px), subtle gaps between bars
                   Area charts: 10% opacity fill under lines
                   Colors: use agent palette or semantic colors, never random
                   
Axis labels:       Caption size (12px), muted color, rotated 0° (never diagonal)
Tooltips:          Dark card (#1E293B) with white text, rounded-lg, appears on hover
Grid lines:        Dashed, very light (#F1F5F9), horizontal only
Legend:             Below chart, horizontal, small colored dots + labels
```

### Empty States
```
Layout:            Centered in the container area
                   Illustration: simple, single-color line art (not cartoon, not 3D)
                   Heading: "No campaigns yet" (H3)
                   Description: one sentence explaining why and what to do
                   CTA button: primary action to resolve the empty state
                   Tone: encouraging, not condescending
```

## 8. Animation & Micro-Interactions

### Principles
- **Purposeful only** — every animation communicates something (loading, transition, status change)
- **Fast** — 150ms for hover states, 200ms for panel transitions, 300ms max for page transitions
- **Subtle** — opacity fades, gentle slides, slight scale changes. No bouncing, no spinning, no dramatic effects
- **Reduced motion respected** — all animations wrapped in `prefers-reduced-motion` media query

### Specific Animations
```
Agent status pulse:     Soft pulsing ring (2s loop) on the status dot when an agent is actively working
Activity feed items:    Slide-in from right (200ms) when new items arrive via WebSocket
Approval card:          Gentle scale-up (1.0→1.02) on hover, green flash on approve, fade-out on complete
Stat card trend arrow:  Subtle bounce-up on load (100ms delay after number renders)
Sidebar collapse:       Width transition (200ms ease) with icon fade-in
Chart data:             Points draw left-to-right (500ms) on first load only
Skeleton loaders:       Gentle shimmer (1.5s loop), shape matches the content being loaded
```

## 9. Responsive Behavior

```
Desktop (>1440px):   Full sidebar (256px) + 3-column widget grid + full tables
                     This is the PRIMARY experience — optimize for 1920×1080 screens
                     
Laptop (1024-1440):  Full sidebar + 2-column widget grid + full tables
                     Slightly tighter spacing, same information density

Tablet (768-1024):   Collapsed sidebar (64px icons) + 2-column grid + horizontal scroll tables
                     Touch-friendly: 44px minimum tap targets

Mobile (<768):       No sidebar — bottom navigation bar (5 items)
                     Single column + cards stacked vertically
                     Tables become card-list view (one card per row)
                     Priority: approval queue, key metrics, alerts
                     This is a CHECK-IN experience, not a WORK experience
```

## 10. Dark Mode Specification

```
Background levels:   bg-page: #0B1120    (deepest — page background)
                     bg-card: #111827    (card surfaces)
                     bg-elevated: #1E293B (popovers, dropdowns, tooltips)
                     
Borders:             #1E293B (subtle) → #334155 (emphasized)
Text:                primary: #F1F5F9, secondary: #94A3B8, muted: #64748B
Accent colors:       Same as light mode (they're designed to work on both)

Key rules:
- Dark mode is NOT just "invert everything" — it's a separate considered palette
- Charts look BETTER in dark mode — vibrant lines on dark backgrounds
- Subtle glows replace shadows (box-shadow with blue/purple tint, 0.1 opacity)
- Seller Central has no dark mode — this is a competitive advantage
```

## 11. Accessibility Requirements

```
Contrast:            WCAG AA minimum (4.5:1 for body text, 3:1 for large text)
Focus indicators:    Visible 2px ring in blue accent color on all interactive elements
Keyboard navigation: Full tab order, arrow key navigation in menus/tables, Escape to close modals
Screen readers:      Proper ARIA labels on all interactive elements, live regions for real-time updates
Color independence:  Never use color alone to convey meaning — always pair with text, icons, or patterns
Motion:              Respect prefers-reduced-motion, provide static alternatives
Font sizes:          Minimum 12px for any visible text, 14px for primary content
```

---

## HOW TO USE THIS DOCUMENT IN PROMPTS

When generating a mockup in Stitch/v0/Lovable, **prepend the relevant sections** before your screen-specific prompt:

```
[Paste Section 1 (What This Product Is)]
[Paste Section 2 (Who Uses This)]
[Paste Section 3 (Visual Identity — especially the "looks like" and "NOT like" benchmarks)]
[Paste Sections 4-5 (Colors + Typography)]
[Paste relevant parts of Section 7 (Component Patterns) for the specific screen]

Now, with that context, design the following screen:
[Your specific screen prompt here]
```

The AI design tool now understands:
- ✅ The product domain (Amazon selling)
- ✅ The user's emotional state (overwhelmed → confident)
- ✅ The aesthetic target (Linear/Vercel/Stripe, NOT Helium 10)
- ✅ The exact color palette, type scale, and spacing rules
- ✅ Component patterns and data density expectations
- ✅ What specifically to avoid
