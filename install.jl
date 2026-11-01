# Installs the Julia packages the model needs into your default Julia environment.
# Run once:  julia install.jl
# Tested with Julia 1.13.1, JuMP 1.32.1, HiGHS 1.26.0, CSV 1.1.0, DataFrames 1.8.2.
using Pkg
Pkg.add(["JuMP", "HiGHS", "CSV", "DataFrames"])
Pkg.precompile()
println("Julia packages installed: JuMP, HiGHS, CSV, DataFrames")
