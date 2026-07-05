# RavenStore Design System

## Identity

RavenStore uses a graphite-black foundation with violet as the brand signal. Cyan communicates
information, emerald success, amber attention, and rose destructive states. Purple is an accent,
not the entire palette. Product imagery and operational data remain the visual focus.

## Foundations

- Typography: Segoe UI Variable/Inter/system sans, tabular numerals for metrics, zero letter spacing.
- Geometry: 4px controls, 6px compact surfaces, 8px cards/modals. No decorative pill containers.
- Spacing: 4px base scale; common control heights are 32, 40, and 44px.
- Elevation: thin light borders, restrained blur, inset highlight, and two shadow levels.
- Focus: visible 2px violet ring with 2px offset.

Tokens live in each app's `app/globals.css` and are exposed through Tailwind:
`background`, `foreground`, `card`, `muted`, `primary`, `success`, `warning`,
`danger`, and `info`.

## Motion

- Fast feedback: 120-200ms.
- Page and modal entry: 200-240ms using `cubic-bezier(.22,1,.36,1)`.
- Drag/reorder and counters: damped springs.
- Lists use short stagger and layout animation; data refreshes do not flash or resize containers.
- `prefers-reduced-motion` disables transforms, looping particles, shimmer travel, and long transitions.

Shared presets are in `lib/motion.ts`. Motion must communicate state or hierarchy, never delay work.

## Components

Buttons use familiar Lucide icons, stable heights, focus rings, press feedback, and restrained ripple.
Cards use the `glass`/`glass-panel` surface and `card-lift` only for interactive objects. Inputs,
tables, badges, alerts, progress, skeletons, empty states, tooltips, dialogs, command palette, and
toasts share the same semantic colors and geometry.

## Product Rules

- Telegram is the primary experience: compact messages, localized labels, inline keyboards, status
  symbols, safe `<code>` formatting, and predictable back navigation.
- Admin is dense and operational: scan-friendly tables, small headings, keyboard navigation, live
  status, draggable widgets, and semantic charts.
- Storefront is image-led and trustworthy: full-bleed hero, obvious pricing/availability, concise
  checkout stages, accessible commerce feedback, and Telegram as the prominent secondary route.

All visible strings remain in the localization layer. New features should use existing primitives and
semantic tokens rather than introducing page-specific colors, radii, shadows, or motion curves.
