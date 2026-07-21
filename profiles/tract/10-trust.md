# 10. Trust

> **Drafting status.** This section is scoped but not yet normative. It states what it will
> specify, which existing standards it profiles, and the decisions still open. Nothing here is
> implementable yet; text becomes normative when the RFC 2119 keywords appear.

## 10.1 Scope

Reviews, purchase attestation, and ranking — without creating an authority.

## 10.2 What this section will specify

- `Review` as a signed public object attached to a product address, seller, distributor or courier.
- **Purchase attestation**: a proof, issued by the seller or an escrow operator at completion, that
  the author actually transacted. Verifiable by anyone, unlike a platform's "verified purchase"
  badge, and it makes ballot-stuffing cost a real transaction.
- Per-seller pseudonymous authorship (§1.2).
- Seller responses, and supersede-based retraction.

## 10.3 The prohibition

**No network-wide published score.** Computing one requires a party that aggregates and ranks,
which is the authority the design removes. Ranking is derived data; indexes will differ, and that
is the intended outcome, not a defect.

## 10.3a What attestation does not fix (§21.6)

§21.9 obliges this section to state the measured outcome rather than the hypothetical one.

OpenBazaar's reputation failure was self-published, unweighted reviews with no banning authority,
and **one vendor faked 60% of measured sales value**. A purchase attestation is strictly stronger
than what OpenBazaar had — it binds a review to a real transaction, so ballot-stuffing costs actual
trades. Two of the failure conditions nonetheless survive unchanged:

1. **Self-dealing produces genuine attestations.** A seller transacting with itself generates real
   proofs. Attestation raises the cost and leaves a public trail; it does not establish that the
   counterparty was independent, and nothing in this document does.
2. **Escrow-issued attestations are scarcest where they would matter most**, because escrow is
   opt-in and declined by exactly the actors it constrains (§9.5a).

The achievable Sybil-cost floor on a signed-feed substrate is an **open question** (§21.8), not a
solved one. An index's weighting policy is where that judgement lives, and different indexes
reaching different answers is the design rather than a defect.

## 10.4 Honest limits this section must state

- Rankings disagree between indexes; buyers lose the convenience of one authoritative number.
- Attestation raises manipulation cost but does not eliminate it — a seller can transact with
  itself, expensively and visibly.
- Whitewashing is bounded, not solved: a new key has no history, and discounting new keys is the
  only available defence.
- **Erasure**: a review is public, irrevocable, and signed by a person. Retraction is a superseding
  tombstone honoured by conformant clients and gateways; the residual — bytes persist if any
  independent holder keeps them — must be disclosed to the author before publishing.

## 10.5 Prior art

Sybil, whitewashing and ballot-stuffing literature on decentralized reputation; web-of-trust and
locally-measured reputation as the alternatives to a global score.
