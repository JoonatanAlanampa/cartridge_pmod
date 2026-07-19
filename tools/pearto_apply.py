"""Draw the pearto logo on B.Silkscreen, back of the audio extension.
X-mirrored so it views correctly from the physical back side."""
import json, pcbnew

FMM = pcbnew.FromMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
data = json.load(open(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\tools\pearto_contours.json"))
W, H = data["size"]

CX, CY = 188.3, 79.4      # board-mm center of logo
HEIGHT = 8.6              # mm
S = HEIGHT / H
LINE = FMM(0.16)
LAYER = pcbnew.B_SilkS

def xf(px, py):
    # mirror X for back-side viewing
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
    print("poly", name, len(pts))

for c in data["circles"]:
    sh = pcbnew.PCB_SHAPE(b)
    sh.SetShape(pcbnew.SHAPE_T_CIRCLE)
    sh.SetCenter(xf(c["cx"], c["cy"]))
    sh.SetEnd(xf(c["cx"] + c["r"], c["cy"]))
    sh.SetFilled(bool(c["fill"]))
    sh.SetWidth(LINE)
    sh.SetLayer(LAYER)
    b.Add(sh)
    print("circle", round(c["r"] * S, 2), "mm", "filled" if c["fill"] else "")

pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
