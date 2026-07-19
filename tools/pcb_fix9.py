"""Fix round 9: widen +3.3V column top (x->171.2 above y79) to reconnect
the C1/C2/U1.8/L1 supply cluster through the channel east of the GND fence."""
import pcbnew

FMM = pcbnew.FromMM
b = pcbnew.LoadBoard(r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_pcb")
PTS = [(140.40, 90.30), (148.70, 90.30), (150.80, 92.20), (155.60, 92.20),
       (155.60, 82.90), (157.90, 82.90), (157.90, 92.20), (168.80, 92.20),
       (168.80, 75.90), (171.20, 75.90), (171.20, 79.00), (170.10, 79.00),
       (170.10, 95.10), (140.40, 95.10)]
for z in b.Zones():
    if z.GetNetname() == "+3.3V":
        o = z.Outline()
        o.RemoveAllContours()
        o.NewOutline()
        for (x, y) in PTS:
            o.Append(FMM(x), FMM(y))
        print("widened column top")
        break
b.BuildConnectivity()
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(b.GetFileName(), b)
print("saved")
