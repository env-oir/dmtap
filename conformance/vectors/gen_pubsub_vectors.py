#!/usr/bin/env python3
"""
gen_pubsub_vectors.py — generates conformance/vectors/pubsub_vectors.json

Throwaway, deterministic vector generator for the DMTAP-PUBSUB extension (spec §25),
independent of the dmtap-core reference crate — exactly the provenance model
gen_pub_vectors.py already uses for §22/§23 (see that script's docstring and this
repo's README.md "Provenance" section): the bytes here are produced from the
specification text alone (BLAKE3-256 + Ed25519, both deterministic, no reference
implementation required), so the Envoir conformance-runner's cross-check against
dmtap_core::pubsub is an INDEPENDENT check on that crate, not a restatement of it.

Why this file exists at all: §25.13 C-03 documents that an earlier revision of
`Subscription.subscription_id` (§25.4.1) was computed over the *complete signed
object* (`0x1e || BLAKE3-256(det_cbor(Subscription))`, by analogy to `announce_id`).
§1.3 forbids exactly that construction — no identifier may be derived from a
signature — because a valid `sig` can be maulable into a different valid signature
over the same body, and an id that moves with `sig` lets a mauled (or merely
differently-encoded) copy of one Subscription escape a SubscriptionRevoke naming the
original: a revocation bypass, and a double-count against the §25.7.1 aggregate quota.
The fixed formula is body-only and DS-tagged:

    subscription_id = 0x1e || BLAKE3-256("DMTAP-PUB-v0/subscription-id" || 0x00 ||
                                          det_cbor(Subscription \\ {10}))

This script pins that formula byte-for-byte against ONE fixed Subscription body,
encoded twice with two DIFFERENT `sig` byte strings (an honest signature is
deterministic under Ed25519 — RFC 8032 — so "two different signatures over the same
body" is realized here as two different `sig` fields, one of which does not even need
to verify; the property under test is that `subscription_id` does not depend on `sig`
at ALL, which holds whether the second encoding is an honest re-signing under a
composite/hybrid suite's AND-composed sig-val — not modeled by the classical-only
reference crate today — or outright tampering). Both MUST recompute to the identical
committed `subscription_id`.

Dependencies: `pip install blake3 cryptography` (both pure Python-callable, no network
at run time). Every value below is a FIXED constant: a fixed 32-byte Ed25519 seed, fixed
timestamps, fixed field values. No randomness, no wall-clock reads.

Run: python3 conformance/vectors/gen_pubsub_vectors.py > conformance/vectors/pubsub_vectors.json
"""
import json

import blake3
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

# ── fixed test constants (no randomness, no timestamps read from the clock) ──────────────
SEED_SUBSCRIBER = bytes([0x11] * 32)  # the Subscription's subscriber/signer IK
FEED = bytes([0x09] * 32)              # an arbitrary feed-author IK (opaque bytes here)
NONCE = bytes([0x5A] * 16)             # SUBSCRIPTION_NONCE_MIN = 16 bytes
TOPIC = "news"
ISSUED = 1_000
EXPIRES = 9_000
SUITE_V0 = 1  # suite = 0x01 (classical)
PUB_V0 = 0

DS_SUBSCRIPTION_ID = b"DMTAP-PUB-v0/subscription-id" + b"\x00"


def b3(data: bytes) -> bytes:
    return blake3.blake3(data).digest()


def content_address(data: bytes) -> bytes:
    """0x1e || BLAKE3-256(data) — the generic §2.2/§18.1.5 content-address rule."""
    return b"\x1e" + b3(data)


# ── minimal deterministic (RFC 8949 §4.2 canonical) CBOR encoder ─────────────────────────
# Integer-keyed maps, ascending key order, definite lengths, shortest-form integers —
# the same subset gen_pub_vectors.py uses, reimplemented here so this script has no
# import-time dependency on that one (independence is the point).
def enc_uint(n: int) -> bytes:
    return _enc_head(0, n)


def _enc_head(major: int, n: int) -> bytes:
    m = major << 5
    if n < 24:
        return bytes([m | n])
    if n < 2**8:
        return bytes([m | 24, n])
    if n < 2**16:
        return bytes([m | 25]) + n.to_bytes(2, "big")
    if n < 2**32:
        return bytes([m | 26]) + n.to_bytes(4, "big")
    return bytes([m | 27]) + n.to_bytes(8, "big")


def enc_bstr(b: bytes) -> bytes:
    return _enc_head(2, len(b)) + b


def enc_tstr(s: str) -> bytes:
    b = s.encode("utf-8")
    return _enc_head(3, len(b)) + b


def enc_map(pairs) -> bytes:
    """pairs: list of (int_key, encoded_value_bytes); sorted ascending by key (canonical)."""
    pairs = sorted(pairs, key=lambda kv: kv[0])
    out = _enc_head(5, len(pairs))
    for k, v in pairs:
        out += enc_uint(k) + v
    return out


def keypair(seed: bytes):
    sk = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
    pk = sk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    return sk, pk


SK_SUB, PK_SUB = keypair(SEED_SUBSCRIBER)

vectors = []


def add(name, operation, input_, expected, note):
    vectors.append({"name": name, "operation": operation, "input": input_, "expected": expected, "note": note})


# ══════════════════════════════════════════════════════════════════════════════════════
# Subscription.subscription_id (§25.4.1, §25.13 C-03) — body-only, DS-tagged
# ══════════════════════════════════════════════════════════════════════════════════════

# The §25.4.1 body: `Subscription \ {10}` — keys 1..9, sig (key 10) excluded by construction.
subscription_body = enc_map(
    [
        (1, enc_uint(PUB_V0)),
        (2, enc_uint(SUITE_V0)),
        (3, enc_bstr(PK_SUB)),   # subscriber
        (4, enc_bstr(FEED)),     # feed
        (5, enc_tstr(TOPIC)),    # topic
        (6, enc_uint(ISSUED)),   # issued
        (7, enc_uint(EXPIRES)),  # expires
        (8, enc_bstr(NONCE)),    # nonce
        (9, enc_bstr(PK_SUB)),   # signer (self-signed: signer == subscriber)
    ]
)
subscription_id = content_address(DS_SUBSCRIPTION_ID + subscription_body)

# Two `sig` (key 10) encodings of the IDENTICAL body above. Neither needs to verify for the
# property under test (subscription_id excludes key 10 entirely) — `sig_a` happens to be a
# genuine signature over the body's signing preimage (`DMTAP-PUB-v0/subscription\x00 || body`,
# §25.4.1) so a reader can also confirm the object is a normally-issued, verifiable
# Subscription; `sig_b` is a different byte string standing in for ANY other encoding of the
# same body a holder might see (an honest re-signing under a composite suite, or outright
# tampering) — the point is that `subscription_id` cannot tell the difference, by design.
DS_SUBSCRIPTION = b"DMTAP-PUB-v0/subscription" + b"\x00"
sig_a = SK_SUB.sign(DS_SUBSCRIPTION + subscription_body)
sig_b = bytes([0xEE] * len(sig_a))
assert sig_a != sig_b, "the two sig encodings must differ, or this proves nothing"

common_input = {
    "v": PUB_V0,
    "suite": SUITE_V0,
    "subscriber_hex": PK_SUB.hex(),
    "feed_hex": FEED.hex(),
    "topic": TOPIC,
    "issued": ISSUED,
    "expires": EXPIRES,
    "nonce_hex": NONCE.hex(),
    "signer_hex": PK_SUB.hex(),
}

add(
    "pubsub_subscription_id_sig_a",
    "pubsub_subscription_id",
    {**common_input, "sig_hex": sig_a.hex()},
    {"subscription_id_hex": subscription_id.hex()},
    "§25.4.1/§25.13 C-03: subscription_id = 0x1e||BLAKE3-256('DMTAP-PUB-v0/subscription-id'||"
    "0x00||det_cbor(Subscription \\ {10})) — sig (key 10) excluded. This encoding's sig is a "
    "genuine signature over the §25.4.1 signing preimage (self-signed: signer == subscriber), "
    "so the object also verify()s, but that is not what this vector is testing.",
)
add(
    "pubsub_subscription_id_sig_b",
    "pubsub_subscription_id",
    {**common_input, "sig_hex": sig_b.hex()},
    {"subscription_id_hex": subscription_id.hex()},
    "IDENTICAL Subscription body to pubsub_subscription_id_sig_a — same v/suite/subscriber/"
    "feed/topic/issued/expires/nonce/signer — with a DIFFERENT sig (key 10): 64 bytes of 0xee, "
    "which does not verify. subscription_id MUST still equal the sig_a vector's value, because "
    "the fixed formula excludes key 10 entirely. Reference (for documentation only, not "
    "separately gated): under the pre-C-03 formula (0x1e||BLAKE3-256(det_cbor(Subscription))"
    ", sig INCLUDED) these two encodings would produce DIFFERENT ids — that divergence is the "
    "exact revocation-bypass / quota double-count §25.13 C-03 closes.",
)

# ══════════════════════════════════════════════════════════════════════════════════════
out = {
    "format": "dmtap-conformance-vectors/1",
    "suite": "DMTAP-PUBSUB (§25) — suite 0x01 (classical): Ed25519 / BLAKE3-256",
    "generated_by": "conformance/vectors/gen_pubsub_vectors.py (this repo) — NOT the dmtap-core "
    "reference crate: these bytes are produced by this script alone, from the specification "
    "text, following gen_pub_vectors.py's provenance model for §22/§23. dmtap-core DOES "
    "implement DMTAP-PUBSUB (`dmtap_core::pubsub`, §25) and the Envoir conformance runner "
    "gates on every vector in this file, so the script-generated bytes are an INDEPENDENT "
    "check on that implementation, not a restatement of it.",
    "methodology": "All values computed from FIXED seeds/inputs by this script; no randomness, "
    "no wall-clock reads. Ed25519 is deterministic (RFC 8032); BLAKE3-256 and CBOR are "
    "deterministic. CBOR here is the same §18-canonical, integer-keyed (COSE/CWT-style) "
    "deterministic encoding used throughout the suite — a second implementer following "
    "§18.1.1/§18.1.2 and §25.4.1 alone reproduces these bytes without running this script.",
    "vectors": vectors,
}
print(json.dumps(out, indent=2))
