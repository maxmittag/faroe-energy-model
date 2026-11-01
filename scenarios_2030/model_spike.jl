# =============================================================================
#  Faroe Islands main grid without oil: brownfield capacity expansion (reader 7.1-7.2)
#  with a cable to Iceland as a transport model (reader 6.4). One year, hourly.
#  Structure and names follow the course file 09_investment.jl.
#  Reader notation: d_t demand, G output, CU curtailment, D_stor charge, L_stor level,
#  CAP_G / CAP_D / CAP_L new capacity, g_max / d_max / l_max existing capacity,
#  ava availability, ann annuity, F_z,zz,t flow between zones, ntc transfer capacity.
#  New symbols (not in the reader): bio_t fixed biogas, inflow_t water into the hydro
#  reservoir, L_hyd hydro reservoir level, SPILL_t spilled water, pi_t Iceland price,
#  ann_x yearly cable cost per MW.
# =============================================================================
using JuMP
using HiGHS
using DataFrames, CSV

data_path = joinpath(@__DIR__, "data")
time_series = CSV.read(joinpath(data_path, get(ENV, "SPIKE_INPUT", "input_hourly.csv")), DataFrame)
tech_data = CSV.read(joinpath(data_path, "technologies.csv"), DataFrame)
tech_data.technology = String.(tech_data.technology)

### data preprocessing ###
T = time_series[:, :hour] |> collect
P = tech_data[:, :technology] |> Vector
DISP = tech_data[tech_data[!, :dispatchable] .== 1, :technology]      # oil, hydro, battery, phs
NONDISP = tech_data[tech_data[!, :dispatchable] .== 0, :technology]   # wind, pv (RES in the reader)
S = ["battery", "phs"]                                                # storage, S ⊂ DISP
INV = tech_data[tech_data[!, :can_invest] .== 1, :technology]         # may be built: wind, pv, battery, phs

### parameters ###
annuity_factor(n, r) = r * (1 + r)^n / (((1 + r)^n) - 1)              # reader 7.1: ann = OC * af

interest_rate = 0.05
ic_generation_cap = Dict{String,Float64}()    # EUR per MW per year (annuity + fixed O&M)
ic_storage_cap = Dict{String,Float64}()       # EUR per MWh per year
g_max = Dict{String,Float64}()                # existing capacity, MW (brownfield, reader 7.2)
d_max = Dict{String,Float64}()                # existing charging power, MW
l_max = Dict{String,Float64}()                # existing storage size, MWh
eff_in = Dict{String,Float64}()
eff_out = Dict{String,Float64}()
vc = Dict{String,Float64}()                   # EUR/MWh

for row in eachrow(tech_data)
    p = row.technology
    if row.can_invest == 1
        af = annuity_factor(row.lifetime, interest_rate)
        ic_generation_cap[p] = row.investment_generation * af + row.fom
        row.investment_storage > 0 && (ic_storage_cap[p] = row.investment_storage * af)
    end
    g_max[p] = row.g_max
    row.d_max >= 0 && (d_max[p] = row.d_max)
    row.l_max >= 0 && (l_max[p] = row.l_max)
    row.storage_efficiency_in > 0 && (eff_in[p] = row.storage_efficiency_in)
    row.storage_efficiency_out > 0 && (eff_out[p] = row.storage_efficiency_out)
    vc[p] = row.vc
end
ic_storage_cap["phs"] = 0.0                   # pumped hydro: whole cost on the turbine MW (DEA sheet 160)

# pumped hydro site Mýruverkið II (SEV): 70 MW pump / 40 MW turbine, 20 h at full turbine power
phs_pump_ratio = 1.75
phs_hours = 20.0
phs_cap_max = 40.0

# cable Faroe Islands - Iceland (DEA transport catalogue 2025, sheets 1.7 / 1.8), cost per MW of ntc
cable_km = parse(Float64, get(ENV, "SPIKE_CABLE_KM", "450.0"))   # scenarios_2030: env override, default 450 km
oc_cable = cable_km * 3220.0                  # EUR/MW, HVDC submarine cable, 3,220 EUR/MW/km
oc_converter = 640.0e3                        # EUR/MW, converter pair
ann_x = (oc_cable + oc_converter) * annuity_factor(40, interest_rate) +
        0.025 * oc_cable + 0.015 * oc_converter   # EUR per MW per year incl. fixed O&M
NO_EXPORT = get(ENV, "SPIKE_NO_EXPORT", "0") == "1"   # scenarios_2030: import only (default off = as before)

demand = time_series[:, :demand] |> Vector                     # d_t, MW
availability = Dict("wind" => time_series[:, :ava_wind], "pv" => time_series[:, :ava_pv])
bio = time_series[:, :biogas] |> Vector                        # bio_t (new), fixed injection
inflow = time_series[:, :hydro_inflow] |> Vector               # inflow_t (new), MWh per hour
pi_IS = time_series[:, :pi] |> Vector                          # pi_t (new), Elma price, EUR/MWh

successor(arr, x) = (x == length(arr)) ? 1 : x + 1             # cyclic year: last hour -> first hour
dispatch_scale = 8760 / length(T)

### model ###
function solve_model(ntc; endo = false, cap = 1000.0)
    m = Model(HiGHS.Optimizer)
    set_silent(m)
    set_attribute(m, "solver", "ipm")

    @variables m begin
        # dispatch variables
        G[DISP, T] >= 0        # output of oil, hydro, and storage discharge
        CU[T] >= 0             # curtailment
        D_stor[S, T] >= 0      # storage charge
        L_stor[S, T] >= 0      # storage level
        # investment variables (new capacity on top of g_max)
        CAP_G[P] >= 0
        CAP_D[S] >= 0
        CAP_L[S] >= 0
        # hydro reservoir (new)
        L_hyd[T] >= 0
        SPILL[T] >= 0
        # cable flows (reader 6.4)
        F_FO_IS[T] >= 0        # export Faroe Islands -> Iceland
        F_IS_FO[T] >= 0        # import Iceland -> Faroe Islands
    end

    # SPIKE: cable size as investment variable (like CAP_G), ntc becomes NTC
    if endo
        @variable(m, 0 <= NTC <= cap)
        ntc = NTC
    end

    # min C = C_gen + C_inv (reader 7.1) + trade with Iceland at pi_t + yearly cable cost
    @objective(m, Min,
        sum(vc[disp] * G[disp, t] for disp in DISP, t in T) * dispatch_scale
        + sum(ic_generation_cap[p] * CAP_G[p] for p in INV)
        + sum(ic_storage_cap[s] * CAP_L[s] for s in S)
        + sum(pi_IS[t] * (F_IS_FO[t] - F_FO_IS[t]) for t in T) * dispatch_scale
        + ann_x * ntc
    )

    # G_res,t = ava_res,t * (g_max_res + CAP_G_res) (reader 7.2), before curtailment
    @expression(m, feed_in[ndisp = NONDISP, t = T],
        availability[ndisp][t] * (g_max[ndisp] + CAP_G[ndisp])
    )

    # energy balance per zone (reader 6.4): generation - charging - curtailment + import - export = d_t
    @constraint(m, ElectricityBalance[t = T],
        sum(G[disp, t] for disp in DISP)
        + sum(feed_in[ndisp, t] for ndisp in NONDISP)
        + bio[t]
        - sum(D_stor[s, t] for s in S)
        - CU[t]
        + F_IS_FO[t] - F_FO_IS[t]
        ==
        demand[t]
    )

    # G_disp,t <= g_max_disp + CAP_G_disp and G_s,t <= g_max_s + CAP_G_s (reader 7.2)
    @constraint(m, MaxGeneration[disp = DISP, t = T],
        G[disp, t] <= g_max[disp] + CAP_G[disp]
    )

    # curtailment only of available wind and solar (reader: G_res,t <= ava_res,t * g_max_res)
    @constraint(m, MaxCurtailment[t = T],
        CU[t] <= sum(feed_in[ndisp, t] for ndisp in NONDISP)
    )

    # D_stor_s,t <= d_max_s + CAP_D_s (reader 7.2)
    @constraint(m, MaxCharge[s = S, t = T],
        D_stor[s, t] <= d_max[s] + CAP_D[s]
    )

    # battery: one inverter for charging and discharging (as in the course file)
    @constraint(m, SymmetricChargingPower,
        CAP_G["battery"] == CAP_D["battery"]
    )

    # pumped hydro site: pump size, storage hours and maximum size are fixed by the site (new)
    @constraint(m, PhsPump, CAP_D["phs"] == phs_pump_ratio * CAP_G["phs"])
    @constraint(m, PhsEnergy, CAP_L["phs"] == phs_hours * CAP_G["phs"])
    @constraint(m, PhsSite, CAP_G["phs"] <= phs_cap_max)

    # L_stor_s,t <= l_max_s + CAP_L_s (reader 7.2)
    @constraint(m, MaxLevel[s = S, t = T],
        L_stor[s, t] <= l_max[s] + CAP_L[s]
    )

    # storage balance (reader 5 / 7.1): L_t+1 = L_t + eta_in * D_t - G_t / eta_out, cyclic over the year
    @constraint(m, StorageLevel[s = S, t = T],
        L_stor[s, successor(T, t)]
        ==
        L_stor[s, t]
        + eff_in[s] * D_stor[s, t]
        - (1 / eff_out[s]) * G[s, t]
    )

    # existing hydro: one reservoir with inflow and spill, cyclic over the year (new)
    @constraint(m, HydroLevel[t = T],
        L_hyd[successor(T, t)] == L_hyd[t] + inflow[t] - G["hydro", t] - SPILL[t]
    )
    @constraint(m, MaxHydroLevel[t = T], L_hyd[t] <= l_max["hydro"])

    # brownfield: no new hydro or oil plants
    @constraint(m, NoNewCapacity[p = setdiff(P, INV)], CAP_G[p] == 0)

    # without oil: G_oil,t = 0 in every hour
    @constraint(m, NoOil[t = T], G["oil", t] == 0)

    # cable (reader 6.4): 0 <= F_z,zz,t <= ntc; one physical cable, so import + export <= ntc
    @constraint(m, MaxExport[t = T], F_FO_IS[t] <= ntc)
    @constraint(m, MaxImport[t = T], F_IS_FO[t] <= ntc)
    @constraint(m, OneCable[t = T], F_FO_IS[t] + F_IS_FO[t] <= ntc)

    # group decision 28.10.2026: import only, no export from the Faroes (env SPIKE_NO_EXPORT=1)
    if NO_EXPORT
        @constraint(m, NoExport[t = T], F_FO_IS[t] == 0)
    end

    optimize!(m)
    return m
end
