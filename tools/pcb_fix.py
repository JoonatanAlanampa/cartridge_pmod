"""Fix round 1: respace audio parts, prune dangling stubs (DRC-guided),
refill zones. Run with KiCad 10 bundled python."""
import pcbnew, json, subprocess, os

PRJ = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge"
PCB = PRJ + r"\cartridge-pmod.kicad_pcb"
CLI = r"C:\Users\Joonatan Alanampa\AppData\Local\Programs\KiCad\10.0\bin\kicad-cli.exe"
FMM = pcbnew.FromMM

MOVES = {
    "L1":  (171.9, 75.9, 0),
    "C8":  (175.6, 75.9, 0),
    "C9":  (178.6, 75.9, 0),
    "C10": (172.2, 82.4, 90),
    "C11": (174.6, 82.4, 90),
    "R5":  (177.2, 82.4, 90),
    "C12": (172.0, 85.0, 90),
    "C13": (175.6, 85.0, 0),
    "RV1": (174.6, 90.4, 0),
}

def run_drc(tag):
    out = PRJ + rf"\drc_{tag}.json"
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "--output", out, PCB],
                   check=True, capture_output=True)
    return json.load(open(out, encoding="utf-8"))

b = pcbnew.LoadBoard(PCB)
for ref, (x, y, rot) in MOVES.items():
    fp = b.FindFootprintByReference(ref)
    fp.SetPosition(pcbnew.VECTOR2I(FMM(x), FMM(y)))
    fp.SetOrientationDegrees(rot)
print("respaced", len(MOVES), "parts")
pcbnew.SaveBoard(PCB, b)

# iterative dangling-track pruning, guided by actual DRC output
for it in range(6):
    rep = run_drc("iter")
    dangl = [v for v in rep.get("violations", []) if v["type"] == "track_dangling"]
    if not dangl:
        print(f"iter {it}: no dangling tracks left")
        break
    b = pcbnew.LoadBoard(PCB)
    killed = 0
    for v in dangl:
        for item in v["items"]:
            px, py = item["pos"]["x"], item["pos"]["y"]
            for t in list(b.GetTracks()):
                for end in (t.GetStart(), t.GetEnd()):
                    if abs(pcbnew.ToMM(end.x) - px) < 0.02 and \
                       abs(pcbnew.ToMM(end.y) - py) < 0.02:
                        b.RemoveNative(t)
                        killed += 1
                        break
                else:
                    continue
                break
    print(f"iter {it}: {len(dangl)} dangling reported, removed {killed} segments")
    if killed == 0:
        break
    pcbnew.SaveBoard(PCB, b)

# refill zones
b = pcbnew.LoadBoard(PCB)
filler = pcbnew.ZONE_FILLER(b)
filler.Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print("zones refilled, saved")
os.remove(PRJ + r"\drc_iter.json")
