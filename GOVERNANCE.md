# Governance

DMTAP is an **open protocol specification** intended to be implemented by anyone, with an
independent reference implementation (Envoir) and an optional hosted operator — none required to
speak the protocol. This document states who decides, how the specification changes, and the
security gates that govern a production deployment. The normative sources are the specification's
**§10** (versioning, conformance, governance) and **§12.8** (operational & security procedures);
where this file and the spec disagree, the spec governs (**§10.4**).

## The specification is authoritative

Independent implementations MUST be buildable from the specification text alone. The Rust reference
in `node/` and `gateway/` is a **proof and a set of libraries, not normative** — where the reference
and the spec disagree, **the spec wins** (or the discrepancy is filed as a bug). "DMTAP-compatible"
means **passes the conformance suite** (`conformance/`), not "resembles the reference" (§10.3, §10.4).

## Standards track & licensing

- **Standards track.** The intent is to pursue an **IETF Internet-Draft** for the wire protocol and
  object formats, aiming for RFC status — neutral governance is what lets competitors adopt without
  fearing capture (§10.5).
- **Licensing.** The **specification** and the **reference implementation** ship under the **MIT
  license** (Apache-2.0 dual-licensing under consideration for its explicit patent grant).
  Everything a user touches and everything trust depends on is open (§10.5, §12.4).
- **Open software + paid operations.** Commercial sustainability comes from a thin, private
  control-plane (a hosted operator) that bills **operations only**. The **inviolable rule** (§12.3):
  privacy, cryptography, metadata privacy, and recovery are **never** behind a paywall or the
  operator seam. This bright line is non-negotiable governance, not a product decision (§12.3, §12.5).

## Changing the specification

- **Backwards-compatible evolution** happens through **capability negotiation** (§10.2) and the
  registries' extension procedure (§21.25): new suites, message kinds, KT log-types, and capability
  tokens are added dual-stack and negotiated per-peer — **no flag day**. Mechanisms are retired the
  same way (§12.8.5): announce the successor, let the suite high-water-mark and monotonic capability
  version make the upgrade stick, then retire the old one with an explicit owner-authorized action.
- **Structural revisions** increment **both** the domain-separation tag (`DMTAP-v0/…` → `DMTAP-v1/…`)
  and the DNS `v=dmtap<N>` anchor in lockstep, giving an unambiguous discriminator (§10.1).
- **Errata and defects** are filed against the spec and corrected under §10.4. Security-relevant
  changes follow the disclosure process below and the audit gate.
- **New fail-closed / downgrade rules** added anywhere in the spec MUST be mirrored into the
  **§10.7** auditable set, so the fail-closed posture stays checkable as a whole.

## Security governance

- **Coordinated vulnerability disclosure** is governed by [`SECURITY.md`](SECURITY.md) and §12.8.1:
  private reporting to `security@envoir.org`, a **90-day** default embargo, CVE assignment, and a
  research **safe harbour**.
- **Independent external audit is a pre-deployment gate (§12.8.4).** A qualified third party MUST
  review the cryptography/protocol and the reference implementation **before any production
  deployment**, and again on any **major crypto or wire change** (a new/retired suite, a changed
  signing preimage, a mixnet or deniable-handshake change). This gate is **paid for by the project**
  and is **distinct from** the post-deployment bug bounty.
- **Bug bounty is post-deployment only** — there is no live target to attack before launch
  (`SECURITY.md`, §12.8.1).
- **Honest limits are governance, not marketing.** The project states what the protocol **cannot**
  do (§6.6) and the disclosed residual of every security property (§6.9) rather than overclaim.
  Presenting a documented residual as solved — e.g. "anonymous" against an active adversary, or
  v0 KT as equivocation-proof — is a governance violation, not a nuance.

## Roles

- **Maintainers** steward the specification and reference implementation, triage disclosures, run
  the audit gate, and arbitrate spec-vs-reference discrepancies (§10.4).
- **Implementers** are first-class: conformance is defined by the public suite, so any independent
  implementation that passes it is DMTAP-compatible without maintainer permission (§10.3).
- **Operators** (gateway, mix, KT-log, postage/token issuers) are **accountable, attested
  identities** with a defined onboarding/reputation/revocation lifecycle (§12.8.6), never anonymous
  infrastructure and never able to gate a privacy/crypto feature (§12.3).
