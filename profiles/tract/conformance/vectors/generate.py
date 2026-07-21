#!/usr/bin/env python3
"""
TRACT §16 conformance vector generator/verifier — pure Python 3 stdlib, no dependencies.

WHY THIS FILE IS THE SOURCE OF TRUTH, NOT vectors/*.json
----------------------------------------------------------------------------------------------
conformance/README.md states the rule this script exists to obey: a vector is derived by
someone reading the specification text, never exported from a running implementation. This
script is that reading, made mechanical. Every encoder rule below cites the §16 sentence it
implements; every derived-value formula (billable weight, place of supply, route totals, escrow
scope intersection) cites the §16 / §4 / §9 text it comes from, including the places that text
is silent and this script has to say so rather than invent an answer.

This script does NOT import, link, shell out to, or read any output of Soko
(/Users/pc/code/vulos/soko). It does not compute a real content address or a real signature —
§16.2 states TRACT introduces no new hash construction, signature framing, or address scheme,
all four are inherited from the DMTAP substrate, and the substrate is out of scope here. Every
`content-address` / `identity-key` value below is a clearly-labelled placeholder byte string
(see `placeholder_bytes`), never something dressed up to look like a real one.

USAGE
----------------------------------------------------------------------------------------------
    python3 conformance/vectors/generate.py --write     # (re)write vectors/*.json from the
                                                           # definitions in this file
    python3 conformance/vectors/generate.py --verify     # re-derive every vector from the same
                                                           # definitions and diff against the
                                                           # committed JSON; nonzero exit on any
                                                           # mismatch
    python3 conformance/vectors/generate.py              # defaults to --verify

What --verify actually proves, and what it does not: it proves the checked-in JSON matches what
this script currently computes — it catches drift from a hand-edited JSON file or a refactor
that silently changed a formula. It does NOT prove this script agrees with an independent
implementation; nothing here does yet, because Soko must not be consulted to build this corpus
(see conformance/README.md and conformance/vectors/README.md). That second, load-bearing check
happens when Soko's own test suite re-derives these vectors independently and compares — a step
this repository does not perform.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

VECTORS_DIR = Path(__file__).resolve().parent

# ================================================================================================
# 1. Canonical CBOR encoder — RFC 8949 §4.2 deterministic-encoding subset, per §16.2:
#    "Deterministic CBOR (RFC 8949 §4.2). Integer-keyed maps, keys assigned per object type
#    from 1, keys >= 64 reserved for extension."
#
#    Rules implemented (the whole deterministic subset §16 needs, nothing more):
#      - definite-length only for byte strings, text strings, arrays and maps (RFC 8949 §4.2.1);
#      - every integer, and every length prefix, uses the SHORTEST possible encoding
#        (RFC 8949 §4.2.1's "preferred serialization" requirement folded into determinism);
#      - map keys are sorted by the bytewise lexicographic order of their OWN canonical encoding
#        (RFC 8949 §4.2.1). Every key used anywhere in §16's objects is a small non-negative
#        integer (1..9, plus a couple of 0-keyed union variants), so shortest-form encoding
#        keeps every key to a single byte and bytewise-lexicographic order coincides with plain
#        numeric order for all of them — there is no case in this corpus where the two orders
#        could diverge, and the encoder still sorts by encoded bytes rather than by raw Python
#        int, so it would not silently paper over a future key >= 24 if one is ever added.
# ================================================================================================


def _encode_head(major: int, n: int) -> bytes:
    """RFC 8949 §3.1 initial byte + shortest-form argument, for major type `major`."""
    if n < 0:
        raise ValueError("CBOR argument must be non-negative")
    if n < 24:
        return bytes([(major << 5) | n])
    if n < 2**8:
        return bytes([(major << 5) | 24, n])
    if n < 2**16:
        return bytes([(major << 5) | 25]) + n.to_bytes(2, "big")
    if n < 2**32:
        return bytes([(major << 5) | 26]) + n.to_bytes(4, "big")
    if n < 2**64:
        return bytes([(major << 5) | 27]) + n.to_bytes(8, "big")
    raise ValueError("integer exceeds CBOR's 64-bit argument range")


def cbor_encode(obj) -> bytes:
    """Canonically encode a native Python value as deterministic CBOR.

    Mapping from §16's CDDL primitives (§16.3) to Python:
      int   -> major type 0 (uint) if >= 0, else major type 1 (negative int)
      bytes -> major type 2 (byte string)   — `content-address`, `identity-key`
      str   -> major type 3 (text string, UTF-8)  — `tstr`
      list  -> major type 4 (array)         — `[* X]` / `[+ X]` productions
      dict  -> major type 5 (map), int keys — every `{ 1 => ..., 2 => ... }` object
      None  -> major type 7, simple value 22 (`null`)
    """
    if obj is None:
        return bytes([0xF6])
    if isinstance(obj, bool):
        # No §16 object defined so far uses a CBOR boolean; keeping this explicit means a
        # future vector that tries to use one fails loudly instead of being silently
        # miscoded as an integer (Python's bool is a subclass of int).
        raise TypeError("no §16 object uses a CBOR boolean; not implemented")
    if isinstance(obj, int):
        if obj >= 0:
            return _encode_head(0, obj)
        return _encode_head(1, -1 - obj)
    if isinstance(obj, bytes):
        return _encode_head(2, len(obj)) + obj
    if isinstance(obj, str):
        raw = obj.encode("utf-8")
        return _encode_head(3, len(raw)) + raw
    if isinstance(obj, list):
        out = _encode_head(4, len(obj))
        for item in obj:
            out += cbor_encode(item)
        return out
    if isinstance(obj, dict):
        encoded_items = [(cbor_encode(k), v) for k, v in obj.items()]
        encoded_items.sort(key=lambda pair: pair[0])  # RFC 8949 §4.2.1: sort by encoded key
        out = _encode_head(5, len(encoded_items))
        for k_bytes, v in encoded_items:
            out += k_bytes + cbor_encode(v)
        return out
    raise TypeError(f"unsupported type for canonical CBOR encoding: {type(obj)!r}")


# ================================================================================================
# 2. JSON <-> native round-trip.
#
#    JSON has no integer-keyed objects and no byte-string type, so vectors/*.json uses two
#    conventions, documented in vectors/README.md:
#      - every JSON object key is the decimal string form of the CDDL integer key it stands for
#        (e.g. "1" means map key 1, never text key "1");
#      - a CBOR byte string is written as {"__bytes__": "<hex>"} so it is never confused with a
#        CBOR text string, which is written as a plain JSON string.
# ================================================================================================

BYTES_MARKER = "__bytes__"


def to_jsonable(obj):
    """Convert a native value to a JSON-serialisable one. Note this is deliberately more
    permissive than `cbor_encode` (it passes plain `bool` through as a JSON boolean): it is used
    both for values that will be CBOR-encoded (which never include a bool, per `cbor_encode`'s
    own guard) and for plain computed JSON results (a `derived-value` / `structural-check`
    vector's `expected`, e.g. True/False for "does this offer decode"), which are ordinary JSON
    values with no CBOR encoding step at all.
    """
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, bytes):
        return {BYTES_MARKER: obj.hex()}
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    raise TypeError(f"unsupported type for JSON round-trip: {type(obj)!r}")


def from_jsonable(obj):
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, list):
        return [from_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        if set(obj.keys()) == {BYTES_MARKER}:
            return bytes.fromhex(obj[BYTES_MARKER])
        return {int(k): from_jsonable(v) for k, v in obj.items()}
    raise TypeError(f"unsupported type for JSON round-trip: {type(obj)!r}")


def placeholder_bytes(label: str, length: int = 32) -> bytes:
    """A deterministic, obviously-fake fixed-length byte string standing in for a
    `content-address` or `identity-key` (§16.3: both typed simply `bytes`).

    §16.2: "TRACT introduces no new hash construction, no new signature framing, and no new
    address scheme... A construction invented in this section is a defect." The multihash-style
    prefix + digest of a real content-address, and the real encoding of an identity key, are
    substrate-defined (§16.3's own comment: "substrate §18.1.5") and out of scope for this
    corpus. This function is deliberately NOT a hash of anything — hashing the label would
    invite exactly the misreading this docstring is warning against, that the result means
    something. It only needs to be *some* fixed-length byte string so the CBOR byte-string
    production (major type 2) is exercised faithfully. The label is embedded as ASCII, right
    padded with zero bytes, purely so a reader diffing hex can tell two placeholders apart at a
    glance.
    """
    raw = label.encode("ascii")
    if len(raw) > length:
        raise ValueError(f"label {label!r} does not fit in {length} placeholder bytes")
    return raw + bytes(length - len(raw))


# ================================================================================================
# 3. Derived-value formulas, each cited to the exact §16 / §4 / §9 text it implements.
# ================================================================================================


def volumetric_weight(l: int, w: int, h: int, dim_divisor: int) -> int:
    """§16.5.3 `RateCard.dim_divisor` comment: "billable = max(actual, L*W*H / divisor)".

    §16 states the formula but not a rounding rule for a non-exact division, and no other
    section read for this vector set (04-fulfilment.md, 08-delivery.md's cross-references)
    supplies one either. Rather than invent a rounding convention (ceiling? banker's rounding?
    truncation?) this function refuses non-exact division outright, and every vector built on
    top of it is chosen so the division is exact — the rounding question stays visibly open
    instead of being answered by fiat.
    """
    product = l * w * h
    if product % dim_divisor != 0:
        raise ValueError(
            "non-exact L*W*H/divisor division; §16 states the formula but not a rounding "
            "rule, and none is invented here — choose vector inputs where the division is exact"
        )
    return product // dim_divisor


def billable_weight(actual: int, l: int, w: int, h: int, dim_divisor: int) -> int:
    """§16.5.3: billable = max(actual, volumetric)."""
    return max(actual, volumetric_weight(l, w, h, dim_divisor))


def select_bracket(brackets: list[dict], billable: int) -> dict:
    """Pick the price for a billable weight against a RateCard `Zone`'s `[+ WeightBracket]`.

    §16.5.3 gives `WeightBracket = { 1 => uint, 2 => money }  ; max_grams, price` and nothing
    more explicit about lookup than the field name itself. The only reading that makes a list of
    (max_grams, price) pairs a usable tariff table — the shape every real-world weight-banded
    rate card uses — is: the applicable bracket is the one with the SMALLEST max_grams that is
    still >= the billable weight (i.e. the first boundary the shipment fits under). That reading
    is applied here and flagged as a reading, not quoted as if §16.5.3 spelled it out.
    """
    candidates = [b for b in brackets if b[1] >= billable]
    if not candidates:
        raise ValueError(
            "billable weight exceeds every bracket's max_grams; §16 does not state what "
            "happens past the top bracket (a surcharge? a rejected quote?), so this is left "
            "unresolved rather than guessed at — choose vector inputs within the top bracket"
        )
    return min(candidates, key=lambda b: b[1])


def route_total(legs: list[dict]) -> dict:
    """§16.7: "Arithmetic across currencies is refused, never coerced." — applied to summing a
    route's per-leg `money` totals (§16.5.3 RateCard pricing feeds §8.2's route total, cited by
    TRACT-DELIV-03). Same-currency legs sum directly; any currency mismatch is refused and the
    refusal is the returned value, never a silently-narrowed or silently-converted total.
    """
    # Each leg is represented as {2 => minor_units, 3 => currency} (see this vector's own
    # description for why those two keys specifically). Key 3 is the currency; key 2 the amount.
    currencies = {leg[3] for leg in legs}
    if len(currencies) > 1:
        return {
            "refused": True,
            "reason": (
                f"currency mismatch across legs: {sorted(currencies)} — §16.7: arithmetic "
                "across currencies is refused, never coerced; no conversion rate is invented"
            ),
        }
    total_minor_units = sum(leg[2] for leg in legs)
    return {
        "refused": False,
        "total": {1: total_minor_units, 2: currencies.pop()},
    }


# §4.3's place-of-supply derivation table, transcribed key-for-key:
#   ship              -> delivery destination (the ONE destination chosen on the order, not the
#                         Fulfilment object's whole `sell_to`-style destination list — §4.8: the
#                         buyer's choice "picks which offer — and therefore which anchor — the
#                         resulting order binds to")
#   collect            -> the stated place (PlaceRef.country)
#   perform-at-place    -> the stated place
#   return-required     -> the stated place
#   perform-remote       -> buyer residence
#   digital-grant        -> buyer residence
#   access-grant          -> the stated place, if named; otherwise buyer residence
FULFILMENT_SHIP = 0
FULFILMENT_COLLECT = 1
FULFILMENT_DIGITAL_GRANT = 2
FULFILMENT_PERFORM_AT_PLACE = 3
FULFILMENT_PERFORM_REMOTE = 4
FULFILMENT_ACCESS_GRANT = 5
FULFILMENT_RETURN_REQUIRED = 6


def place_of_supply(fulfilment: dict, *, buyer_residence: str, chosen_destination: str | None = None) -> str:
    """§4.3's derivation table, §16.5.2's "load-bearing detail" paragraph."""
    if FULFILMENT_SHIP in fulfilment:
        if chosen_destination is None:
            raise ValueError(
                "ship: place of supply is the destination recorded on the ORDER (§4.8), not "
                "derivable from the offer's destination list alone — pass chosen_destination"
            )
        if chosen_destination not in fulfilment[FULFILMENT_SHIP]:
            raise ValueError("chosen_destination is not one of the offer's declared destinations")
        return chosen_destination
    if FULFILMENT_COLLECT in fulfilment:
        return fulfilment[FULFILMENT_COLLECT][1]  # PlaceRef.country
    if FULFILMENT_DIGITAL_GRANT in fulfilment:
        return buyer_residence
    if FULFILMENT_PERFORM_AT_PLACE in fulfilment:
        return fulfilment[FULFILMENT_PERFORM_AT_PLACE][1]
    if FULFILMENT_PERFORM_REMOTE in fulfilment:
        return buyer_residence
    if FULFILMENT_ACCESS_GRANT in fulfilment:
        place = fulfilment[FULFILMENT_ACCESS_GRANT]
        return place[1] if place is not None else buyer_residence
    if FULFILMENT_RETURN_REQUIRED in fulfilment:
        return fulfilment[FULFILMENT_RETURN_REQUIRED][1]
    raise ValueError("unrecognised Fulfilment variant")


def escrow_scope_intersect(buyer: dict, gateway: dict) -> dict:
    """§9.4: "EscrowScope: buyer countries, seller countries, supply countries, currencies,
    rail classes, value ceiling, excluded categories, claimed authorisations." and
    "Fail-closed scope intersection at checkout, and the requirement that an empty intersection
    is disclosed rather than silently downgraded."

    §9.4 names which fields are intersected but not, for the two non-set-valued fields, what
    "intersect" means numerically. Two readings are applied here and flagged as readings, not
    quoted as text:
      - `max_order_value` (a single `money` ceiling, key 7): "intersecting" two ceilings is read
        as taking the MORE RESTRICTIVE one, i.e. min(buyer_ceiling, gateway_ceiling) — the same
        shape as intersecting two ranges [0, ceiling]. This is refused outright if the two
        ceilings are not in the same currency, per §16.7, rather than converted.
      - `excluded_categories` (key 8): a category is a subtractive constraint (excluded, not
        included), so the combined scope's exclusion set is read as the UNION of both scopes'
        exclusions — broader, not narrower, matching "excluded" being the operative word.
      - `authorities` (key 9, "claimed... prose, because regulators share no schema" per
        §16.5.4) is NOT intersected here: §9.4's own list of what gets intersected — countries,
        currencies, rail classes, value ceiling, excluded categories — does not include it, and
        prose claims are not a set with a defined intersection operator.
    An empty result on ANY of the five listed fields' comparable dimension is refused.
    """
    result: dict = {}
    empty_fields: list[str] = []

    for key, name in ((2, "buyer_countries"), (3, "seller_countries"), (4, "supply_countries"),
                       (5, "currencies"), (6, "rail_classes")):
        overlap = sorted(set(buyer[key]) & set(gateway[key]))
        if not overlap:
            empty_fields.append(name)
        result[key] = overlap

    buyer_ceiling, gateway_ceiling = buyer[7], gateway[7]
    if buyer_ceiling[2] != gateway_ceiling[2]:
        return {
            "refused": True,
            "reason": (
                f"max_order_value currencies differ ({buyer_ceiling[2]} vs {gateway_ceiling[2]}) "
                "— §16.7: arithmetic across currencies is refused, never coerced"
            ),
        }
    result[7] = {1: min(buyer_ceiling[1], gateway_ceiling[1]), 2: buyer_ceiling[2]}

    result[8] = sorted(set(buyer[8]) | set(gateway[8]))

    if empty_fields:
        return {
            "refused": True,
            "reason": (
                f"empty intersection on: {', '.join(empty_fields)} — §9.4: an empty intersection "
                "is refused and disclosed, never silently narrowed to whichever subset validates"
            ),
        }
    return {"refused": False, "scope": result}


# ================================================================================================
# 4. Structural checks (decode-time acceptance/rejection derived directly from §16 CDDL).
# ================================================================================================


def offer_declares_all_axes(offer: dict) -> bool:
    """§16.5.2: `Offer` keys 1-4 (Item, Availability, Fulfilment, Consideration) carry no `?` —
    all four are mandatory. TRACT-CAT-03."""
    return {1, 2, 3, 4}.issubset(offer.keys())


REVIEW_KNOWN_KEYS = {1, 2, 3, 4, 5, 6}


def review_rejects_unknown_keys(review: dict) -> bool:
    """§16.5.5 prose: "A review is the one public object signed by a natural person" (so, unlike
    `Offer` — whose signedness §16.8 leaves explicitly open — `Review`'s signed status is not in
    question). §16.2: "Signed objects reject unknown keys fail-closed." TRACT-PUBSEAL-03."""
    return set(review.keys()).issubset(REVIEW_KNOWN_KEYS)


def review_score_in_range(review: dict) -> bool:
    """§16.5.5: `Review` key 3 comment states "score, 0..5" directly."""
    return 0 <= review[3] <= 5


# ================================================================================================
# 5. Vector definitions. Each is built by a small function, read against the §16 text cited in
#    its own docstring/notes, returning a fully self-describing dict.
# ================================================================================================


def _case(name: str, note: str, **fields) -> dict:
    return {"name": name, "note": note, **fields}


def vec_money_basic() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-01",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.3",
        "title": "Money — canonical encoding",
        "kind": "cbor-encoding",
        "description": (
            "`money = { 1 => int, 2 => currency }` (§16.3). Three cases exercise the smallest, "
            "a two-byte, and a four-byte shortest-form integer encoding of `minor_units`, plus "
            "the fixed-length `currency` text string."
        ),
        "cases": [
            _case(
                "typical amount",
                "1999 minor units needs the 2-byte uint form (0x19 + big-endian u16, since "
                "255 < 1999 < 65536): head byte 0x19, then 0x07 0xCF (1999 = 0x07CF). Map has "
                "2 entries -> head 0xA2. Key 1 (0x01) sorts before key 2 (0x02). 'USD' is 3 "
                "ASCII bytes -> text-string head 0x63.",
                input={1: 1999, 2: "USD"},
            ),
            _case(
                "zero amount",
                "0 is the single-byte uint form (head byte 0x00 itself, no argument bytes) — "
                "the shortest-form rule, not a special case for zero.",
                input={1: 0, 2: "ZAR"},
            ),
            _case(
                "amount requiring 4-byte uint form",
                "100000000 (1e8) exceeds 65535, so it takes the 4-byte form: head byte 0x1A "
                "then 4 big-endian bytes (100000000 = 0x05F5E100).",
                input={1: 100000000, 2: "JPY"},
            ),
        ],
    }


def vec_placeref_basic() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-02",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.2",
        "title": "PlaceRef — canonical encoding",
        "kind": "cbor-encoding",
        "description": (
            "`PlaceRef = { 1 => country, 2 => tstr }` — country plus a coarse locality, "
            "explicitly never a street address (§16.4)."
        ),
        "cases": [
            _case(
                "venue example",
                "Two-entry map, keys already in ascending order (1, 2). `country` is a fixed "
                "2-byte ISO 3166-1 alpha-2 text string; `locality` is free text — note there is "
                "no third field this object COULD carry a street address in (§16.4).",
                input={1: "FR", 2: "Paris, 8th arrondissement"},
            ),
            _case(
                "pickup point example",
                "Same shape, different values, to show the encoding is not hard-coded to one "
                "string length.",
                input={1: "US", 2: "Springfield"},
            ),
        ],
    }


def vec_attribute_basic() -> dict:
    canonicalized = sorted(
        [("dpi", "1600"), ("color", "black")],
        key=lambda kv: (kv[0].casefold(), kv[1]),
    )
    return {
        "id": "TRACT-WIRE-VEC-03",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.1",
        "title": "Attribute — canonical encoding and the array-ordering rule's unambiguous slice",
        "kind": "cbor-encoding",
        "description": (
            "`Attribute = { 1 => tstr, 2 => tstr }` (key, value), and `ProductRecord` field 3 "
            "is commented '[* Attribute], attributes sorted, deduplicated, keys casefolded'. "
            "CBOR canonicalisation itself does not reorder ARRAY elements (only MAP keys, "
            "§16.2) — the sort is an application-level canonicalisation step that has to happen "
            "before encoding. This vector only covers the part of that rule the text pins down "
            "unambiguously: casefolded lexicographic order with NO key collision. §16.5.1 does "
            "not state a tie-break for two attributes that casefold to the same key (overwrite? "
            "keep both? keep first/last?), so that case is deliberately not attempted here — "
            "inventing a tie-break would be exactly the kind of gap-filling this corpus exists "
            "to avoid."
        ),
        "cases": [
            _case(
                "two attributes, published out of order",
                "Input order is [dpi, color]. Casefolded lexicographic order is "
                "'color' < 'dpi', so the canonical array is [color, dpi] — 'color' sorts first "
                "regardless of publication order. Each Attribute map encodes with key 1 before "
                "key 2 (already ascending).",
                input=[
                    {1: "dpi", 2: "1600"},
                    {1: "color", 2: "black"},
                ],
                canonical_order_input=[{1: k, 2: v} for k, v in canonicalized],
            ),
        ],
    }


def vec_identityrung_variants() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-04",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.1",
        "title": "IdentityRung — the three union variants, individually encoded",
        "kind": "cbor-encoding",
        "description": (
            "`IdentityRung = ContentAddressRung / ClaimedExternalRung / ManufacturerSignedRung`. "
            "The three are structurally disjoint by key-set alone: ContentAddressRung has only "
            "key 0; ManufacturerSignedRung has only key 2 (value type `identity-key`, i.e. CBOR "
            "byte string); ClaimedExternalRung has both keys 1 and 2 (value type `tstr`, i.e. "
            "CBOR text string) — so a decoder can disambiguate from map size plus the CBOR major "
            "type at key 2, with no extra tag needed. This vector does not attempt the "
            "'weakest first' ORDERING §16.5.1 field 4 asks for across a real ProductRecord's "
            "identity ladder — the text names which rung is weakest only by describing "
            "ClaimedExternalRung as 'a claim and nothing more... UNVERIFIED' (§16.5.1), and does "
            "not give a total order across all three, so composing a multi-rung ladder is left "
            "to a future vector rather than guessed at here."
        ),
        "cases": [
            _case(
                "ContentAddressRung",
                "Single-entry map, key 0, value is a placeholder content-address (32 bytes).",
                input={0: placeholder_bytes("contentaddr-rung")},
            ),
            _case(
                "ClaimedExternalRung",
                "Two-entry map, keys 1 (scheme, 'gtin') and 2 (value, the claimed GTIN as text) "
                "— both text strings, distinguishing this from ManufacturerSignedRung's single "
                "byte-string key 2.",
                input={1: "gtin", 2: "00012345678905"},
            ),
            _case(
                "ManufacturerSignedRung",
                "Single-entry map, key 2, value is a placeholder identity-key (32 bytes) — a "
                "CBOR byte string, not a text string, at the same key ClaimedExternalRung uses "
                "for a text value.",
                input={2: placeholder_bytes("brand-ik")},
            ),
        ],
    }


def vec_productrecord_basic() -> dict:
    attrs = [{1: "color", 2: "black"}, {1: "dpi", 2: "1600"}]  # already in canonical order
    return {
        "id": "TRACT-WIRE-VEC-05",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.1",
        "title": "ProductRecord — full object with optional fields present",
        "kind": "cbor-encoding",
        "description": (
            "`ProductRecord = { 1 => tstr, 2 => tstr, 3 => [* Attribute], 4 => [* IdentityRung], "
            "?5 => content-address, ?6 => [* content-address] }`. Exercises every field "
            "including the two optional ones (group, components)."
        ),
        "cases": [
            _case(
                "full record",
                "6-entry map, keys 1..6 already ascending. Field 3 is the pre-canonicalised "
                "attribute array from TRACT-WIRE-VEC-03 (color before dpi). Field 4 is a "
                "single-rung identity ladder (ClaimedExternalRung, from TRACT-WIRE-VEC-04) — "
                "kept to one rung to sidestep the unresolved 'weakest first' ordering across "
                "multiple rungs, same reasoning as TRACT-WIRE-VEC-04. Field 5 (group) and field "
                "6 (components, a 2-element array) are both placeholder content-addresses.",
                input={
                    1: "Wireless Optical Mouse",
                    2: "2.4GHz wireless optical mouse, 3 buttons, USB receiver",
                    3: attrs,
                    4: [{1: "gtin", 2: "00012345678905"}],
                    5: placeholder_bytes("product-group-addr"),
                    6: [placeholder_bytes("component-1-addr"), placeholder_bytes("component-2-addr")],
                },
            ),
            _case(
                "minimal record (optional fields absent)",
                "Only the mandatory keys 1-4 are present; fields 3 and 4 are present as EMPTY "
                "arrays (they are `[* X]`, zero-or-more, not optional fields — there is no `?` "
                "before keys 3 or 4 in §16.5.1's CDDL, unlike keys 5 and 6). 4-entry map.",
                input={1: "Unbranded Widget", 2: "", 3: [], 4: []},
            ),
        ],
    }


def vec_productrecord_canonical_order() -> dict:
    r1 = {
        1: "Wireless Optical Mouse",
        2: "2.4GHz wireless optical mouse",
        3: [{1: "color", 2: "black"}],
        4: [{1: "gtin", 2: "00012345678905"}],
    }
    # Same content, dict LITERALLY built with keys inserted in descending order, to prove the
    # canonical encoder — not incidental Python dict ordering — is what makes the bytes agree.
    r2 = {}
    for k in (4, 3, 2, 1):
        r2[k] = r1[k]
    r3_different = dict(r1)
    r3_different[2] = "a different description"
    return {
        "id": "TRACT-WIRE-VEC-06",
        "suite_ids": ["TRACT-CAT-01"],
        "coverage": "partial",
        "section": "§16.5.1, §2.2, §16.2",
        "title": "ProductRecord canonical-byte convergence and divergence (TRACT-CAT-01, partial)",
        "kind": "cbor-encoding",
        "description": (
            "TRACT-CAT-01 asserts that two independently-published ProductRecords converging on "
            "identical canonical bytes converge on the identical CONTENT ADDRESS, and that "
            "records differing before canonicalisation do not silently collide. The content "
            "address itself is `multihash-style prefix || digest` over those canonical bytes "
            "(§16.3, 'substrate §18.1.5') — the hash construction is substrate-defined and out "
            "of scope here (§16.2: TRACT introduces no new hash construction). What IS "
            "computable from §16 alone, and is the precondition the address-convergence claim "
            "depends on, is that canonical CBOR encoding is independent of the field-insertion "
            "order a publisher happened to use, and that a genuine content difference produces "
            "different bytes. This vector proves exactly that precondition, and no more — see "
            "vectors/README.md for why TRACT-CAT-01 is marked PARTIAL rather than covered."
        ),
        "cases": [
            _case(
                "same content, keys inserted ascending vs descending -> identical bytes",
                "r1's dict is built inserting keys 1,2,3,4 in that order; r2's dict is built "
                "inserting the SAME key/value pairs in order 4,3,2,1. Because the canonical "
                "encoder sorts map entries by encoded key before emitting them (§16.2), both "
                "produce byte-for-byte identical output regardless of how each dict was built.",
                input_a=r1,
                input_b=r2,
                expect_equal=True,
            ),
            _case(
                "different description -> different bytes",
                "r3 is r1 with field 2 (description) changed. The encoded map differs at the "
                "bytes for key 2's value, so the two outputs are NOT equal — a genuine content "
                "difference does not collide.",
                input_a=r1,
                input_b=r3_different,
                expect_equal=False,
            ),
        ],
    }


def vec_offer_item_variants() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-07",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.2",
        "title": "Offer.Item — the five union variants",
        "kind": "cbor-encoding",
        "description": "`Item` (§16.5.2): product / variant-of-group / service / right-licence / capacity.",
        "cases": [
            _case("product", "{0 => content-address}, single-entry map.",
                  input={0: placeholder_bytes("product-addr")}),
            _case("variant-of-group", "{1 => group content-address, 2 => variant content-address}.",
                  input={1: placeholder_bytes("group-addr"), 2: placeholder_bytes("variant-addr")}),
            _case("service", "{3 => content-address}.",
                  input={3: placeholder_bytes("service-addr")}),
            _case("right / licence", "{4 => content-address}.",
                  input={4: placeholder_bytes("licence-addr")}),
            _case("capacity", "{5 => content-address}.",
                  input={5: placeholder_bytes("capacity-addr")}),
        ],
    }


def vec_offer_availability_variants() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-08",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.2",
        "title": "Offer.Availability — StockSignal's 4 sub-variants plus Availability's other 4 variants",
        "kind": "cbor-encoding",
        "description": (
            "`Availability = {0=>StockSignal} / {1,2 time-slots} / {3,4 capacity-per-interval} / "
            "{5=>null unlimited} / {6=>uint made-to-order}`, and `StockSignal = {0=>uint} / "
            "{1=>null} / {2=>null} / {3=>null}` (exact / in-stock / low / out-of-stock)."
        ),
        "cases": [
            _case("stock: exact(42)", "Availability{0 => StockSignal{0 => 42}} — nested map, outer key 0, inner key 0.",
                  input={0: {0: 42}}),
            _case("stock: in-stock", "Availability{0 => StockSignal{1 => null}}.", input={0: {1: None}}),
            _case("stock: low", "Availability{0 => StockSignal{2 => null}}.", input={0: {2: None}}),
            _case("stock: out-of-stock", "Availability{0 => StockSignal{3 => null}}.", input={0: {3: None}}),
            _case("time-slots", "Availability{1 => RFC 5545 payload, 2 => slot minutes}.",
                  input={1: "FREQ=WEEKLY;BYDAY=MO,WE,FR", 2: 60}),
            _case("capacity-per-interval", "Availability{3 => capacity, 4 => RFC 5545 recurrence}.",
                  input={3: 20, 4: "FREQ=DAILY"}),
            _case("unlimited", "Availability{5 => null}.", input={5: None}),
            _case("made-to-order", "Availability{6 => lead days}.", input={6: 14}),
        ],
    }


def vec_offer_fulfilment_variants() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-09",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.2, §4.2",
        "title": "Offer.Fulfilment — all 7 variants (feeds TRACT-WIRE-VEC-13's place-of-supply derivation)",
        "kind": "cbor-encoding",
        "description": "`Fulfilment` (§16.5.2): ship / collect / digital-grant / perform-at-place / perform-remote / access-grant (x2) / return-required.",
        "cases": [
            _case("ship", "{0 => [* country]} — destinations SERVED (the offer-level set); the order-time chosen destination is a separate, order-level fact (§4.8, TRACT-WIRE-VEC-13).",
                  input={0: ["FR", "DE", "ZA"]}),
            _case("collect", "{1 => PlaceRef}.", input={1: {1: "US", 2: "Portland"}}),
            _case("digital-grant", "{2 => null}.", input={2: None}),
            _case("perform-at-place", "{3 => PlaceRef} — the venue.", input={3: {1: "FR", 2: "Cannes"}}),
            _case("perform-remote", "{4 => null}.", input={4: None}),
            _case("access-grant, with place", "{5 => PlaceRef}.", input={5: {1: "GB", 2: "London"}}),
            _case("access-grant, without place", "{5 => null}.", input={5: None}),
            _case("return-required", "{6 => PlaceRef, 7 => term days}.", input={6: {1: "JP", 2: "Osaka"}, 7: 30}),
        ],
    }


def vec_offer_consideration_variants() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-10",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.2",
        "title": "Offer.Consideration — all 6 variants, including the PriceTier array",
        "kind": "cbor-encoding",
        "description": "`Consideration` (§16.5.2): fixed / tiered / recurring / metered / deposit+balance / quote-required.",
        "cases": [
            _case("fixed", "{0 => money}.", input={0: {1: 2500, 2: "USD"}}),
            _case(
                "tiered / volume",
                "{1 => [+ PriceTier]}; `PriceTier = {1 => min_qty, 2 => unit_price}`. Array "
                "order here is the tier ordering as published — §16 does not state that tiers "
                "must be sorted by min_qty, only that the array is non-empty (`[+ ...]`), so "
                "this vector keeps them in ascending min_qty as the natural publication order "
                "without asserting that CBOR or the spec requires it.",
                input={1: [{1: 1, 2: {1: 1000, 2: "USD"}}, {1: 10, 2: {1: 900, 2: "USD"}}, {1: 100, 2: {1: 750, 2: "USD"}}]},
            ),
            _case("recurring", "{2 => money, 3 => RFC 5545 RRULE}.", input={2: {1: 999, 2: "USD"}, 3: "FREQ=MONTHLY;INTERVAL=1"}),
            _case("metered", "{4 => dimension, 5 => unit price}.", input={4: "api-calls", 5: {1: 1, 2: "USD"}}),
            _case("deposit + balance", "{6 => deposit money, 7 => balance money}.", input={6: {1: 5000, 2: "USD"}, 7: {1: 15000, 2: "USD"}}),
            _case("quote-required (RFQ)", "{8 => null}.", input={8: None}),
        ],
    }


def vec_offer_full_example() -> dict:
    offer = {
        1: {3: placeholder_bytes("haircut-service-addr")},  # Item: service
        2: {1: "FREQ=DAILY;BYHOUR=9,10,11,12,13,14,15,16", 2: 30},  # Availability: time-slots
        3: {3: {1: "FR", 2: "Paris, 8th arrondissement"}},  # Fulfilment: perform-at-place
        4: {0: {1: 4500, 2: "EUR"}},  # Consideration: fixed
        5: ["FR", "DE", "BE"],  # sell_to
        6: 1755000000000,  # published (ms epoch) — an arbitrary but plausible example instant
    }
    return {
        "id": "TRACT-WIRE-VEC-11",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.2",
        "title": "Offer — one complete object touching all four axes at once",
        "kind": "cbor-encoding",
        "description": (
            "A single realistic Offer (a hairdresser's appointment slot) exercising all six top-"
            "level keys together: Item (service), Availability (time-slots), Fulfilment "
            "(perform-at-place), Consideration (fixed), sell_to and published. This is the "
            "'Offer with each of the four axes' vector the task asked for as one worked example, "
            "distinct from TRACT-WIRE-VEC-07..10 which enumerate every variant of each axis in "
            "isolation."
        ),
        "cases": [
            _case(
                "haircut appointment offer",
                "6-entry map, keys 1-6 all present and already ascending. `published` (1755000000000 "
                "ms since epoch) needs the 8-byte uint form (0x1B) since it exceeds 2**32-1.",
                input=offer,
            ),
        ],
    }


def vec_offer_missing_axis_rejected() -> dict:
    valid_offer = {
        1: {3: placeholder_bytes("haircut-service-addr")},
        2: {1: "FREQ=DAILY", 2: 30},
        3: {3: {1: "FR", 2: "Cannes"}},
        4: {0: {1: 4500, 2: "EUR"}},
        5: ["FR"],
        6: 1755000000000,
    }
    missing_consideration = {k: v for k, v in valid_offer.items() if k != 4}
    return {
        "id": "TRACT-WIRE-VEC-12",
        "suite_ids": ["TRACT-CAT-03"],
        "coverage": "full",
        "section": "§16.5.2",
        "title": "Offer missing an axis is structurally rejected (TRACT-CAT-03)",
        "kind": "structural-check",
        "checker": "offer_declares_all_axes",
        "description": (
            "§16.5.2's CDDL gives `Offer` keys 1 (Item), 2 (Availability), 3 (Fulfilment), 4 "
            "(Consideration) with no `?` prefix on any of the four — all four are mandatory "
            "fields of the map production itself, not values that default when absent. "
            "TRACT-CAT-03 asserts exactly this: a partially-specified offer is rejected, not "
            "accepted with the missing axis defaulted."
        ),
        "cases": [
            _case(
                "all four axes present -> accepted",
                "Keys present: {1,2,3,4,5,6} ⊇ {1,2,3,4} — the mandatory set is satisfied.",
                input=valid_offer,
                expected=True,
            ),
            _case(
                "Consideration (key 4) absent -> rejected",
                "Keys present: {1,2,3,5,6} does NOT include 4 — the map does not match the "
                "`Offer` production at all; it is not 'a valid Offer with an empty price', "
                "there is no such thing to decode as, so decode must fail rather than proceed "
                "with a missing/defaulted Consideration.",
                input=missing_consideration,
                expected=False,
            ),
        ],
    }


def vec_ratecard_basic() -> dict:
    zone1 = {
        1: 1,
        2: [{1: 1000, 2: {1: 500, 2: "EUR"}}, {1: 5000, 2: {1: 900, 2: "EUR"}}, {1: 20000, 2: {1: 1800, 2: "EUR"}}],
        3: 3,
    }
    zone2 = {
        1: 2,
        2: [{1: 2000, 2: {1: 700, 2: "EUR"}}, {1: 10000, 2: {1: 1300, 2: "EUR"}}],
        3: 5,
    }
    return {
        "id": "TRACT-WIRE-VEC-14",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.3",
        "title": "RateCard — full object with two zones",
        "kind": "cbor-encoding",
        "description": (
            "`RateCard = {1=>identity-key, 2=>[*country], 3=>[*Zone], 4=>dim_divisor, "
            "5=>surcharge_pct, 6=>[*tstr] excluded_categories, 7=>ts}`; `Zone = {1=>id, "
            "2=>[+WeightBracket], 3=>transit_days}`; `WeightBracket = {1=>max_grams, 2=>money}`. "
            "`dim_divisor` here (5000) is this vector's own example calibration value, not a "
            "value §16 mandates — see TRACT-WIRE-VEC-15 for the formula that field feeds."
        ),
        "cases": [
            _case(
                "two-zone carrier rate card",
                "7-entry top-level map. Field 3 is a 2-element array of Zone maps, each a "
                "3-entry map whose field 2 is itself an array of WeightBracket maps (2-entry "
                "maps containing a nested `money` map) — three levels of map nesting, each "
                "canonically key-sorted independently.",
                input={
                    1: placeholder_bytes("carrier-ik"),
                    2: ["FR", "DE", "BE", "NL"],
                    3: [zone1, zone2],
                    4: 5000,
                    5: 3,
                    6: ["hazmat", "live-animals"],
                    7: 1755000000000,
                },
            ),
        ],
        "zone1_for_reuse": zone1,  # not part of the CBOR case; consumed by TRACT-WIRE-VEC-15
    }


def vec_delivery_billable_weight() -> dict:
    zone1_brackets = [(1000, 500), (5000, 900), (20000, 1800)]  # (max_grams, price minor units EUR) — mirrors TRACT-WIRE-VEC-14's zone1

    def bracket_case(name, note, actual, l, w, h, divisor):
        vw = volumetric_weight(l, w, h, divisor)
        bw = billable_weight(actual, l, w, h, divisor)
        # Price is represented here as a plain EUR minor-units integer (matching zone1's actual
        # 500/900/1800 values), not a nested `money` map — the nested-map encoding of
        # WeightBracket.price is already exercised by TRACT-WIRE-VEC-14; this vector is only
        # about the max()/bracket-selection arithmetic.
        bracket = select_bracket([{1: mg, 2: price} for mg, price in zone1_brackets], bw)
        return _case(
            name, note,
            input={"actual_grams": actual, "l_cm": l, "w_cm": w, "h_cm": h, "dim_divisor": divisor},
            expected={
                "volumetric_grams": vw,
                "billable_grams": bw,
                "selected_bracket_max_grams": bracket[1],
                "price_eur_minor_units": bracket[2],
            },
        )

    c1 = bracket_case(
        "actual weight dominates",
        "volumetric = 10*10*10 / 1000 = 1000/1000 = 1g (exact). billable = max(4000, 1) = "
        "4000g. Zone 1's brackets (max_grams, price EUR minor units) are (1000,500) (5000,900) "
        "(20000,1800); the smallest max_grams >= 4000 is 5000 -> price 900.",
        actual=4000, l=10, w=10, h=10, divisor=1000,
    )
    c2 = bracket_case(
        "volumetric weight dominates",
        "volumetric = 100*80*125 / 1000 = 1000000/1000 = 1000g (exact). billable = "
        "max(200, 1000) = 1000g. Smallest bracket max_grams >= 1000 is exactly 1000 -> price 500 "
        "(the boundary is inclusive under the >= rule stated in the `select_bracket` docstring).",
        actual=200, l=100, w=80, h=125, divisor=1000,
    )
    c3 = bracket_case(
        "tie — actual equals volumetric",
        "volumetric = 100*50*40 / 100 = 200000/100 = 2000g (exact), equal to actual (2000g). "
        "max(2000, 2000) = 2000g either way. Smallest bracket >= 2000 is 5000 -> price 900.",
        actual=2000, l=100, w=50, h=40, divisor=100,
    )
    return {
        "id": "TRACT-WIRE-VEC-15",
        "suite_ids": ["TRACT-DELIV-01"],
        "coverage": "full",
        "section": "§16.5.3, §4",
        "title": "Billable weight and local rate-card price lookup (TRACT-DELIV-01)",
        "kind": "derived-value",
        "formula": "billable_weight, select_bracket",
        "description": (
            "§16.5.3: 'dim_divisor — billable = max(actual, L*W*H / divisor)'. TRACT-DELIV-01 "
            "asserts a leg's price is computed LOCALLY from a published RateCard, without a "
            "live call to the carrier. All three cases reuse zone 1's brackets from "
            "TRACT-WIRE-VEC-14's RateCard example. Units: §16 does not pin L/W/H or dim_divisor "
            "to a length unit; every case here is constructed so L*W*H/divisor divides exactly, "
            "so the (open, unspecified) rounding question never has to be answered to check the "
            "arithmetic (see `volumetric_weight`'s docstring). `dim_divisor` is read as the "
            "carrier's own calibration constant that already lands the result in the same unit "
            "as `actual` and `WeightBracket.max_grams` (grams) — a real carrier's published "
            "divisor is exactly the free parameter that makes that true for its own cm/kg "
            "convention; nothing here asserts a specific real-world divisor value is standard."
        ),
        "cases": [c1, c2, c3],
    }


def vec_route_totals() -> dict:
    same_currency_legs = [{2: 1200, 3: "USD"}, {2: 850, 3: "USD"}]
    mixed_currency_legs = [{2: 1200, 3: "USD"}, {2: 700, 3: "EUR"}]
    r_same = route_total(same_currency_legs)
    r_mixed = route_total(mixed_currency_legs)
    return {
        "id": "TRACT-WIRE-VEC-16",
        "suite_ids": ["TRACT-DELIV-03"],
        "coverage": "full",
        "section": "§16.7, §8.2",
        "title": "Route totals — same-currency sum, mixed-currency refusal (TRACT-DELIV-03)",
        "kind": "derived-value",
        "formula": "route_total",
        "description": (
            "§16.7: 'Arithmetic across currencies is refused, never coerced. A silently "
            "converted total is a wrong total that looks right, and it gets carried into an "
            "order.' TRACT-DELIV-03 asserts exactly this at the route-total level: a mismatch "
            "is surfaced explicitly, never summed as if the units were the same. Each leg here "
            "is represented as {2 => minor_units, 3 => currency} for brevity (a leg's own full "
            "shape, e.g. carrier + zone + money, is not yet given a name in §16's text as read; "
            "only the money components that matter to this arithmetic are used)."
        ),
        "cases": [
            _case(
                "two legs, same currency -> summed",
                "1200 + 850 = 2050 minor units, both USD -> a single money total, no conversion "
                "needed or performed.",
                input=same_currency_legs,
                expected=r_same,
            ),
            _case(
                "two legs, different currencies -> refused",
                "USD and EUR cannot be summed into one `money` value (§16.3: money is ONE "
                "minor_units integer and ONE currency, not a multi-currency amount). Per §16.7 "
                "this is refused and disclosed as a refusal, not silently narrowed to one leg's "
                "currency or converted at an invented rate.",
                input=mixed_currency_legs,
                expected=r_mixed,
            ),
        ],
    }


def vec_fulfilment_place_of_supply() -> dict:
    seller_establishment = "ZA"  # constant across every case: the anchor must never leak to this
    buyer_residence = "DE"

    cases = []

    ship_fulfilment = {0: ["FR", "DE", "ZA"]}
    cases.append(_case(
        "ship — anchor is the ORDER's chosen destination, not the offer's whole destination list",
        f"§4.3: ship -> delivery destination. The Fulfilment object lists destinations SERVED "
        f"({ship_fulfilment[0]}); the actual anchor is whichever ONE the buyer chose on the "
        f"order (§4.8, TRACT-FULF-02) — here 'FR'. Seller establishment ({seller_establishment}) "
        f"and buyer residence ({buyer_residence}) play no role.",
        fulfilment=ship_fulfilment,
        chosen_destination="FR",
        expected=place_of_supply(ship_fulfilment, buyer_residence=buyer_residence, chosen_destination="FR"),
    ))

    collect_fulfilment = {1: {1: "IT", 2: "Milan"}}
    cases.append(_case(
        "collect — anchor is the stated place",
        "§4.3: collect -> the stated place. PlaceRef.country = 'IT', independent of "
        f"seller ({seller_establishment}) and buyer ({buyer_residence}).",
        fulfilment=collect_fulfilment,
        expected=place_of_supply(collect_fulfilment, buyer_residence=buyer_residence),
    ))

    digital_fulfilment = {2: None}
    cases.append(_case(
        "digital-grant — anchor is buyer residence",
        "§4.3: digital-grant -> buyer residence ('nothing physical happens anywhere'). "
        f"Anchor = '{buyer_residence}'.",
        fulfilment=digital_fulfilment,
        expected=place_of_supply(digital_fulfilment, buyer_residence=buyer_residence),
    ))

    perform_fulfilment = {3: {1: "FR", 2: "Cannes"}}
    cases.append(_case(
        "perform-at-place — THE §0.1/§4.3/§11.2 forcing example, verbatim (TRACT-FULF-01)",
        "The exact case TRACT-FULF-01 and §4.3 both cite: an event held in country C ('FR', "
        f"the venue), sold by a seller established in country A ('{seller_establishment}'), to "
        f"a buyer resident in country B ('{buyer_residence}'). Only the venue answers the place-"
        "of-supply question; neither party's country does. Anchor = 'FR', matching neither A "
        "nor B.",
        fulfilment=perform_fulfilment,
        expected=place_of_supply(perform_fulfilment, buyer_residence=buyer_residence),
    ))

    remote_fulfilment = {4: None}
    cases.append(_case(
        "perform-remote — anchor is buyer residence",
        f"§4.3: perform-remote -> buyer residence ('no physical venue to anchor to'). "
        f"Anchor = '{buyer_residence}'.",
        fulfilment=remote_fulfilment,
        expected=place_of_supply(remote_fulfilment, buyer_residence=buyer_residence),
    ))

    access_with_place = {5: {1: "GB", 2: "London"}}
    cases.append(_case(
        "access-grant, place named — anchor is that place",
        "§4.3: access-grant -> the stated place, if named. Anchor = 'GB'.",
        fulfilment=access_with_place,
        expected=place_of_supply(access_with_place, buyer_residence=buyer_residence),
    ))

    access_without_place = {5: None}
    cases.append(_case(
        "access-grant, no place named — anchor is buyer residence",
        f"§4.3: access-grant -> buyer residence, otherwise. Anchor = '{buyer_residence}'. Same "
        "Fulfilment variant (key 5) as the previous case, opposite anchor — 'the field name is "
        "shared by two economically different cases, and the anchor has to follow whichever one "
        "this instance actually is' (§4.3).",
        fulfilment=access_without_place,
        expected=place_of_supply(access_without_place, buyer_residence=buyer_residence),
    ))

    return_fulfilment = {6: {1: "JP", 2: "Osaka"}, 7: 30}
    cases.append(_case(
        "return-required — anchor is the stated place",
        "§4.3: return-required -> the stated place ('the same reasoning as collect — the item "
        "changes hands there'). Anchor = 'JP'; the term (30 days, key 7) does not affect the "
        "anchor.",
        fulfilment=return_fulfilment,
        expected=place_of_supply(return_fulfilment, buyer_residence=buyer_residence),
    ))

    return {
        "id": "TRACT-WIRE-VEC-13",
        "suite_ids": ["TRACT-FULF-01", "TRACT-FULF-02"],
        "coverage": "full",
        "section": "§4.3, §16.5.2",
        "title": "Place-of-supply derivation for all 7 Fulfilment variants (TRACT-FULF-01, TRACT-FULF-02)",
        "kind": "derived-value",
        "formula": "place_of_supply",
        "description": (
            "§4.3's derivation table, applied to every Fulfilment variant from "
            "TRACT-WIRE-VEC-09, with a constant seller establishment and buyer residence held "
            "across every case specifically so a reader can see the anchor is NEVER either of "
            "those two values except in the two variants §4.3 says should equal buyer "
            "residence. The 'ship' case additionally demonstrates TRACT-FULF-02: the anchor is "
            "bound only once the buyer's fulfilment choice (the one destination out of the "
            "offer's served list) is recorded on the order, per §4.8."
        ),
        "cases": cases,
        "seller_establishment": seller_establishment,
        "buyer_residence": buyer_residence,
    }


def vec_escrowscope_basic() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-17",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.5.4",
        "title": "EscrowScope — full object",
        "kind": "cbor-encoding",
        "description": "`EscrowScope` (§16.5.4): operator, 3 country lists, currencies, rail classes, value ceiling, excluded categories, claimed authorities.",
        "cases": [
            _case(
                "US/EU-facing operator scope",
                "9-entry map, keys 1-9 ascending. `rail_classes` (key 6) is `[* RailClass]` "
                "where `RailClass = 0 / 1` (§16.5.4) — plain small integers, not a nested map.",
                input={
                    1: placeholder_bytes("operator-ik"),
                    2: ["US", "CA"],
                    3: ["GB", "FR", "DE"],
                    4: ["US", "GB"],
                    5: ["USD", "EUR"],
                    6: [0, 1],
                    7: {1: 1000000, 2: "USD"},
                    8: ["weapons"],
                    9: ["MSB-registered-US", "EMI-licensed-EU"],
                },
            ),
        ],
    }


def vec_escrowscope_intersection() -> dict:
    buyer_scope = {
        2: ["US", "CA"], 3: ["GB", "DE"], 4: ["US"], 5: ["USD", "EUR"], 6: [0, 1],
        7: {1: 5000_00, 2: "USD"}, 8: ["weapons"],
    }
    gateway_scope = {
        2: ["US", "MX"], 3: ["GB", "FR"], 4: ["US", "GB"], 5: ["USD"], 6: [0],
        7: {1: 3000_00, 2: "USD"}, 8: ["alcohol"],
    }
    ok_result = escrow_scope_intersect(buyer_scope, gateway_scope)

    buyer_scope_empty = dict(buyer_scope)
    buyer_scope_empty[5] = ["USD"]
    gateway_scope_empty = dict(gateway_scope)
    gateway_scope_empty[5] = ["EUR"]
    empty_result = escrow_scope_intersect(buyer_scope_empty, gateway_scope_empty)

    return {
        "id": "TRACT-WIRE-VEC-18",
        "suite_ids": ["TRACT-SETTLE-01"],
        "coverage": "partial",
        "section": "§9.4, §16.5.4",
        "title": "EscrowScope checkout intersection — success and empty-intersection refusal (TRACT-SETTLE-01, partial)",
        "kind": "derived-value",
        "formula": "escrow_scope_intersect",
        "description": (
            "§9.4: 'Fail-closed scope intersection at checkout, and the requirement that an "
            "empty intersection is disclosed rather than silently downgraded', over the exact "
            "fields §16.5.4 defines. §9.4 names WHICH fields intersect but not, for the two "
            "non-set fields, what intersecting them numerically means — this vector applies the "
            "reading documented in `escrow_scope_intersect`'s docstring (value ceiling: "
            "narrower/min; excluded categories: union) and is marked PARTIAL because that "
            "reading is necessary-but-unstated, not quoted spec text. What IS textually direct: "
            "the five set-valued fields intersect as literal set intersection, and an empty "
            "result on any of them is refused rather than narrowed to whatever validates."
        ),
        "cases": [
            _case(
                "compatible scopes -> intersection succeeds",
                "buyer_countries {US,CA}∩{US,MX}={US}; seller_countries {GB,DE}∩{GB,FR}={GB}; "
                "supply_countries {US}∩{US,GB}={US}; currencies {USD,EUR}∩{USD}={USD}; "
                "rail_classes {0,1}∩{0}={0}; value ceiling both USD -> min(5000.00,3000.00)="
                "3000.00 USD; excluded_categories union {weapons}∪{alcohol}={alcohol,weapons}. "
                "No field intersects to empty -> disclosed as a successful, narrower scope.",
                input={"buyer_scope": buyer_scope, "gateway_scope": gateway_scope},
                expected=ok_result,
            ),
            _case(
                "disjoint currencies -> refused",
                "buyer offers only USD, gateway offers only EUR -> currencies intersect to the "
                "empty set. Per §9.4 this is refused and disclosed as a refusal outright — the "
                "other four fields' overlap is irrelevant once one field is empty; it is never "
                "narrowed to 'proceed without currency agreement'.",
                input={"buyer_scope": buyer_scope_empty, "gateway_scope": gateway_scope_empty},
                expected=empty_result,
            ),
        ],
    }


def vec_order_basic() -> dict:
    seller_ik = placeholder_bytes("seller-ik")
    order = {
        1: placeholder_bytes("buyer-ik"),
        2: seller_ik,
        3: [
            {1: placeholder_bytes("offer-1-addr"), 2: seller_ik, 3: 2},
            {1: placeholder_bytes("offer-2-addr"), 2: seller_ik, 3: 1},
        ],
        4: {1: 8000, 2: "EUR"},
        5: 1,  # placed
        6: 1755000000000,
    }
    return {
        "id": "TRACT-WIRE-VEC-19",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.6",
        "title": "Order — sealed object, two lines, one seller",
        "kind": "cbor-encoding",
        "description": (
            "`Order = {1=>buyer, 2=>seller, 3=>[+OrderLine], 4=>total money, 5=>OrderState, "
            "6=>placed ts}`; `OrderLine = {1=>offer content-address, 2=>seller identity-key, "
            "3=>quantity}`. §16.6: 'Order names a single seller and carries only that seller's "
            "lines' — both order lines' key-2 seller value equals the Order's own key-2 seller, "
            "demonstrating the one-seller-per-order shape rather than asserting a rule the "
            "encoder itself enforces (nothing in the CDDL forces the two to match; that is a "
            "semantic invariant, noted here rather than silently assumed)."
        ),
        "cases": [
            _case(
                "two-line order, state=placed(1)",
                "6-entry top-level map; field 3 is a 2-element array of OrderLine (3-entry) "
                "maps. `OrderState` (key 5) is the plain integer 1 ('placed', §16.6's ordering: "
                "0=draft/1=placed/2=accepted/.../8=cancelled).",
                input=order,
            ),
        ],
    }


def vec_paymentattestation_basic() -> dict:
    return {
        "id": "TRACT-WIRE-VEC-20",
        "suite_ids": [],
        "coverage": None,
        "section": "§16.6",
        "title": "PaymentAttestation — canonical encoding",
        "kind": "cbor-encoding",
        "description": (
            "`PaymentAttestation = {1=>payer, 2=>payee, 3=>order content-address, 4=>money, "
            "5=>RailClass, 6=>opaque external reference, 7=>ts}`. §16.6: 'carries a reference, "
            "never funds and never card data.'"
        ),
        "cases": [
            _case(
                "custodial-reversible rail attestation",
                "7-entry map, keys 1-7 ascending. `RailClass` (key 5) is the plain integer 0 "
                "(custodial-reversible, §16.5.4). Key 6 is an opaque external settlement "
                "reference — just a `tstr`, not parsed or validated by the wire format.",
                input={
                    1: placeholder_bytes("payer-ik"),
                    2: placeholder_bytes("payee-ik"),
                    3: placeholder_bytes("order-addr"),
                    4: {1: 4500, 2: "EUR"},
                    5: 0,
                    6: "stripe:pi_3Nx000000000000opaque",
                    7: 1755000000000,
                },
            ),
        ],
    }


def vec_review_bounded_fields() -> dict:
    valid_review = {
        1: {0: placeholder_bytes("product-addr")},  # Subject: product
        2: placeholder_bytes("author-per-subject-subkey"),
        3: 4,
        4: "Fast shipping, exactly as described.",
        5: {1: 0, 2: placeholder_bytes("seller-ik"), 3: placeholder_bytes("order-addr"), 4: 1754990000000},
        6: 1755000000000,
    }
    review_with_smuggled_key = dict(valid_review)
    review_with_smuggled_key[7] = "123 Main St, Springfield"  # an attempted personal-data smuggle
    review_score_out_of_range = dict(valid_review)
    review_score_out_of_range[3] = 7

    return {
        "id": "TRACT-WIRE-VEC-21",
        "suite_ids": ["TRACT-PUBSEAL-03"],
        "coverage": "full",
        "section": "§16.5.5, §16.2, §0.5.1",
        "title": "Review — closed field set and score bound (TRACT-PUBSEAL-03)",
        "kind": "structural-check",
        "checker": "review_rejects_unknown_keys / review_score_in_range",
        "description": (
            "TRACT-PUBSEAL-03: 'a Review is rejected if it carries any field outside the "
            "bounded set §10.4 permits'. §16.5.5 gives Review's CDDL as exactly keys 1-6 with "
            "no address/contact production anywhere in it, and its own prose confirms (unlike "
            "Offer, whose signed status §16.8 leaves open) that 'a review is the one public "
            "object signed by a natural person' — so §16.2's 'signed objects reject unknown "
            "keys fail-closed' applies unambiguously. This is the one PUBSEAL-family case this "
            "corpus can cover without inventing semantic personal-data classification or "
            "resolving an open question — see vectors/README.md for TRACT-PUBSEAL-01/02/04, "
            "which are NOT covered and why."
        ),
        "cases": [
            _case(
                "valid review -> accepted",
                "Keys {1,2,3,4,5,6} ⊆ the known set {1,2,3,4,5,6}; score 4 is within 0..5.",
                input=valid_review,
                expected={"rejects_unknown_keys_check": True, "score_in_range_check": True},
            ),
            _case(
                "extra key 7 (an attempted address smuggle) -> rejected",
                "Keys {1..7} is NOT a subset of {1..6}; key 7 is unknown to the Review "
                "production. Per §16.2 a signed object rejects this on decode — the smuggled "
                "'123 Main St, Springfield' string never has a field to occupy in the first "
                "place. (§16.5.5 already notes body/tstr fields remain free text a person could "
                "still type an address into — this vector is only about the KEY-level smuggle, "
                "not that separate, acknowledged-open gap.)",
                input=review_with_smuggled_key,
                expected={"rejects_unknown_keys_check": False},
            ),
            _case(
                "score 7 (out of 0..5) -> rejected",
                "§16.5.5: 'score, 0..5' stated directly in the CDDL comment. 7 > 5.",
                input=review_score_out_of_range,
                expected={"score_in_range_check": False},
            ),
        ],
    }


VECTOR_BUILDERS = [
    vec_money_basic,
    vec_placeref_basic,
    vec_attribute_basic,
    vec_identityrung_variants,
    vec_productrecord_basic,
    vec_productrecord_canonical_order,
    vec_offer_item_variants,
    vec_offer_availability_variants,
    vec_offer_fulfilment_variants,
    vec_offer_consideration_variants,
    vec_offer_full_example,
    vec_offer_missing_axis_rejected,
    vec_fulfilment_place_of_supply,
    vec_ratecard_basic,
    vec_delivery_billable_weight,
    vec_route_totals,
    vec_escrowscope_basic,
    vec_escrowscope_intersection,
    vec_order_basic,
    vec_review_bounded_fields,
    vec_paymentattestation_basic,
]


# ================================================================================================
# 6. Rendering to / from the JSON on disk.
# ================================================================================================


def _filename_for(vector: dict) -> str:
    slug = vector["title"].split("—")[0].strip().lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in slug)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") + ".json"


def render_vector(vector: dict) -> dict:
    """Turn a native-Python vector definition into the JSON-serialisable document written to
    disk, computing every expected value (hex or derived) at render time so the JSON always
    carries a value alongside the formula that produced it."""
    out = {
        "id": vector["id"],
        "suite_ids": vector["suite_ids"],
        "coverage": vector["coverage"],
        "section": vector["section"],
        "title": vector["title"],
        "kind": vector["kind"],
        "description": vector["description"],
    }
    if "formula" in vector:
        out["formula"] = vector["formula"]
    if "checker" in vector:
        out["checker"] = vector["checker"]

    cases_out = []
    for case in vector["cases"]:
        c_out = {"name": case["name"], "note": case["note"]}
        if vector["kind"] == "cbor-encoding":
            if "input" in case:
                c_out["input"] = to_jsonable(case["input"])
                c_out["expected_hex"] = cbor_encode(case["input"]).hex()
            else:
                # comparison case: input_a / input_b (+ expect_equal)
                c_out["input_a"] = to_jsonable(case["input_a"])
                c_out["input_b"] = to_jsonable(case["input_b"])
                c_out["expected_hex_a"] = cbor_encode(case["input_a"]).hex()
                c_out["expected_hex_b"] = cbor_encode(case["input_b"]).hex()
                c_out["expect_equal"] = case["expect_equal"]
            if "canonical_order_input" in case:
                c_out["canonical_order_input"] = to_jsonable(case["canonical_order_input"])
                c_out["canonical_order_expected_hex"] = cbor_encode(case["canonical_order_input"]).hex()
        elif vector["kind"] in ("derived-value", "structural-check"):
            if "input" in case:
                c_out["input"] = to_jsonable(case["input"])
            else:
                # Some derived-value cases pass their inputs as several named fields (e.g.
                # `fulfilment=`, `chosen_destination=`) rather than one `input=` blob, because
                # that reads more clearly next to the §4.3 table being exercised. Collect
                # whatever isn't `name`/`note`/`expected` into the rendered "input".
                extra = {k: v for k, v in case.items() if k not in ("name", "note", "expected")}
                c_out["input"] = to_jsonable(extra)
            c_out["expected"] = to_jsonable(case["expected"])
        else:
            raise ValueError(f"unknown vector kind {vector['kind']!r}")
        cases_out.append(c_out)
    out["cases"] = cases_out
    return out


def write_all() -> list[Path]:
    written = []
    for builder in VECTOR_BUILDERS:
        vector = builder()
        doc = render_vector(vector)
        path = VECTORS_DIR / _filename_for(vector)
        path.write_text(json.dumps(doc, indent=2, sort_keys=False, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(path)
    return written


# ================================================================================================
# 7. Verification: recompute everything and diff against the committed JSON.
# ================================================================================================


def verify_all() -> bool:
    ok = True
    seen_ids = set()
    seen_files = set()

    for builder in VECTOR_BUILDERS:
        vector = builder()
        expected_doc = render_vector(vector)
        path = VECTORS_DIR / _filename_for(vector)
        seen_files.add(path.name)

        if vector["id"] in seen_ids:
            print(f"FAIL  duplicate vector id: {vector['id']}")
            ok = False
        seen_ids.add(vector["id"])

        if not path.exists():
            print(f"FAIL  {path.name}: missing on disk (run --write)")
            ok = False
            continue

        on_disk = json.loads(path.read_text(encoding="utf-8"))
        if on_disk != expected_doc:
            print(f"FAIL  {path.name}: on-disk JSON does not match what generate.py currently computes")
            ok = False
            continue

        # Independent re-check per case, re-deriving from native values rather than trusting the
        # JSON round-trip alone.
        for case in vector["cases"]:
            if vector["kind"] == "cbor-encoding":
                if "input" in case:
                    got = cbor_encode(from_jsonable(to_jsonable(case["input"]))).hex()
                    want = cbor_encode(case["input"]).hex()
                    if got != want:
                        print(f"FAIL  {path.name} / {case['name']}: hex mismatch after JSON round-trip")
                        ok = False
                else:
                    hex_a = cbor_encode(case["input_a"]).hex()
                    hex_b = cbor_encode(case["input_b"]).hex()
                    if (hex_a == hex_b) != case["expect_equal"]:
                        print(f"FAIL  {path.name} / {case['name']}: expect_equal={case['expect_equal']} but equality was {hex_a == hex_b}")
                        ok = False
            elif vector["kind"] == "structural-check":
                if vector["id"] == "TRACT-WIRE-VEC-12":
                    got = offer_declares_all_axes(case["input"])
                    if got != case["expected"]:
                        print(f"FAIL  {path.name} / {case['name']}: offer_declares_all_axes={got}, expected {case['expected']}")
                        ok = False
                elif vector["id"] == "TRACT-WIRE-VEC-21":
                    exp = case["expected"]
                    if "rejects_unknown_keys_check" in exp:
                        got = review_rejects_unknown_keys(case["input"])
                        if got != exp["rejects_unknown_keys_check"]:
                            print(f"FAIL  {path.name} / {case['name']}: review_rejects_unknown_keys={got}, expected {exp['rejects_unknown_keys_check']}")
                            ok = False
                    if "score_in_range_check" in exp:
                        got = review_score_in_range(case["input"])
                        if got != exp["score_in_range_check"]:
                            print(f"FAIL  {path.name} / {case['name']}: review_score_in_range={got}, expected {exp['score_in_range_check']}")
                            ok = False
            # derived-value cases are already fully checked by the expected_doc == on_disk
            # comparison above (their "expected" field is computed by the same formula both
            # times); nothing further to recompute independently without a second implementation.

    extra_files = {p.name for p in VECTORS_DIR.glob("*.json")} - seen_files
    for name in sorted(extra_files):
        print(f"FAIL  {name}: present on disk but no longer produced by any vector builder (stale file?)")
        ok = False

    if ok:
        print(f"OK    {len(seen_ids)} vector file(s) verified against generate.py's definitions")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="(re)write vectors/*.json")
    parser.add_argument("--verify", action="store_true", help="verify vectors/*.json against this script (default)")
    args = parser.parse_args()

    if args.write:
        written = write_all()
        print(f"wrote {len(written)} vector file(s)")
        return 0

    return 0 if verify_all() else 1


if __name__ == "__main__":
    sys.exit(main())
