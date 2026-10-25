from pathlib import Path
import json, re, sys
from docx import Document

R = Path(__file__).resolve().parents[1]
M = R / 'manuscript'
O = R / 'results/revision_review_20261023'

def body_data(doc):
    paras = doc.paragraphs
    data_i = next((i for i, p in enumerate(paras) if p.text.strip().startswith('Data, code')), len(paras))
    ref_i = next((i for i, p in enumerate(paras) if p.text.strip() == 'References'), len(paras))
    body_end = min(data_i, ref_i)
    body = [p.text.strip() for p in paras[:body_end] if p.text.strip()]
    tail = [p.text.strip() for p in paras[data_i:ref_i] if p.text.strip()]
    refs = [p.text.strip() for p in paras[ref_i + 1:] if p.text.strip()]
    return body, tail, refs, paras, data_i, ref_i

def audit_main():
    doc = Document(M / 'ESWA_Manuscript.docx')
    body, tail, refs, paras, data_i, ref_i = body_data(doc)
    text = '\n'.join(body)
    abstract = '\n'.join(body[body.index('Abstract') + 1:body.index('Keywords: anomaly monitoring; historical review; finite retention; query completeness; time series; compressed storage')]) if 'Abstract' in body else ''
    # Simpler abstract extraction from known positions
    ai = next((p for p in tail if 'OpenAI Codex' in p), '')
    cites = []
    for m in re.finditer(r'\[([0-9][0-9,\s]*)\]', text):
        nums = [int(x) for x in re.findall(r'\d+', m.group(1))]
        cites.append((m.start(), nums, m.group(0)))
    first = {}
    for pos, nums, raw in cites:
        for n in nums:
            first.setdefault(n, pos)
    order = [n for n, _ in sorted(first.items(), key=lambda kv: kv[1])]
    ref_nums = [int(m.group(1)) for r in refs for m in [re.match(r'\[(\d+)\]', r)] if m]
    table_refs = [(m.start(), int(m.group(1))) for m in re.finditer(r'Table\s+(\d+)', text)]
    fig_refs = [(m.start(), int(m.group(1))) for m in re.finditer(r'Fig\.\s*(\d+)', text)]
    first_tables = []
    for _, n in table_refs:
        if n not in first_tables:
            first_tables.append(n)
    first_figs = []
    for _, n in fig_refs:
        if n not in first_figs:
            first_figs.append(n)
    caption_cites = [p for p in body if (p.startswith('Table ') or p.startswith('Fig.')) and re.search(r'\[\d', p)]
    tail_cites = [p for p in tail if re.search(r'\[\d', p)]
    table_cites = []
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                if re.search(r'\[\d', c.text):
                    table_cites.append(c.text)
    hyphen_tokens = re.findall(r"\b[\w]+(?:-[\w]+)+\b", text)
    result = {
        'file': str(M / 'ESWA_Manuscript.docx'),
        'paragraphs': len(paras),
        'tables': len(doc.tables),
        'inline_figures': len(doc.inline_shapes),
        'abstract_words': len(re.findall(r"\b[\w'-]+\b", abstract)),
        'abstract_sentences': len(re.findall(r'[.!?](?:\s|$)', abstract)),
        'abstract_has_not': bool(re.search(r'\bnot\b', abstract, re.I)),
        'em_dash_body': text.count('\u2014'),
        'en_dash_body': text.count('\u2013'),
        'hyphen_tokens_body': len(hyphen_tokens),
        'hyphen_examples': sorted(set(hyphen_tokens)),
        'not_body': len(re.findall(r'\bnot\b', text, re.I)),
        'journal_name_body': bool(re.search(r'Expert Systems|ESWA|Journal of', text)),
        'citation_occurrences': len(cites),
        'citation_order': order,
        'citation_order_ascending': order == sorted(order),
        'citation_missing': [n for n in range(1, 21) if n not in first],
        'reference_count': len(ref_nums),
        'reference_numbers': ref_nums,
        'reference_order_ok': ref_nums == list(range(1, 21)),
        'first_table_mentions': first_tables,
        'first_figure_mentions': first_figs,
        'table_mentions': len(table_refs),
        'figure_mentions': len(fig_refs),
        'caption_citations': caption_cites,
        'tail_citations': tail_cites,
        'table_citations': table_cites,
        'author_year_citations': re.findall(r'\((?:[A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+)?(?: et al\.)?),?\s+(?:19|20)\d\d\)', text),
        'ai_disclosure': ai,
        'ai_checks': {
            'name': 'OpenAI Codex' in ai,
            'version': 'GPT-5 Codex' in ai,
            'date': '23 October 2026' in ai,
            'application': 'limited Python code assistance and English language polishing' in ai,
            'sections': 'Sections 3.4 and 3.5' in ai,
            'validation': 'validated' in ai,
            'privacy': 'No sensitive, proprietary, or human participant data' in ai,
            'substantive': 'All substantive research tasks' in ai,
            'data': 'AI did not generate or alter data' in ai,
            'responsibility': 'full responsibility for the manuscript' in ai,
        },
        'unresolved_markers': bool(re.search(r'\[@|TODO|\{\{|MLWork|[A-Z]:[\\/]', text)),
    }
    return result

def audit_supp():
    doc = Document(M / 'ESWA_Supplementary.docx')
    body, tail, refs, paras, data_i, ref_i = body_data(doc)
    text = '\n'.join(body)
    cites = re.findall(r'\[([0-9][0-9,\s]*)\]', text)
    return {
        'file': str(M / 'ESWA_Supplementary.docx'),
        'paragraphs': len(paras),
        'tables': len(doc.tables),
        'inline_figures': len(doc.inline_shapes),
        'em_dash_body': text.count('\u2014'),
        'en_dash_body': text.count('\u2013'),
        'hyphen_tokens_body': len(re.findall(r"\b[\w]+(?:-[\w]+)+\b", text)),
        'citations': cites,
        'reference_count': len([r for r in refs if re.match(r'\[\d+\]', r)]),
        'journal_name_body': bool(re.search(r'Expert Systems|ESWA|Journal of', text)),
        'unresolved_markers': bool(re.search(r'\[@|TODO|\{\{|MLWork|[A-Z]:[\\/]', text)),
    }

if __name__ == '__main__':
    out = {'main': audit_main(), 'supplementary': audit_supp()}
    (O / 'FINAL_SUBMISSION_AUDIT.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(out, indent=2, ensure_ascii=False))
    ok = (out['main']['citation_order_ascending'] and not out['main']['citation_missing'] and
          out['main']['reference_order_ok'] and not out['main']['abstract_has_not'] and
          out['main']['em_dash_body'] == 0 and out['main']['hyphen_tokens_body'] < 20 and
          not out['main']['journal_name_body'] and not out['main']['caption_citations'] and
          not out['main']['tail_citations'] and not out['main']['table_citations'] and
          all(out['main']['ai_checks'].values()))
    print('AUDIT_OK', ok)
    sys.exit(0 if ok else 1)
