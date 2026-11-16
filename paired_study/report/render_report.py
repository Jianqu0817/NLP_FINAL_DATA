"""Typeset the editable course report. No experiment computations are performed."""
from pathlib import Path
from xml.sax.saxutils import escape
import argparse
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE=HERE/'course_report.md'
OUTPUT=ROOT/'output'/'pdf'/'cisc7021_schema_adaptation_report.pdf'
FONT=Path('C:/Windows/Fonts')
for name,file in [('Body','georgia.ttf'),('BodyBold','georgiab.ttf'),('BodyItalic','georgiai.ttf'),('Sans','calibri.ttf'),('SansBold','calibrib.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(FONT/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='BodyItalic',boldItalic='BodyBold')
pdfmetrics.registerFontFamily('Sans',normal='Sans',bold='SansBold',italic='Sans',boldItalic='SansBold')
INK=colors.HexColor('#203039'); TEAL=colors.HexColor('#087F8C'); MUTED=colors.HexColor('#596B75')
styles={
 'title':ParagraphStyle('title',fontName='SansBold',fontSize=25,leading=29,textColor=INK,spaceAfter=12),
 'meta':ParagraphStyle('meta',fontName='Sans',fontSize=9.5,leading=13,textColor=MUTED,spaceAfter=16),
 'h2':ParagraphStyle('h2',fontName='SansBold',fontSize=15,leading=18,textColor=TEAL,spaceBefore=11,spaceAfter=8,keepWithNext=True),
 'h3':ParagraphStyle('h3',fontName='SansBold',fontSize=11.4,leading=14,textColor=INK,spaceBefore=9,spaceAfter=6,keepWithNext=True),
 'p':ParagraphStyle('p',fontName='Body',fontSize=10.1,leading=14.0,textColor=INK,spaceAfter=8,splitLongWords=True),
 'bullet':ParagraphStyle('bullet',fontName='Body',fontSize=10.1,leading=14.0,textColor=INK,spaceAfter=6,leftIndent=11,firstLineIndent=-8),
 'cell':ParagraphStyle('cell',fontName='Sans',fontSize=8.8,leading=11.1,textColor=INK,spaceAfter=0),
 'head':ParagraphStyle('head',fontName='SansBold',fontSize=8.8,leading=11.1,textColor=colors.white,spaceAfter=0),
}

def inline(text):
    text=escape(text)
    text=re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)',lambda m:f'<a href="{m[2]}" color="#087F8C">{m[1]}</a>',text)
    text=re.sub(r'`([^`]+)`',lambda m:f'<font name="Mono" size="8.5">{m[1]}</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    return text

WIDTH=A4[0]-100

def table(lines):
    cells=[[c.strip() for c in line.strip().strip('|').split('|')] for line in lines]
    cells=[row for row in cells if not all(re.fullmatch(r':?-+:?',v) for v in row)]
    n=len(cells[0])
    # Long mechanism and probe columns get space, while numeric columns remain compact.
    header=cells[0]
    if 'Trainable mechanism' in header: ratios=[.18,.43,.14,.25]
    elif header[0]=='Rule family': ratios=[.20,.08,.37,.35]
    elif header[0].startswith('Main test'): ratios=[.29,.18,.17,.18,.18]
    elif header[0]=='Track' and n==5: ratios=[.23,.06,.237,.237,.236]
    elif n==2: ratios=[.48,.52]
    else: ratios=[1/n]*n
    data=[[Paragraph(inline(v),styles['head' if j==0 else 'cell']) for v in row] for j,row in enumerate(cells)]
    t=Table(data,colWidths=[WIDTH*r/sum(ratios) for r in ratios],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),TEAL),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F0F5F6'),colors.white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#D2DFE2'))]))
    return [t,Spacer(1,9)]

def render(draft):
    text=SOURCE.read_text(encoding='utf-8-sig')
    if not draft and re.search(r'\[(?:FINAL|PAIRED RESULTS|ORIGINAL-TASK|NEW PAIRED)',text):
        raise SystemExit('Unresolved report scaffold; use --draft or insert accepted results.')
    story=[]; lines=text.splitlines(); i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1;continue
        if line=='\\pagebreak': story.append(PageBreak());i+=1;continue
        if line.startswith('|'):
            block=[]
            while i<len(lines) and lines[i].strip().startswith('|'): block.append(lines[i]);i+=1
            story.extend(table(block));continue
        if line.startswith('# '): story.append(Paragraph(inline(line[2:]),styles['title']));i+=1;continue
        if line.startswith('## '): story.append(Paragraph(inline(line[3:]),styles['h2']));i+=1;continue
        if line.startswith('### '): story.append(Paragraph(inline(line[4:]),styles['h3']));i+=1;continue
        block=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#','|','- ','\\pagebreak')):
            block.append(lines[i].strip());i+=1
        content=' '.join(block)
        kind='bullet' if content.startswith('- ') else ('meta' if content.startswith('CISC7021 |') else 'p')
        if kind=='bullet':content='- '+content[2:]
        story.append(Paragraph(inline(content),styles[kind]))
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    target=OUTPUT.with_name(OUTPUT.stem+'_draft.pdf') if draft else OUTPUT
    def page(canvas,doc):
        canvas.saveState()
        canvas.setStrokeColor(TEAL);canvas.setLineWidth(.8);canvas.line(50,A4[1]-31,A4[0]-50,A4[1]-31)
        canvas.setFont('Sans',8);canvas.setFillColor(MUTED)
        canvas.drawString(50,A4[1]-24,'CISC7021 / STRUCTURED GENERATION')
        canvas.drawRightString(A4[0]-50,26,str(doc.page))
        canvas.drawString(50,26,'JSON Schema + data | frozen-checkpoint study'+(' | WORKING DRAFT' if draft else ''))
        canvas.restoreState()
    doc=SimpleDocTemplate(str(target),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=48,bottomMargin=44,title='Generating JSON Schema and Data from Chinese Requirements',author='',subject='CISC7021 course project: parameter-efficient adaptation and paired behavioral evaluation')
    doc.build(story,onFirstPage=page,onLaterPages=page)
    print(target)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--draft',action='store_true');render(p.parse_args().draft)
