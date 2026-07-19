"""Iteratively tune RV1/J3 3D model rotation+offset. Edit TUNE, run, render."""
import sys, pcbnew

b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")

# ref: (rot_x, rot_y, rot_z, off_x_mm, off_y_mm, off_z_mm)
TUNE = {
    "RV1": (-90, 0, 0, 0, 0, 0),
    "J3":  (0, 0, 180, 0, 0, 0),
}
if len(sys.argv) > 1:  # override from CLI: ref rx ry rz ox oy oz
    a = sys.argv[1:]
    TUNE = {a[0]: tuple(float(x) for x in a[1:7])}

for ref, (rx, ry, rz, ox, oy, oz) in TUNE.items():
    fp = b.FindFootprintByReference(ref)
    for m in fp.Models():
        m.m_Rotation = pcbnew.VECTOR3D(rx, ry, rz)
        m.m_Offset = pcbnew.VECTOR3D(ox, oy, oz)
        print(ref, "rot", (rx, ry, rz), "off", (ox, oy, oz))
pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
