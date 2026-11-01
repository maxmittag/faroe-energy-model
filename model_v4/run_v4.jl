# =============================================================================
#  Runs the model for the four cable sizes (the only varied input) and writes
#  results/summary.csv and results/hourly_ntc<size>.csv.   Run: julia run_v3.jl
# =============================================================================
include("model_v4.jl")

OUT = joinpath(@__DIR__, "results")
mkpath(OUT)

summary = DataFrame()
for ntc in [0.0, 25.0, 50.0, 100.0]
    t0 = time()
    m = solve_model(ntc)
    st = termination_status(m)
    dt = round(time() - t0, digits = 1)
    println("ntc = $(Int(ntc)) MW: $(st), $(dt) s")
    flush(stdout)
    if st != MOI.OPTIMAL
        global summary = vcat(summary, DataFrame(ntc_MW = ntc, status = string(st)), cols = :union)
        continue
    end

    G, CU, D_stor, L_stor = m[:G], m[:CU], m[:D_stor], m[:L_stor]
    CAP_G, CAP_L, L_hyd, SPILL = m[:CAP_G], m[:CAP_L], m[:L_hyd], m[:SPILL]
    F_IS_FO, F_FO_IS, feed_in = m[:F_IS_FO], m[:F_FO_IS], m[:feed_in]
    bal = m[:ElectricityBalance]

    # import and export carry the same price pi_t, so simultaneous flows in one hour are cost-neutral and
    # the LP optimum is degenerate. Netting per hour gives an equivalent optimal solution (same balance,
    # same cost, import + export <= ntc still holds); the raw overlap is kept as a check column.
    imp_raw = [value(F_IS_FO[t]) for t in T]
    exp_raw = [value(F_FO_IS[t]) for t in T]
    overlap = min.(imp_raw, exp_raw)
    imp_net = imp_raw .- overlap
    exp_net = exp_raw .- overlap

    hourly = DataFrame(
        hour = T, time_utc = time_series.time_utc, demand = demand, biogas = bio,
        wind_avail = [value(feed_in["wind", t]) for t in T],
        pv_avail = [value(feed_in["pv", t]) for t in T],
        curtailment = [value(CU[t]) for t in T],
        hydro = [value(G["hydro", t]) for t in T],
        hydro_level = [value(L_hyd[t]) for t in T],
        spill = [value(SPILL[t]) for t in T],
        oil = [value(G["oil", t]) for t in T],
        bat_dis = [value(G["battery", t]) for t in T],
        bat_ch = [value(D_stor["battery", t]) for t in T],
        bat_level = [value(L_stor["battery", t]) for t in T],
        phs_dis = [value(G["phs", t]) for t in T],
        phs_ch = [value(D_stor["phs", t]) for t in T],
        phs_level = [value(L_stor["phs", t]) for t in T],
        imp = imp_net,
        exp = exp_net,
        pi = pi_IS,
        price_FO = [dual(bal[t]) for t in T],      # zonal price = dual of the energy balance (reader 6.4)
    )
    CSV.write(joinpath(OUT, "hourly_ntc$(Int(ntc)).csv"), hourly)

    # checks
    supply = hourly.hydro .+ hourly.oil .+ hourly.bat_dis .+ hourly.phs_dis .+ hourly.wind_avail .+
             hourly.pv_avail .+ hourly.biogas .- hourly.curtailment .+ hourly.imp
    use = hourly.demand .+ hourly.bat_ch .+ hourly.phs_ch .+ hourly.exp
    dem = sum(hourly.demand)
    total = objective_value(m)
    cap = Dict(p => value(CAP_G[p]) for p in P)
    res_avail = sum(hourly.wind_avail .+ hourly.pv_avail)
    c_wind = ic_generation_cap["wind"] * cap["wind"]
    c_pv = ic_generation_cap["pv"] * cap["pv"]
    c_stor = sum(ic_generation_cap[s] * cap[s] + ic_storage_cap[s] * value(CAP_L[s]) for s in S)
    c_vc = sum(vc[p] * sum(value(G[p, t]) for t in T) for p in DISP)
    c_trade = sum(hourly.pi .* (hourly.imp .- hourly.exp))
    row = DataFrame(
        ntc_MW = ntc, status = string(st),
        total_cost_MEUR = total / 1e6, cost_per_MWh_demand = total / dem,
        new_wind_MW = cap["wind"], new_pv_MW = cap["pv"],
        new_bat_MW = cap["battery"], new_bat_MWh = value(CAP_L["battery"]),
        new_phs_MW = cap["phs"], new_phs_MWh = value(CAP_L["phs"]),
        import_GWh = sum(hourly.imp) / 1e3, export_GWh = sum(hourly.exp) / 1e3,
        curtail_share = sum(hourly.curtailment) / res_avail,
        price_FO_mean = sum(hourly.price_FO) / length(T),
        price_FO_demand_weighted = sum(hourly.price_FO .* hourly.demand) / dem,
        c_wind_MEUR = c_wind / 1e6, c_pv_MEUR = c_pv / 1e6, c_storage_MEUR = c_stor / 1e6,
        c_storage_vc_MEUR = c_vc / 1e6, c_trade_MEUR = c_trade / 1e6, c_cable_MEUR = ann_x * ntc / 1e6,
        wind_total_MW = g_max["wind"] + cap["wind"],
        wind_avail_GWh = sum(hourly.wind_avail) / 1e3, pv_avail_GWh = sum(hourly.pv_avail) / 1e3,
        curtail_GWh = sum(hourly.curtailment) / 1e3, hydro_GWh = sum(hourly.hydro) / 1e3,
        spill_GWh = sum(hourly.spill) / 1e3, demand_GWh = dem / 1e3,
        cable_util = ntc > 0 ? (sum(hourly.imp) + sum(hourly.exp)) / (ntc * length(T)) : 0.0,
        price_FO_max = maximum(hourly.price_FO), price_FO_min = minimum(hourly.price_FO),
        check_balance_err_max = maximum(abs.(supply .- use)),
        check_oil_max_MW = maximum(abs.(hourly.oil)),
        check_import_max_MW = maximum(hourly.imp), check_flow_max_MW = maximum(hourly.imp .+ hourly.exp),
        check_cost_sum_err = (c_wind + c_pv + c_stor + c_vc + c_trade + ann_x * ntc - total),
        check_raw_simultaneous_GWh = sum(overlap) / 1e3,
        check_raw_simultaneous_hours = count(overlap .> 1e-6),
        check_raw_import_GWh = sum(imp_raw) / 1e3, check_raw_export_GWh = sum(exp_raw) / 1e3,
        check_raw_flow_max_MW = maximum(imp_raw .+ exp_raw),
        ann_wind = ic_generation_cap["wind"], ann_pv = ic_generation_cap["pv"], ann_x = ann_x,
        solve_s = dt,
    )
    global summary = vcat(summary, row, cols = :union)
    CSV.write(joinpath(OUT, "summary.csv"), summary)
    println("   cost $(round(total / 1e6, digits = 2)) M EUR/yr, wind +$(round(cap["wind"], digits = 1)) MW, ",
        "pv $(round(cap["pv"], digits = 1)) MW, battery $(round(cap["battery"], digits = 1)) MW / ",
        "$(round(value(CAP_L["battery"]), digits = 0)) MWh, phs $(round(cap["phs"], digits = 1)) MW, ",
        "import $(round(sum(hourly.imp) / 1e3, digits = 1)) GWh, export $(round(sum(hourly.exp) / 1e3, digits = 1)) GWh, ",
        "balance err $(maximum(abs.(supply .- use)))")
    flush(stdout)
end
CSV.write(joinpath(OUT, "summary.csv"), summary)
println("done")
