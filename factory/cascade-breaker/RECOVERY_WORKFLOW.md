# Recovery Workflow and Post-Action Verification

**Status: planned design only.** The current prototype does not implement an operational action executor, rollback engine, or post-action verifier. `ACT_AUTO` means the deterministic policy criteria were met; it does not mean an action was executed or succeeded.

## Proposed lifecycle

1. **Pre-action validation:** confirm the action is explicitly allowlisted, its target and parameters are in bounds, required evidence is current, an operational owner has approved the action class, and stop conditions are defined.
2. **Record pre-state:** persist an action ID, idempotency key, policy/schema versions, evidence references, target identity, timestamp, and the relevant initial state.
3. **Bounded execution:** keep model agents separate from operational credentials. A dedicated least-privilege executor must enforce the approved scope, timeout, retry policy, and stop conditions.
4. **Independent verification:** check authoritative postconditions using evidence independent of the executor's success response. Record `VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, or `OUTCOME_UNKNOWN`. Missing, stale, or unavailable verification is never success.
5. **Recovery or escalation:** use a compensating action only if it has been separately approved and is safe for the observed state. If outcome is unknown, reconcile the real state before retrying. Rollback is not always safe or possible; escalate when recovery preconditions are not met.
6. **Audit and close:** retain the decision, authorization, execution receipt, verification evidence, recovery/escalation result, timestamps, and version identifiers. Stop further automated actions on unexpected effects, repeated failures, or operator stop request.

## Required failure-injection tests

- Timeout with uncertain target state does not trigger a blind retry.
- Executor reports success but independent verification fails.
- Verification data is missing, stale, contradictory, or unavailable.
- Target state changes after authorization.
- Duplicate requests do not repeat side effects.
- Action is outside the approved allowlist or parameter bounds.
- Rollback is unsafe or irreversible and the system escalates instead.
- Recovery fails and the workflow stops rather than retrying indefinitely.
- Audit persistence is unavailable before an action that requires a durable record.

## Release gate

Do not connect this design to live operational controls until the executor, verifier, recovery path, authorization checks, stop mechanism, audit trail, and failure-injection tests are implemented and reviewed. Begin with historical replay and read-only shadow mode. Any later pilot must have a named operational owner, a narrow approved scope, and documented go/no-go criteria.
