"""Group assumption (Notion, 28.10.): 2030 demand = 600/506 x today's hourly profile, factor fixed at 1.186.
Multiplies ONLY the 'demand' column of both input files; every other column is copied byte for byte.

python scale_demand.py  ->  data/input_hourly_2030.csv, data/input_hourly_gb_2030.csv
"""
import pathlib

FACTOR = 1.186
DATA = pathlib.Path(__file__).parent / "data"

for src, dst in [("input_hourly.csv", "input_hourly_2030.csv"), ("input_hourly_gb.csv", "input_hourly_gb_2030.csv")]:
    lines = (DATA / src).read_text().splitlines()
    head = lines[0].split(",")
    k = head.index("demand")
    out = [lines[0]]
    for ln in lines[1:]:
        if not ln.strip():
            continue
        cells = ln.split(",")
        cells[k] = f"{float(cells[k]) * FACTOR:.6f}"
        out.append(",".join(cells))
    (DATA / dst).write_text("\n".join(out) + "\n")
    print(dst, len(out) - 1, "hours")
