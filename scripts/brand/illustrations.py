"""Line illustrations used where real site photos are not uploaded yet (gallery placeholders, project covers, service
headers). Engineering-drawing style on ink: steel line work, yellow for live parts. Replace with real photos in the
staff app (Website -> Gallery / Projects).
    python scripts/brand/illustrations.py   -> frontend/public/illustrations/*.svg
"""
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "frontend/public/illustrations"
INK, GRID, STEEL, DIM, LIVE, WHITE = "#0A1626", "#13253B", "#A9ADB3", "#4C5E75", "#FFC400", "#E8ECF1"


def frame(body, title):
    grid = "".join(f'<path d="M{x} 0V800" />' for x in range(0, 1201, 40)) + "".join(f'<path d="M0 {y}H1200" />' for y in range(0, 801, 40))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" role="img" aria-label="{title}">'
            f'<rect width="1200" height="800" fill="{INK}"/><g stroke="{GRID}" stroke-width="1">{grid}</g>'
            f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">{body}</g>'
            '</svg>')


def s(d, w=4, c=STEEL, extra=""):
    return f'<path d="{d}" stroke="{c}" stroke-width="{w}" {extra}/>'


def transformer(cx=600, cy=470, sc=1.0):
    b = []
    w, h = 300 * sc, 220 * sc
    x0, y0 = cx - w / 2, cy - h / 2
    b.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="8" stroke="{STEEL}" stroke-width="5"/>')
    for i in range(9):
        x = x0 - 50 * sc
        y = y0 + 20 * sc + i * 22 * sc
        b.append(s(f"M{x} {y}H{x0}", 3, DIM))
        b.append(s(f"M{x0 + w} {y}H{x0 + w + 50 * sc}", 3, DIM))
    b.append(s(f"M{x0 - 50 * sc} {y0 + 15 * sc}V{y0 + h - 15 * sc}M{x0 + w + 50 * sc} {y0 + 15 * sc}V{y0 + h - 15 * sc}", 4))
    for i in range(3):
        bx = x0 + 60 * sc + i * 90 * sc
        b.append(f'<rect x="{bx - 12 * sc}" y="{y0 - 90 * sc}" width="{24 * sc}" height="{90 * sc}" rx="4" stroke="{STEEL}" stroke-width="4"/>')
        for k in range(4):
            b.append(s(f"M{bx - 18 * sc} {y0 - 80 * sc + k * 20 * sc}H{bx + 18 * sc}", 3))
        b.append(s(f"M{bx} {y0 - 90 * sc}V{y0 - 140 * sc}", 5, LIVE))
    b.append(f'<rect x="{x0 + 40 * sc}" y="{y0 - 150 * sc}" width="{w - 80 * sc}" height="{36 * sc}" rx="18" stroke="{STEEL}" stroke-width="4"/>')
    b.append(s(f"M{x0 + 30 * sc} {y0 + h}V{y0 + h + 40 * sc}M{x0 + w - 30 * sc} {y0 + h}V{y0 + h + 40 * sc}M{x0} {y0 + h + 40 * sc}H{x0 + w}", 5))
    return "".join(b)


def panel(x0=380, y0=170, n=3):
    b = []
    for i in range(n):
        x = x0 + i * 150
        b.append(f'<rect x="{x}" y="{y0}" width="140" height="460" rx="6" stroke="{STEEL}" stroke-width="5"/>')
        b.append(f'<rect x="{x + 18}" y="{y0 + 24}" width="104" height="70" rx="4" stroke="{DIM}" stroke-width="3"/>')
        b.append(f'<circle cx="{x + 45}" cy="{y0 + 59}" r="18" stroke="{STEEL}" stroke-width="3"/><path d="M{x + 45} {y0 + 59}l12 -10" stroke="{LIVE}" stroke-width="3"/>')
        b.append(f'<circle cx="{x + 95}" cy="{y0 + 59}" r="18" stroke="{STEEL}" stroke-width="3"/><path d="M{x + 95} {y0 + 59}l-6 -14" stroke="{LIVE}" stroke-width="3"/>')
        b.append(f'<rect x="{x + 30}" y="{y0 + 140}" width="80" height="120" rx="4" stroke="{STEEL}" stroke-width="4"/>')
        b.append(s(f"M{x + 70} {y0 + 165}V{y0 + 235}", 6, LIVE if i == 1 else STEEL))
        for k in range(3):
            b.append(f'<circle cx="{x + 40 + k * 30}" cy="{y0 + 300}" r="7" fill="{LIVE if k == i else DIM}" stroke="none"/>')
        b.append(s(f"M{x + 120} {y0 + 340}v40", 6))
        for k in range(6):
            b.append(s(f"M{x + 20} {y0 + 400 + k * 8}h100", 2, DIM))
    b.append(s(f"M{x0 - 20} {y0 + 460}H{x0 + n * 150 + 10}", 5))
    return "".join(b)


def ground(y=640):
    return s(f"M60 {y}H1140", 4, DIM) + "".join(s(f"M{x} {y}l-20 22", 2, DIM) for x in range(80, 1140, 36))


def substation():
    b = [ground(640)]
    b.append(transformer(560, 500, 0.8))
    for x in (180, 1000):
        b.append(s(f"M{x} 640V120M{x - 70} 160H{x + 70}M{x - 50} 200H{x + 50}", 6))
        for k in (-60, 0, 60):
            b.append(s(f"M{x + k} 160v-24", 4) + f'<circle cx="{x + k}" cy="132" r="7" fill="{LIVE}" stroke="none"/>')
    b.append(s("M120 132C 400 180, 760 180, 1060 132", 3, LIVE))
    b.append(s("M180 200H330V360H450", 4, LIVE))
    for x in range(120, 1120, 30):
        b.append(s(f"M{x} 640V560", 2, DIM))
    b.append(s("M110 560H1130M110 600H1130", 2, DIM))
    b.append(panel(800, 420, 1).replace(f'height="460"', 'height="200"'))
    return frame("".join(b), "Substation")


def cable():
    b = [s("M80 220H380L440 640H760L820 220H1120", 5)]
    b.append(f'<path d="M455 600H745L760 640H440Z" fill="#1A2C42" stroke="none"/>')
    for i, x in enumerate((520, 600, 680)):
        b.append(f'<circle cx="{x}" cy="560" r="34" stroke="{STEEL}" stroke-width="5"/>')
        for a in range(3):
            import math
            cx = x + 13 * math.cos(a * 2.094)
            cy = 560 + 13 * math.sin(a * 2.094)
            b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" fill="{LIVE if i == 1 else DIM}" stroke="none"/>')
    b.append(s("M470 500H730", 3, DIM) + s("M480 470H720", 3, DIM))
    for x in range(480, 730, 40):
        b.append(f'<rect x="{x}" y="440" width="34" height="18" stroke="{STEEL}" stroke-width="2"/>')
    b.append(s("M520 380V300l60 -40", 3, LIVE) + f'<circle cx="580" cy="260" r="8" fill="{LIVE}" stroke="none"/>')
    b.append(s("M80 300H300M80 340H260M80 380H220", 2, DIM))
    return frame("".join(b), "Cable trench")


def solar():
    b = [ground(660)]
    import math
    b.append(f'<circle cx="980" cy="170" r="60" stroke="{LIVE}" stroke-width="5"/>')
    for k in range(12):
        a = k * math.pi / 6
        b.append(s(f"M{980 + 80 * math.cos(a):.0f} {170 + 80 * math.sin(a):.0f}L{980 + 110 * math.cos(a):.0f} {170 + 110 * math.sin(a):.0f}", 4, LIVE))
    for row in range(3):
        y = 360 + row * 100
        x0 = 120 + row * 60
        b.append(s(f"M{x0} {y + 60}L{x0 + 120} {y - 20}H{x0 + 640}L{x0 + 520} {y + 60}Z", 4))
        for k in range(1, 8):
            b.append(s(f"M{x0 + k * 65} {y + 60}L{x0 + 120 + k * 65} {y - 20}", 2, DIM))
        b.append(s(f"M{x0 + 60} {y + 20}H{x0 + 580}", 2, DIM))
        b.append(s(f"M{x0 + 40} {y + 60}V{y + 90}M{x0 + 500} {y + 60}V{y + 90}", 4))
    return frame("".join(b), "Solar plant")


def earthing():
    b = [s("M80 300H1120", 4, DIM)]
    for k, c in enumerate(("#16283F", "#13243A", "#102033")):
        b.append(f'<rect x="80" y="{300 + k * 140}" width="1040" height="140" fill="{c}" stroke="none"/>')
    b.append(f'<rect x="520" y="230" width="160" height="90" rx="6" stroke="{STEEL}" stroke-width="5"/>')
    b.append(s("M600 250V700", 10, STEEL) + s("M600 700l-12 30h24z", 4))
    b.append(s("M200 270H520", 6, LIVE) + s("M680 270H1000", 6, LIVE))
    for x in (200, 1000):
        b.append(s(f"M{x} 270V140", 6))
        b.append(f'<rect x="{x - 40}" y="90" width="80" height="50" rx="4" stroke="{STEEL}" stroke-width="4"/>')
    for r in (60, 110, 170):
        b.append(f'<path d="M{600 - r} 720 a{r} {r * 0.35} 0 0 0 {2 * r} 0" stroke="{LIVE}" stroke-width="2" stroke-dasharray="6 10"/>')
    return frame("".join(b), "Earthing")


def testing():
    b = [f'<rect x="300" y="200" width="420" height="300" rx="16" stroke="{STEEL}" stroke-width="5"/>',
         f'<rect x="340" y="240" width="340" height="150" rx="6" stroke="{DIM}" stroke-width="3"/>',
         s("M350 340C 400 260, 440 260, 470 320S 540 380, 570 300S 640 250, 670 320", 4, LIVE)]
    for k in range(4):
        b.append(f'<circle cx="{370 + k * 80}" cy="440" r="16" stroke="{STEEL}" stroke-width="3"/>')
    b.append(s("M370 456C 380 600, 700 520, 860 600", 4, "#E5484D") + s("M450 456C 470 640, 760 640, 900 640", 4, STEEL))
    b.append(f'<rect x="840" y="560" width="160" height="120" rx="6" stroke="{STEEL}" stroke-width="5"/>')
    b.append(s("M860 620H980", 3, DIM))
    return frame("".join(b), "Testing")


def lighting():
    b = [ground(680)]
    b.append(s("M600 680L620 140H640L660 680Z", 5))
    b.append(f'<circle cx="640" cy="120" r="70" stroke="{STEEL}" stroke-width="4"/>')
    import math
    for k in range(8):
        a = k * math.pi / 4
        x, y = 640 + 70 * math.cos(a), 120 + 70 * math.sin(a)
        b.append(f'<rect x="{x - 18:.0f}" y="{y - 10:.0f}" width="36" height="20" rx="4" fill="{LIVE}" stroke="none"/>')
    b.append(f'<path d="M560 170L260 680H1020L720 170Z" fill="{LIVE}" fill-opacity="0.07" stroke="none"/>')
    for x in (200, 1000):
        b.append(s(f"M{x} 680V420H{x + (60 if x < 600 else -60)}", 5) + f'<rect x="{x + (40 if x < 600 else -80)}" y="410" width="40" height="18" rx="4" fill="{LIVE}" stroke="none"/>')
    return frame("".join(b), "Lighting")


def safety():
    b = [s("M380 420C 380 250, 820 250, 820 420", 6), s("M340 420H860", 8), s("M600 260V420M520 280V420M680 280V420", 3, DIM)]
    b.append(f'<rect x="700" y="470" width="220" height="200" rx="12" stroke="{LIVE}" stroke-width="5"/>')
    b.append(s("M760 470V420a50 50 0 0 1 100 0V470", 6, LIVE))
    b.append(f'<circle cx="810" cy="550" r="16" stroke="{LIVE}" stroke-width="4"/>' + s("M810 566V610", 4, LIVE))
    b.append(f'<rect x="260" y="480" width="300" height="190" rx="8" stroke="{STEEL}" stroke-width="4"/>' + s("M290 530H530M290 570H480M290 610H510", 3, DIM))
    return frame("".join(b), "Safety")


def ev():
    b = [ground(660), f'<rect x="250" y="220" width="160" height="440" rx="14" stroke="{STEEL}" stroke-width="5"/>',
         f'<rect x="280" y="260" width="100" height="70" rx="6" stroke="{LIVE}" stroke-width="4"/>', s("M410 420C 520 420, 520 560, 640 560", 6, LIVE)]
    b.append(s("M600 600C 620 520, 680 470, 780 470H930C 990 470, 1040 520, 1060 600V630H600Z", 5))
    b.append(f'<circle cx="700" cy="640" r="34" stroke="{STEEL}" stroke-width="5"/><circle cx="980" cy="640" r="34" stroke="{STEEL}" stroke-width="5"/>')
    b.append(s("M330 300l-12 22h18l-12 22", 4, LIVE))
    return frame("".join(b), "EV charging")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = {"substation": substation(), "panel": frame(panel(), "Panels") , "transformer": frame(ground(660) + transformer(), "Transformer"),
             "cable": cable(), "solar": solar(), "earthing": earthing(), "testing": testing(), "lighting": lighting(), "safety": safety(), "ev": ev()}
    for k, v in pages.items():
        (OUT / f"{k}.svg").write_text(v)
    print(len(pages), "illustrations")


if __name__ == "__main__":
    main()
