"""Draw the pearto logo + caption on B.Silkscreen (idempotent: clears the
previous logo/caption first). X-mirrored for correct back-side viewing."""
import json, pcbnew

FMM = pcbnew.FromMM
mm = pcbnew.ToMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
data = json.load(open(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\tools\pearto_contours.json"))
W, H = data["size"]

CX, CY = 188.3, 79.4
HEIGHT = 8.6
S = HEIGHT / H
LINE = FMM(0.16)
LAYER = pcbnew.B_SilkS

# ---- clear previous logo shapes and caption
removed = 0
for d in list(b.GetDrawings()):
    if d.GetLayerName() != "B.Silkscreen":
        continue
    if d.GetClass() == "PCB_SHAPE":
        c = d.GetBoundingBox().GetCenter()
        if 182.0 < mm(c.x) < 195.0 and 72.0 < mm(c.y) < 87.0:
            b.RemoveNative(d); removed += 1
    elif d.GetClass() == "PCB_TEXT" and "by JA" in d.GetText():
        b.RemoveNative(d); removed += 1
print("cleared", removed)

def xf(px, py):
    return pcbnew.VECTOR2I(FMM(CX - (px - W / 2) * S),
                           FMM(CY + (py - H / 2) * S))

for name, pts in data["polylines"].items():
    if len(pts) < 3:
        continue
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_POLY)
    chain = pcbnew.SHAPE_LINE_CHAIN()
    for (px, py) in pts:
        chain.Append(xf(px, py))
    chain.SetClosed(True)
    poly = pcbnew.SHAPE_POLY_SET()
    poly.AddOutline(chain)
    sh.SetPolyShape(poly)
    sh.SetFilled(False)
    sh.SetWidth(LINE)
    sh.SetLayer(LAYER)
    b.Add(sh)

for c in data["circles"]:
    r_mm = max(c["r"] * S, 0.16 if c["fill"] else 0.0)
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_CIRCLE)
    ctr = xf(c["cx"], c["cy"])
    sh.SetCenter(ctr)
    sh.SetEnd(pcbnew.VECTOR2I(ctr.x + FMM(r_mm), ctr.y))
    sh.SetFilled(bool(c["fill"]))
    sh.SetWidth(LINE)
    sh.SetLayer(LAYER)
    b.Add(sh)

for a in data.get("arcs", []):
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_ARC)
    sh.SetArcGeometry(xf(*a["p1"]), xf(*a["pm"]), xf(*a["p2"]))
    sh.SetFilled(False)
    sh.SetWidth(FMM(0.2))
    sh.SetLayer(LAYER)
    b.Add(sh)

txt = pcbnew.PCB_TEXT(b)
txt.SetText("Cartridge Pmod by JA")
txt.SetPosition(pcbnew.VECTOR2I(FMM(189.0), FMM(88.8)))
txt.SetLayer(LAYER)
txt.SetMirrored(True)
txt.SetTextSize(pcbnew.VECTOR2I(FMM(0.8), FMM(0.8)))
txt.SetTextThickness(FMM(0.13))
b.Add(txt)
print("caption added")

pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
