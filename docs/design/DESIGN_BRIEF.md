# Seller Autopilot — Master Design Brief: Joyful Tech

> **This document is the CONTEXT PREAMBLE for every mockup prompt.**
> Extracted from the approved Stitch reference (`docs/design/stitch-audit/v2-approved-reference.html`).
> Every screen in the application MUST match this aesthetic.

---

## 1. Creative North Star: "The Joyful Copilot"

Seller Autopilot is a **friendly, approachable AI companion** that makes the complexity of Amazon selling feel light and manageable. The aesthetic is **bright, playful, warm, and encouraging** — like a brilliant assistant who also happens to have a great personality.

We reject the dark, clinical "Bloomberg Terminal" approach. Instead, we embrace the idea that **professional tools can be delightful**. Sellers already spend their days in the anxiety-inducing UX of Amazon Seller Central. Our product is the antidote — a place that feels good to open, celebrates wins, and makes hard tasks feel easy.

### Brand Personality
| Trait | Expression |
|-------|-----------|
| **Joyful** | Bright sky-blue backgrounds, playful character mascot, celebratory language |
| **Warm** | Fredoka rounded typeface, pink accents, soft gradients, encouraging copy |
| **Trustworthy** | Clean layouts, clear data, blue primary — reliable but not boring |
| **Playful** | 3D push buttons, floating animations, decorative sparkle icons, dashed borders |
| **Smart** | Data identifiers styled distinctly, clear hierarchy, professional when it matters |

### Visual Benchmarks (Looks Like)
- **Notion** (warmth + approachability) crossed with **Duolingo** (character + celebration)
- **Linear** (clean structure) crossed with **Headspace** (calming, encouraging)
- **Stripe** (data clarity) crossed with **Figma** (personality + delight)
- **Lottie / Rive animations** — playful micro-interactions that reward user actions

### Anti-Patterns (Must NOT Look Like)
- ❌ Amazon Seller Central (anxiety-inducing, orange alerts, dated)
- ❌ Bloomberg Terminal / dark "hacker" dashboards (intimidating, cold)
- ❌ Generic Bootstrap admin templates (soulless, no personality)
- ❌ Enterprise B2B grey-on-grey (boring, forgettable)
- ❌ Crypto/fintech dark neon (try-hard, untrustworthy)

---

## 2. Application Context

**Seller Autopilot** is a B2B SaaS for Amazon sellers. AI agents handle listings, pricing, ads, inventory, and compliance. The seller focuses on strategy while the AI handles execution.

**Users:** Amazon sellers ($10K-$500K/month), ages 28-55. They're stressed from Amazon's complexity. Our UI is the relief — the place where things just work and progress feels celebratory.

**Emotional Journey:**
```
BEFORE:  Overwhelmed → Anxious → Reactive → Exhausted
AFTER:   Supported → Confident → Celebratory → In Control
```

The mascot character is their **AI copilot** — friendly, always working, always celebrating wins with them.

---

## 3. Color System

### Primary Palette
```
TOKEN            HEX         TAILWIND           ROLE
─────────────────────────────────────────────────────────────────────
primary-pop      #3b82f6     blue-500           Primary buttons, links, headings, character accent,
                                                 logo, interactive elements. The hero color.
accent-joy       #f472b6     pink-400           Secondary accent: resend links, decorative elements,
                                                 antenna, heart icons, selection highlight
sky-joy          #e0f2fe     sky-100            Top of page gradient, sky feeling
surface          #ffffff     white              Card backgrounds, character body, input surfaces
on-surface       #1e293b     slate-800          Primary text — headings, body, high-emphasis
```

### Extended Palette
```
page-bg          #f0f9ff     sky-50 variant     Page background (lightest sky)
text-muted       #475569     slate-600          Body text, descriptions
text-lighter     #94a3b8     slate-400          Footer text, timestamps, helper text
blue-dark        #1e3a8a     blue-900           3D button shadow base
yellow-pop       #facc15     yellow-400         Star decoration, celebration accents
pink-soft        #fce7f3     pink-50            Soft background blobs
blue-light       #dbeafe     blue-100           Background blobs, soft decorations
```

### Page Background Treatment (CRITICAL — Defines the Entire Feel)
The page is NEVER a flat color. It's a living, breathing sky:
```
Layer 1 (base):     bg-gradient-to-b from-[#e0f2fe] via-[#f0f9ff] to-[#ffffff]
Layer 2 (clouds):   Drifting white blobs (bg-white/60, rounded-full, blur-3xl) — slow 15s animation
Layer 3 (blue):     Bottom-left blue blob (bg-blue-100, 600px, opacity-40, mix-blend-multiply, blur-3xl)
Layer 4 (pink):     Top-right pink blob (bg-pink-50, 500px, opacity-50, mix-blend-multiply, blur-3xl)
Layer 5 (yellow):   Bottom-left subtle (bg-yellow-100, 48px, blur-2xl, opacity-40)
Layer 6 (blue):     Bottom-right subtle (bg-primary-pop/10, blur-3xl, opacity-30)
```

This layered gradient-blob background is used on **all auth screens, onboarding, marketing pages, and empty states.** Dashboard and data-heavy screens use a simplified version (just Layer 1 gradient, no blobs).

### Selection Color
```css
selection: bg-accent-joy/30  /* Pink-tinted text selection across the app */
```

---

## 4. Typography

### Dual Font System
```
Whimsical Voice:  Fredoka (400/600/700) — for headlines, buttons, logo, celebration moments
                  This font makes everything feel friendly and approachable.
                  Google Fonts: family=Fredoka:wght@400;600;700

Body Voice:       Inter (400/500/600) — for body text, UI chrome, data, descriptions
                  Clean and professional when it matters.
                  Google Fonts: family=Inter:wght@400;500;600
```

### Type Scale
```
ROLE              SIZE               WEIGHT   FONT      USAGE
─────────────────────────────────────────────────────────────────────
Display Hero      text-6xl/text-7xl  700      Fredoka   "Woohoo!" celebration headings
                  (3.75rem → 4.5rem)                    tracking-tight, leading-tight

Headline          text-3xl/text-4xl  700      Fredoka   Page titles, section hero text
                  (1.875rem → 2.25rem)

Section Head      text-2xl           600      Fredoka   Card section headers, widget titles
                  (1.5rem)

Button Text       text-xl            700      Fredoka   Primary CTA buttons
                  (1.25rem)

Logo Text         text-lg            700      Fredoka   "Seller Autopilot" in footer/header
                  (1.125rem)

Body Large        text-lg/text-xl    500      Inter     Descriptions, subtitles
                  (1.125rem → 1.25rem)

Body              text-base          400      Inter     Default text, form labels
                  (1rem)

Body Small        text-sm            400/500  Inter     Footer links, helper text, timestamps
                  (0.875rem)

Data Identifier   text-base          700      Inter     Emails, ASINs — styled in primary-pop
                  (1rem)                               with dashed border badge treatment
```

### Typography Rules
- **Fredoka for everything the user FEELS** — headings, buttons, celebration text, logo
- **Inter for everything the user READS** — body text, data, descriptions, form labels
- **Data identifiers** (emails, ASINs, SKUs) get a special badge: `inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30 rounded-lg text-primary-pop font-bold`
- **tracking-tight** on Display and Headline scales
- **leading-relaxed** on body text for comfortable reading
- **Hero numbers** (revenue, profit) use Fredoka at Display scale

---

## 5. The Mascot Character

A core brand element — a **friendly robot/mail envelope character** that appears on:
- Auth screens (success states, error states, loading)
- Empty states (waving, pointing, encouraging)
- Celebration moments (confetti, sparkles, floating)
- Onboarding (guiding, explaining)

### Character Construction (CSS/SVG)
```
Body:            w-64 h-48, bg-white, border-4 border-primary-pop, rounded-3xl, shadow-2xl
Upper half:      bg-blue-50, border-b-4 border-primary-pop/20 (envelope flap)
Eyes:            Two w-4 h-4 bg-slate-800 rounded-full circles, gap-6
Smile:           w-8 h-4 border-b-4 border-slate-800 rounded-full (curved bottom border)
Arms:            Two w-16 h-4 bg-primary-pop rounded-full — left rotated 12°, right rotated -12°
Antenna:         w-1 h-12 bg-slate-400 vertical line, topped with w-12 h-2 bg-accent-joy pill
Heart badge:     Top-right corner, border-2 border-accent-joy/40, favorite icon
Shadow:          drop-shadow(0 20px 30px rgba(59, 130, 246, 0.3))
Animation:       float — translateY(-20px) rotate(2deg), 4s ease-in-out infinite
```

### Decorative Sparkle Icons (Around Character)
```
Star:            material-symbols star, text-yellow-400, text-4xl, top-left
Sparkle:         material-symbols auto_awesome, text-primary-pop, text-3xl, top-right
Celebration:     material-symbols celebration, text-pink-400, text-3xl, bottom-center
```

### When to Use the Character
- ✅ Auth success/error states
- ✅ Empty states ("No campaigns yet" — character waving)
- ✅ Onboarding wizard steps
- ✅ Achievement celebrations ("Buy Box won!", "ACoS target hit!")
- ❌ NOT on data-heavy dashboard screens (too distracting from data)
- ❌ NOT on tables or analytics (the data is the star there)

---

## 6. Component Patterns

### Primary CTA Button (The "3D Push Button" — Signature Element)
```css
/* This tactile, pushable button is a brand signature. Use on all primary CTAs. */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 20px 40px;                              /* px-10 py-5 */
  font-family: 'Fredoka', sans-serif;
  font-size: 1.25rem;                              /* text-xl */
  font-weight: 700;
  color: white;
  background-color: #3b82f6;                       /* primary-pop */
  border-radius: 16px;                             /* rounded-2xl */
  box-shadow: 0 10px 0 rgb(30, 58, 138);          /* 3D depth — blue-900 */
  transition: all 200ms;
}
.btn-primary:hover {
  background-color: #1e293b;                       /* slate-900 */
  box-shadow: 0 5px 0 rgb(0, 0, 0);               /* Compressed shadow */
  transform: translateY(5px);                      /* Pushed down */
}
.btn-primary:active {
  box-shadow: none;                                /* Fully pressed */
  transform: translateY(8px);
}
```

### Secondary Button
```
Background: surface (#ffffff) or transparent
Border: 2px solid primary-pop/30
Text: text-primary-pop, font-bold, Inter
Radius: rounded-xl (12px)
Hover: bg-sky-joy (#e0f2fe)
```

### Text Links
```
Primary link:    text-primary-pop (#3b82f6), font-bold, hover:underline, underline-offset-4
Secondary link:  text-accent-joy (#f472b6), font-bold, hover:underline, underline-offset-4
Muted link:      text-slate-400, hover:text-primary-pop, transition-colors
```

### Input Fields
```
Background:      bg-white (surface)
Border:          border-2 border-slate-200 (inactive)
                 border-2 border-primary-pop (focused)
Radius:          rounded-xl (12px)
Height:          48px (py-3 px-4)
Font:            Inter, text-base
Label:           Floating or above-field, Inter text-sm font-medium text-slate-600
Shadow:          shadow-sm on focus (gentle lift)
```

### Cards (Dashboard Widgets)
```
Background:      bg-white (surface)
Border:          border border-slate-100
Radius:          rounded-2xl (16px)
Padding:         p-6 (24px)
Shadow:          shadow-lg (gentle, warm)
Hover:           shadow-xl (slight lift)
Header:          Fredoka text-lg font-bold text-on-surface
```

### Data Badge (For ASINs, Emails, SKUs)
```html
<span class="inline-block px-2 py-1 bg-white border-2 border-dashed border-primary-pop/30
             rounded-lg text-primary-pop font-bold">B08XYZ123</span>
```

### Stat Cards
```
Number:          Fredoka, text-4xl font-bold text-on-surface
Label:           Inter, text-sm text-slate-400 uppercase tracking-wider
Trend:           Positive: text-emerald-500 + ↑ arrow. Negative: text-rose-500 + ↓ arrow
Sparkline:       Stroke primary-pop, 2px, 48px tall
```

### Tables (Dashboard Context — Professional Mode)
```
Header:          bg-slate-50, Inter text-xs uppercase tracking-wider text-slate-400, font-medium
Rows:            bg-white, hover:bg-sky-joy/30, border-b border-slate-100
Text:            Inter text-sm text-slate-700
Numbers:         Inter tabular-nums, text-right
Status dots:     8px rounded-full (emerald-400, amber-400, rose-400)
Actions:         text-primary-pop hover:underline
```

### Agent Status Components
```
Agent Dot:       12px rounded-full with 2px ring, agent color
  Active:        Pulse animation (2s ease-in-out infinite)
  Idle:          Solid, no animation
  Error:         Rose-500, no pulse
Agent Card:      White card with 4px left-border in agent color
Agent Colors:
  Listing:       #3b82f6 (primary-pop blue)
  Inventory:     #22c55e (emerald)
  Advertising:   #f59e0b (amber)
  Pricing:       #8b5cf6 (violet)
  Analytics:     #06b6d4 (cyan)
  Compliance:    #6b7280 (gray)
  Orchestrator:  #f472b6 (accent-joy pink)
```

### Approval Cards
```
Background:      White card, rounded-2xl, shadow-lg
Left border:     4px solid agent-color
Agent badge:     Small pill with agent icon + name, agent-color bg at 10%, text in agent-color
Action text:     Inter text-base text-on-surface
Reasoning:       Expandable, Inter text-sm text-slate-500
Approve button:  bg-emerald-500 text-white rounded-xl, shadow-[0_4px_0_rgb(21,128,61)]
Reject button:   bg-white border-2 border-slate-200 text-slate-600 rounded-xl
```

### Empty States
```
Character:       Mascot variant (waving, pointing, or thinking)
Heading:         Fredoka text-2xl font-bold text-on-surface
Body:            Inter text-lg text-slate-500, max-w-md, leading-relaxed
CTA:             Primary 3D push button
Tone:            Encouraging: "No campaigns yet — let's launch your first one!"
```

---

## 7. Shadows & Depth

```
Card shadow:         shadow-lg (0 10px 15px rgba(0,0,0,0.1))
Card hover:          shadow-xl (gentle lift)
Primary button:      shadow-[0_10px_0_rgb(30,58,138)] — 3D push effect
Character:           drop-shadow(0 20px 30px rgba(59,130,246,0.3)) — blue glow
Background blobs:    blur-3xl, opacity-40/50, mix-blend-multiply — dreamy atmosphere
Modals/popovers:     shadow-2xl + backdrop-blur-sm (frosted glass)
Inputs focused:      shadow-sm (subtle lift on focus)
```

**Shadow color rule:** Shadows should always have a BLUE or WARM tint (rgba of primary-pop or slate), never pure black. This keeps the overall feeling warm.

---

## 8. Animation & Motion

```
Character float:     translateY(-20px) rotate(2deg), 4s ease-in-out infinite
Cloud drift:         translateX(-10% → 10%), 15s ease-in-out infinite alternate
Button press:        translateY(5px), 200ms — physical push-down feedback
Hover transitions:   transition-all duration-200
Page transitions:    300ms fade + slide-up
Celebration:         Confetti burst on achievement moments (use canvas-confetti library)
Agent pulse:         2s ease-in-out infinite on active status dots
Skeleton loaders:    Shimmer sweep, slate-100 → slate-200, 1.5s loop
```

**Animation philosophy:** Animations make the product feel ALIVE. The character floats gently. Clouds drift. Buttons physically push down. The AI feels present and active. But data screens are calmer — animations are subtler in the dashboard than on auth/onboarding screens.

All animations respect `prefers-reduced-motion`.

---

## 9. Border Radius Scale

The radius scale is GENEROUS — everything feels soft and rounded:
```
Chips/badges:        rounded-lg (8px)
Inputs:              rounded-xl (12px)
Buttons:             rounded-2xl (16px)
Cards:               rounded-2xl (16px)
Character body:      rounded-3xl (24px)
Avatars/dots:        rounded-full
Background blobs:    rounded-full
Logo icon:           rounded-lg (8px)
```

---

## 10. Icons

**Library:** Material Symbols Outlined (Google)
```html
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1" rel="stylesheet"/>
```

**Decorative icons** (celebrations, character accessories):
- `star` — yellow-400
- `auto_awesome` — primary-pop (sparkle)
- `celebration` — pink-400 (confetti)
- `favorite` — accent-joy (heart)
- `bolt` — white on primary-pop (logo)

**Functional icons** (navigation, actions):
- Default weight, 24px
- Color: text-slate-500 (inactive), text-primary-pop (active/hover)
- Used in: sidebar nav, table actions, form field left-icons, buttons

---

## 11. Language & Tone

The copywriting is a CORE part of the design system. Our product has personality.

### Auth & Onboarding Screens (Maximum Personality)
```
Success:     "Woohoo! It's on its way!"     NOT "Email sent successfully"
Error:       "Hmm, that didn't work"        NOT "Error: Invalid credentials"
Loading:     "Warming up the engines..."     NOT "Loading..."
Welcome:     "Welcome aboard!"              NOT "Welcome"
CTA:         "Let's go!"                    NOT "Continue"
Reset:       "Back to the login party"      NOT "Return to login"
Resend:      "Give it another nudge!"       NOT "Resend email"
Empty:       "Nothing here yet — let's change that!"
```

### Dashboard & Data Screens (Professional with Warmth)
```
Data labels:     Professional: "Total Revenue", "Buy Box Win Rate", "ACoS"
Insights:        Warm but clear: "Your pricing agent saved you $340 today"
Approvals:       Direct: "Review 3 pending actions"
Alerts:          Friendly: "Heads up — Widget X is running low"   NOT "WARNING: Low inventory"
```

The split: **Auth/onboarding/celebrations = full personality. Dashboard/data = warm professionalism.**

---

## 12. Responsive Behavior

```
Desktop (>1024px):  Full sidebar + multi-column grid + full tables + character illustrations
Tablet (768-1024):  Collapsed sidebar + 2-column grid + character at reduced scale
Mobile (<768):      Bottom nav + single column + no character on data screens + simplified bg
```

---

## 13. Logo

```
Icon:    8×8 square, bg-primary-pop (#3b82f6), rounded-lg (8px)
         Material Symbols "bolt" icon inside, text-white
Text:    "Seller Autopilot" — Fredoka, font-bold, text-lg, text-slate-600
Layout:  Icon + text horizontal, gap-2
```

---

## 14. Tailwind Config

```javascript
tailwind.config = {
  theme: {
    extend: {
      colors: {
        "sky-joy": "#e0f2fe",
        "primary-pop": "#3b82f6",
        "accent-joy": "#f472b6",
        "surface": "#ffffff",
        "on-surface": "#1e293b"
      },
      fontFamily: {
        "whimsical": ["Fredoka", "sans-serif"],
        "body": ["Inter", "sans-serif"]
      }
    }
  }
}
```

---

## 15. Prompt Template

Structure for EVERY mockup prompt:

```
=== DESIGN SYSTEM: JOYFUL TECH ===

This is "Seller Autopilot" — a friendly, bright B2B SaaS for Amazon sellers.
The aesthetic is JOYFUL, WARM, PLAYFUL, and ENCOURAGING.
Think: Notion warmth × Duolingo character × Stripe data clarity × Figma personality.

MUST look like the reference (light sky-blue gradient, Fredoka headlines, 3D push buttons, 
playful character mascot, celebratory language, generous rounded corners).

MUST NOT look like: dark dashboards, Bloomberg terminals, generic Bootstrap, enterprise grey.

COLORS:
- Page: gradient from #e0f2fe via #f0f9ff to #ffffff + soft blurred blobs
- Primary: #3b82f6 (bright blue — buttons, links, character)
- Accent: #f472b6 (pink — secondary links, decorative)
- Surface: #ffffff (white cards)
- Text: #1e293b (slate-800 primary), #475569 (slate-600 muted), #94a3b8 (slate-400 light)
- Selection: accent-joy (#f472b6) at 30% opacity

FONTS:
- Headlines/Buttons/Logo: Fredoka (400/600/700) — rounded, friendly
- Body/UI: Inter (400/500/600) — clean, professional
- Data identifiers (emails, ASINs): Inter bold in primary-pop, with dashed-border badge

COMPONENTS:
- Primary buttons: 3D push effect — bg #3b82f6, shadow-[0_10px_0_rgb(30,58,138)], rounded-2xl
  Hover: shadow compresses + translateY(5px). Active: fully pressed, shadow-none + translateY(8px)
- Cards: white bg, rounded-2xl (16px), shadow-lg, p-6
- Inputs: white bg, border-2 slate-200 → primary-pop on focus, rounded-xl (12px), 48px height
- Border radius scale: badges 8px, inputs 12px, buttons/cards 16px, character 24px

CHARACTER: Friendly robot/envelope mascot with eyes, smile, arms, antenna.
Float animation. Blue drop-shadow. Decorative sparkle/star/celebration icons around it.
Use on: auth screens, empty states, celebrations, onboarding.
Do NOT use on: data tables, analytics charts.

LANGUAGE: Playful and warm.
"Woohoo!" not "Success". "Let's go!" not "Continue". "Give it another nudge!" not "Resend".

BACKGROUND: Sky gradient + drifting white cloud blobs + soft colored blobs (blue, pink, yellow).
SHADOWS: Blue-tinted, warm. 3D on buttons. Drop-shadow on character. Never pure black.
ANIMATION: Character floats (4s). Clouds drift (15s). Buttons push. Everything alive but calm.

[Your specific screen description here]
```

---

## 16. Do's and Don'ts

### Do
- ✅ Use Fredoka for all headlines, buttons, and celebratory text
- ✅ Use the sky gradient + blob background on auth/onboarding screens
- ✅ Use the 3D push-button effect on all primary CTAs
- ✅ Use the mascot character on appropriate screens (auth, empty, celebrations)
- ✅ Write playful, encouraging copy on auth/onboarding screens
- ✅ Use generous border radius (12-24px on main elements)
- ✅ Use Material Symbols Outlined for all icons
- ✅ Use dashed-border badges for data identifiers (emails, ASINs)
- ✅ Use blue-tinted shadows, never pure black
- ✅ Add floating/drift animations for atmosphere on non-data screens

### Don't
- ❌ Use dark backgrounds (this is a light, bright, sky-themed app)
- ❌ Use sharp corners (minimum 8px radius on everything)
- ❌ Use flat, shadowless buttons (the 3D push effect is a signature)
- ❌ Write clinical/cold copy ("Error occurred" → "Hmm, that didn't work")
- ❌ Use the mascot character on data-heavy screens (distracting)
- ❌ Use generic grey admin template patterns
- ❌ Use thin, corporate fonts for headlines (Fredoka's roundedness is key)
- ❌ Use black shadows (always blue-tinted or warm-tinted)
- ❌ Flatten the background to a single color (the gradient + blobs create atmosphere)
