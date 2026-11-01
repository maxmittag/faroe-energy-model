# =============================================================================
#  scenarios_2030: runs for the group assumptions of 28.10.2026 (Notion "Open decisions", part C)
#  Model = model_spike.jl (= model_v4 + endogenous cable option), unchanged except the
#  SPIKE_CABLE_KM override. Demand = 1.186 x today's hourly profile (scale_demand.py).
#  The data is read when model_spike.jl is included, so one counterpart per Julia process:
#    SPIKE_TAG=is       SPIKE_INPUT=input_hourly_2030.csv     SPIKE_CABLE_KM=450
#    SPIKE_TAG=gb       SPIKE_INPUT=input_hourly_gb_2030.csv  SPIKE_CABLE_KM=400
#  Output: results/summary_<tag>.csv
# =============================================================================
include("model_spike.jl")

const TAG = get(ENV, "SPIKE_TAG", "is")
const INPUT = get(ENV, "SPIKE_INPUT", "input_hourly.csv")
const COUNTERPART = TAG == "is" ? "Iceland" : "Scotland"
const DEMAND_CASE = "2030"

function report(label, m, solve_s; counterpart, case_type, ntc_fixed = NaN, cap = NaN)
    st = termination_status(m)
    head = DataFrame(case = label, counterpart = counterpart, case_type = case_type, demand_case = DEMAND_CASE,
        input = INPUT, status = string(st), primal_status = string(primal_status(m)))
    if st != MOI.OPTIMAL
        println(label, ": ", st); flush(stdout)
        return head
    end
    CAP_G, CAP_L, G, D_stor = m[:CAP_G], m[:CAP_L], m[:G], m[:D_stor]
    F_IS_FO, F_FO_IS, CU, feed_in = m[:F_IS_FO], m[:F_FO_IS], m[:CU], m[:feed_in]
    endo = haskey(object_dictionary(m), :NTC)
    ntc_val = endo ? value(m[:NTC]) : ntc_fixed
    # raw flows, then netting of simultaneous import and export (same price, no effect on cost)
    imp_raw = [value(F_IS_FO[t]) for t in T]; ex_raw = [value(F_FO_IS[t]) for t in T]
    ov = min.(imp_raw, ex_raw); imp = imp_raw .- ov; ex = ex_raw .- ov
    avail = sum(value(feed_in[n, t]) for n in NONDISP, t in T)
    cu = sum(value(CU[t]) for t in T)
    # checks
    bal = [sum(value(G[d, t]) for d in DISP) + sum(value(feed_in[n, t]) for n in NONDISP) + bio[t] -
           sum(value(D_stor[s, t]) for s in S) - value(CU[t]) + imp_raw[t] - ex_raw[t] - demand[t] for t in T]
    oil_max = maximum(value(G["oil", t]) for t in T)
    # cost components (EUR per year), must add up to the objective
    c_inv_gen = sum(ic_generation_cap[p] * value(CAP_G[p]) for p in INV)
    c_inv_sto = sum(ic_storage_cap[s] * value(CAP_L[s]) for s in S)
    c_var = sum(vc[d] * value(G[d, t]) for d in DISP, t in T) * dispatch_scale
    c_trade = sum(pi_IS[t] * (imp_raw[t] - ex_raw[t]) for t in T) * dispatch_scale
    c_cable = ann_x * ntc_val
    obj = objective_value(m)
    hit_cap = endo ? (ntc_val >= cap - 0.01) : false
    d = hcat(head, DataFrame(
        cable_km = ntc_val > 0 ? cable_km : 0.0, ann_x_EUR_per_MW = ann_x, cap_MW = cap, ntc_hit_cap = hit_cap,
        cost_MEUR = obj / 1e6, ntc_MW = ntc_val,
        new_wind_MW = value(CAP_G["wind"]), new_pv_MW = value(CAP_G["pv"]),
        new_bat_MW = value(CAP_G["battery"]), new_bat_MWh = value(CAP_L["battery"]), new_phs_MW = value(CAP_G["phs"]),
        import_GWh = sum(imp) / 1e3, export_GWh = sum(ex) / 1e3,
        demand_GWh = sum(demand) / 1e3, peak_demand_MW = maximum(demand),
        import_share_demand = sum(imp) / sum(demand), export_share_demand = sum(ex) / sum(demand),
        curtail_share = avail > 0 ? cu / avail : 0.0, curtail_GWh = cu / 1e3,
        wind_total_MW = g_max["wind"] + value(CAP_G["wind"]),
        import_hours = count(>(0.01), imp), export_hours = count(>(0.01), ex),
        cable_util = ntc_val > 0 ? (sum(imp) + sum(ex)) / (ntc_val * length(T)) : 0.0,
        pi_mean = sum(pi_IS) / length(T),
        c_inv_gen_MEUR = c_inv_gen / 1e6, c_inv_storage_MEUR = c_inv_sto / 1e6, c_var_MEUR = c_var / 1e6,
        c_trade_MEUR = c_trade / 1e6, c_cable_MEUR = c_cable / 1e6,
        check_cost_sum_err_EUR = c_inv_gen + c_inv_sto + c_var + c_trade + c_cable - obj,
        check_balance_err_max_MW = maximum(abs.(bal)), check_oil_max_MW = oil_max,
        check_flow_max_MW = maximum(imp_raw .+ ex_raw), check_simultaneous_GWh = sum(ov) / 1e3,
        solve_s = solve_s))
    println(label, ": ", round(obj / 1e6, digits = 2), " MEUR, ntc ", round(ntc_val, digits = 1),
        " (cap hit: ", hit_cap, "), wind +", round(value(CAP_G["wind"]), digits = 1), ", pv +",
        round(value(CAP_G["pv"]), digits = 1), ", bat +", round(value(CAP_G["battery"]), digits = 1), " MW / ",
        round(value(CAP_L["battery"]), digits = 1), " MWh, import ", round(sum(imp) / 1e3, digits = 1),
        " GWh, export ", round(sum(ex) / 1e3, digits = 1), " GWh, balance err ",
        maximum(abs.(bal)), ", oil max ", oil_max, ", ", solve_s, " s"); flush(stdout)
    return d
end

function run_case(label; ntc = 0.0, endo = false, cap = NaN, counterpart = COUNTERPART, case_type = "fixed")
    t0 = time()
    m = endo ? solve_model(0.0; endo = true, cap = cap) : solve_model(ntc)
    return report(label, m, round(time() - t0, digits = 1); counterpart = counterpart, case_type = case_type,
        ntc_fixed = ntc, cap = cap)
end

function main()
    println("tag $TAG, input $INPUT, cable_km $cable_km, ann_x $(round(ann_x)) EUR/MW/yr, demand ",
        round(sum(demand) / 1e3, digits = 1), " GWh, peak ", round(maximum(demand), digits = 1), " MW"); flush(stdout)
    rows = DataFrame()
    if TAG == "is"
        rows = vcat(rows, run_case("base_no_cable"; ntc = 0.0, counterpart = "none", case_type = "base"), cols = :union)
        for n in [25.0, 50.0, 100.0]
            rows = vcat(rows, run_case("is_fixed_$(Int(n))"; ntc = n), cols = :union)
        end
        rows = vcat(rows, run_case("is_variable_cap1000"; endo = true, cap = 1000.0, case_type = "variable"), cols = :union)
    else
        for n in [25.0, 50.0, 100.0]
            rows = vcat(rows, run_case("gb_fixed_$(Int(n))"; ntc = n), cols = :union)
        end
        r500 = run_case("gb_variable_cap500"; endo = true, cap = 500.0, case_type = "variable")
        rows = vcat(rows, r500, cols = :union)
        if r500.status[1] == "OPTIMAL" && r500.ntc_hit_cap[1]   # task: if the cap binds, show it moves with the cap
            rows = vcat(rows, run_case("gb_variable_cap1000"; endo = true, cap = 1000.0, case_type = "variable"),
                cols = :union)
        end
        # check: the no-cable case must not depend on which price file is loaded
        rows = vcat(rows, run_case("check_base_gb_input"; ntc = 0.0, counterpart = "none", case_type = "check"),
            cols = :union)
    end
    CSV.write(joinpath(@__DIR__, "results", "summary_$(TAG).csv"), rows)
    println("written results/summary_$(TAG).csv"); flush(stdout)
end

main()
