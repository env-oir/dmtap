# WRAP conformance vectors

`wrap_vectors.json` is the file `14-conformance.md` §15.1 says is **normative
and takes precedence over the prose** wherever the two disagree. This document
explains its format and how to drive it against an implementation. It is not
itself normative — if this README and the JSON disagree, the JSON wins.

## Why hex, not a language's native types

Every byte value in the file — canonical CBOR encodings, ids, signatures,
public keys, seeds — is a lowercase hex string with no `0x` prefix. Vectors
must be reproducible by an implementation in any language, so nothing here
depends on Go's `[]byte`, Rust's `Vec<u8>`, or any other host representation.

## Top-level shape

```jsonc
{
  "wrap_version": 0,
  "conformance_vectors_version": "0.1.0",
  "description": "...",
  "value_typing_convention": { ... },  // see below
  "keys": { "issuer": {...}, "performer": {...}, ... },
  "objects": { "wo1": {...}, "offer1": {...}, ... },
  "vectors": [ {...}, {...}, ... ]
}
```

### `keys`

Fixed Ed25519 keypairs, each derived from a 32-byte **seed** via the standard
Ed25519 key-derivation function (RFC 8032 §5.1.5; in Go,
`ed25519.NewKeyFromSeed(seed)`; in most other languages, whatever function
turns a 32-byte seed into an expanded signing key). A seed is not a random
value here — every seed in this file is 32 repetitions of a single byte
(`issuer` = `0x11` × 32, `performer` = `0x22` × 32, and so on) specifically so
a reader can eyeball which key is which without a lookup table. **Do not
reuse these keys for anything except reproducing these vectors** — the whole
point of a fixed, public seed is that anyone can derive the matching private
key.

Each entry is `{"seed": "<hex>", "pub": "<hex>"}`. `pub` is the 32-byte raw
Ed25519 public key — the value that appears everywhere in WRAP as `author`,
`performer`, `subject`, and so on (§2.1's Principal).

### `objects`

Ten fully-specified WRAP objects, referenced by name from `vectors[].object`
(or `objects` / `object_set` for vectors spanning more than one). Each entry
carries:

- `kind` / `kind_hex` — the object kind name and its `0x..` value (§3.1).
- `author` — which `keys` entry signed it.
- `ts` — the exact HLC stamp used (§7.2's `{unix_ms:013d}-{counter:04x}-{author_hex}` format).
- `fields` — the kind-specific fields (keys 6+) in the **typed-value
  convention** below, sufficient to reconstruct the object from scratch.
- `canonical_bytes_hex` — the deterministic CBOR encoding of the full object
  (common header keys 1,2,4,5 plus `fields`), with key 3 (`id`) and the
  signature both excluded, exactly as defined in §4.3/§5.2.
- `id_hex` — `0x1e ‖ BLAKE3-256(canonical_bytes)` (§4.3).
- `signature_hex` — Ed25519 signature (RFC 8032) by `author`'s private key
  over `preimage = "WRAP-v0/object" ‖ 0x00 ‖ canonical_bytes` (§5.2).
- `envelope_hex` — the two-element CBOR array `[canonical_bytes, signature]`
  transmitted on the wire (§5.3).

An implementation can and should reconstruct `canonical_bytes_hex` from
`fields` independently — that reconstruction, byte-for-byte, **is** the
`encode` conformance check. Do not treat `canonical_bytes_hex` as an opaque
blob to feed straight to a decoder and call it done; that only tests decode,
never encode.

### `value_typing_convention`

CBOR has more scalar types than JSON, so every typed value in this file
(inside `objects[].fields`, `vectors[].value`, etc.) is a small tagged object:

| `t` | Meaning | `v` |
|---|---|---|
| `uint` | CBOR major type 0 | JSON number, always ≥ 0 |
| `int` | CBOR major type 0 or 1 (encoder picks by sign) | JSON number, may be negative |
| `float64` | CBOR major type 7, IEEE 754 | JSON number, OR `"special": "nan"\|"inf"\|"neg_inf"\|"neg_zero"` in place of `v` |
| `bool` | CBOR major type 7 (`0xf4`/`0xf5`) | JSON boolean |
| `null` | CBOR major type 7 (`0xf6`) | (no `v`) |
| `tstr` | CBOR major type 3 | JSON string |
| `bstr` | CBOR major type 2 | lowercase hex string, `""` for empty |
| `array` | CBOR major type 4, definite-length | JSON array of typed values |
| `map` | CBOR major type 5, definite-length, **unsigned-integer keys** | JSON object; keys are decimal strings of the uint key, values are typed |
| `refmap` | The one WRAP map with **text** keys: `WorkOrder.refs` (key 14, §3.3) only | plain JSON object of string:string, no typing wrapper |

Why not just use bare JSON numbers/strings? Because `1` and `1.0` are
frequently indistinguishable once round-tripped through a JSON parser, and
this file needs to pin *exactly* which CBOR major type and width a given
field encodes as — that distinction is the entire subject of the `encode`
group.

### `vectors`

Each vector has a stable `id`, a `group` (one of the twelve in
`14-conformance.md` §15.2), a `description` explaining the property it pins,
and an `expect` block. Beyond that the shape varies by what the vector is
checking — a vector may reference `object` (one name from `objects`),
`objects`/`object_set` (several), inline `value`/`input`/`construction`
fields, or raw hex directly. Read `description` first; it says what to do.

Two fields you will see repeated across the `reject` and `sign` groups:

- `expect.error_code` / `expect.error_name` — the four-hex-digit code and
  name from `12-errors.md` §13.1 (e.g. `"0x0104"` / `"ERR_BAD_SIG"`).
- `expect.decodes: false` — the object MUST be rejected outright, not
  accepted-with-a-warning and not repaired-and-accepted (§5.4's "reject...
  do **not** re-encode and continue").

## Running the vectors against an implementation

There is no vector-runner binary in this repository — WRAP is a wire format,
not a library, and different implementations expose the decode/verify/fold
surface differently. The reference driver lives in the *implementation*
repository this vector set was validated against:

```
github.com/vul-os/propfix, branch fix/wrap-cbor
backend/internal/wrap/vectors_test.go
```

That test loads this file by path, walks `vectors[]`, and for each one either
runs a real check against `internal/wrap`, or marks it explicitly
**not-covered** with a stated reason (most commonly: this particular
reference implementation is a narrow encode/sign/decode/authorship binding —
it does not implement WRAP's HLC, merge, fold, or lifecycle-expiry runtime at
all, so the `hlc`, `tiebreak`, `merge`, `fold`, `expiry`, and `proof` groups
are legitimately outside its surface). **Not-covered is not the same as
passing.** A conformance claim requires an explicit accounting of every
group, and `14-conformance.md` §15.1 requires skips to be named, not silent.

To validate a *different* implementation:

1. For every `objects[]` entry, reconstruct the object from `kind` +
   `author` + `ts` + `fields` and confirm your encoder produces
   `canonical_bytes_hex` byte-for-byte.
2. Confirm `id_hex` = `0x1e ‖ BLAKE3-256(canonical_bytes)` for each.
3. Confirm `signature_hex` verifies as Ed25519 over
   `"WRAP-v0/object" ‖ 0x00 ‖ canonical_bytes` under the named key's `pub`.
4. Feed each `envelope_hex` / raw-bytes vector in the `reject` group to your
   decoder and confirm it fails with the stated `error_code`, at the stated
   step (§5.4 lists the required order — a vector may pin *which* check must
   fire first when more than one would eventually catch the input).
5. For `hlc`/`tiebreak`/`merge`/`fold`/`expiry`/`proof`, these are specified
   independently of any particular implementation's API — implement the
   check described in each vector's `description` against your own HLC,
   merge, fold, and proof-verification code, since those are exactly the
   parts of the protocol most implementations build themselves rather than
   import.

## A claim of conformance

Per §15.1: **all vectors pass, with no skips.** If your implementation skips
any, say which and why — "we do not implement lifecycle folding" is an
honest, acceptable answer; silence is not.
