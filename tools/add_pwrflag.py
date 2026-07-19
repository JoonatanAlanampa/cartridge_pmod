"""Add PWR_FLAG #FLG03 to the ferrite-filtered VCCA rail (fixes ERC
power_pin_not_driven on U4 VCC)."""
import re, uuid

PATH = r"C:\Users\Joonatan Alanampa\Documents\ASIC\pmod-cartridge\cartridge-pmod.kicad_sch"
lines = open(PATH, encoding="utf-8").read().splitlines()

# find the #FLG01 symbol block as template
start = end = None
for i, ln in enumerate(lines):
    if ln == "\t(symbol" and start is None:
        j = i
    if '"Reference" "#FLG01"' in ln:
        start = j
    if start is not None and ln == "\t)" and i > start:
        end = i
        break
tpl = lines[start:end + 1]

src = None
for ln in tpl:
    m = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)", ln)
    if m:
        src = (float(m.group(1)), float(m.group(2)))
        break
dx, dy = 203.2 - src[0], 146.05 - src[1]

def fnum(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return s or "0"

new = []
for ln in tpl:
    m = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)( [\d.-]+)?\)", ln)
    if m:
        x, y = float(m.group(1)) + dx, float(m.group(2)) + dy
        ln = ln[:m.start()] + f"(at {fnum(x)} {fnum(y)}{m.group(3) or ''})" + ln[m.end():]
    ln = re.sub(r'"#FLG01"', '"#FLG03"', ln)
    ln = re.sub(r'\(uuid "[^"]*"\)', lambda _: f'(uuid "{uuid.uuid4()}")', ln)
    new.append(ln)

def wire(p1, p2):
    return ["\t(wire", "\t\t(pts",
            f"\t\t\t(xy {fnum(p1[0])} {fnum(p1[1])}) (xy {fnum(p2[0])} {fnum(p2[1])})",
            "\t\t)", "\t\t(stroke", "\t\t\t(width 0)", "\t\t\t(type default)",
            "\t\t)", f"\t\t(uuid \"{uuid.uuid4()}\")", "\t)"]

new += wire((203.2, 146.05), (203.2, 149.86))
new += ["\t(junction", "\t\t(at 203.2 149.86)", "\t\t(diameter 0)",
        "\t\t(color 0 0 0 0)", f"\t\t(uuid \"{uuid.uuid4()}\")", "\t)"]

idx = lines.index("\t(sheet_instances")
out = lines[:idx] + new + lines[idx:]
open(PATH, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
print(f"inserted #FLG03 ({len(new)} lines) before sheet_instances")
