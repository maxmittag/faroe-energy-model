# =============================================================================
#  Runs all four import-only scenario sets of run_import_only.jl, one Julia process each,
#  with the right environment variables. Works the same on Windows, macOS and Linux.
#    julia run_all_import_only.jl              -> all four (about 25 min)
#    julia run_all_import_only.jl is_2030      -> only Iceland, 2030 demand (about 6 min)
#  Choices: is_2030, gb_2030, is_today, gb_today
#  Output: results_import_only/summary_<tag>_<demand case>.csv and log_<tag>_<demand case>.txt
#  Afterwards: python make_summary_import_only.py
# =============================================================================
const SETS = Dict(
    "is_2030"  => ("is", "2030",  "input_hourly_2030.csv",    "450"),
    "gb_2030"  => ("gb", "2030",  "input_hourly_gb_2030.csv", "400"),
    "is_today" => ("is", "today", "input_hourly.csv",         "450"),
    "gb_today" => ("gb", "today", "input_hourly_gb.csv",      "400"),
)
const ORDER = ["is_2030", "gb_2030", "is_today", "gb_today"]

todo = isempty(ARGS) ? ORDER : ARGS
for k in todo
    haskey(SETS, k) || error("unknown set $k, choose from $(join(ORDER, ", "))")
end
mkpath(joinpath(@__DIR__, "results_import_only"))
for k in todo
    tag, dc, input, km = SETS[k]
    env = copy(ENV)
    env["SPIKE_NO_EXPORT"] = "1"; env["SPIKE_TAG"] = tag; env["SPIKE_DEMAND_CASE"] = dc
    env["SPIKE_INPUT"] = input; env["SPIKE_CABLE_KM"] = km
    logfile = joinpath(@__DIR__, "results_import_only", "log_$(tag)_$(dc).txt")
    println("running $k (SPIKE_TAG=$tag SPIKE_DEMAND_CASE=$dc SPIKE_INPUT=$input SPIKE_CABLE_KM=$km), log: $logfile")
    flush(stdout)
    t0 = time()
    cmd = setenv(`$(Base.julia_cmd()) run_import_only.jl`, env; dir = @__DIR__)
    run(pipeline(cmd; stdout = logfile, stderr = logfile))
    for ln in eachline(logfile)   # show the result lines, skip Julia's soft-scope warnings
        occursin(r"MEUR|written", ln) && println("  ", ln)
    end
    println("  done in ", round(Int, time() - t0), " s"); flush(stdout)
end
