# 2. Catalogue

> **Drafting status.** This section is scoped but not yet normative. It states what it will
> specify, which existing standards it profiles, and the decisions still open. Nothing here is
> implementable yet; text becomes normative when the RFC 2119 keywords appear.

## 2.1 Scope

Product records, offers, the product-identity ladder, variants, and the rules that keep indexes
from becoming authorities.

## 2.2 The split, and why it is mechanical rather than conventional

A **product record** describes what a thing is; an **offer** is one seller's claim to supply it.
Because the substrate content-addresses public blobs over plaintext, two sellers publishing the
same record converge on the same address by construction, and the swarm stores it once. The
global product view is therefore an emergent consequence of hashing, not a registry.

## 2.2a How strong the convergence claim actually is (§21.2)

Weaker than §2.2 sounds, and §21.9 obliges this section to say so rather than let a reader infer
otherwise.

Convergence is trivially true for identical bytes and says nothing about the real case: two shops
describing the same shoe. A July 2026 literature pass found **no deployed system achieving
cross-publisher product identity without a licensed registry**, and the one candidate for
permissionless crawl-derived resolution was refuted 0-3 under adversarial verification. The two
models that exist in the field are the only two: a permissioned monopoly namespace (GS1 GTIN —
licensed rather than sold, fee-bearing, issued through national member organisations) and a purely
nominal string with no issuer or uniqueness guarantee (schema.org `productGroupID`). Nothing in
between is deployed.

So the content address is a sound **mechanism** carrying an **unproven** claim. The canonicalisation
rules of §2.3 — not the hashing — are the load-bearing part of this section, and §2.5 keeps
near-duplicate resolution listed as open rather than implied-solved.

## 2.3 What this section will specify

- `ProductRecord` and `Offer` object shapes.
- **Canonicalisation**: the normalisation applied before addressing, since convergence is only
  useful to the extent independent publishers can actually produce identical bytes. This is the
  hard part of the section.
- The **identity ladder** — content address (floor, zero authority) → claimed external identifiers
  (advisory, unverified, squattable) → manufacturer-signed record (authority = the brand).
- **Variants**: product groups, varies-by axes, and per-variant records.
- **Bundles and kits**, including components published by other sellers.
- The **index rule**: derived, rebuildable, never authoritative; disagreement resolves toward the
  feed; no protocol mechanism exists by which an index can delist a seller from the network.
- **The gap between permission and practice** (§21.3, §21.9). "Any node may build an index" does not
  mean many will. A content-addressed substrate offers no global index, so discovery is the *first*
  function to re-centralize: whichever index becomes economically dominant becomes a de facto
  content-policy gatekeeper regardless of what this document permits. That is what happened to the
  closest deployed relative of this design, and the largest live decentralized-commerce network
  avoided it only by adopting a central approval-gating registry (§21.4). **No rule in this
  document prevents it.** Multiple competing indexers with verifiable completeness or censorship
  proofs is the candidate answer, and it has no deployed precedent (§21.8). This is the weakest
  load-bearing claim in the specification and is marked as such rather than defended.

## 2.4 Standards profiled

schema.org product vocabulary (`Product`, `Offer`, `ProductGroup`, `hasVariant`, `variesBy`) for
the data model, so existing merchant feeds map in by translation. GS1 identifiers (GTIN, MPN) are
supported as **claims only** — issuance is gated and fee-bearing, so a spec that depended on them
would import a centralization point and a cost barrier.

## 2.5 Open

- Near-duplicate resolution. The address floor is exact-match; merging almost-identical records is
  an index-side heuristic, and heuristics differ between indexes. Whether the spec should
  recommend one, or deliberately leave it to differ, is undecided.
- Bootstrapping manufacturer signatures when most brands will not participate early.
