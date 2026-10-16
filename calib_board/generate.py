"""Generate a fixed-size vector PDF and render its preview from the same PDF."""
import argparse
from pathlib import Path
import cv2
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import pypdfium2 as pdfium
from .common import DEFAULT_SPEC, read_data, make_board

PT = 72/25.4

def rectangles(spec):
    """Yield filled vector rectangles in board coordinates (mm), with RGB colors."""
    board, dictionary = make_board(spec)
    for s in spec['charuco']['squares']:
        yield s['id'], s['rect_mm'], [0,0,0] if s['black'] else [1,1,1]
    n = dictionary.markerSize + 2*spec['charuco']['border_bits']
    for m in spec['charuco']['markers']:
        bits = cv2.aruco.generateImageMarker(dictionary, m['id'], n, borderBits=1)
        x,y,w,h = m['rect_mm']
        for r in range(n):
            for c in range(n):
                v = int(bits[r,c])/255
                yield f"marker{m['id']}_{r}_{c}", [x+c*w/n,y+r*h/n,w/n,h/n], [v,v,v]
    for g in spec['gray_ramp']:
        yield g['id'],g['rect_mm'],[v/255 for v in g['nominal_srgb']]

def generate(spec_path=DEFAULT_SPEC, output='build/board_v1_1_A3.pdf', preview=True):
    spec = read_data(spec_path)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    pw,ph = spec['paper']['size_mm']; ox,oy = spec['paper']['board_origin_from_top_left_mm']
    c = canvas.Canvas(str(output), pagesize=(pw*PT,ph*PT), invariant=1, pageCompression=1)
    c.setTitle(spec['board_id']+' '+spec['version'])
    c.setAuthor('station_calib_board')
    def xy(x,y): return (x+ox)*PT,(ph-y-oy)*PT
    c.setLineWidth(.2*PT)
    for name,(x,y,w,h),rgb in rectangles(spec):
        c.setFillColorRGB(*rgb)
        c.rect(*xy(x,y+h),w*PT,h*PT,fill=1,stroke=0)
    c.setFillColorRGB(0,0,0)
    c.setStrokeColorRGB(0,0,0)
    for r in spec['frames']:
        x,y,w,h=r['rect_mm']; c.rect(*xy(x,y+h),w*PT,h*PT,stroke=1,fill=0)
    for ruler in spec['rulers']:
        a,b=ruler['start_mm'],ruler['end_mm']; c.line(*xy(*a),*xy(*b))
        for tick in ruler['ticks']:
            c.line(*xy(*tick['start_mm']),*xy(*tick['end_mm']))
    for h in spec['holes']:
        x,y=h['center_mm']; c.circle(*xy(x,y),h['diameter_mm']/2*PT,stroke=1,fill=0)
        for a,b in h['cross_segments_mm']: c.line(*xy(*a),*xy(*b))
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    for t in spec['texts']:
        font = 'Helvetica' if t['text'].isascii() else 'STSong-Light'
        c.setFont(font,t['font_pt']); c.drawString(*xy(*t['baseline_mm']),t['text'])
    c.showPage(); c.save()
    if preview:
        doc=pdfium.PdfDocument(str(output)); page=doc[0]
        page.render(scale=300/72).to_pil().save(str(Path(output).with_suffix('.png')),dpi=(300,300))
        page.close(); doc.close()
    return Path(output)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',default=str(DEFAULT_SPEC));p.add_argument('--output',default='build/board_v1_1_A3.pdf')
    a=p.parse_args();generate(a.spec,a.output)
if __name__=='__main__': main()
