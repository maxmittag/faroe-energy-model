"""Merge the Julia outputs into results/summary_2030.csv and write results/reference_today.csv.

reference_today.csv = the group's results at TODAY's demand (given, not re-run). The Scotland values
were computed with a 450 km cable; for a like-for-like comparison with the 400 km Scotland runs they are
also given at 400 km. That conversion is exact: for a fixed cable size the cable annuity is a constant
in the objective (ann_x * ntc), so the dispatch/investment solution is unchanged and only the constant
shifts by (ann_x(450) - ann_x(400)) * ntc. For the model-chosen case the 450 km optimum sits at the 500 MW
limit; a cheaper cable keeps it there, so the same shift applies.
"""
import pathlib

import pandas as pd

HERE = pathlib.Path(__file__).parent
RES = HERE / "results"

ORDER = ["base_no_cable", "is_fixed_25", "is_fixed_50", "is_fixed_100", "is_variable_cap1000",
         "gb_fixed_25", "gb_fixed_50", "gb_fixed_100", "gb_variable_cap500", "gb_variable_cap1000",
         "check_base_gb_input"]
LABEL = {"base_no_cable": "No cable (base)", "is_fixed_25": "Iceland 25 MW", "is_fixed_50": "Iceland 50 MW",
         "is_fixed_100": "Iceland 100 MW", "is_variable_cap1000": "Iceland, size chosen by model",
         "gb_fixed_25": "Scotland 25 MW", "gb_fixed_50": "Scotland 50 MW", "gb_fixed_100": "Scotland 100 MW",
         "gb_variable_cap500": "Scotland, chosen (limit 500 MW)",
         "gb_variable_cap1000": "Scotland, chosen (limit 1,000 MW)",
         "check_base_gb_input": "check: no cable, GB price file"}

df = pd.concat([pd.read_csv(RES / "summary_is.csv"), pd.read_csv(RES / "summary_gb.csv")], ignore_index=True)
df["order"] = df["case"].map({c: k for k, c in enumerate(ORDER)})
df = df.sort_values("order").drop(columns="order")
df.insert(1, "label", df["case"].map(LABEL))
df["demand_factor"] = 1.186
df.to_csv(RES / "summary_2030.csv", index=False)
print(df[["case", "status", "cable_km", "ntc_MW", "ntc_hit_cap", "cost_MEUR", "new_wind_MW", "new_pv_MW",
          "new_bat_MW", "new_bat_MWh", "new_phs_MW", "import_GWh", "export_GWh", "demand_GWh",
          "peak_demand_MW"]].round(2).to_string())

# ---- reference at today's demand (numbers given in the task; Scotland shifted to 400 km, see docstring)
def ann_x(km, r=0.05, n=40):
    af = r * (1 + r) ** n / ((1 + r) ** n - 1)
    oc_c, oc_v = km * 3220.0, 640.0e3
    return (oc_c + oc_v) * af + 0.025 * oc_c + 0.015 * oc_v


shift = ann_x(450) - ann_x(400)          # EUR per MW per year
# unrounded values of the given reference runs (read only): model_v4 (Iceland fixed) and the 28.10. spike
FAROE = HERE.parent
v4 = pd.read_csv(FAROE / "model_v4" / "results" / "summary.csv").set_index("ntc_MW")
el = pd.read_csv(FAROE / "spikes" / "2026-10-28_jens" / "results" / "summary_elma.csv").iloc[0]
gb = pd.read_csv(FAROE / "spikes" / "2026-10-28_jens" / "results" / "summary_gb.csv").set_index("case")
rows = [("base_no_cable", 0.0, v4.loc[0.0, "total_cost_MEUR"])]
rows += [(f"is_fixed_{n}", float(n), v4.loc[float(n), "total_cost_MEUR"]) for n in (25, 50, 100)]
rows += [("is_variable_cap1000", el.ntc_MW, el.cost_MEUR)]
rows += [(f"gb_fixed_{n}", float(n), gb.loc[f"gb_fixed_{n}", "cost_MEUR"]) for n in (25, 50, 100)]
rows += [("gb_variable_cap500", 500.0, gb.loc["gb_endogenous_cap500", "cost_MEUR"])]
ref = pd.DataFrame(rows, columns=["case", "ntc_MW_today", "cost_MEUR_today_as_given_450km"])
ref["cost_MEUR_today"] = [c - (shift * n / 1e6 if k.startswith("gb") else 0.0)
                          for k, n, c in zip(ref.case, ref.ntc_MW_today, ref.cost_MEUR_today_as_given_450km)]
ref["note"] = ["", "", "", "", "",
               *["Scotland: given at 450 km, converted to 400 km (exact for fixed size)"] * 4]
ref["demand_GWh_today"], ref["peak_MW_today"] = 487.8, 78.1
ref.to_csv(RES / "reference_today.csv", index=False)
print(f"\nshift 450->400 km: {shift:.0f} EUR/MW/yr")
print(ref.round(2).to_string())
