import pcbnew
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
for ref in ("RV1", "J3"):
    fp = b.FindFootprintByReference(ref)
    for m in fp.Models():
        print(ref, "rot", (m.m_Rotation.x, m.m_Rotation.y, m.m_Rotation.z),
              "off", (m.m_Offset.x, m.m_Offset.y, m.m_Offset.z))
