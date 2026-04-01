---
name: Hancom
description: HWPX 한컴문서를 읽고 작성하는 스킬. 한컴문서(HWPX) 파일을 분석하거나, 사용자가 제공한 내용을 바탕으로 한국 정부 공문서 수준의 문서를 생성한다. "한컴", "한글문서", "hwpx", "hwp", "보도자료 작성", "공문서 작성", "한컴으로 만들어줘", "hwpx로 저장", "이 hwpx 파일 읽어줘" 등의 요청이나 .hwpx 파일이 언급될 때 이 스킬을 사용한다. 한컴문서 관련 작업이라면 명시적으로 스킬을 요청하지 않아도 적극적으로 사용할 것.
---

# HWPX Document Skill

HWPX is Korea's standard document format — a ZIP archive containing XML files. The core idea: `header.xml` defines all styles by ID (like CSS), and `section0.xml` references those IDs to format content (like HTML). The converter (`md_to_hwpx.py`) handles all XML generation from annotated markdown.

## Environment

This skill runs in two contexts: local (CLI/IDE) and Cowork (cloud sandbox).

In Cowork, uploaded files are mounted read-only. Bash `cp` preserves the source
permissions, so copied files are also read-only — scripts that write in-place will
fail with PermissionError.

Three rules for Cowork compatibility:

1. **All working files go to the writable working directory** — the upload
   directory is read-only. `cleaned_original.md` must be in a writable directory
   because the linter writes to it in-place, and you Edit() it afterward for
   normalization. The final `.hwpx` output must also go to a writable directory.
   Never create working files in the upload directory.
2. **Default to Edit() for subsequent changes** — each Edit() transmits only the
   changed portion (~100 tokens vs ~2000 for full rewrite). Use Write() only when
   changes are so pervasive (30+ edits) that cumulative Edit() overhead exceeds
   a single Write().
3. **Script paths are absolute in Cowork** — the skill directory is at a long
   path under `/sessions/.../mnt/.remote-plugins/...`. Use the full resolved path
   when calling scripts via Bash.

These rules also apply locally — they just don't cause errors there.

## Reference Docs

| When | Read |
|------|------|
| Preparing content (normalize + annotate) | `references/content-prep-guide.md` |
| Understanding design principles | `references/document-design.md` |
| Looking up style IDs | `references/style-catalog.md` |
| Understanding HWPX XML structure | `references/hwpx-format.md` |

## Writing Workflow

### Step 1: Lint the markdown

Run the linter with `-o` to create a linted copy in the working directory:

```bash
python3 scripts/md_lint.py original.md -o cleaned_original.md
```

The `-o` flag reads the original, applies lint rules, and writes the result to
`cleaned_original.md`. No separate copy step needed. The output file must be in
a writable directory — in Cowork, that's the session working directory, not the
upload directory.

Lint rules: heading level gaps, consecutive blank lines, blank lines between list items, multiple spaces, trailing whitespace, EOF newline. No semantic judgment — purely mechanical.

### Step 2: Prepare content (normalize + annotate)

Read `references/content-prep-guide.md`. Then apply changes to `cleaned_original.md`.

**Choose Edit() or Write() based on the scope of changes:**

- **Edit() — default.** When changes are localized (a few headings, frontmatter removal,
  emoji stripping, annotation insertion), use targeted Edit() calls. Each call transmits
  only the changed portion, so 5 edits on a 100-line file ≈ 200 tokens.

- **Write() — exception.** When normalization requires pervasive restructuring (reordering
  sections, converting most bullets to tables, rewriting 80%+ of lines), the cumulative
  overhead of dozens of Edit() calls exceeds a single Write(). In that case, Read() the
  file, restructure in full, and Write() once. This is rare — most documents need only
  localized cleanup.

**How to decide:** estimate how many Edit() calls you'd need. If <10, use Edit().
If 30+, Write() is likely cheaper. In between, use judgment.

Typical Edit() sequence:
```
Edit("---\ntags:...\n---\n", "")              ← remove YAML frontmatter
Edit("## 🏛️ Section", "## Section")           ← strip emoji from heading
Edit("> [!cite]\n> ...\n> ...", "")            ← remove Obsidian callout block
Edit("## Duplicate Title\n\n", "")             ← remove redundant heading
```

The converter turns markdown into 5x more XML. Every token saved in the input
saves 5x in the output — this is why Edit() is the default.

Typical cleanup tasks:
- Restructure where needed (bullet→table conversions, condensing repetitive content)
- Add annotations where design judgment is needed (`<!-- table:compare -->`, `<!-- box:note -->`, etc.)
- Clean up Obsidian syntax, decorative emoji, inline URLs

Most elements need no annotation — the converter auto-detects headings, bullets, tables, and paragraphs from standard markdown syntax.

### Step 3: Convert to HWPX

```bash
python3 scripts/md_to_hwpx.py cleaned_original.md --output output.hwpx --build --title "문서 제목"
```

Images referenced in the markdown (`![](file.png)`) are automatically detected and embedded.

The converter handles all XML generation: headings, bullets, tables, boxes, images, spacing. No manual XML assembly needed.

All paths (`cleaned_original.md`, `output.hwpx`) are resolved relative to the
current working directory. In Cowork, this is the session directory — which is
writable. Never write output to the upload directory.

## Reading Workflow

```bash
python3 scripts/read_hwpx.py input.hwpx           # text only
python3 scripts/read_hwpx.py input.hwpx --verbose  # with style info
```

## Critical Constraints

These are hard technical requirements — violating them crashes Hancom Office:

1. **Never hand-write header.xml** — always use `templates/base/Contents/header.xml`
2. **Never use Python ElementTree to write header.xml** — it rewrites `hh:`/`hc:` prefixes to `ns0:`/`ns1:`, breaking Hancom rendering
3. **Don't write secPr** — `build_hwpx.py` injects it from the template automatically
4. **paraPr 2-8 are dangerous** — they trigger auto-numbering. Use 0, 1, 15 for indentation

## Script Paths

All scripts are in `scripts/` within this skill directory:
- `scripts/md_lint.py` — mechanical markdown linter (pre-processing)
- `scripts/md_to_hwpx.py` — annotated markdown → HWPX (main converter)
- `scripts/build_hwpx.py` — section0.xml → HWPX ZIP assembly
- `scripts/validate_hwpx.py` — structural validation
- `scripts/read_hwpx.py` — HWPX → structured text extraction

Templates are in `templates/`:
- `templates/base/` — header.xml, secPr template, base ZIP structure
- `templates/xml-parts/` — XML fragment templates used by md_to_hwpx.py
