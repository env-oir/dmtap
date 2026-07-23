# KOTVA spec-perfection — driven by the Wakala session (founder-authorised)

Temporary process file (delete at convergence). Edits land directly in kotva; **no co-author footer**.
The Wakala session is driving this pass per founder; the spec session should HOLD spec edits to avoid
collision (see wakala COORDINATION.md).

## Founder calls — DECIDED (agents obey these)
- **MIXNET = DEMOTE.** Move `04-transport §4.4` (Sphinx/Loopix mixnet, ~883 lines) and `09-anti-abuse
  §9.4.1` (VDF, ~115 lines) to a new `research/` dir as **non-normative / experimental**, leaving short
  stub pointers. **Flip the transport default off the mixnet/`private` tier to `fast`/direct.** Demote
  `06-privacy` SP-3/SP-4/§6.10. **Restate the metadata-privacy claim honestly**: sealed-sender
  *reduction* vs intermediaries — NOT global-passive-adversary immunity (a global observer can still
  recover the graph via IP+timing correlation). Keep the mixnet as an **opt-in tier + a stated roadmap
  goal**. Reconcile DIRECTION §9, THREAT-MODEL SEC-9/R-9, README, 00-overview, substrate/README+ROLES so
  they all agree (they already say "research-tier" — make the flagship match).
- **ECONOMICS = SEAM ONLY.** CONTRACT §6 keeps the *mechanism* normative (signed tariff object, signed
  usage-receipt object, settlement seam over an existing asset, no token, no published price-rank, stake
  verified on-rail, **charge for service — never for deliverability/classification**) and the *numbers*
  out of scope (operator policy). Do NOT add pricing / rails / billing models. Add ONE honest sentence:
  "whether charge-for-service sustainably funds coordinators is an open question."
- **PQ:** classical suite `0x01` is the interoperable floor; `0x02` (X-Wing + ML-DSA composite) is
  **PROVISIONAL**, pinned to a specific draft revision — not hard-mandated.
- **Personhood:** require interop with **≥2 structurally-different** bindings as a v0 target + a non-crypto
  day-one path; disclose the single-vendor (World ID) fragility.
- **Custodial escrow:** disclose + accept (the one honest load-bearing exception); hold it to the same
  MUST-verify-stake bar as other kinds; add it as a disclosed self-host exception class in CONTRACT §2.3.
- **Naming:** keep legacy brands (DMTAP / TRACT / WRAP) primary as aliases; **wakala** = the coordinator
  umbrella (provisional resolved).
- **SA/British English + RFC layout: LAST**, after correctness is frozen (don't re-spell churned text).

## Guardrails (every wave)
Perfect, don't rewrite. PRESERVE all normative content, every honest-residual, every security MUST, every
wire byte/CBOR key/DS-tag/error code, every RFC citation. Never introduce an overclaim. Keep cross-refs
resolving + BCP-14 correct. Commit per wave; `git pull --rebase` before push; one writer per doc-cluster.

## Waves
**W1 (substantive, cross-cutting — file-disjoint, run now):**
- **A1 governing alignment** — DIRECTION, 00-overview, README, THREAT-MODEL, SPEC, substrate/README,
  substrate/ROLES: apply the mixnet-demotion *statements* + canonical **six** waist capabilities (restore
  MOTE + Transport to substrate/README §2) + align every coordinator-kind count/tally to CONTRACT §5.
  Does NOT edit CONTRACT (A2 owns it).
- **A1b mixnet mechanics** — 04-transport §4.4, 06-privacy SP-3/SP-4/§6.10, 09-anti-abuse §9.4.1; create
  `research/mixnet.md` + `research/vdf.md`; move the content, stub pointers, flip the default.
- **A2 contract + wire-debt** — coordinator/CONTRACT (§5 canonical kinds; §6 economics + the honesty note;
  custodial-escrow bar §2.3/§6), 07-gateway, 12-operators, 26-legacy-adapters, 18-wire-format, 21-errors:
  write **GatewayAuthz / CoordinatorDescriptor / SignedTariff / UsageReceipt** CDDL + DS-tags + signing
  preimages (match the Wakala impl's logged descriptor layout where sensible), so "Accountable" is
  wire-checkable.

**W2 (substantive residuals — after W1 commits, watch overlaps):** RecoveryPolicy §1.4 formal model
(01/13); HPKE-mode pinned Base (02/05/18); SYNC split minimal-core+extension + open-namespace determinism
(substrate/SYNC); premature-generality cuts (suites 0x03-0x05→appendix; compute-kind note; media-relay/
reachability collapse consideration); multi-homing RECOMMENDED (substrate/ROLES); REPUTATION→OpenRank
"degraded" label (primitives/REPUTATION + bindings); personhood ≥2 (bindings + profiles); discovery/
indexer + coordinator-funding named as first-class open problems (DIRECTION/SPEC); GOVERNANCE.md refresh +
coordinator-contract ratification process; §19.7.1 Payload.from=gateway-IK fix (19).

**W3 (simplify):** compress per-doc SEC-invariant/honest-residual boilerplate to reference tables
(THREAT-MODEL = single argued source, ~15-20% cut, zero normative loss); turn reproduced index tables into
pointers; publish a minimal "Identity + MOTE + one transport" first-implementation conformance tier.

**W4 (cross-doc consistency):** unified terminology, all cross-refs resolve, family "connection" (SPEC
index + inter-profile links), including the previously-skipped profiles/tract/* + profiles/wrap/*.

**W5 (LAST — editorial):** South African/British English (prose only — NOT the `Authorization` header,
`GatewayAuthz`, wire fields, code, RFC proper nouns) + one RFC-grade skeleton per doc (abstract, BCP-14
conventions, stable numbering, normative/informative references, honest-residual section), modelled on
RFC 9051 / RFC 9420.

**W6 (converge):** fresh multi-lens re-critique → fix residuals → repeat W-as-needed until the critique
reports zero contradictions, consistent SA English, RFC-grade layout, all cross-refs resolving. Then delete
this file + report DONE.
