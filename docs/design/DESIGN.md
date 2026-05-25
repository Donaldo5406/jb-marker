---
name: Auralis System
colors:
  surface: '#fdf8f8'
  surface-dim: '#ddd9d8'
  surface-bright: '#fdf8f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f7f3f2'
  surface-container: '#f1edec'
  surface-container-high: '#ebe7e6'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#444748'
  inverse-surface: '#313030'
  inverse-on-surface: '#f4f0ef'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#5e5e5e'
  on-secondary: '#ffffff'
  secondary-container: '#e1dfdf'
  on-secondary-container: '#626262'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1d1b1a'
  on-tertiary-container: '#868381'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#e4e2e2'
  secondary-fixed-dim: '#c7c6c6'
  on-secondary-fixed: '#1b1c1c'
  on-secondary-fixed-variant: '#464747'
  tertiary-fixed: '#e6e1df'
  tertiary-fixed-dim: '#cac6c3'
  on-tertiary-fixed: '#1d1b1a'
  on-tertiary-fixed-variant: '#484645'
  background: '#fdf8f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  h1:
    fontFamily: Inter
    fontSize: 64px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  button:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1440px
  gutter: 24px
  margin-x: 40px
  header-height: 72px
---

## Brand & Style
The design system is rooted in architectural minimalism and precision engineering, reflecting the sophisticated nature of high-end AI voice infrastructure. It evokes a sense of "quiet intelligence"—unobtrusive, premium, and highly functional. 

The visual style blends **Minimalism** with elements of **Glassmorphism**. It prioritizes vast amounts of whitespace and structural clarity, using "floated" UI elements to create an airy, weightless feel. The aesthetic is punctuated by ethereal, muted gradient orbs that represent the fluid, organic nature of voice and sound, providing a soft contrast to the otherwise rigid, monochromatic grid.

## Colors
The palette is dominated by soft, cool neutrals that mimic high-end architectural materials like limestone and brushed aluminum. The core interface relies on a monochrome foundation for maximum legibility and professional authority.

Accents are never solid; they are applied as muted, blurred atmospheric gradients (orbs). These orbs should be used sparingly behind glass-like panels to suggest depth and movement without distracting from the data-heavy content.

## Typography
This design system utilizes a high-performance, neutral Grotesk to maintain a utilitarian yet premium feel. Typography is treated as a structural element. 

Headlines use tight line-heights and slight negative letter-spacing to create a "locked" architectural look. Body text is prioritized for legibility with generous leading. Captions and labels are occasionally set in all-caps with increased letter-spacing to denote metadata or secondary technical information.

## Layout & Spacing
The layout follows a **fixed grid** philosophy centered within the viewport, ensuring that the AI infrastructure's complex data remains legible and focused. A 12-column system is used for dashboard layouts, while marketing and editorial pages utilize a more expansive 8-column center-aligned grid.

The "whitespace-heavy" mandate is achieved by doubling standard margins between major sections. Spacing should follow an 8px rhythmic scale, but components like cards and panels should utilize a minimum of 32px to 48px of internal padding to maintain the "premium gallery" aesthetic.

## Elevation & Depth
Depth is created through **Glassmorphism** and tonal layering rather than traditional heavy shadows. Surfaces are stacked to create a "floated" look:

1.  **Level 0 (Base):** The main background (#F7F7F5).
2.  **Level 1 (Panels):** Slightly darker surfaces (#F3F2EF) with ultra-light borders (#E7E7E4).
3.  **Level 2 (Floated Cards):** White or semi-transparent glass surfaces with a 1px border and an extremely diffused "ambient glow" (0px offset, 40px blur, 2% black opacity).

Background blurs (backdrop-filter: blur(20px)) are applied to navigation bars and modal overlays to maintain context while emphasizing the foreground.

## Shapes
The shape language balances geometric precision with organic softness. Buttons always take a full-pill form, emphasizing a tactile, interactive nature. 

Cards and panels use a "Soft Rounded" approach, with a primary radius between 20px and 28px. This significant curvature helps soften the technical nature of the AI platform, making the infrastructure feel approachable and modern.

## Components
- **Buttons:** Primary buttons are full black pills with white text, providing a strong focal point. Secondary buttons use the panel color (#F3F2EF) with primary text for a subtle, integrated look.
- **Cards:** Defined by 24px corner radii and 1px #E7E7E4 borders. Internal padding is generous (minimum 32px). Cards should appear to "float" above the background.
- **Navigation:** A fixed top header (72px) with a semi-transparent glass effect. Links are minimal, using the Caption style.
- **Input Fields:** Minimalist underlines or subtle #F3F2EF fills with 8px radii. Focus states are indicated by a 1px primary text color border.
- **Glass Panels:** Used for overlays and sidebar navigation, featuring a 20px-40px backdrop blur to allow the accent orbs to peek through.
- **Visual Indicators:** Use small, vibrant dots (the accent colors) to indicate status (e.g., "Active," "Processing," "Error") instead of large disruptive banners.