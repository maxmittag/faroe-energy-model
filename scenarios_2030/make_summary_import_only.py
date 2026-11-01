"""Import-only runs (group decision 28.10.2026: no export from the Faroes).

Merges results_import_only/summary_<tag>_<demand case>.csv into
  results_import_only/summary_2030.csv   (2030 demand, factor 1.186)
  results_import_only/summary_today.csv  (today's demand, same cable lengths 450/400 km)
and adds the export-allowed cost of the same case for comparison:
  2030:  _archive_with_export/summary_2030.csv
  today: _archive_with_export/reference_today.csv (Scotland converted to 400 km, see make_summary.py)

python make_summary_import_only.py
"""
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).parent
RES = HERE / "results_import_only"
ARC = HERE / "_archive_with_export"

ORDER = ["base_no_cable", "is_fixed_25", "is_fixed_50", "is_fixed_100", "is_variable_cap1000",
         "gb_fixed_25", "gb_fixed_50", "gb_fixed_100", "gb_variable_cap500", "gb_variable_cap1000",
         "check_base_gb_input"]
LABEL = {"base_no_cable": "No cable (base)", "is_fixed_25": "Iceland 25 MW", "is_fixed_50": "Iceland 50 MW",
         "is_fixed_100": "Iceland 100 MW", "is_variable_cap1000": "Iceland, size chosen by model",
         "gb_fixed_25": "Scotland 25 MW", "gb_fixed_50": "Scotland 50 MW", "gb_fixed_100": "Scotland 100 MW",
         "gb_variable_cap500": "Scotland, chosen (limit 500 MW)",
         "gb_variable_cap1000": "Scotland, chosen (limit 1,000 MW)",
         "check_base_gb_input": "check: no cable, GB price file"}

old30 = pd.read_csv(ARC / "summary_2030.csv").set_index("case")
oldtd = pd.read_csv(ARC / "reference_today.csv").set_index("case")
COLS = ["case", "status", "ntc_MW", "ntc_hit_cap", "cost_MEUR", "cost_MEUR_with_export", "delta_MEUR",
        "new_wind_MW", "new_pv_MW", "new_bat_MW", "new_bat_MWh", "new_phs_MW", "import_GWh", "export_GWh",
        "import_share_demand", "curtail_share", "cable_util", "demand_GWh"]

for dc, factor in [("2030", 1.186), ("today", 1.0)]:
    parts = [RES / f"summary_{t}_{dc}.csv" for t in ("is", "gb")]
    df = pd.concat([pd.read_csv(p) for p in parts if p.exists()], ignore_index=True)
    df["order"] = df["case"].map({c: k for k, c in enumerate(ORDER)})
    df = df.sort_values("order").drop(columns="order")
    df.insert(1, "label", df["case"].map(LABEL))
    df["demand_factor"] = factor
    if dc == "2030":
        df["cost_MEUR_with_export"] = df.case.map(old30["cost_MEUR"])
        df["ntc_MW_with_export"] = df.case.map(old30["ntc_MW"])
    else:
        ref = oldtd["cost_MEUR_today"].to_dict()
        ref["check_base_gb_input"] = ref["base_no_cable"]
        df["cost_MEUR_with_export"] = df.case.map(ref)
        df["ntc_MW_with_export"] = df.case.map(oldtd["ntc_MW_today"].to_dict() | {"check_base_gb_input": 0.0})
    df["delta_MEUR"] = df.cost_MEUR - df.cost_MEUR_with_export
    df.to_csv(RES / f"summary_{dc}.csv", index=False)
    print(f"\n=== {dc} (import only) ===")
    print(df[[c for c in COLS if c in df.columns]].round(3).to_string())
