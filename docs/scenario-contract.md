# Scenario contract

- `carbon_g_per_kwh`: per-hour grid intensity, 0–2000 g CO₂e/kWh.
- `heat_demand_kwh`: useful heat demand per hour, same horizon length.
- `capacity_kwh_per_hour`: integer compute-energy capacity, 1–16.
- `heat_recovery`: fraction of compute energy available as useful heat, 0–1.
- `displaced_heat_g_per_kwh`: assumed intensity of the displaced heating source.
- `jobs`: unique name, integer `release` inclusive, `deadline` exclusive, and `energy_kwh`.

An infeasible schedule returns HTTP 400 with an explanation. No job is silently dropped.

Jobs supply integer kWh demand to a min-cost-flow graph. A job connects only to hourly slots inside its release/deadline window. Hourly capacity is split into one-kWh marginal arcs; their cost is grid carbon minus the credit for heat that can actually displace heating in that hour.

`recovered_heat[h] = min(heat_demand[h], compute[h] × heat_recovery)`

`net_carbon = Σ compute[h] × grid_carbon[h] − Σ recovered_heat[h] × displaced_heat_factor`

Successive shortest augmenting paths use a residual graph and queue-based Bellman–Ford. Reverse edges allow existing placements to be reassigned rather than locking in greedy choices. Costs are rounded to 0.001 g; the solution is optimal for that discrete linear model. The comparison schedule minimizes total hour index under the same feasibility constraints, making it an earliest-feasible baseline rather than an unconstrained immediate-start schedule.

Limits: 2–48 hourly slots, 1–16 jobs, integer 1–16 kWh/hour capacity, and at most 100 kWh per job.
