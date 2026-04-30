# Pulse Portfolio Design Specification

This document defines the visual tokens, interaction language, and layout intent for the portfolio interface.

It is the design source of truth for:
- semantic color tokens in `frontend/app/globals.css`
- component geometry and panel treatments
- tone, hierarchy, and system framing

This portfolio should read as a structured systems interface, not a conventional personal site.

## 1. Product Framing

The intended character is:
- precise
- traceable
- technical
- restrained

The page should feel assembled from documented modules, visible states, and explicit system framing rather than from generic marketing patterns.

The interface should feel:
- editorial in hierarchy
- engineered in structure
- deliberate in labeling
- calm in motion

## 2. Design Principles

These rules should guide every component decision.

1. Prioritize clarity over ornament.
2. Use spacing, borders, and typography for contrast before decorative effects.
3. Keep interaction states explicit and legible.
4. Make system behavior visible through labels, metadata, and staged transitions.
5. Preserve the same design intent across desktop and mobile by reducing complexity, not changing the pattern language.

## 3. Visual System

### 3.1 Color Model

The palette is token-based and should be defined in `frontend/app/globals.css` using OKLCH values.

Required semantic tokens:
- `--background`
- `--foreground`
- `--surface`
- `--surface-elevated`
- `--muted-foreground`
- `--accent`
- `--border`
- `--radius`

These tokens should be treated as semantic roles, not one-off color picks.

### 3.2 Token Intent

- `--background`: the primary canvas
- `--foreground`: default readable text
- `--surface`: standard panel background
- `--surface-elevated`: emphasized panel background for stacked hierarchy
- `--muted-foreground`: secondary text, metadata, timestamps, captions
- `--accent`: active state, key system markers, controlled emphasis
- `--border`: structural lines and module separation
- `--radius`: global geometry control

### 3.3 Light Theme Rules

- Backgrounds should feel bright but not sterile.
- Borders should stay soft but clearly visible.
- Surfaces should separate through tonal steps, not heavy shadows.
- Accent usage should stay sparse and intentional.
- Text contrast must remain high enough for dense technical layouts.

### 3.4 Dark Theme Rules

- Dark mode should feel like a control surface, not a neon interface.
- Contrast should come from value separation and typography, not glow.
- Borders must remain readable against dark surfaces.
- Accent should remain measured and precise.
- Elevated surfaces should read as layered panels, not floating cards.

### 3.5 Baseline Token Proposal

These are recommended starting values for implementation in OKLCH.

```css
:root {
  --background: oklch(0.97 0.004 240);
  --foreground: oklch(0.20 0.015 240);
  --surface: oklch(0.94 0.006 240);
  --surface-elevated: oklch(0.90 0.008 240);
  --muted-foreground: oklch(0.47 0.012 240);
  --accent: oklch(0.58 0.11 230);
  --border: oklch(0.84 0.006 240);
  --radius: 0rem;
}

@media (prefers-color-scheme: dark) {
  :root {
    --background: oklch(0.16 0.01 240);
    --foreground: oklch(0.92 0.01 240);
    --surface: oklch(0.20 0.012 240);
    --surface-elevated: oklch(0.25 0.014 240);
    --muted-foreground: oklch(0.68 0.01 240);
    --accent: oklch(0.72 0.10 230);
    --border: oklch(0.32 0.01 240);
    --radius: 0rem;
  }
}
```

These values are intentionally restrained:
- blue accent instead of decorative gradients
- cool neutrals to support an editorial technical tone
- enough tonal separation to create structure without cards feeling soft

## 4. Typography

### 4.1 Type System

Typography should carry most of the identity.

Requirements:
- primary type should feel engineered and contemporary
- mono usage should communicate metadata, labels, and system framing
- hierarchy should come from size, weight, casing, and spacing
- avoid expressive display theatrics unless tightly controlled

Recommended role split:
- sans serif for narrative and section headlines
- mono for labels, timestamps, keys, tags, and state indicators

Typography should communicate:
- what is primary
- what is metadata
- what is status
- what is structural chrome

### 4.2 Text Behavior

- Labels may use uppercase sparingly where system framing benefits.
- Metadata should be compact and visually subordinate.
- Paragraphs should stay readable and measured, not airy and promotional.
- Headlines should feel declarative, not inspirational.

## 5. Surface Rules

Global geometry:
- `--radius: 0rem`
- square geometry by default
- borders instead of shadows
- offset border treatments only where depth clarification is useful

Cards and modules must read as system panels, not floating marketing blocks.

Surface behavior:
- use solid panel separation first
- use shadows rarely and only when hierarchy becomes ambiguous
- prefer inner spacing and border rhythm over large decorative containers
- keep panel edges crisp across themes

## 6. Layout Intent

The layout should feel like a documented interface composed of sections with distinct responsibilities.

Each section should answer a concrete question:
- who is this person
- what systems do they build
- how do they think
- what evidence supports that
- what state is the work in

Avoid:
- oversized empty hero sections
- testimonial-style marketing layouts
- soft startup landing page patterns
- decorative cards without structural purpose

## 7. Interaction Model

Interaction should feel explicit and inspectable.

Rules:
- hover states should clarify affordance, not entertain
- focus states must be obvious and keyboard-readable
- selected states should use accent plus structural reinforcement
- loading states should show staged progress, not vague spinners when status can be named
- transitions should be short, restrained, and purposeful

Visible system behaviors to prefer:
- status chips
- timestamps
- module labels
- section counters
- change indicators
- active/inactive state framing

## 8. Responsive Behavior

The mobile version should preserve the same design language as desktop.

Do not:
- switch to a completely different visual style
- remove all metadata
- collapse everything into oversized generic cards

Do:
- reduce simultaneous density
- stack modules cleanly
- preserve labels and borders
- keep state indicators intact
- simplify layout, not identity

## 9. Required Hero Intent

The hero area should:
- establish identity
- communicate specialization quickly
- introduce the system-framed tone

The hero should feel like a system header or dossier entry, not a marketing billboard.

Recommended content pattern:
- primary identity line
- role or specialization summary
- supporting metadata row
- one or two explicit actions
- optional live state or availability marker

## 10. Component Language

Components should feel assembled from a consistent interface grammar.

Preferred primitives:
- bordered panels
- section headers with labels
- metadata rows
- state chips
- tabular or list-based evidence blocks
- inline annotations
- structured call-to-action rows

Avoid:
- glassmorphism
- pill-heavy decorative UI
- oversized drop shadows
- gradient-driven hierarchy
- vague icon-only actions without labels

## 11. Implementation Notes

When translating this into code:
- define all semantic tokens in `frontend/app/globals.css`
- map tokens into Tailwind theme variables where needed
- keep component variants tied to semantic roles, not arbitrary color names
- encode states with reusable patterns instead of one-off styling
- prefer CSS variables for theme consistency across components

## 12. Open Item

The provided spec ended with `Required structure:` but did not include the full section list after that point.

Until that is provided, treat the following as the minimum required structure:
- hero / system header
- specialization summary
- selected work or evidence modules
- process / thinking section
- contact or next-action section

If a fuller structure is added later, this document should be extended rather than replaced.
