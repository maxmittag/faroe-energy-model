# CHECKS: scenarios 2030 (28.10.2026)

Runs: `run_2030.jl` (two Julia processes, one per counterpart), merged by `make_summary.py` into
`results/summary_2030.csv`. Logs: `results/log_is.txt`, `results/log_gb.txt`, `results/log_check_*.txt`.

## Inputs

| Check | Expected | Result | OK |
|---|---|---|---|
| Demand factor | 600/506, fixed at 1.186 | `scale_demand.py`: sum ratio 1.18600000 (both files) | yes |
| Only demand changed | all other columns identical | pandas: wind/PV availability, hydro inflow, biogas, price columns identical | yes |
| Demand 2030 | 1.186 x 487.8 = 578.5 GWh | 578.47 GWh, peak 92.6 MW (today 78.1 MW) | yes |
| Cable length Iceland | 450 km (model default) | 450 km, ann_x 167,568 EUR/MW/yr | yes |
| Cable length Scotland | sourced number | 400 km, NAEN (2016) *North Atlantic Energy Network*, p. 9 table "Faroese - Scotland 400 km" (same table: Iceland - Faroes 450 km); also p. 45 Table 1. PDF in `sources/`. ann_x 154,160 EUR/MW/yr | yes |
| Model copy faithful | today's demand, Iceland 25 MW, 450 km = 3.78 (given) | `check_today_25.jl`: 3.782 M EUR, wind +14.1 MW (given 3.78, +14.1) | yes |

## Every run (`summary_2030.csv`, columns `check_*`)

| Check | Result | OK |
|---|---|---|
| Status | all 11 runs OPTIMAL, primal FEASIBLE_POINT | yes |
| Oil = 0 every hour | `check_oil_max_MW` = 0.0 in all runs | yes |
| Energy balance | max hourly error <= 6.4e-13 MW | yes |
| Cost components add up to objective | max error 8e-7 EUR | yes |
| Flows within cable size | `check_flow_max_MW` = ntc in every run | yes |
| No-cable case independent of price file | base with Elma file = base with GB file = 24.77 M EUR, identical build | yes |
| Simultaneous import + export | at most 0.5 GWh (1,000 MW run), netted out in import/export columns, no cost effect | yes |

## Plausibility

| Check | Expected | Result | OK |
|---|---|---|---|
| No cable dearer than today | > 16.9 | 24.8 M EUR (+7.9) | yes |
| Iceland 25 MW dearer than today | > 3.8 | 8.9 M EUR (+5.1) | yes |
| All cases dearer (or less income) than today | yes | yes, every case, see `reference_today.csv` | yes |
| Scotland chosen size, limit 500 MW | may hit the limit | hits 500 MW, -215.4 M EUR | as expected |
| Scotland chosen size, limit 1,000 MW | moves with the limit | hits 1,000 MW, -439.3 M EUR, export 7,126 GWh = 12.3 x own demand | as expected |

## Surprises investigated

1. **Iceland: 50 MW is cheaper than 25 MW at 2030 demand (7.5 vs 8.9 M EUR); at today's demand it was the other way round (5.8 vs 3.8).**
   Cause: with 92.6 MW peak a 25 MW cable is used 90 % of the year (cable_util 0.90) and the model
   adds a long-duration battery (20 MW / 360 MWh, storage cost 3.9 M EUR/yr) to bridge calm spells. With
   50 MW no new battery is needed. The model-chosen size moves from 24.7 MW (today) to 34.3 MW (2030),
   consistent with this. Not an error.
2. **Model-chosen Iceland cable (34 MW, 6.6 M EUR) is cheaper than every fixed size**, as it must be
   (LP optimum over a superset). Yes: 6.6 < 7.5 < 8.9 < 12.5.
3. **Scotland runs curtail 22-29 % of wind** although export is unlimited at the GB price: in hours when
   the cable is full (or the GB price is <= 0) extra wind has nowhere to go. Plausible.
4. **Scotland 25 MW: cost -0.8 M EUR** (net income), today -5.1 M EUR at the same 400 km. Higher demand
   leaves less wind for export. Plausible.
5. **Battery in Scotland runs is large** (e.g. 76 MW / 447 MWh at 100 MW cable): arbitrage against the
   hourly GB price, not only security of supply. Plausible for a price-taker model.

## Today vs 2030 comparison (`results/reference_today.csv`)

Today's numbers are the given reference runs (not re-run), read unrounded from `model_v4/results/summary.csv`
and `spikes/2026-10-28_jens/results/summary_*.csv`. The Scotland reference runs used a 450 km cable;
to compare like with like they are converted to 400 km: for a fixed cable size the cable annuity is a
constant term `ann_x * ntc`, so the solution does not change and the cost shifts by
(167,568 - 154,160) x ntc = 13,408 EUR per MW per year. Verified with a re-solve of Scotland 25 MW at
today's demand and 400 km: -5.096 M EUR vs converted -5.096 (given -4.76 at 450 km). For the 500 MW
model-chosen case the optimum is at the limit for 450 km already; a cheaper cable keeps it there, so the
same shift applies (-212.5 -> -219.2).

## Not done / open

- Suðuroy (about 7 % of demand) not in the model, as agreed.
- No re-run of today's cases except the two single checks above.
