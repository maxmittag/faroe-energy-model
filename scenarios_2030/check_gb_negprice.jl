# Check only (CHECKS_import_only.md): Scotland runs curtail more than Iceland runs and import at lower
# average prices when the cable is bigger. Hypothesis: in the 181 hours with GB price < 0 the model is paid
# to import, so it imports at full cable size and curtails its own wind instead.
# SPIKE_NO_EXPORT=1 SPIKE_INPUT=input_hourly_gb_2030.csv SPIKE_CABLE_KM=400 julia check_gb_negprice.jl
include("model_spike.jl")
NO_EXPORT || error("needs SPIKE_NO_EXPORT=1")
neg = pi_IS .< 0
println("hours with GB price < 0: ", count(neg), ", mean price in them ", round(sum(pi_IS[neg]) / count(neg), digits = 1))
for (label, m) in [("gb_fixed_100", solve_model(100.0)), ("gb_variable_cap500", solve_model(0.0; endo = true, cap = 500.0))]
    ntc = haskey(object_dictionary(m), :NTC) ? value(m[:NTC]) : 100.0
    imp = [value(m[:F_IS_FO][t]) for t in T]
    ex = [value(m[:F_FO_IS][t]) for t in T]
    cu = [value(m[:CU][t]) for t in T]
    both = (imp .> 0.01) .& (cu .> 0.01)
    println(label, ": ntc ", round(ntc, digits = 1), " cost ", round(objective_value(m) / 1e6, digits = 3),
        " MEUR, export max ", maximum(ex))
    println("  import total ", round(sum(imp) / 1e3, digits = 2), " GWh, of which at price < 0: ",
        round(sum(imp[neg]) / 1e3, digits = 2), " GWh (", round(100 * sum(imp[neg]) / sum(imp), digits = 1), " %)",
        "; payment received for it ", round(-sum(pi_IS[neg] .* imp[neg]) / 1e6, digits = 3), " MEUR")
    println("  curtailment total ", round(sum(cu) / 1e3, digits = 2), " GWh, of which in price < 0 hours: ",
        round(sum(cu[neg]) / 1e3, digits = 2), " GWh")
    println("  hours with import AND curtailment: ", count(both), ", of which price <= 0: ", count(both .& (pi_IS .<= 0)),
        "; import in such hours with price > 0: ", round(sum(imp[both .& (pi_IS .> 0)]) / 1e3, digits = 3), " GWh")
    println("  hours with import > demand: ", count(imp .> demand .+ 0.01))
    println("  import-weighted price, price >= 0 hours only: ",
        round(sum((pi_IS .* imp)[.!neg]) / sum(imp[.!neg]), digits = 2), " EUR/MWh")
    flush(stdout)
end
