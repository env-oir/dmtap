# 4. Fulfilment

> **Drafting status.** This section is scoped but not yet normative. It states what it will
> specify, which existing standards it profiles, and the decisions still open. Nothing here is
> implementable yet; text becomes normative when the RFC 2119 keywords appear.

## 4.1 Scope

The second offer axis: how the thing reaches the buyer. This is not only a logistics question — it
is the **only** object that knows where a supply happens, and §11.2 derives the tax anchor from it
and from nothing else.

## 4.2 Variants

| Variant | Carries (§16.5.2) | Covers |
|---|---|---|
| `ship` | destination countries | carried to an address |
| `collect` | a `PlaceRef` | buyer picks up |
| `digital-grant` | nothing | download, licence key |
| `perform-at-place` | a `PlaceRef` | the venue for a haircut, an event |
| `perform-remote` | nothing | consulting over video |
| `access-grant` | a `PlaceRef` or nothing | a gym membership, or a streaming subscription — same variant |
| `return-required` | a `PlaceRef`, a term in days | a rental or hire |

Each `Offer` carries exactly one `Fulfilment` value (§16.5.2, key 3) — the union is a choice, not a
set. §4.8 covers what that means for a seller who genuinely offers more than one fulfilment mode for
the same item.

## 4.3 The place-of-supply derivation table

| Fulfilment variant | Anchor | Why |
|---|---|---|
| `ship` | delivery destination | the goods physically arrive there; import VAT/GST and duty regimes key off where they land |
| `collect` | the stated place | the buyer takes possession there, regardless of where either party is established |
| `perform-at-place` | the stated place | admission and physically-performed services are generally taxed where the performance happens |
| `return-required` | the stated place | the same reasoning as `collect` — the item changes hands there |
| `perform-remote` | buyer residence | there is no physical venue to anchor to |
| `digital-grant` | buyer residence | nothing physical happens anywhere |
| `access-grant` | the stated place, if named; otherwise buyer residence | the field name is shared by two economically different cases, and the anchor has to follow whichever one this instance actually is |

This is the forcing example §0.1 and §11.2 both cite: an event held in one country, sold by a seller
established in a second, to a buyer resident in a third. Only the venue in the `Fulfilment` object
answers the question; neither party's country does, and averaging or defaulting to either one is
simply wrong.

## 4.4 Why the anchor is derived, never supplied

§11.2 states the rule this section has to honour: place of supply is **computed from** the
`Fulfilment` object, and it is not a separate field an implementation fills in alongside it. This is
stricter than it sounds, and it is stricter on purpose.

An earlier implementation took place of supply as its own parameter, populated independently of the
fulfilment details rather than derived from them. Once the two could be set independently, nothing
checked that they agreed — and in practice the anchor defaulted to the seller's own establishment,
because that is the natural default in ordinary billing code, not because anyone decided a haircut
performed abroad should be taxed at home. The system returned a country. It was wrong, and nothing
about the output looked wrong: no error, no missing field, just a confidently incorrect
jurisdiction.

Deriving the anchor as a pure function of the `Fulfilment` value — §16.5.2's grammar comment, and
`Fulfilment::place_of_supply_kind` in the reference implementation — removes the second parameter
entirely. There is nothing left for the anchor to disagree with, because there is nothing else it
could be computed from. This is also why neither `Offer` nor `Order` carries a place-of-supply field
of its own (§16.5.2, §16.6): adding one back would reopen exactly this failure mode.

## 4.5 Handover: what counts, and who signs it

§18.4 already states the general rule for custody: a handoff is signed by the party **taking**
custody, not the party giving it up, because a chain attested only by the sender proves someone
tried, and attested by the receiver proves something actually moved. Fulfilment variants differ in
whether a custody chain exists at all.

| Variant | What constitutes handover | Evidence |
|---|---|---|
| `ship` | the carrier takes custody at first-leg pickup, beginning the consignment chain (§18.4 `created → accepted`, signed by the receiving custodian); final handover is the last leg's `delivered` transition | carrier or recipient signature, per §18.4 |
| `collect` | the buyer takes physical possession at the stated place | no consignment leg exists — see below |
| `digital-grant` | the grant (download, licence key, credential) is transmitted | signed by the seller at transmission |
| `perform-at-place` | the service is completed at the venue | — |
| `perform-remote` | the remote session or deliverable is completed | — |
| `access-grant` | access is issued, and for a term, remains valid until it lapses | signed by the seller at issuance |
| `return-required` | two handovers: outbound at the start of the term, inbound return at or before it | — |

**The gap this table exposes.** §18.3's order state machine signs the generic `fulfilling →
delivered` transition as "carrier or seller". That is a good fit for `ship`, where a carrier's
proof-of-delivery is independent third-party evidence. It is a weaker fit for `collect`,
`perform-at-place`, `perform-remote` and `access-grant`, where there is no carrier and the signature
available is the seller's own claim that handover happened — exactly the kind of unilateral
assertion the signed-transition model exists elsewhere to avoid. Whether those variants should
instead require the buyer's counter-signature to reach `delivered` is not resolved here; see §4.10.

## 4.6 Incoterms 2020: risk and cost transfer for shipped goods

Incoterms 2020 govern a different question from §4.3's anchor, and the two are easy to conflate the
same way seller/buyer country and place of supply are (§11.2): Incoterms fix **when risk and cost**
pass from seller to buyer on a shipped good, not **where the supply is taxed**. A `DAP` shipment and
an `EXW` shipment to the same destination have the same place of supply and different points at
which the buyer bears loss in transit.

The `Fulfilment::Ship` variant carries only destination countries (§16.5.2) — it has no field for
which Incoterm applies. That term, where it matters, currently sits at the leg or order level rather
than the offer's fulfilment axis; whether it needs a wire field of its own is open (§4.10).

## 4.7 Return terms for rentals

`return-required` carries a place and a term in days and nothing else. What happens if the item
comes back damaged, or late, is not a fulfilment-axis question — it is a dispute over an order
already placed, resolved through the order and escrow machinery (§7, §18.5) rather than encoded as a
condition on the offer. The natural pairing is with `DepositBalance` consideration (§5.8): a deposit
taken at order time is the mechanism by which a late-return or damage claim is actually made whole,
and the fulfilment axis's job stops at stating where and for how long, not at what enforces it.

## 4.8 One item, several ways to get it

A seller who genuinely offers both `collect` and `ship` for the same item — common, not an edge
case — cannot express that as a single `Offer`, because `Fulfilment` is a one-of union and an
`Offer` carries exactly one value of it (§16.5.2, key 3). The way to express it under the current
grammar is two `Offer` objects: same `Item`, same `Availability`, same `Consideration`, differing
only in `Fulfilment`. Each is independently signed and independently withdrawable (§18.2). A buyer's
node presents both against the same underlying product and lets the buyer's fulfilment choice pick
which offer — and therefore which anchor (§4.3) — the resulting order binds to.

This replaces the earlier framing of "multi-variant offers" with the grammar's actual shape: there
is no offer-level alternative-fulfilment construct today, only multiple offers that happen to share
everything but the fulfilment axis. Whether that repetition is worth a dedicated grouping construct
is open (§4.10).

## 4.9 Standards profiled

Incoterms 2020 for the risk/cost transfer point on shipped goods. ISO 3166-1 for places (`PlaceRef`,
§16.5.2).

## 4.10 Open

- Whether `digital-grant` needs a licence-terms sub-object, or defers entirely to §5's consideration
  axis.
- Whether an Incoterm needs its own wire field on `Ship`, or remains a leg/order-level convention
  outside the offer (§4.6).
- Whether fulfilment variants without a carrier (`collect`, `perform-at-place`, `perform-remote`,
  `access-grant`) should require the buyer's counter-signature to reach `delivered`, rather than
  accepting the seller's signature alone (§4.5).
- Whether repeated same-item, different-fulfilment offers (§4.8) warrant a first-class grouping
  construct, given the grammar currently expresses the case only as separate, independently signed
  objects.
