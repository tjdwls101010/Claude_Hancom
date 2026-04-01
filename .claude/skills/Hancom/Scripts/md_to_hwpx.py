#!/usr/bin/env python3
"""
md_to_hwpx.py — Convert annotated markdown to HWPX section0.xml

Reads a markdown file (optionally with HTML comment annotations)
and produces section0.xml that can be packaged into HWPX via build_hwpx.py.

Usage:
    python3 md_to_hwpx.py input.md --output section0.xml
    python3 md_to_hwpx.py input.md --output output.hwpx --build
"""

import argparse
import re
import os
import sys

# ──────────────────────────────────────────────
# Style ID constants (from user-customized header.xml)
# ──────────────────────────────────────────────
CHAR = {
    'title': '19',       # 26pt 바탕체 bold — main title
    'body': '12',        # 14pt 함초롬돋움 — standard body
    'bold': '20',        # 14pt 함초롬돋움 bold — keyword emphasis (same size as body)
    'shade': '4',        # 15pt 함초롬바탕 bold, shade=#FFD700 — ▢ level
    'sky_shade': '21',   # 14pt 함초롬돋움 bold, shade=#87CEEB — ○ level
    'table_body': '18',  # 12pt 바탕 — table cells
    'table_head': '13',  # 12pt 돋움체 bold — table headers
    'caption': '16',     # 12pt 맑은고딕 bold — < Caption >
    'spacer': '10',      # 11pt 바탕체 — spacer line
    'sec_num': '1',      # 16pt HY울릉도M — section header number
    'sec_title': '14',   # 15pt HY울릉도M bold — section header title
    'underline': '17',   # 15pt 맑은고딕 underline — emphasis
    'small': '0',        # 10pt 함초롬돋움 — default small
}

PARA = {
    'default': '0',      # JUSTIFY
    'bullet': '1',       # JUSTIFY indented (□/○)
    'sub_item': '15',    # LEFT deep indent (-/*)
    'center': '19',      # CENTER
    'right': '21',       # RIGHT
    'table_cell': '22',  # CENTER (table)
}

BF = {
    'none': '1',         # invisible
    'green_fill': '2',   # #E3F4E3 — section header
    'cell': '9',         # SOLID all — standard table cell
    'gray_head': '11',   # #D9D9D9 — data table header
    'blue_head': '12',   # #C5D4F0 — compare table header
    'note': '13',        # #F5F5F5 SOLID 0.4mm — ※ note box
    'info': '14',        # #ECF2FA DASH — info box
}

# ──────────────────────────────────────────────
# Template loader
# ──────────────────────────────────────────────
_TEMPLATE_CACHE = {}
_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates', 'xml-parts')


def _load_template(name):
    """Load an XML template file from templates/xml-parts/. Cached after first load."""
    if name not in _TEMPLATE_CACHE:
        path = os.path.join(_TEMPLATE_DIR, f'{name}.xml')
        with open(path, encoding='utf-8') as f:
            _TEMPLATE_CACHE[name] = f.read()
    return _TEMPLATE_CACHE[name]


def _escape(text):
    """Escape XML special characters."""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ──────────────────────────────────────────────
# XML Constants
# ──────────────────────────────────────────────
XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'

SEC_OPEN = ('<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
            ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
            ' xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph"'
            ' xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"'
            ' xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
            ' xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">')

SEC_CLOSE = '</hs:sec>'

FULL_WIDTH = 42520  # content area in HWPUNIT (A4 210mm - 30mm×2 margins)


def p(para_id, char_id, text, page_break=False):
    """Generate a simple paragraph with one run."""
    run_xml = _load_template('run').format(char_id=char_id, text=_escape(text))
    return _load_template('paragraph').format(
        para_id=para_id, page_break='1' if page_break else '0', runs=run_xml)


def p_multi_run(para_id, runs, page_break=False):
    """Generate a paragraph with multiple runs [(char_id, text), ...]."""
    run_tpl = _load_template('run')
    runs_xml = ''.join(run_tpl.format(char_id=cid, text=_escape(txt)) for cid, txt in runs)
    return _load_template('paragraph').format(
        para_id=para_id, page_break='1' if page_break else '0', runs=runs_xml)


def spacer():
    """Generate an 11pt spacer line."""
    return p(PARA['default'], CHAR['spacer'], ' ')


def emit_title(text):
    """Emit main document title (centered, 26pt bold) wrapped in info box."""
    # Remove emoji if present
    clean = re.sub(r'[\U0001F000-\U0001FFFF\u2600-\u27FF\u2B50]', '', text).strip()
    title_p = p(PARA['center'], CHAR['title'], clean)
    return _load_template('box').format(
        bf=BF['info'], width=FULL_WIDTH, char_small=CHAR['small'],
        bf_cell=BF['cell'], content=title_p
    )


def emit_body(text):
    """Emit body paragraph with full-width indent and bold support."""
    if '**' in text:
        runs = _split_bold_runs(text, CHAR['body'], CHAR['bold'])
        # Add full-width indent to first run
        if runs:
            first_char, first_text = runs[0]
            runs[0] = (first_char, f'\u3000\u3000{first_text}')
        return p_multi_run(PARA['default'], runs)
    return p(PARA['default'], CHAR['body'], f'\u3000\u3000{text}')


def _split_bold_runs(text, default_char, bold_char):
    """Split text with **bold** markers into runs [(char_id, text), ...]."""
    runs = []
    parts = re.split(r'(\*\*.+?\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            runs.append((bold_char, part[2:-2]))
        elif part:
            runs.append((default_char, part))
    return runs


CIRCLED_NUMBERS = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'


def emit_bullet(text, indent=False):
    """Emit a bullet item with ▷ symbol. indent=True for deeper sub-items."""
    bold_match = re.match(r'\*\*\((.+?)\)\*\*\s*(.*)', text)
    bold_match2 = re.match(r'\*\*(.+?)\*\*:\s*(.*)', text)

    if indent:
        # Deeper sub-item: ▷ with extra indent
        runs = _split_bold_runs(text, CHAR['body'], CHAR['bold'])
        return p_multi_run(PARA['sub_item'], [
            (CHAR['body'], '  ▷ '),
        ] + runs)

    if bold_match:
        return p_multi_run(PARA['sub_item'], [
            (CHAR['body'], '▷ '),
            (CHAR['bold'], f'({bold_match.group(1)})'),
            (CHAR['body'], f' {bold_match.group(2)}'),
        ])
    elif bold_match2:
        return p_multi_run(PARA['sub_item'], [
            (CHAR['body'], '▷ '),
            (CHAR['bold'], bold_match2.group(1)),
            (CHAR['body'], f': {bold_match2.group(2)}'),
        ])
    else:
        runs = _split_bold_runs(text, CHAR['body'], CHAR['bold'])
        return p_multi_run(PARA['sub_item'], [
            (CHAR['body'], '▷ '),
        ] + runs)


def emit_numbered_item(number, text):
    """Emit a numbered item with circled number ①②③."""
    idx = number - 1
    if 0 <= idx < len(CIRCLED_NUMBERS):
        symbol = CIRCLED_NUMBERS[idx]
    else:
        symbol = f'{number}.'
    runs = _split_bold_runs(text, CHAR['body'], CHAR['bold'])
    return p_multi_run(PARA['sub_item'], [
        (CHAR['body'], f'{symbol} '),
    ] + runs)


def emit_section_header(text):
    """Emit ## heading as section header table (always green table).
    Numbered: '1. 개요' → table with number + title.
    Unnumbered: '핵심 발견사항' → table with title only (empty number cell)."""
    num_match = re.match(r'^(\d+)[\.\s]+(.+)', text.strip())
    if num_match:
        number = num_match.group(1)
        title = num_match.group(2).strip()
    else:
        number = ''
        title = text.strip()
    return _emit_section_header_table(number, title)


def _emit_section_header_table(number, title):
    """Emit the green table section header from template."""
    return _load_template('section_header').format(
        number=number, title=title,
        char_small=CHAR['small'], sec_num=CHAR['sec_num'], sec_title=CHAR['sec_title'],
        bf_green=BF['green_fill'], bf_cell=BF['cell'], table_cell=PARA['table_cell']
    )


def emit_heading3(text):
    """Emit ### heading as ▢ sub-section (gold shade)."""
    clean = re.sub(r'^[\d.]+\s*', '', text).strip()
    return p_multi_run(PARA['bullet'], [
        (CHAR['body'], '▢ '),
        (CHAR['shade'], clean),
    ])


def emit_heading4(text):
    """Emit #### heading as ○ sub-sub-section (sky blue shade)."""
    clean = re.sub(r'^[\d.]+\s*', '', text).strip()
    return p_multi_run(PARA['bullet'], [
        (CHAR['body'], '○ '),
        (CHAR['sky_shade'], clean),
    ])


def emit_caption(text):
    """Emit centered caption like < Title >."""
    return p(PARA['center'], CHAR['caption'], f'< {text} >')


def emit_image(image_id):
    """Emit an image placeholder from template."""
    return _load_template('image').format(
        image_id=image_id, width=FULL_WIDTH, height=30000, char_small=CHAR['small']
    )


def emit_table(rows, style='data'):
    """Emit a table from parsed rows using templates. First row = header."""
    if not rows or len(rows) < 2:
        return ''

    num_cols = len(rows[0])
    if num_cols == 0:
        return ''

    col_width = FULL_WIDTH // num_cols
    head_bf = BF['gray_head'] if style == 'data' else BF['blue_head']
    body_bf = BF['cell']
    cell_tpl = _load_template('table_cell')

    xml = _load_template('table_open').format(
        row_cnt=len(rows), col_cnt=num_cols,
        bf_cell=BF['cell'], char_small=CHAR['small'])

    for row_idx, row in enumerate(rows):
        is_header = (row_idx == 0)
        bf = head_bf if is_header else body_bf
        char = CHAR['table_head'] if is_header else CHAR['table_body']

        xml += '<hp:tr>\n'
        for col_idx, cell_text in enumerate(row):
            cell_text = re.sub(r'\*\*(.+?)\*\*', r'\1', cell_text.strip())
            xml += cell_tpl.format(
                col_addr=col_idx, row_addr=row_idx, width=col_width,
                bf=bf, para_id=PARA['table_cell'], char=char, text=_escape(cell_text))
        xml += '</hp:tr>\n'

    xml += '</hp:tbl></hp:run></hp:p>\n'
    return xml


def emit_box(content_lines, box_type='note'):
    """Emit a 1x1 table box wrapping content lines, using template."""
    bf = BF.get(box_type, BF['cell'])
    char = CHAR['small'] if box_type == 'note' else CHAR['table_body']
    run_tpl = _load_template('run')
    para_tpl = _load_template('paragraph')

    inner_xml = ''
    for line in content_lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('- '):
            line = line[2:]
        if '**' in line:
            runs = _split_bold_runs(line, char, CHAR['bold'])
            runs_xml = ''.join(run_tpl.format(char_id=rc, text=_escape(rt)) for rc, rt in runs)
        else:
            runs_xml = run_tpl.format(char_id=char, text=_escape(line))
        inner_xml += para_tpl.format(para_id=PARA['default'], page_break='0', runs=runs_xml)

    return _load_template('box').format(
        bf=bf, width=FULL_WIDTH, char_small=CHAR['small'],
        bf_cell=BF['cell'], content=inner_xml
    )


# ──────────────────────────────────────────────
# Parser
# ──────────────────────────────────────────────
def parse_table_block(lines):
    """Parse markdown table lines into list of rows (list of cells)."""
    rows = []
    for line in lines:
        line = line.strip()
        if not line.startswith('|'):
            continue
        # Skip separator row (|---|---|)
        if re.match(r'\|[\s:|-]+\|$', line):
            continue
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if cells:
            rows.append(cells)
    return rows


def convert(md_text, md_dir=''):
    """Convert annotated markdown to section0.xml content.
    Returns (xml_parts, image_files) where image_files is list of absolute paths."""
    lines = md_text.split('\n')
    xml_parts = []
    image_files = []  # collect image file paths for --images flag
    i = 0
    pending_pagebreak = False
    pending_table_style = 'data'
    is_first_element = True
    heading_level = 0  # track current heading context for bullet hierarchy

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank line → insert spacer for paragraph separation
        if not stripped:
            if xml_parts and xml_parts[-1] != spacer():
                xml_parts.append(spacer())
            i += 1
            continue

        # ── Annotations ──
        if stripped == '<!-- pagebreak -->':
            pending_pagebreak = True
            i += 1
            continue

        if stripped.startswith('<!-- table:'):
            m = re.match(r'<!-- table:(\w+) -->', stripped)
            if m:
                pending_table_style = m.group(1)
            i += 1
            continue

        if stripped.startswith('<!-- box:'):
            m = re.match(r'<!-- box:(\w+) -->', stripped)
            box_type = m.group(1) if m else 'note'
            # Collect lines until <!-- /box -->
            box_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() != '<!-- /box -->':
                box_lines.append(lines[i])
                i += 1
            i += 1  # skip closing tag

            if not is_first_element:
                xml_parts.append(spacer())
            xml_parts.append(emit_box(box_lines, box_type))
            xml_parts.append(spacer())
            is_first_element = False
            continue

        # ── Images: ![alt](file) or ![[file]] ──
        img_match = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', stripped)
        img_match2 = re.match(r'^!\[\[([^\]]+)\]\]', stripped)
        if img_match or img_match2:
            if img_match:
                filename = img_match.group(2).strip()
            else:
                filename = img_match2.group(1).strip()

            # Resolve path relative to markdown file directory
            img_path = os.path.join(md_dir, filename) if md_dir else filename
            if os.path.isfile(img_path):
                image_files.append(os.path.abspath(img_path))
                # Generate image ID from filename
                img_id = re.sub(r'[^A-Za-z0-9_]', '_', os.path.splitext(filename)[0])
                if not is_first_element:
                    xml_parts.append(spacer())
                xml_parts.append(emit_image(img_id))
                xml_parts.append(spacer())
                is_first_element = False
            # If file doesn't exist, skip silently
            i += 1
            continue

        # ── Horizontal rule (---) ──
        if re.match(r'^-{3,}$', stripped):
            # Treat as section separator — add extra spacer
            xml_parts.append(spacer())
            i += 1
            continue

        # ── Headings ──
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title = stripped[2:].strip()
            if is_first_element:
                xml_parts.append(emit_title(title))
                xml_parts.append(spacer())
                is_first_element = False
            else:
                # Subsequent # headings (shouldn't normally happen)
                xml_parts.append(spacer())
                xml_parts.append(emit_title(title))
                xml_parts.append(spacer())
            i += 1
            continue

        if stripped.startswith('#### '):
            heading = stripped[5:].strip()
            if not is_first_element:
                xml_parts.append(spacer())
            xml_parts.append(emit_heading4(heading))
            xml_parts.append(spacer())
            is_first_element = False
            heading_level = 4
            i += 1
            continue

        if stripped.startswith('### '):
            heading = stripped[4:].strip()
            if not is_first_element:
                xml_parts.append(spacer())
            xml_parts.append(emit_heading3(heading))
            xml_parts.append(spacer())
            is_first_element = False
            heading_level = 3
            i += 1
            continue

        if stripped.startswith('## '):
            heading = stripped[3:].strip()
            # ## always starts a new page (unless it's the first element)
            if not is_first_element:
                xml_parts.append(spacer())
            result = emit_section_header(heading)
            # Inject pageBreak="1" if not the first element
            if not is_first_element:
                result = result.replace('pageBreak="0"', 'pageBreak="1"', 1)
            xml_parts.append(result)
            xml_parts.append(spacer())
            pending_pagebreak = False
            is_first_element = False
            heading_level = 2
            i += 1
            continue

        # ── Tables ──
        if stripped.startswith('|'):
            # Collect all table lines
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                table_lines.append(lines[i])
                i += 1
            rows = parse_table_block(table_lines)
            if rows:
                if not is_first_element:
                    xml_parts.append(spacer())
                xml_parts.append(emit_table(rows, style=pending_table_style))
                xml_parts.append(spacer())
                pending_table_style = 'data'  # reset to default
                is_first_element = False
            continue

        # ── Bullet items ──
        bullet_match = re.match(r'^(\s*)- (.+)', line)
        if bullet_match:
            indent_level = len(bullet_match.group(1))
            text = bullet_match.group(2).strip()
            is_indented = indent_level >= 2
            xml_parts.append(emit_bullet(text, indent=is_indented))
            is_first_element = False
            i += 1
            continue

        # ── Numbered list ──
        num_match = re.match(r'^(\s*)(\d+)\.\s+(.+)', line)
        if num_match:
            indent_level = len(num_match.group(1))
            number = int(num_match.group(2))
            text = num_match.group(3).strip()
            xml_parts.append(emit_numbered_item(number, text))
            is_first_element = False
            i += 1
            continue

        # ── Plain paragraph ──
        if stripped:
            xml_parts.append(emit_body(stripped))
            is_first_element = False

        i += 1

    return xml_parts, image_files


def main():
    parser = argparse.ArgumentParser(description='Convert annotated markdown to HWPX section0.xml')
    parser.add_argument('input', help='Path to annotated markdown file')
    parser.add_argument('--output', '-o', required=True, help='Output path (.xml or .hwpx)')
    parser.add_argument('--build', action='store_true',
                        help='Also build HWPX (requires build_hwpx.py)')
    parser.add_argument('--title', default='', help='Document title for HWPX metadata')
    args = parser.parse_args()

    # Read input
    with open(args.input, encoding='utf-8') as f:
        md_text = f.read()

    # Resolve markdown file directory for relative image paths
    md_dir = os.path.dirname(os.path.abspath(args.input))

    # Convert
    xml_parts, image_files = convert(md_text, md_dir=md_dir)

    # Assemble section0.xml
    xml_content = XML_HEADER + SEC_OPEN + '\n'
    xml_content += ''.join(xml_parts)
    xml_content += '\n' + SEC_CLOSE + '\n'

    # Determine output path
    if args.output.endswith('.hwpx'):
        section_path = args.output.replace('.hwpx', '_section0.xml')
    else:
        section_path = args.output

    with open(section_path, 'w', encoding='utf-8') as f:
        f.write(xml_content)
    print(f'[INFO] section0.xml written: {section_path} ({len(xml_content)} bytes)')

    # Optionally build HWPX
    if args.build or args.output.endswith('.hwpx'):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        build_script = os.path.join(script_dir, 'build_hwpx.py')

        # Extract title from markdown if not provided
        title = args.title
        if not title:
            m = re.search(r'^# (.+)', md_text, re.MULTILINE)
            if m:
                title = re.sub(r'[\U0001F000-\U0001FFFF\u2600-\u27FF\u2B50]', '', m.group(1)).strip()
            else:
                title = 'Untitled'

        hwpx_path = args.output if args.output.endswith('.hwpx') else args.output.replace('.xml', '.hwpx')
        cmd = f'python3 "{build_script}" --section "{section_path}" --output "{hwpx_path}" --title "{title}"'
        if image_files:
            img_args = ' '.join(f'"{p}"' for p in image_files)
            cmd += f' --images {img_args}'
            print(f'[INFO] Including {len(image_files)} image(s)')
        print(f'[INFO] Building HWPX...')
        os.system(cmd)


if __name__ == '__main__':
    main()
