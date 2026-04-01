# Document Design Guide

This guide explains the design principles behind Korean government-style documents — the WHY behind each visual choice. The converter (`md_to_hwpx.py`) handles the XML implementation; this guide helps you make better content preparation decisions.

## Core Values

Korean government documents optimize for three things simultaneously:

**Authority** — The document must look official. Color restraint (only green/gray/blue accents), justified text, serif body fonts, and structured headers all signal institutional credibility. This is why emoji get removed, why fonts are conservative, and why the section header uses a formal green table rather than just bold text.

**Scannability** — Readers (legislators, executives, journalists) need to extract key info in 30 seconds. The ▢/○/▷ hierarchy, bold keyword markers, and table-based section headers exist for rapid visual scanning. A reader should be able to flip through and grasp the structure without reading a single full paragraph.

**Information density** — Government announcements pack enormous detail into few pages. Micro-spacing (11pt spacers instead of 14pt blank lines), compact tables, and indentation hierarchy compress information without sacrificing readability. This is why we use spacer lines rather than full empty paragraphs.

## Page Structure

A typical document flows like this:

```
Page 1 (Cover/Summary):
  Title (26pt, centered, bold)
  Spacer
  Introductory paragraph (full-width indent)
  Spacer
  Summary table or key facts
  Spacer
  Note box (※ prerequisites or notices)

Page 2+ (Sections):
  Section Header (green table: number + title)
  Spacer
  ▢ Major topic (gold shade, bold)
    Body paragraph explaining the topic
    ○ Sub-topic (sky blue shade, bold)
      ▷ Detail item
      ▷ Another detail
        ▷ Indented sub-detail
  Spacer
  Data table
  Spacer
  Info box (reference material)
```

## The Symbol Hierarchy

Korean government documents use a standardized visual hierarchy for structuring information within sections:

```
▢ (네모, gold shade)  — Major topics. The first level of organization within a section.
○ (동그라미, sky blue shade)  — Sub-topics under ▢. Second level.
▷ (삼각형)  — Detail items under ○. Third level.
  ▷ (indented 삼각형)  — Sub-details. Deepest level.
```

This maps to markdown as:
```
### Major Topic          → ▢ gold shade heading
#### Sub-Topic           → ○ sky blue shade heading
- Detail item            → ▷ bullet
  - Sub-detail           → ▷ indented bullet
```

Numbered items use circled numbers: ① ② ③ instead of 1. 2. 3.

This hierarchy is not decorative — it's a standardized information architecture that Korean civil servants and journalists are trained to scan. Using it correctly makes your document instantly legible to its target audience.

## Section Headers

`##` always produces a section header table (green-filled) and starts on a new page (except the first one). Numbered sections like `## 1. Analysis Results` show the number in a separate cell; unnumbered sections like `## Key Findings` show the title only.

The distinction between `##` and `###` matters: `##` is for major divisions that deserve their own page (like chapter headings in a book). `###` is for sub-section topics within a page (▢ gold shade, no page break). Most article subheadings belong at the `###` level.

## Professional Techniques

### Full-width space indent
Every body paragraph starts with two ideographic spaces (U+3000 `　`). This creates a subtle visual indent that signals "this is body text, not a heading or bullet." The converter handles this automatically — you don't need to add them in markdown.

### Micro-spacing
The converter inserts 11pt spacer lines between elements (not full 14pt blank lines). This breathing room is essential — without it, elements visually bleed into each other. But too much space wastes the density that makes government documents effective.

### Bold keyword technique
In body text, bold only the key noun phrase, not the entire sentence. Verb endings (-했다, -됩니다, -을 추진) stay in normal weight. This creates a "journalist's highlight" effect where a reader's eye catches the key terms while scanning.

**Example**: "정부는 **창업 생태계 혁신 방안**을 발표하였다."

The bold makes the topic scannable; the normal-weight verb keeps the sentence natural.

### Table design
- Every table header row has a colored background — without it, headers are indistinguishable from data rows
- Gray headers for data/lookup tables (the reader asks "what exists?")
- Blue headers for comparison tables (the reader asks "how do they differ?")
- Table cells use 12pt sans-serif font, smaller than body text (14pt serif), creating visual differentiation between narrative and tabular content

### Box patterns
- **Note boxes** (light gray, solid border): warnings and caveats the reader must not miss
- **Info boxes** (light blue, dashed border): reference material and supplementary context
- **Wrapper boxes** (thin border, no fill): group related elements into one visual unit
