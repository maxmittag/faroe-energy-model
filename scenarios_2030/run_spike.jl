# Spike 28.10.2026 (after talk with Jens): endogenous cable size, Scotland/GB price instead of Elma.
# Only the price series or the cable treatment changes; everything else = model_v4.
include("model_spike.jl")
cases = get(ENV, "SPIKE_CASES", "")
rows = DataFrame()
function report(label, m)
    st = termination_status(m)
    if st != MOI.OPTIMAL
        println("$label: $st"); flush(stdout)
        return DataFrame(case = label, status = string(st))
    end
    CAP_G, CAP_L, F_IS_FO, F_FO_IS, CU, feed_in = m[:CAP_G], m[:CAP_L], m[:F_IS_FO], m[:F_FO_IS], m[:CU], m[:feed_in]
    imp = [value(F_IS_FO[t]) for t in T]; ex = [value(F_FO_IS[t]) for t in T]
    ov = min.(imp, ex); imp .-= ov; ex .-= ov
    ntc_val = haskey(object_dictionary(m), :NTC) ? value(m[:NTC]) : NaN
    avail = sum(value(feed_in[n, t]) for n in NONDISP, t in T)
    d = DataFrame(case = label, status = "OPTIMAL", cost_MEUR = objective_value(m) / 1e6,
        ntc_MW = ntc_val, new_wind_MW = value(CAP_G["wind"]), new_pv_MW = value(CAP_G["pv"]),
        new_bat_MW = value(CAP_G["battery"]), new_bat_MWh = value(CAP_L["battery"]), new_phs_MW = value(CAP_G["phs"]),
        import_GWh = sum(imp) / 1e3, export_GWh = sum(ex) / 1e3, demand_GWh = sum(demand) / 1e3,
        import_share_demand = sum(imp) / sum(demand), curtail_share = sum(value(CU[t]) for t in T) / avail,
        import_hours = count(>(0.01), imp), export_hours = count(>(0.01), ex), pi_mean = sum(pi_IS) / length(T))
    println(label, ": ", round(objective_value(m) / 1e6, digits = 2), " MEUR, ntc ", round(ntc_val, digits = 1),
        ", wind +", round(value(CAP_G["wind"]), digits = 1), ", import ", round(sum(imp) / 1e3, digits = 1),
        " GWh, export ", round(sum(ex) / 1e3, digits = 1), " GWh"); flush(stdout)
    return d
end
tag = get(ENV, "SPIKE_TAG", "elma")
if tag == "elma"
    t0 = time(); m = solve_model(0.0; endo = true, cap = 1000.0)
    global rows = vcat(rows, report("elma_endogenous", m), cols = :union); println("  ", round(time() - t0), " s")
else
    for ntc in [25.0, 50.0, 100.0]
        t0 = time(); m = solve_model(ntc)
        global rows = vcat(rows, report("gb_fixed_$(Int(ntc))", m), cols = :union); println("  ", round(time() - t0), " s")
    end
    t0 = time(); m = solve_model(0.0; endo = true, cap = 500.0)
    global rows = vcat(rows, report("gb_endogenous_cap500", m), cols = :union); println("  ", round(time() - t0), " s")
end
CSV.write(joinpath(@__DIR__, "results", "summary_$(tag).csv"), rows)
