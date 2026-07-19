"""Attach the exact C2884998 EasyEDA STEP model to J3.
CLI: rx ry rz ox oy oz (defaults from geometry mapping)."""
import sys, pcbnew

b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
args = [float(x) for x in sys.argv[1:7]] or [0, 0, 90, 0.6, 0, 0]
rx, ry, rz, ox, oy, oz = args
fp = b.FindFootprintByReference("J3")
models = fp.Models()
models.clear()
m = pcbnew.FP_3DMODEL()
m.m_Filename = "${KIPRJMOD}/easyeda/ea.3dshapes/AUDIO-SMD_PJ-320B_C2884998.step"
m.m_Rotation = pcbnew.VECTOR3D(rx, ry, rz)
m.m_Offset = pcbnew.VECTOR3D(ox, oy, oz)
models.push_back(m)
print("J3 model:", m.m_Filename.split("/")[-1], "rot", (rx, ry, rz), "off", (ox, oy, oz))
pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
