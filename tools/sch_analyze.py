"""Analyze KiCad schematic top-level elements: type, position, key info."""
import re, sys

def parse_top_elements(path):
    text = open(path, encoding="utf-8").read()
    # find top-level (depth-1) elements: lines starting with exactly one tab + (
    lines = text.splitlines()
    elements = []  # (start_line, end_line, header)
    depth = 0
    start = None
    header = None
    for i, ln in enumerate(lines):
        opens = ln.count("(") - ln.count(")")
        stripped = ln.strip()
        if depth == 1 and ln.startswith("\t(") and not ln.startswith("\t\t"):
            start = i
            header = stripped
        depth += opens
        if start is not None and depth == 1 and i >= start:
            elements.append((start + 1, i + 1, header))  # 1-indexed
            start = None
    return lines, elements

def summarize(path):
    lines, elems = parse_top_elements(path)
    for (s, e, h) in elems:
        block = "\n".join(lines[s - 1:e])
        kind = h.split()[0].lstrip("(")
        if kind == "lib_symbols":
            print(f"{s}-{e}: lib_symbols ({e-s+1} lines)")
            continue
        # first (at x y ...) in block
        at = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)", block)
        pos = f"({at.group(1)},{at.group(2)})" if at else "(?)"
        info = ""
        if kind == "symbol":
            lib = re.search(r'\(lib_id "([^"]+)"', block)
            ref = re.search(r'\(property "Reference" "([^"]+)"', block)
            info = f'{ref.group(1) if ref else "?"} {lib.group(1) if lib else "?"}'
        elif kind in ("label", "global_label", "text"):
            m = re.match(r'\(\w+ "([^"]*)', h)
            info = repr(m.group(1))[:60] if m else ""
        elif kind == "wire":
            pts = re.findall(r"\(xy (-?[\d.]+) (-?[\d.]+)\)", block)
            info = " -> ".join(f"({x},{y})" for x, y in pts)
            pos = ""
        elif kind == "rectangle":
            pts = re.findall(r"\((?:start|end) (-?[\d.]+) (-?[\d.]+)\)", block)
            info = " to ".join(f"({x},{y})" for x, y in pts)
            pos = ""
        print(f"{s}-{e}: {kind} {pos} {info}")

if __name__ == "__main__":
    summarize(sys.argv[1])
