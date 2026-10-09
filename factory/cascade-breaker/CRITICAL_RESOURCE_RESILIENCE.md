# Critical-resource resilience scenarios

This design note extends Cascade Breaker beyond supplier delays to infrastructure and essential-resource constraints.

## Common failure pattern

1. A critical resource becomes constrained: fuel, backup-power endurance, oxygen inventory, signal quality, or a replenishment route.
2. Demand, resource state, supply/recovery estimates, and dependent services are correlated.
3. The system estimates a time-to-impact only when the data supports one; otherwise it reports an evidence gap and abstains.
4. The system maps downstream dependencies and identifies a responsible human decision owner.
5. It proposes reversible, policy-compliant mitigation for review. Consequential action remains subject to sector-specific authority.

## Synthetic cases

The file `data/critical_resource_resilience_scenarios.json` defines three illustrative scenarios:

- **IT park / facilities:** a long grid outage, constrained diesel supply, UPS endurance, and the dependency between server rooms, cooling, networking, and life-safety systems.
- **Hospital oxygen supply:** changing demand and uncertain replenishment. The model can raise operational alerts and support supply coordination, but must never triage patients, rank them, allocate oxygen, or recommend withdrawing treatment.
- **Broadcast / IPTV / OTT:** storm risk correlated with degrading feed telemetry, followed through headend, packaging, DRM/CAS where relevant, distribution, and viewer-facing services.

All data is synthetic and unverified. Example quantities are illustrative only and must not be treated as validated operating thresholds or time-to-impact predictions.

## Resource endurance model

A first approximation is:

`remaining endurance ≈ usable resource / observed consumption rate`

This is not sufficient on its own. Production use must account for variable loads, unusable reserve, measurement quality, equipment operating limits, replenishment confidence, dependency failures, and uncertainty. For fuel and power, preserve required cooling and life-safety systems. For medical oxygen, use approved clinical/facility thresholds and immediate escalation procedures.

Compare estimated endurance with recovery or replenishment time and a policy-defined safety margin. If the evidence is stale, conflicting, incomplete, or not independently verified, return **ABSTAIN** and explain what must be confirmed.

## Safety and governance

- Forecasts and external events are risk signals, not proof of failure.
- Keep source provenance, timestamps, units, freshness and confidence explicit.
- Distinguish observation, hypothesis, counter-evidence, recommendation and decision.
- Do not authorize switching, shutdown, clinical allocation or other consequential actions from synthetic fixtures.
- Require accountable human approval and audit records for actions affecting production infrastructure.
- A deterministic policy gate remains the final software gate; AI-generated confidence alone never authorizes an action.

## Current implementation boundary

These fixtures are documentation and test data only. They are not connected to weather APIs, facility management systems, generator/UPS telemetry, hospital oxygen systems, CAS/DRM systems, broadcast monitoring, or live supplier feeds. No live time-to-impact calculation or production readiness is claimed.
