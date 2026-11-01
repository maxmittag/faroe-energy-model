# Check only (CHECKS_import_only.md): Iceland 50 MW, 2030 demand, import only, builds no new wind
# although wind LCOE (~14 EUR/MWh) is below the mean import price (~23 EUR/MWh). Two tests:
#  1) marginal value of 1 MW new wind = sum_t ava_wind_t * dual(ElectricityBalance_t) vs its annual cost
#  2) re-solve with 10 MW new wind forced in: cost must go up (LP optimum)
# SPIKE_NO_EXPORT=1 SPIKE_INPUT=input_hourly_2030.csv SPIKE_CABLE_KM=450 julia check_is50_wind.jl
include("model_spike.jl")
NO_EXPORT || error("needs SPIKE_NO_EXPORT=1")
m = solve_model(50.0)
c0 = objective_value(m)
bal = m[:ElectricityBalance]
mu = [dual(bal[t]) for t in T]                 # EUR per MWh of demand in hour t (per hour of the data year)
val = sum(availability["wind"][t] * mu[t] for t in T) * dispatch_scale
imp = [value(m[:F_IS_FO][t]) for t in T]
cu = [value(m[:CU][t]) for t in T]
println("cost ", round(c0 / 1e6, digits = 4), " MEUR; new wind ", value(m[:CAP_G]["wind"]))
println("annual cost of 1 MW wind: ", round(ic_generation_cap["wind"]), " EUR; marginal value from duals: ",
    round(val), " EUR; reduced cost CAP_G[wind]: ", round(reduced_cost(m[:CAP_G]["wind"])))
println("wind-weighted dual ", round(sum(availability["wind"] .* mu) / sum(availability["wind"]), digits = 2),
    " EUR/MWh, mean dual ", round(sum(mu) / length(T), digits = 2), ", import-weighted price ",
    round(sum(pi_IS .* imp) / sum(imp), digits = 2))
println("hours with import > 0: ", count(>(0.01), imp), "; mean ava_wind in import hours ",
    round(sum(availability["wind"][imp .> 0.01]) / count(>(0.01), imp), digits = 3), ", in other hours ",
    round(sum(availability["wind"][imp .<= 0.01]) / count(<=(0.01), imp), digits = 3))
# 2) force 10 MW new wind (rebuild, fix wind, re-optimise)
m2 = solve_model(50.0)
fix(m2[:CAP_G]["wind"], 10.0; force = true)
optimize!(m2)
println("forced +10 MW wind: ", termination_status(m2), " cost ", round(objective_value(m2) / 1e6, digits = 4),
    " MEUR (delta ", round((objective_value(m2) - c0) / 1e6, digits = 4), "), curtailment ",
    round(sum(value(m2[:CU][t]) for t in T) / 1e3, digits = 1), " GWh vs ", round(sum(cu) / 1e3, digits = 1))
