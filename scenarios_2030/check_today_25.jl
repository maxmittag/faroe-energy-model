# Check only (CHECKS.md): today's demand, fixed 25 MW cable.
#  - SPIKE_INPUT=input_hourly.csv    SPIKE_CABLE_KM=450 -> must reproduce the given 3.8 M EUR (copy of the model is faithful)
#  - SPIKE_INPUT=input_hourly_gb.csv SPIKE_CABLE_KM=400 -> tests the 450->400 km conversion of the Scotland reference
include("model_spike.jl")
m = solve_model(25.0)
println(get(ENV, "SPIKE_INPUT", ""), " km ", cable_km, ": ", termination_status(m), " cost ",
    round(objective_value(m) / 1e6, digits = 3), " MEUR, wind +", round(value(m[:CAP_G]["wind"]), digits = 1),
    ", demand ", round(sum(demand) / 1e3, digits = 1), " GWh")
