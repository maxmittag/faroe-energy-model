# Check only (CHECKS_import_only.md): import only, Scotland model-chosen size. With limit 500 MW the optimum is
# interior (31 MW at 2030 demand, 22 MW today), so the 1,000 MW limit must give the same solution.
# SPIKE_NO_EXPORT=1 SPIKE_INPUT=<gb input> SPIKE_CABLE_KM=400 julia check_gb_cap1000.jl
include("model_spike.jl")
NO_EXPORT || error("needs SPIKE_NO_EXPORT=1")
for cap in (500.0, 1000.0)
    t0 = time()
    m = solve_model(0.0; endo = true, cap = cap)
    println(get(ENV, "SPIKE_INPUT", ""), " cap ", cap, ": ", termination_status(m), " cost ",
        round(objective_value(m) / 1e6, digits = 4), " MEUR, ntc ", round(value(m[:NTC]), digits = 2), " MW, wind +",
        round(value(m[:CAP_G]["wind"]), digits = 2), ", bat ", round(value(m[:CAP_L]["battery"]), digits = 1),
        " MWh, export max ", maximum(value(m[:F_FO_IS][t]) for t in T), ", ", round(time() - t0), " s")
    flush(stdout)
end
