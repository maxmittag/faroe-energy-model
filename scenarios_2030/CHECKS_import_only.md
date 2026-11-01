# CHECKS: scenarios 2030, IMPORT ONLY (28.10.2026)

Group decision: no export from the Faroes, the cable only imports. All cases of `CHECKS.md` re-run at 2030
demand and again at today's demand. The earlier runs with export allowed are kept in `_archive_with_export/`
(results CSVs, deck, PDF, deck scripts).

## What changed

- `model_spike.jl`: flag `NO_EXPORT` (env `SPIKE_NO_EXPORT=1`, default off = old behaviour) adds
  `NoExport[t]: F_FO_IS[t] == 0`. Nothing else in the model changed.
- `run_import_only.jl`: same cases as `run_2030.jl`, refuses to run without the flag; writes
  `results_import_only/summary_<is|gb>_<2030|today>.csv` (logs `log_<tag>_<demand>.txt`).
- `make_summary_import_only.py` -> `results_import_only/summary_2030.csv`, `summary_today.csv`, each with
  `cost_MEUR_with_export` (2030: old `summary_2030.csv`; today: old `reference_today.csv`, Scotland at 400 km).
- Today's demand runs use the unscaled input files (`input_hourly.csv`, `input_hourly_gb.csv`) with the same
  cable lengths as 2030 (Iceland 450 km, Scotland 400 km).

## Every run (20 runs, columns `check_*`)

| Check | Result | OK |
|---|---|---|
| Status | all OPTIMAL, primal FEASIBLE_POINT | yes |
| Export = 0 every hour | `check_export_max_MW` = 0.0 in all runs | yes |
| Oil = 0 every hour | `check_oil_max_MW` = 0.0 | yes |
| Energy balance | max hourly error 2.4e-13 MW | yes |
| Cost components add up | max error 2e-7 EUR | yes |
| Import <= cable size | yes in every run | yes |
| No-cable case unchanged | 24.77 (2030) and 16.87 (today) M EUR, = earlier runs and both price files | yes |
| Default without the flag unchanged | `check_today_25.jl` without `SPIKE_NO_EXPORT`: 3.782 M EUR, wind +14.1 (= given reference) | yes |

## Plausibility

| Check | Expected | Result | OK |
|---|---|---|---|
| Import only never cheaper than with export (same case) | >= 0 | Iceland +2.4 to +7.5, Scotland +15.5 to +230.6 M EUR | yes |
| Model-chosen <= every fixed size | yes | 2030: Iceland 9.3 < 11.1; Scotland 15.1 < 15.6. Today: 6.2 < 6.3; 10.1 < 10.4 | yes |
| Scotland chosen size moves with the limit? | no longer, optimum is interior | 31.2 MW at limit 500 and at limit 1,000, identical cost (`check_gb_cap1000.jl`) | yes |
| 2030 dearer than today, every case | yes | yes (+1.2 to +7.9 M EUR) | yes |
| Iceland 25 MW today, with export 3.78 | import only higher | 6.25 | yes |

## Surprises investigated

1. **Iceland 50 and 100 MW at 2030 demand build no new wind**, although wind costs about 80 k EUR per MW and
   year and the mean Elma price is 23 EUR/MWh. `check_is50_wind.jl`: 1 MW of extra wind is worth only 59.6 k
   EUR per year (dual values x wind profile), reduced cost +20.4 k EUR. Reason: imports happen in calm hours
   (mean wind availability 0.34), in windy hours (0.91) the existing 61.6 MW already covers demand and extra
   wind would be curtailed. Forcing +10 MW wind raises cost by 0.38 M EUR and curtailment from 4.7 to 26.6 GWh.
   Not an error.
2. **100 MW imports the same as 50 MW** (Iceland 117.6 GWh): with import only, the cable is only needed up to
   the gap between demand and own supply; the extra 50 MW is pure cable cost (+8.3 M EUR). Plausible.
3. **Scotland curtails 14-22 % of wind while importing** (`check_gb_negprice.jl`): all 180 hours with import and
   curtailment at the same time have a GB price <= 0 (181 such hours in the year): the model is paid to
   import. In hours with a positive price, import and curtailment never coincide. Volume small (0.07 M EUR at
   the chosen size). At 100 MW the model imports more than demand in 413 hours, all at negative prices.
   Price-taker artefact, small.
4. **Scotland still builds 20-39 MW new wind** (Iceland from 50 MW: none): GB power costs about 100 EUR/MWh
   per MWh imported vs about 22 from Iceland, so own wind pays off. Plausible.
5. **Today's demand: 100 MW cable dearer than no cable** (Iceland 18.2, Scotland 21.2 vs 16.9). Without export
   income a big cable is mostly unused (6.8 % average use). Plausible.

## Per case (import only; cable use = import GWh / (ntc x 8760))

| Demand | Case | Cable MW | Cost M EUR | With export | Change | New wind MW | New solar MW | Battery MW / MWh | Import GWh | Import % demand | Curtailed % | Cable use % | Export max MW | Demand GWh |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2030 | No cable (base) | 0.0 | 24.77 | 24.77 | +0.00 | 89.6 | 72.3 | 46.0 / 1052 | 0.0 | 0.0 | 44.3 | 0.0 | 0.0 | 578.5 |
| 2030 | Iceland 25 MW | 25.0 | 12.38 | 8.86 | +3.52 | 29.1 | 7.5 | 15.3 / 362 | 44.6 | 7.7 | 15.3 | 20.4 | 0.0 | 578.5 |
| 2030 | Iceland 50 MW | 50.0 | 11.06 | 7.55 | +3.51 | 0.0 | 0.0 | 0.0 / 0 | 117.6 | 20.3 | 1.4 | 26.8 | 0.0 | 578.5 |
| 2030 | Iceland 100 MW | 100.0 | 19.39 | 12.53 | +6.86 | 0.0 | 0.0 | 0.0 / 0 | 117.6 | 20.3 | 1.4 | 13.4 | 0.0 | 578.5 |
| 2030 | Iceland, size chosen by model | 35.0 | 9.33 | 6.57 | +2.75 | 0.3 | 0.0 | 5.5 / 76 | 113.0 | 19.5 | 0.2 | 36.9 | 0.0 | 578.5 |
| 2030 | Scotland 25 MW | 25.0 | 15.56 | -0.80 | +16.36 | 39.4 | 0.0 | 20.5 / 358 | 44.0 | 7.6 | 22.2 | 20.1 | 0.0 | 578.5 |
| 2030 | Scotland 50 MW | 50.0 | 17.29 | -12.98 | +30.27 | 22.7 | 0.0 | 4.6 / 70 | 75.9 | 13.1 | 15.4 | 17.3 | 0.0 | 578.5 |
| 2030 | Scotland 100 MW | 100.0 | 24.66 | -35.81 | +60.48 | 19.9 | 0.0 | 12.1 / 103 | 80.3 | 13.9 | 13.7 | 9.2 | 0.0 | 578.5 |
| 2030 | Scotland, chosen (limit 500 MW) | 31.2 | 15.15 | -215.42 | +230.56 | 30.7 | 0.0 | 11.4 / 154 | 60.6 | 10.5 | 19.0 | 22.2 | 0.0 | 578.5 |
| today | No cable (base) | 0.0 | 16.87 | 16.87 | +0.00 | 51.7 | 64.9 | 26.4 / 677 | 0.0 | 0.0 | 45.5 | 0.0 | 0.0 | 487.8 |
| today | Iceland 25 MW | 25.0 | 6.25 | 3.78 | +2.47 | 1.1 | 0.0 | 1.2 / 42 | 54.2 | 11.1 | 8.0 | 24.7 | 0.0 | 487.8 |
| today | Iceland 50 MW | 50.0 | 9.85 | 5.77 | +4.08 | 0.0 | 0.0 | 0.0 / 0 | 59.2 | 12.1 | 7.8 | 13.5 | 0.0 | 487.8 |
| today | Iceland 100 MW | 100.0 | 18.23 | 10.77 | +7.46 | 0.0 | 0.0 | 0.0 / 0 | 59.2 | 12.1 | 7.8 | 6.8 | 0.0 | 487.8 |
| today | Iceland, size chosen by model | 25.2 | 6.21 | 3.78 | +2.43 | 0.0 | 0.0 | 0.9 / 40 | 55.2 | 11.3 | 6.6 | 25.0 | 0.0 | 487.8 |
| today | Scotland 25 MW | 25.0 | 10.36 | -5.10 | +15.46 | 12.2 | 0.0 | 1.1 / 45 | 49.6 | 10.2 | 17.6 | 22.6 | 0.0 | 487.8 |
| today | Scotland 50 MW | 50.0 | 13.56 | -16.89 | +30.45 | 4.5 | 0.0 | -0.0 / 41 | 59.3 | 12.1 | 12.3 | 13.5 | 0.0 | 487.8 |
| today | Scotland 100 MW | 100.0 | 21.16 | -39.65 | +60.81 | 4.4 | 0.0 | 2.0 / 55 | 60.4 | 12.4 | 12.5 | 6.9 | 0.0 | 487.8 |
| today | Scotland, chosen (limit 500 MW) | 21.6 | 10.14 | -219.17 | +229.30 | 18.6 | 0.0 | 4.5 / 79 | 42.6 | 8.7 | 21.8 | 22.5 | 0.0 | 487.8 |

## Group deck (rebuilt 28.10., `deck_build/`, render `_render/r8/`)

- 10 slides: title, setup (incl. "Cable: import only, no export from the Faroes (group decision 28.10.)"), cases,
  results table (cable, cost, new wind/solar/battery, import GWh, import % of demand, curtailment %), cost-vs-cable
  chart, capacity chart, Iceland fixed vs chosen, Scotland fixed vs chosen, 2030 vs today (both import only), limits
  (7 cards incl. "No export: surplus wind is curtailed").
- A slide comparing with the export-allowed runs was built in between and then left out: the group excluded
  export, so the earlier numbers should not appear in the group deck. The comparison is in the table above.
- Text checks on the final pptx/pdf: no run < 12 pt, no meta words, titles <= 54 characters, "export" only in
  intended places (setup bullet, table footnote "No export in any run", "Without export income", limit card "No export").
- Every slide looked at after render (r5-r8); fixed: table header wrap, legend over a label / cut legend.

## Not done / open

- Suðuroy not in the model, as agreed.
- Notes/Max version of the deck not rebuilt (only the group deck was asked for).

