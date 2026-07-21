# 5. Consideration

> **Drafting status.** This section is scoped but not yet normative. It states what it will
> specify, which existing standards it profiles, and the decisions still open. Nothing here is
> implementable yet; text becomes normative when the RFC 2119 keywords appear.

## 5.1 Scope

The third offer axis: what is paid, on what schedule, and how tax attaches to it.

## 5.2 Variants

| Variant | Carries (§16.5.2) | Covers |
|---|---|---|
| `fixed` | one `money` | a single price |
| `tiered` / `volume` | `[+ PriceTier]` (min_qty, unit_price) | cheaper per unit above a threshold |
| `recurring` | `money`, an RFC 5545 `RRULE` | subscriptions |
| `metered` | a dimension string, a unit `money` | usage billed after the fact |
| `deposit + balance` | two `money` values | part now, remainder on delivery or completion |
| `quote-required` | nothing | RFQ, and B2B contract pricing |

## 5.3 Money is minor units and a currency code, never a float

```
money = { 1 => int, 2 => currency }   ; minor_units, ISO 4217
```

This matters more inside `Consideration` than it would in an ordinary API, because a `Consideration`
value is either signed directly (inside a published `Offer`) or carried into a sealed `Order` whose
transitions are themselves signed (§18.3). A float invites a value like 19.999999999998 to enter
through a UI slider or a percentage calculation, and once that value is signed, the signature covers
the wrong number — there is no later step at which it can be corrected, only a new object that
supersedes the old one and a gap in between where the wrong figure was the authoritative one.
Integer minor units foreclose the error at the type: 1999 either is or is not what was meant, with
nothing in between for a rounding step to introduce.

## 5.4 Cross-currency arithmetic is refused, not coerced

A `money` value has one currency. Summing two `money` values with different currency codes requires
a conversion rate, and a rate is a claim about a moment in time that neither party necessarily agreed
was authoritative — unlike a price, which the seller signed directly. Converting one side and adding
therefore produces a total that looks exact and is not one either party actually committed to.
TRACT's position is that this arithmetic is refused rather than performed: a sum is only defined
across values sharing one currency, and this is why an `Order`'s `total` (§16.6) is a single `money`,
consistent with an order being scoped to one seller (§16.6, "one order per seller is a grammar-level
property") who is expected to quote consistently.

The grammar does not yet enforce this **within** a single `Consideration` value, and that is a real
gap rather than a settled point: `DepositBalance`'s two `money` fields, and each `PriceTier`'s
`unit_price`, each carry their own independent currency code. Nothing today rejects a deposit
denominated in one currency against a balance denominated in another, even though the two are
instalments of one price rather than two independent prices.

## 5.5 Tiered / volume pricing

`[+ PriceTier]` — at least one tier, each a `(min_qty, unit_price)` pair. The natural selection rule
is the tier with the greatest `min_qty` not exceeding the requested quantity, standard volume-pricing
practice. Two things the grammar does not currently pin down:

- **Ordering and duplicates.** `ProductRecord`'s attribute list is specified as sorted and
  deduplicated (§16.5.1); the `PriceTier` array carries no equivalent canonicalisation rule, so two
  tiers naming the same `min_qty` are not excluded and their relative order is not defined.
- **Coverage below the lowest tier.** `[+ PriceTier]` guarantees at least one entry, not one whose
  `min_qty` is 1 — a quantity below every published tier's threshold has no defined price.

## 5.6 Recurring — reusing §3's calendar machinery

`recurring` carries an amount and an RFC 5545 `RRULE`, the same standard §3.4 profiles for
availability, and for the same reason: a seller who already runs billing or calendar software
against RFC 5545 recurrence should not need a second schedule format to describe a subscription
period. The amount is fixed per period — a recurring charge that also varies by usage is `metered`
(§5.7), not `recurring`, and a trade needing both is two axes' worth of behaviour that this grammar
does not currently let one `Consideration` value express at once.

What is unresolved is how a recurring consideration interacts with §18.3's order state machine, which
runs one lifecycle from `draft` to a terminal state and does not loop. Whether each renewal period is
a fresh `Order` — reasonable, since `Order` is a lightweight sealed object and "was this specific
charge accepted" is naturally per-period — or one `Order` that somehow persists across periods is not
decided, and §18.3 as written does not describe a renewal path either way.

## 5.7 Metered

`metered` carries a dimension string (calls, kWh, gigabytes) and a unit price, billed after
consumption is known. Two consequences the grammar does not yet resolve:

- **No usage-attestation object exists.** §16.6 defines no object for reporting or disputing how much
  of the metered dimension was actually consumed, so the mechanism by which a metered charge's final
  figure gets attested by one party and verified — or contested — by the other is unspecified.
- **`Order.total` is mandatory, and a metered order's total is not knowable up front.** §16.6 defines
  `total` as key 4 with no `?` — it is required on every `Order`, placed at `draft`/`placed` time. A
  metered offer's actual charge is only known after fulfilment. Whether `total` for a metered order is
  an estimate, a cap, or whether metered consideration needs a different order shape entirely is open
  (§5.13).

## 5.8 Deposit + balance

Deposit payable at order, balance payable at delivery or completion — the shape a genuine
deposit-taking trade has, rather than modelling it as two unrelated fixed prices. It pairs naturally
with `ReturnRequired` fulfilment (§4.7): the deposit is the mechanism that makes a late-return or
damage claim on a rental whole, and §4.7 is explicit that condition and lateness are handled as an
order-level dispute, not as a fulfilment-axis field. §5.4 already flags that the grammar does not
require `deposit` and `balance` to share a currency, which is the sharpest instance of that gap.

## 5.9 Quote-required — RFQ and B2B contract pricing

`quote-required` carries nothing (`{ 8 => null }`): the published offer states only that no price is
published, and that a buyer must ask.

The mechanism does not need a new object type for the answer. A seller's response to a quote request
is an ordinary `Offer` — `Fixed`, `Tiered`, whatever consideration the seller actually wants to
charge this buyer — distributed differently from the rest of the catalogue: handed directly to the
requester's key rather than published in the open feed. This is exactly how B2B contract pricing
works under the same mechanism: a per-buyer price is nothing more than an `Offer` addressed to one
key instead of broadcast to all of them. No pricing-tier object, no buyer-group primitive — the
existing `Offer` grammar already expresses "this price, for you specifically" the moment its
distribution, not its shape, is restricted.

Two things this leaves unspecified:

- **The request itself has no defined wire shape.** A buyer asking for a quote is plausibly sealed —
  it may disclose volume or identity a seller would rather not publish an answer about openly — but
  §16.6 defines no such object today.
- **Nothing links a private per-buyer `Offer` back to the request that produced it.** Without that
  link, a buyer holding such an offer has no signed record of having asked for it, only of having
  received it.

## 5.10 Tax treatment categories belong here; tax rates do not

The offer carries a **treatment category** — standard-rated, zero-rated, exempt, reduced, and
whatever taxonomy a given regime uses — plus the anchors §11.2 derives, principally the place of
supply this axis's counterpart, §4, computes. It does not carry a **rate**. Rates change by
jurisdiction and by week; encoding one into a specification guarantees the specification ships stale
law the day a legislature changes a number. Rate lookup, keyed by treatment category, place of
supply, and the applicable date, is deliberately left to whatever source an implementation trusts —
a jurisdiction's published schedule, a commercial rate service — never to a table in this document.

Neither `Consideration` nor `Offer` currently has a field for the treatment category itself
(§16.5.2) — this section states the policy the grammar has not yet been given a slot to carry.

## 5.11 Currency conversion is a presentation concern

An offer's `money` is denominated in one currency, and that is the currency a resulting `Order`'s
`total` and any `PaymentAttestation` (§16.6) are bound to — the **settlement currency**. A storefront
or client may show a buyer a converted estimate in a currency they prefer while browsing, computed
live against whatever FX source that display layer trusts, and visibly marked as an estimate rather
than a price. That converted figure never becomes what gets signed; §5.4 and §16.7 are the same rule
applied at two different points — refused in arithmetic, estimated only in presentation.

## 5.12 Standards profiled

ISO 4217 currency codes. RFC 5545 recurrence rules, reusing §3's machinery rather than inventing a
second schedule format.

## 5.13 Open

- Whether `Consideration` values with more than one `money` field (`deposit + balance`, and each
  `PriceTier`'s `unit_price` against its neighbours) need a grammar-level rule requiring a shared
  currency (§5.4, §5.8).
- Whether `PriceTier` needs a canonical ordering rule and duplicate-`min_qty` rejection the way
  `ProductRecord`'s attributes have, and what a quantity below every published tier resolves to
  (§5.5).
- How a `recurring` consideration's renewal periods map onto §18.3's single-shot order lifecycle —
  fresh `Order` per period, or some other shape the state machine does not currently describe (§5.6).
- Whether `metered` consideration needs a usage-attestation object, and how a metered order satisfies
  `Order.total` as a mandatory field when the true amount is only known after consumption (§5.7).
- Whether a quote request needs a defined sealed wire shape, and whether a private per-buyer `Offer`
  needs a field linking it back to the request that produced it (§5.9).
- Where the tax treatment category is actually carried on the wire, given neither `Consideration` nor
  `Offer` has a field for it today (§5.10).
