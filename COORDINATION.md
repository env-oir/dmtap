
---

## SPEC CONVERGENCE — W6 STOP RULE FIRED (2026-07-24, spec session)

Three successive W6 re-critiques each found substantive residuals, so per the loop's own rule the
pass STOPS here for a founder decision rather than looping further.

| Round | Substantive residuals |
|---|---|
| 1 | SA-English doctrine phrase left American in 5 files (self-inflicted by W5's letter-case freeze rule). Fixed `f0810a1`. |
| 2 | **HIGH** — ack existence-oracle still open in the §20.2 state machine; then found in 6 more artefacts that *encode* the rule. Fixed `0254027`, `0074e18`. Plus 2 coherence findings, fixed `d051d80`. |
| 3 | **HIGH** — dedup ran *before* classification, so a cold replay of a previously-acked `id` under a throwaway key earned an `ack`. Fixed `8330c2a`. Plus 1 low overclaim (MED-4). |

**The spec is in better shape than at any prior point and every finding above is fixed.** The stop
rule fired not because quality is falling but because the yield has not reached zero, and the honest
reading is that **it is not converging on "no findings" — it is converging on "one finding per deep
read of a previously-unread surface"**. Rounds 2 and 3 both found HIGH defects in the *same rule*
(ack eligibility), on two different axes, in artefacts that encode rather than state it.

**Two known coverage gaps, disclosed rather than closed:**
1. No conformance vector exists for §18.7.3 **capability caveats** — the rule that caveats are
   conjunctive across the whole chain and that an unrecognised caveat key MUST fail closed. `grep
   caveat conformance/` returns nothing. The rule is normative and untested.
2. `21-errors-iana.md`'s ~188 `FAIL_CLOSED_BLOCK`/`DROP_SILENT` actions have never been checked
   systematically against the prose clauses they cite; only a handful were spot-checked.

**Founder decision required: how much further to invest.** The options, honestly stated:
- **(a) Declare done.** Defensible: 30+ real defects fixed, every known finding closed, lint clean.
  Accepts that a further deep read would likely find something.
- **(b) One more targeted round** on the two disclosed gaps above, then stop regardless.
- **(c) Keep looping.** Not recommended without a changed method — the current method's yield per
  round is roughly constant, so this does not terminate on its own.

**Recommendation: (b).** Both gaps are narrow, both are security-load-bearing, and closing them
converts the largest remaining "unknown" into a known. Then freeze with the audit map recorded.
