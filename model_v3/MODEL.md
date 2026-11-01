# Faroe Islands main grid without oil: base model

## Question

How much new wind, solar and storage does the Faroese main grid need to run without oil for one year, and how does a cable of a given size (0, 25, 50 or 100 MW) to Iceland change the build-out and the yearly cost?

## Model

Brownfield capacity expansion model (reader ch. 7.1 to 7.2) for the zone Faroe Islands (FO), plus a transport model (reader ch. 6.4) with a second zone Iceland (IS). Iceland is represented only by its hourly day-ahead price. One year, 8,760 hours, one linear program, solved with HiGHS.

**Sets.** $T$ hours; $P$ = {wind, pv, oil, hydro, battery, phs}; $RES$ = {wind, pv}; $DISP$ = {oil, hydro, battery, phs}; $S$ = {battery, phs} $\subset DISP$; $Z$ = {FO, IS}.

**Variables.** $G_{disp,t}$ output (storage: discharge); $D^{stor}_{s,t}$ charge; $L^{stor}_{s,t}$ storage level; $CU_t$ curtailment; $CAP^G_p, CAP^D_s, CAP^L_s$ new capacity; $F_{FO,IS,t}$ export, $F_{IS,FO,t}$ import; $L^{hyd}_t$ hydro reservoir level (new); $SPILL_t$ spilled water (new).

**Parameters.** $d_t$ demand; $ava_{res,t}$ availability; $g^{max}_p, d^{max}_s, l^{max}_s$ existing capacity; $\eta^{in}_s, \eta^{out}_s$ efficiencies; $mc_s$ storage discharge cost; $ann_p$ annuity incl. fixed O&M; $ntc$ cable capacity (set by us); new symbols: $bio_t$ fixed biogas output, $inflow_t$ water into the hydro reservoir, $\pi_t$ Iceland price, $ann_x$ yearly cable cost per MW.

**Objective** (reader 7.1, plus trade and cable):

$$\min C = \sum_{s,t} mc_s \, G_{s,t} + \sum_{p \in \{wind,pv,battery,phs\}} ann_p \, CAP^G_p + \sum_{s} ann^L_s \, CAP^L_s + \sum_t \pi_t \,(F_{IS,FO,t} - F_{FO,IS,t}) + ann_x \cdot ntc$$

with $ann_p = OC_p \cdot \frac{r}{1-(1+r)^{-T_p}} + fom_p$ and $r$ = 5 %.

**Energy balance in FO** (reader 6.4, one zone with exchange; its dual is the Faroese price):

$$\sum_{disp} G_{disp,t} + \sum_{res} ava_{res,t}\,(g^{max}_{res} + CAP^G_{res}) + bio_t - \sum_s D^{stor}_{s,t} - CU_t + F_{IS,FO,t} - F_{FO,IS,t} = d_t \quad \forall t$$

**Capacity limits** (reader 7.2, existing capacity added to the new capacity):

| Constraint | Equation |
|---|---|
| Output | $G_{disp,t} \le g^{max}_{disp} + CAP^G_{disp}$ |
| Charging | $D^{stor}_{s,t} \le d^{max}_s + CAP^D_s$ |
| Storage level | $L^{stor}_{s,t} \le l^{max}_s + CAP^L_s$ |
| Curtailment | $CU_t \le \sum_{res} ava_{res,t}\,(g^{max}_{res} + CAP^G_{res})$ |
| Storage balance (cyclic) | $L^{stor}_{s,t+1} = L^{stor}_{s,t} + \eta^{in}_s D^{stor}_{s,t} - G_{s,t}/\eta^{out}_s$ |
| Hydro reservoir (new, cyclic) | $L^{hyd}_{t+1} = L^{hyd}_t + inflow_t - G_{hydro,t} - SPILL_t$, $\;L^{hyd}_t \le l^{max}_{hydro}$ |
| Without oil | $G_{oil,t} = 0$ |
| No new hydro or oil plants | $CAP^G_{hydro} = CAP^G_{oil} = 0$ |
| Battery: one inverter | $CAP^G_{battery} = CAP^D_{battery}$ |
| Pumped hydro site | $CAP^D_{phs} = 1.75\,CAP^G_{phs}$, $\;CAP^L_{phs} = 20\,CAP^G_{phs}$, $\;CAP^G_{phs} \le 40$ |
| Cable (reader 6.4) | $0 \le F_{FO,IS,t} \le ntc$, $\;0 \le F_{IS,FO,t} \le ntc$, $\;F_{FO,IS,t} + F_{IS,FO,t} \le ntc$ |

All variables are $\ge 0$. "Cyclic" means the level in the last hour connects to the first hour, so no free energy enters the year.

## Data

Model year: 1 October 2025, 00:00 to 30 September 2026, 23:00 (UTC), 8,760 hours. The same year is used for every hourly input.

| Input | Construction | Source | Value in the model year |
|---|---|---|---|
| Demand $d_t$ | Sum of all main-grid production records per hour (no interconnector today, so production = consumption). Suðuroy plants excluded. | SEV hourly production per plant | 487.8 GWh, peak 78.1 MW, min 35.6 MW (today 45 % from oil) |
| Wind $ava_{wind,t}$ | SEV main-grid wind output / 61.55 MW installed in the feed, clipped to [0, 1] | SEV | capacity factor 0.27 (2,364 full-load hours) |
| Solar $ava_{pv,t}$ | Output of the Sumba PV plant / 0.24 MW, clipped to [0, 1] | SEV (plant and plant list) | 185 MWh, 772 full-load hours |
| Hydro inflow $inflow_t$ | SEV hydro production of each month, spread evenly over the hours of that month | SEV | 111.3 GWh |
| Biogas $bio_t$ | Førka output as produced | SEV | 9.9 GWh, max 1.5 MW |
| Iceland price $\pi_t$ | Day-ahead price, hourly | Elma (Icelandic power exchange) | mean 26.5, median 23.7, max 488 EUR/MWh |
| Costs | see assumptions A18 to A23 | DEA technology catalogues; Tróndheim et al. (2021) for solar | |

Time handling: SEV reports Faroese local time and is converted to UTC; the two hours around the autumn clock change (26.10.2025) are filled by linear interpolation. Elma reports UTC; one missing price (10.12.2025, 03:00) is interpolated.

## Assumptions

Type: **F** = fact from a source, **G** = group decision, **A** = own assumption.

| ID | Assumption | Value | Source | Type |
|---|---|---|---|---|
| A01 | Without oil | $G_{oil,t} = 0$ in every hour; demand met in every hour (no load shedding) | group | G |
| A02 | One model year for all hourly inputs | Oct 2025 to Sep 2026, 8,760 h, UTC | group; lecturer feedback 20.10.2026 | G |
| A03 | Only varied input | cable capacity $ntc$ = 0 / 25 / 50 / 100 MW | group | G |
| A04 | Iceland = hourly price only | Elma day-ahead $\pi_t$, same price for import and export; Iceland can always deliver or take up to $ntc$ | group; Elma | G |
| A05 | Imported power counts as renewable | Iceland's power is almost fully hydro and geothermal | group | G |
| A06 | Demand = main-grid production, no growth | 487.8 GWh | SEV | F + A |
| A07 | Main grid only | Suðuroy (Vágur, Botnur, Suðuroy plants) excluded, about 7 % of Faroese demand | group | G |
| A08 | Existing wind | 61.55 MW (Neshagi 4.65, Húsahagi 11.7, Gellingaklettur 25.2, Flatnahagi 18, Vestmanna 2) | SEV plant list, farm data | F |
| A09 | Wind profile | SEV output / installed capacity; SEV output is curtailed, so the profile is conservative | SEV | F + A |
| A10 | Solar profile | Sumba PV output / 0.24 MW; the same profile for all new PV | SEV | A |
| A11 | Sumba capacity | 0.24 MW (earlier notes 0.24 to 0.26 MW; at 0.25 MW the plant would give 741 instead of 772 full-load hours) | SEV plant list | F |
| A12 | Existing PV in the main grid | 0 MW (Sumba is on Suðuroy) | SEV | F |
| A13 | One profile per technology, no site limits for new wind and PV | | stylised | A |
| A14 | Existing hydro | 37.3 MW, one aggregated reservoir, 5.85 GWh usable (50 % of 11.7 GWh) | SEV plant list; Ea Energy Analyses (2018), Table 3 | F |
| A15 | Hydro inflow | monthly SEV hydro production, flat within the month (production, not natural inflow) | SEV | F + A |
| A16 | Cyclic storage and reservoir | level at the end = level at the start | course model | A |
| A17 | Biogas fixed as produced; existing battery 12 MW / 12.5 MWh (Sund) | | SEV | F |
| A18 | Wind cost | 1.036 M EUR/MW, fixed O&M 12,600 EUR/MW/yr, 30 yr | DEA electricity catalogue, sheet 20, 2030 | F |
| A19 | Solar cost (Faroe-specific) | 1.11 M EUR/MW, fixed O&M 7,000 EUR/MW/yr, 30 yr | Tróndheim et al. (2021), Table 5, 2030 | F |
| A20 | Battery cost | 170 k EUR/MW + 151 k EUR/MWh, fixed O&M 574 EUR/MW/yr, 25 yr, round trip 92 % | DEA storage catalogue, sheet 180, 2030 | F |
| A21 | Pumped hydro option | 4.25 M EUR/MW, fixed O&M 8,507 EUR/MW/yr, 50 yr, round trip 75 %; max 40 MW turbine, pump 1.75 × turbine, 20 h storage | DEA storage catalogue, sheet 160; SEV Mýruverkið II project | F |
| A22 | Storage discharge cost | 1 EUR/MWh | course model | F |
| A23 | Cable cost | 450 km × 3,220 EUR/MW/km (fixed O&M 2.5 %/yr) + converter pair 640 EUR/kW (fixed O&M 1.5 %/yr), 40 yr = 167.6 k EUR per MW per year, linear in $ntc$ | DEA transport catalogue (2025), sheets 1.7 / 1.8; distance NAEN (2016) | F |
| A24 | Discount rate | 5 % real | common value | A |
| A25 | Existing plants are sunk | cost = additional yearly cost of the oil-free system | reader 7.2 | A |
| A26 | Cable | no losses, always available, one physical cable (import + export ≤ $ntc$) | group | G + A |
| A27 | Curtailment free; perfect foresight over the year | | course model | F |
| A28 | No grid inside the Faroes, no frequency or inertia | | course model | F |
| A29 | Costs as published | EUR2015 (wind), EUR2020 (storage), no inflation | DEA | A |

## Results

| Cable $ntc$ | Cost (M EUR/yr) | Cost per MWh demand (EUR) | New wind (MW) | New solar PV (MW) | New battery (MW / MWh) | Pumped hydro (MW) | Import (GWh) | Export (GWh) | Curtailment (% of wind + PV) | Mean FO price (EUR/MWh) |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 MW | 30.9 | 63.3 | 98.0 | 110.3 | 28.4 / 1,296 | 0 | 0 | 0 | 18.5 | 150.5 |
| 25 MW | 12.0 | 24.5 | 47.0 | 29.5 | 1.5 / 65 | 0 | 130.4 | 41.7 | 0.0 | 70.6 |
| 50 MW | 12.4 | 25.5 | 0 | 0 | 0 / 3 | 0 | 235.1 | 13.4 | 0.0 | 27.6 |
| 100 MW | 20.8 | 42.6 | 0 | 0 | 0 / 13 | 0 | 237.3 | 15.2 | 0.0 | 26.5 |

Cost = yearly cost of new capacity, storage use, net import and cable, on top of today's system. Import and export are netted per hour. Mean FO price = unweighted mean over the year of the dual of the energy balance.

Cost split (M EUR/yr): 0 MW: wind 7.8, solar 8.7, storage 14.3. 25 MW: wind 3.8, solar 2.3, storage 0.7, net import 0.9, cable 4.2. 50 MW: storage 0.04, net import 4.0, cable 8.4. 100 MW: storage 0.1, net import 3.9, cable 16.8.

![Yearly cost by cable size](figures/fig1_cost_vs_cable.png)

![New capacity by cable size](figures/fig2_capacity_vs_cable.png)

![Dispatch in the calmest summer week](figures/fig3_dispatch_calm_week.png)

Model checks: all four runs solve to optimality; the energy balance closes in every hour (largest error below 10⁻¹³ MW); oil output is 0 in every hour; import never exceeds $ntc$ (largest import 25, 50 and 73 MW); the cost components add up to the objective value.

## Key findings

- **Without a cable, an oil-free main grid costs about 31 M EUR per year (63 EUR per MWh of demand) on top of today's system.** The model builds 98 MW of new wind, 110 MW of solar PV and a 28 MW / 1.3 GWh battery. 18.5 % of the wind and solar output is curtailed, and the Faroese price spikes to very high values in a few scarcity hours.
- **Solar is built, even at the Faroe-specific cost.** Without a cable, PV supplies about 15 % of demand. It fills the calm summer months, when wind and hydro are lowest (Figure 3). With a 25 MW cable, PV falls to 30 MW. With 50 MW or more, no PV is built.
- **A small cable is the cheapest option tested.** With 25 MW the cost falls to 12.0 M EUR per year (−61 %). With 50 MW it is about the same (12.4 M EUR), and with 100 MW it rises again (20.8 M EUR) because the cable cost is linear in MW and imports never go above 73 MW. With 50 MW or more, almost nothing new is built locally (only 3 to 13 MWh of extra battery energy), and imports cover about half of demand.
- **The cable is used for hourly trade, not only for backup.** The existing hydro reservoir and battery shift energy so that the Faroes import in cheap Elma hours (about 20 EUR/MWh on average) and export in expensive hours (about 44 to 49 EUR/MWh).
- **Pumped hydro is never built.** The battery (without a cable) or the cable covers the balancing more cheaply.

## Limitations

- **Iceland price.** Elma is a thin market (median traded volume about 35 MWh per hour in the model year). A 50 to 100 MW cable is as large as the whole traded volume and would move the Icelandic price. The model treats Iceland as a price taker that can always deliver or take up to $ntc$, including in Icelandic dry years. This overstates the value of the cable.
- **Solar profile from one small plant.** One 0.24 MW plant on Suðuroy gives 772 full-load hours. The literature gives 584 to 620 hours for the Faroes, so PV is probably too favourable here. All new PV uses this one profile.
- **Wind profile from curtailed output.** SEV wind output is limited by the grid operator (capacity factor 0.27, while the farms report about 0.40). New wind is therefore probably undervalued.
- **Hydro inflow is SEV production, not natural inflow.** It contains SEV's own seasonal water use. All plants are aggregated into one reservoir.
- **No grid physics.** Frequency, inertia, reserves and voltage are not modelled. Running with exactly zero oil may need extra equipment (e.g. synchronous condensers) that is not costed.
- **One year, today's demand.** There is no demand growth from electrification (SEV expects about 675 GWh in 2030), only one weather year, and perfect foresight.
- **Simple cost structure.** The cable cost is linear per MW, with no fixed part, no losses and no outages. There are no site limits for wind and solar (160 MW of wind and 110 MW of PV in the no-cable case would need land), and cost sources are used in their published price years.
