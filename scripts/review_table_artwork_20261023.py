"""Source-exact editable three-rule paper tables; no manuscript mutation.

Run with the dedicated scifig interpreter. Each table is a 183-mm vector
canvas with 7-point Arial, source strings, 1200-dpi raster and 150-dpi preview.
Titles and captions are delivered separately, outside table-only artwork.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/revision_review_20261023/artwork'
SOURCES = [ROOT / 'manuscript/ESWA_Manuscript.md',
           ROOT / 'manuscript/ESWA_Supplementary.md']
os.environ['MPLCONFIGDIR'] = str(ROOT / 'temp/mpl_review_20261023')
from figstyle import apply_house_style, audit

plt = apply_house_style(fontsize=7.0)
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D
from PIL import Image
import pymupdf as fitz

plt.rcParams.update({'font.family': 'Arial', 'font.size': 7.0,
                     'pdf.fonttype': 42, 'ps.fonttype': 42,
                     'svg.fonttype': 'none', 'savefig.bbox': None,
                     'text.color': 'black', 'figure.facecolor': 'white',
                     'svg.hashsalt': 'eswa-tables-20261023'})
WIDTH_MM = 183.0
WIDTH_PT = WIDTH_MM / 25.4 * 72
FONT_PT = 7.0
MARGIN_PT = 6.0
CELL_XPAD = 5.0
LINE_SPACING_PT = 8.5
NORMAL = FontProperties(family='Arial', size=FONT_PT)
BOLD = FontProperties(family='Arial', size=FONT_PT, weight='bold')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalize(s):
    return ' '.join(s.split())


def parse_tables(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    tables = []
    pending = None
    i = 0
    while i < len(lines):
        if re.match(r'^\*\*Table (?:S)?\d+\.', lines[i]):
            pending = lines[i]
        if lines[i].startswith('|'):
            block = []
            start = i + 1
            while i < len(lines) and lines[i].startswith('|'):
                block.append([x.strip() for x in lines[i].strip('|').split('|')])
                i += 1
            if len(block) < 3 or not all(re.fullmatch(r':?-+:?', x) for x in block[1]):
                raise AssertionError((path, start, 'Not a Markdown table'))
            if pending is None:
                raise AssertionError((path, start, 'Missing external title/caption'))
            label = re.match(r'^\*\*Table ((?:S)?\d+)\.', pending).group(1)
            cells = [block[0]] + block[2:]
            assert all(len(row) == len(cells[0]) for row in cells)
            tables.append(dict(label=label, source=path.name, line=start,
                               caption=pending, cells=cells))
            pending = None
            continue
        i += 1
    return tables


def width_pt(text, renderer, prop):
    return renderer.get_text_width_height_descent(text, prop, False)[0] * 72 / renderer.dpi


def wrap(text, available, renderer, prop):
    # Keep a denominator with its slash when a header wraps; source characters
    # and word order remain identical after whitespace normalization.
    words = re.findall(r'/\s+\S+|\S+', text)
    lines = []
    current = ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if current and width_pt(candidate, renderer, prop) > available:
            lines.append(current)
            current = word
        else:
            current = candidate
        if width_pt(current, renderer, prop) > available:
            raise AssertionError((text, available, 'Unbreakable word is too wide'))
    if current:
        lines.append(current)
    return '\n'.join(lines)


def col_widths(label, ncol):
    usable = WIDTH_PT - 2 * MARGIN_PT
    # Allocate space to the actual source labels. Remaining numeric columns
    # share one width; the two text columns in table1 have explicit allocations.
    if label == '1':
        return [usable * .22] + [usable * .145] * 4 + [usable * .20]
    first = {'2': .35, '3': .30, '4': .35,
             'S1': .43, 'S2': .28, 'S3': .30, 'S4': .30, 'S5': .18}[label]
    return [usable * first] + [usable * (1-first)/(ncol-1)] * (ncol-1)


def svg_source_check(path, wrapped):
    ns = {'s': 'http://www.w3.org/2000/svg'}
    root = ET.parse(path).getroot()
    assert not root.findall('.//s:image', ns), 'SVG contains raster content'
    found = 0
    for ri, row in enumerate(wrapped):
        for ci, text in enumerate(row):
            node = root.find(f".//*[@id='cell-r{ri}-c{ci}']")
            assert node is not None, (ri, ci, 'Editable cell not found')
            rendered = ' '.join(''.join(n.itertext()) for n in node.findall('.//s:text', ns))
            assert normalize(rendered) == normalize(text), (ri, ci, rendered, text)
            found += 1
    return found


def draw_table(table):
    label = table['label']
    cells = table['cells']
    ncol = len(cells[0])
    widths = col_widths(label, ncol)
    probe = plt.figure(figsize=(WIDTH_MM/25.4, 1), dpi=150)
    probe.canvas.draw()
    renderer = probe.canvas.get_renderer()
    wrapped = [[wrap(cell, widths[ci]-2*CELL_XPAD, renderer,
                      BOLD if ri == 0 else NORMAL)
                for ci, cell in enumerate(row)] for ri, row in enumerate(cells)]
    plt.close(probe)
    assert all(normalize(cells[r][c]) == normalize(wrapped[r][c])
               for r in range(len(cells)) for c in range(ncol))
    heights = [max(22.0 if ri == 0 else 18.0,
                   max(s.count('\n')+1 for s in row)*LINE_SPACING_PT + 10.0)
               for ri, row in enumerate(wrapped)]
    height_pt = sum(heights) + 2*MARGIN_PT
    fig = plt.figure(figsize=(WIDTH_PT/72, height_pt/72), dpi=150)
    artists = []
    ytop = height_pt-MARGIN_PT
    row_bounds = []
    for ri, row in enumerate(wrapped):
        bottom = ytop-heights[ri]
        row_bounds.append((bottom, ytop))
        left = MARGIN_PT
        for ci, text in enumerate(row):
            right = left+widths[ci]
            x = left+CELL_XPAD if ci == 0 else right-CELL_XPAD
            artist = fig.text(x/WIDTH_PT, ((ytop+bottom)/2)/height_pt, text,
                              fontsize=FONT_PT, fontfamily='Arial',
                              fontweight='bold' if ri == 0 else 'normal',
                              ha='left' if ci == 0 else 'right', va='center',
                              linespacing=1.2, color='black')
            artist.set_gid(f'cell-r{ri}-c{ci}')
            artists.append((artist, ri, ci, (left, bottom, right, ytop)))
            left = right
        ytop = bottom
    rules = [(height_pt-MARGIN_PT, .75),
             (height_pt-MARGIN_PT-heights[0], .45),
             (MARGIN_PT, .75)]
    for y, lw in rules:
        fig.add_artist(Line2D([MARGIN_PT/WIDTH_PT, 1-MARGIN_PT/WIDTH_PT],
                             [y/height_pt, y/height_pt],
                             transform=fig.transFigure, linewidth=lw,
                             color='black', solid_capstyle='butt'))
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    boxes = []
    violations = []
    for artist, ri, ci, cell in artists:
        bb = artist.get_window_extent(renderer)
        bb = [float(v)*72/fig.dpi for v in (bb.x0, bb.y0, bb.x1, bb.y1)]
        if not (bb[0] >= cell[0]+1 and bb[2] <= cell[2]-1 and
                bb[1] >= cell[1]+1 and bb[3] <= cell[3]-1):
            violations.append(dict(kind='outside-cell', row=ri, column=ci, bbox=bb, cell=cell))
        for yy, lw in rules:
            if bb[1]-.75-lw/2 <= yy <= bb[3]+.75+lw/2:
                violations.append(dict(kind='rule-text-intersection', row=ri, column=ci, rule_y=yy))
        boxes.append(dict(row=ri, column=ci, source=cells[ri][ci],
                          display=wrapped[ri][ci], bbox_pt=bb, cell_pt=cell,
                          font_pt=artist.get_fontsize(), alignment=artist.get_ha()))
    for i, a in enumerate(boxes):
        for b in boxes[i+1:]:
            aa, bb = a['bbox_pt'], b['bbox_pt']
            if min(aa[2], bb[2]) > max(aa[0], bb[0]) and min(aa[3], bb[3]) > max(aa[1], bb[1]):
                violations.append(dict(kind='text-overlap', cells=[[a['row'],a['column']],[b['row'],b['column']]]))
    house = audit(fig, verbose=False)
    house = json.loads(json.dumps(house, default=lambda value: value.item()))
    assert house['ok'], house
    assert not violations, violations
    stem = OUT/f'table_{label.lower()}'
    for ext in ('svg','pdf'):
        fig.savefig(str(stem)+'.'+ext, bbox_inches=None, pad_inches=0,
                    metadata={'Creator':'Source-exact editable paper table generator'})
    fig.savefig(str(stem)+'.png', dpi=1200, bbox_inches=None, pad_inches=0)
    fig.savefig(str(stem)+'_preview.png', dpi=150, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    editable = svg_source_check(str(stem)+'.svg', wrapped)
    with fitz.open(str(stem)+'.pdf') as doc:
        assert len(doc)==1 and not doc[0].get_images(), 'PDF is not a pure vector table'
        assert abs(doc[0].rect.width-WIDTH_PT)<.01
        fonts=[]
        for font in doc[0].get_fonts(full=True):
            name, ext, typ, payload=doc.extract_font(font[0])
            assert ext=='ttf' and payload, ('Font not embedded TrueType',font)
            fonts.append(dict(name=name, extension=ext, embedded_bytes=len(payload)))
        assert fonts
    raster=[]
    for suffix, dpi in [('.png',1200),('_preview.png',150)]:
        with Image.open(str(stem)+suffix) as im:
            reported=im.info.get('dpi')
            assert reported and abs(reported[0]-dpi)<.1
            assert abs(im.width/dpi*25.4-WIDTH_MM)<25.4/dpi+.001
            raster.append(dict(file=stem.name+suffix, pixels=list(im.size), dpi=reported))
    geometry=dict(table=label, source=table['source'], source_line=table['line'],
                  width_mm=WIDTH_MM, height_mm=height_pt/72*25.4,
                  min_font_pt=FONT_PT, font_family='Arial', rows=len(cells)-1,
                  columns=ncol, horizontal_rules=3, vertical_rules=0,
                  body_fill=False, header_bands=1, editable_cells=editable,
                  rule_y_pt=[x[0] for x in rules], text_boxes=boxes,
                  violations=violations, house_audit=house,
                  pdf_fonts=fonts, raster=raster, passed=True)
    (OUT/(stem.name+'_geometry.json')).write_text(json.dumps(geometry,indent=2),encoding='utf-8')
    print(json.dumps({k:geometry[k] for k in ['table','rows','columns','width_mm','height_mm','passed']}),flush=True)
    return geometry


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    tables=[t for path in SOURCES for t in parse_tables(path)]
    assert [t['label'] for t in tables]==['1','2','3','4','S1','S2','S3','S4','S5']
    font_path=font_manager.findfont('Arial',fallback_to_default=False)
    inputs={str(path.relative_to(ROOT)):sha(path) for path in SOURCES}
    reports=[draw_table(table) for table in tables]
    assert inputs=={str(path.relative_to(ROOT)):sha(path) for path in SOURCES}, 'Manuscript source changed during run'
    (OUT/'table_source_data.json').write_text(json.dumps(tables,indent=2),encoding='utf-8')
    (OUT/'table_captions.md').write_text('# Table titles and captions\n\n'+'\n\n'.join(t['caption'] for t in tables)+'\n',encoding='utf-8')
    report=dict(passed=True, tables=len(tables), source_sha256=inputs,
                generator_sha256=sha(__file__), Arial_font=font_path,
                editable_svg=True, pdf_embedded_truetype=True, pdf_raster_images=0,
                final_width_mm=WIDTH_MM, raster_dpi=1200, preview_dpi=150,
                geometry_violations=sum(len(r['violations']) for r in reports),
                source_cell_count=sum(r['editable_cells'] for r in reports),
                files=[dict(stem='table_'+r['table'].lower(), height_mm=r['height_mm'],
                            rows=r['rows'],columns=r['columns']) for r in reports])
    (OUT/'table_artwork_metadata.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
