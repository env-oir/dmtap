# 3. Availability

> **Drafting status.** This section is scoped but not yet normative. It states what it will
> specify, which existing standards it profiles, and the decisions still open. Nothing here is
> implementable yet; text becomes normative when the RFC 2119 keywords appear.

## 3.1 Scope

The first of the four offer axes: when a thing is available, and how much of it there is. §16.5.2
already defines the grammar; this section is the reasoning behind each variant and the rule for
evaluating one.

## 3.2 Variants

| Variant | Carries (§16.5.2) | Covers |
|---|---|---|
| `count` | a `StockSignal` band | physical or digital stock, exact or banded |
| `time-slots` | an RFC 5545 payload, slot length in minutes | bookable appointments |
| `capacity-per-interval` | a capacity number, an RFC 5545 recurrence | seats, tables, room-nights |
| `unlimited` | nothing | digital goods with no bound |
| `made-to-order` | lead days | built or provisioned after the order, not held in stock |

Five variants, one grammar. A haircut and a restaurant table are both bookable, but a haircut
consumes an appointment slot and a table seats a party against a nightly cap — `time-slots` and
`capacity-per-interval` are distinct variants because those are different questions, not the same
question asked twice.

## 3.3 The stock signal is a band, not a number

```
StockSignal = exact(n) / in-stock / low / out-of-stock
```

A seller may publish `exact(n)` when it chooses to, but the count variant does not require it, for
two reasons that both matter:

- **Exact stock is commercially sensitive.** A competitor watching a public feed can infer sell-through
  rate, restock cadence, and even unit economics from a bare number changing over time. Browsing a
  catalogue does not need that number; it needs to know whether the thing can be bought.
- **A band degrades honestly; an exact number degrades into a lie.** Stock moves between publishes.
  `in-stock` stays true across a wide range of underlying counts, so it survives the gap between one
  publish and the next. `exact(4)` is precisely correct at the moment it is signed and increasingly
  wrong afterwards — and it is wrong with the same apparent confidence throughout. A band's
  imprecision is disclosed by its shape; a stale exact count's imprecision is not disclosed at all.

`out-of-stock` and `low` are distinct from each other for the same reason `made-to-order` is
distinct from `out-of-stock` (§3.6): a buyer deciding whether to add something to a cart needs to
know whether waiting a moment might work, not just whether it works right now.

## 3.4 Time slots — profiling RFC 5545

`time-slots` carries an opaque RFC 5545 payload (`VAVAILABILITY` / `VFREEBUSY`) plus a slot length
in minutes, rather than a bespoke schedule grammar. The reasoning is the same one §5.6 makes for
recurring consideration: a seller who already runs calendar software should publish from it
directly, not maintain a second, TRACT-specific source of truth that drifts out of sync with the
first.

The buyer's node parses the payload locally against the slot length to enumerate candidate slots —
there is no slot-listing endpoint to call. What the payload cannot express is which slots other
buyers have since taken; §3.9 covers why that is a staleness problem, not a grammar problem.

## 3.5 Capacity per interval

`capacity-per-interval` carries a unit count and an RFC 5545 recurrence describing the intervals it
applies to — 40 covers per sitting, three sittings a night. This is not `time-slots` with a number
attached: a time slot is claimed whole by one booking, where a capacity interval is shared by many
bookings up to its cap. Modelling a restaurant table as a time slot would force one party to occupy
the whole sitting; modelling a haircut as capacity-per-interval would allow two people to book the
same ten minutes.

## 3.6 Made-to-order is not out-of-stock

`made-to-order` carries a lead-time figure and nothing else — no stock number, no slot, no capacity,
because none of those describe it. The thing is available. It simply is not sitting in a warehouse
yet, and that is a different fact from having none.

Conflating the two is why lead-time products display badly on retail platforms built around a stock
count: a made-to-measure suit or a build-to-order machine gets forced into `in stock` (wrong — it
does not exist yet) or `out of stock` (wrong — it is buyable right now, just not instantly). Neither
label is honest, and a buyer who wanted to know "how long" was never asked the right question.
`made-to-order` exists so that question has a field.

§19.2's `FULFIL_TIMEOUT` reads this figure directly: it cannot be one protocol-wide number because
a made-to-order lead time and an instant digital grant have nothing in common, so the availability
axis supplies the floor a buyer may expect to wait before cancelling becomes reasonable, rather than
the protocol asserting a duration it cannot know.

Whether the lead-time figure is counted in calendar days or working days is not settled by the
grammar — see §3.12.

## 3.7 Evaluating availability locally

The buyer's node does this work; nothing is queried live.

| Variant | Local evaluation |
|---|---|
| `count` | compare the requested quantity against the band. `exact(n)` supports an exact check; `in-stock` / `low` support only "probably yes, ask to be sure"; `out-of-stock` blocks the add. |
| `time-slots` | expand the RFC 5545 payload against the slot length into candidate slots and present them. |
| `capacity-per-interval` | expand the recurrence into intervals and show the published cap per interval — not how much of the cap is already taken by other buyers. |
| `unlimited` | nothing to evaluate. |
| `made-to-order` | add the lead days to the order date to show an expected dispatch date, feeding §19.2's `FULFIL_TIMEOUT` floor. |

None of this evaluation contacts the seller. That is the point of publishing the object at all —
but it also means every row above is read from whatever copy of the offer the buyer's node last
fetched, which is the subject of §3.9.

## 3.8 What happens when published availability is stale

An `Offer` carries one freshness signal: its own `published` timestamp (§16.5.2, key 6).
Availability has no timestamp of its own — a stale `Offer` and a stale `Availability` are the same
event, because they are the same object. There is no push notification for an availability change
specifically; substrate capability ⑤ wakes a seller's node for incoming orders, not a buyer's node
for outgoing price or stock changes. Freshness is bounded only by how often the buyer's client
re-fetches the seller's feed, no more often than `FEED_POLL_MIN` (§19.6) but with no upper bound the
protocol enforces.

The consequence: a buyer can add something to a cart that sold out between the last fetch and now.
This is not treated as a protocol defect to be engineered away — §3.3's whole argument is that a
band already discloses this uncertainty rather than hiding it. What resolves the gap is not a
tighter poll interval; it is that the seller's `placed → accepted / declined` step (§18.3) is
authoritative and the browsing-time signal is not. An offer that turned out to be wrong is declined
there, explicitly, rather than silently honoured against stock that no longer exists.

## 3.9 A signal, not a reservation

Nothing in this section commits stock. `Availability` is what a seller publishes and what a buyer's
node reads to decide whether adding something to a cart is worth attempting — it is input to a
decision, not a hold on the outcome.

§6 is where a hold actually exists: a seller's bounded-counter inventory (§6.2, §6.2a) is what
guarantees that concurrent sales never exceed real stock, and it operates beneath what gets
published here. A buyer's node never sees counter state directly, only the band this section
defines. Reading `Availability` as a reservation would be a category error in both directions — it
would credit the band with a guarantee only the counter provides, and it would blame the band for a
staleness gap that the counter, not the signal, is responsible for closing.

## 3.10 Standards profiled

RFC 5545 `VAVAILABILITY` / `VFREEBUSY` for `time-slots`; RFC 5545 recurrence rules for
`capacity-per-interval`'s interval definition. Time zones per RFC 5545 / IANA tzdata.

## 3.11 Open

- Whether published availability bands need a normative vocabulary or stay seller-defined.
- Whether `Availability` needs its own freshness parameter, distinct from the offer's `published`
  timestamp and from `RateCard`'s `RATE_CARD_MAX_AGE` (§19.6) — stock and slots plausibly move much
  faster than price, and currently nothing distinguishes "this offer is a day old" from "this stock
  band is a day old" because they are the same field.
- Whether `made-to-order` lead days are calendar days or working days. The reference implementation
  documents working days; the grammar carries a bare integer and does not encode the distinction.
- Whether the capacity number in `capacity-per-interval` is meant to be read as remaining capacity
  or total capacity once bookings exist against an interval — the same signal-versus-reservation
  question as `count`, unresolved for this variant specifically.
