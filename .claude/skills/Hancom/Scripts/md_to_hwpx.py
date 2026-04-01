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
    'shade': '4',        # 15pt 함초롬바탕 bold, shade=#FFD700 — ○-level
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
# XML Templates
# ──────────────────────────────────────────────
XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'

SEC_OPEN = ('<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section"'
            ' xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph"'
            ' xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph"'
            ' xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core"'
            ' xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"'
            ' xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">')

SEC_CLOSE = '</hs:sec>'

FULL_WIDTH = 48190  # content area in HWPUNIT


def p(para_id, char_id, text, page_break=False):
    """Generate a simple paragraph with one run."""
    pb = '1' if page_break else '0'
    escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return (f'<hp:p id="0" paraPrIDRef="{para_id}" styleIDRef="0"'
            f' pageBreak="{pb}" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{char_id}"><hp:t>{escaped}</hp:t></hp:run>'
            f'</hp:p>\n')


def p_multi_run(para_id, runs, page_break=False):
    """Generate a paragraph with multiple runs [(char_id, text), ...]."""
    pb = '1' if page_break else '0'
    xml = (f'<hp:p id="0" paraPrIDRef="{para_id}" styleIDRef="0"'
           f' pageBreak="{pb}" columnBreak="0" merged="0">')
    for char_id, text in runs:
        escaped = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        xml += f'<hp:run charPrIDRef="{char_id}"><hp:t>{escaped}</hp:t></hp:run>'
    xml += '</hp:p>\n'
    return xml


def spacer():
    """Generate an 11pt spacer line."""
    return p(PARA['default'], CHAR['spacer'], ' ')


def emit_title(text):
    """Emit main document title (centered, 26pt bold)."""
    # Remove emoji if present
    clean = re.sub(r'[\U0001F000-\U0001FFFF\u2600-\u27FF\u2B50]', '', text).strip()
    return p(PARA['center'], CHAR['title'], clean)


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


def emit_bullet(text, level=0):
    """Emit a bullet item. Level 0 = □, level 1 = ○ (under ##)."""
    # Check for bold keyword pattern: **(keyword)** value
    bold_match = re.match(r'\*\*\((.+?)\)\*\*\s*(.*)', text)
    bold_match2 = re.match(r'\*\*(.+?)\*\*:\s*(.*)', text)

    symbol = '□' if level == 0 else '○'
    para = PARA['bullet'] if level == 0 else PARA['sub_item']

    if bold_match:
        # symbol (keyword) explanation
        return p_multi_run(para, [
            (CHAR['body'], f'{symbol} '),
            (CHAR['bold'], f'({bold_match.group(1)})'),
            (CHAR['body'], f' {bold_match.group(2)}'),
        ])
    elif bold_match2:
        # symbol keyword: value
        return p_multi_run(para, [
            (CHAR['body'], f'{symbol} '),
            (CHAR['bold'], bold_match2.group(1)),
            (CHAR['body'], f': {bold_match2.group(2)}'),
        ])
    else:
        # Split any remaining **bold** in the text
        runs = _split_bold_runs(text, CHAR['body'], CHAR['bold'])
        return p_multi_run(para, [
            (CHAR['body'], f'{symbol} '),
        ] + runs)


def emit_heading2(text, page_break=False):
    """Emit ## heading as □ section-level (gold shade, no parentheses)."""
    # Remove numbering like "1. " or "2.1 "
    clean = re.sub(r'^[\d.]+\s*', '', text).strip()
    return p_multi_run(PARA['bullet'], [
        (CHAR['body'], '□ '),
        (CHAR['shade'], clean),
    ], page_break=page_break)


def emit_heading3(text):
    """Emit ### heading as ○ sub-section (bold, no shade)."""
    clean = re.sub(r'^[\d.]+\s*', '', text).strip()
    return p_multi_run(PARA['bullet'], [
        (CHAR['body'], '○ '),
        (CHAR['bold'], clean),
    ])


def emit_caption(text):
    """Emit centered caption like < Title >."""
    return p(PARA['center'], CHAR['caption'], f'< {text} >')


def emit_table(rows, style='data'):
    """Emit a table from parsed rows. First row = header."""
    if not rows or len(rows) < 2:
        return ''

    num_cols = len(rows[0])
    if num_cols == 0:
        return ''

    # Calculate column widths (distribute evenly)
    col_width = FULL_WIDTH // num_cols

    head_bf = BF['gray_head'] if style == 'data' else BF['blue_head']
    body_bf = BF['cell']

    xml = (f'<hp:p id="0" paraPrIDRef="0" styleIDRef="0"'
           f' pageBreak="0" columnBreak="0" merged="0">'
           f'<hp:run charPrIDRef="{CHAR["small"]}">'
           f'<hp:tbl rowCnt="{len(rows)}" colCnt="{num_cols}"'
           f' cellSpacing="0" borderFillIDRef="{BF["cell"]}"'
           f' pageBreak="CELL" repeatHeader="0" id="0">\n')

    for row_idx, row in enumerate(rows):
        is_header = (row_idx == 0)
        bf = head_bf if is_header else body_bf
        char = CHAR['table_head'] if is_header else CHAR['table_body']

        xml += '<hp:tr>\n'
        for col_idx, cell_text in enumerate(row):
            cell_text = cell_text.strip()
            # Remove bold markers from cell text
            cell_text = re.sub(r'\*\*(.+?)\*\*', r'\1', cell_text)
            escaped = cell_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

            xml += (f'<hp:tc name="" header="0" hasMargin="0" protect="0"'
                    f' editable="0" dirty="0" borderFillIDRef="{bf}">'
                    f'<hp:cellAddr colAddr="{col_idx}" rowAddr="{row_idx}"/>'
                    f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
                    f'<hp:cellSz width="{col_width}" height="1200"/>'
                    f'<hp:cellMargin left="283" right="283" top="141" bottom="141"/>'
                    f'<hp:subList>'
                    f'<hp:p paraPrIDRef="{PARA["table_cell"]}" styleIDRef="0">'
                    f'<hp:run charPrIDRef="{char}"><hp:t>{escaped}</hp:t></hp:run>'
                    f'</hp:p>'
                    f'</hp:subList>'
                    f'</hp:tc>\n')
        xml += '</hp:tr>\n'

    xml += '</hp:tbl></hp:run></hp:p>\n'
    return xml


def emit_box(content_lines, box_type='note'):
    """Emit a 1x1 table box wrapping content lines."""
    bf = BF.get(box_type, BF['cell'])
    char = CHAR['small'] if box_type == 'note' else CHAR['table_body']

    inner_xml = ''
    for line in content_lines:
        line = line.strip()
        if not line:
            continue
        # Strip bullet prefix if present
        if line.startswith('- '):
            line = line[2:]
        if '**' in line:
            runs = _split_bold_runs(line, char, CHAR['bold'])
            run_xml = ''
            for rc, rt in runs:
                esc = rt.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                run_xml += f'<hp:run charPrIDRef="{rc}"><hp:t>{esc}</hp:t></hp:run>'
            inner_xml += (f'<hp:p paraPrIDRef="{PARA["default"]}" styleIDRef="0">'
                          f'{run_xml}</hp:p>\n')
        else:
            escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            inner_xml += (f'<hp:p paraPrIDRef="{PARA["default"]}" styleIDRef="0">'
                          f'<hp:run charPrIDRef="{char}"><hp:t>{escaped}</hp:t></hp:run>'
                          f'</hp:p>\n')

    xml = (f'<hp:p id="0" paraPrIDRef="0" styleIDRef="0"'
           f' pageBreak="0" columnBreak="0" merged="0">'
           f'<hp:run charPrIDRef="{CHAR["small"]}">'
           f'<hp:tbl rowCnt="1" colCnt="1" cellSpacing="0"'
           f' borderFillIDRef="{BF["cell"]}"'
           f' pageBreak="CELL" repeatHeader="0" id="0">'
           f'<hp:tr>'
           f'<hp:tc name="" header="0" hasMargin="0" protect="0"'
           f' editable="0" dirty="0" borderFillIDRef="{bf}">'
           f'<hp:cellAddr colAddr="0" rowAddr="0"/>'
           f'<hp:cellSpan colSpan="1" rowSpan="1"/>'
           f'<hp:cellSz width="{FULL_WIDTH}" height="1800"/>'
           f'<hp:cellMargin left="283" right="283" top="141" bottom="141"/>'
           f'<hp:subList>\n'
           f'{inner_xml}'
           f'</hp:subList>'
           f'</hp:tc>'
           f'</hp:tr>'
           f'</hp:tbl></hp:run></hp:p>\n')
    return xml


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


def convert(md_text):
    """Convert annotated markdown to section0.xml content."""
    lines = md_text.split('\n')
    xml_parts = []
    i = 0
    pending_pagebreak = False
    pending_table_style = 'data'
    is_first_element = True
    under_h2 = False  # track if we're under a ## heading (bullets become sub-items)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
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

        if stripped.startswith('### '):
            heading = stripped[4:].strip()
            if not is_first_element:
                xml_parts.append(spacer())
            xml_parts.append(emit_heading3(heading))
            xml_parts.append(spacer())
            is_first_element = False
            under_h2 = True  # ### is under ##, bullets stay as sub-items
            i += 1
            continue

        if stripped.startswith('## '):
            heading = stripped[3:].strip()
            if not is_first_element:
                xml_parts.append(spacer())
            xml_parts.append(emit_heading2(heading, page_break=pending_pagebreak))
            xml_parts.append(spacer())
            pending_pagebreak = False
            is_first_element = False
            under_h2 = True  # bullets after ## become sub-items
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
            indent = len(bullet_match.group(1))
            text = bullet_match.group(2).strip()
            # Under ## or ###: top-level bullets become sub-items
            if under_h2 and indent < 2:
                level = 1  # force sub-item level under headings
            else:
                level = 1 if indent >= 2 else 0
            # No spacer between consecutive bullets at same level
            xml_parts.append(emit_bullet(text, level))
            is_first_element = False
            i += 1
            continue

        # ── Numbered list ──
        num_match = re.match(r'^(\s*)\d+\.\s+(.+)', line)
        if num_match:
            text = num_match.group(2).strip()
            indent = len(num_match.group(1))
            if under_h2 and indent < 2:
                level = 1
            else:
                level = 1 if indent >= 2 else 0
            xml_parts.append(emit_bullet(text, level))
            is_first_element = False
            i += 1
            continue

        # ── Plain paragraph ──
        if stripped:
            xml_parts.append(emit_body(stripped))
            is_first_element = False

        i += 1

    return xml_parts


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

    # Convert
    xml_parts = convert(md_text)

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
        print(f'[INFO] Building HWPX...')
        os.system(cmd)


if __name__ == '__main__':
    main()
