# Changelog

All notable changes to the DMTAP specification are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **Conformance: 22 cases for the new normative requirements** (172 → **194**), closing the gap the
  hardening and one-binary-with-roles commits left open — a MUST with no case is unenforceable, and
  §10.3 makes the suite the operational definition of compatibility. New families: `MIXPROF`
  (§4.4.10a Bootstrap-profile anti-drift constraints), `FLEET` (§4.4.2 derived fleet view), `GUARD`
  (§4.4.8 persistent guard sample + ASN/attested-operator diversity), `LOC` (§4.2 per-epoch
  `peer_id`, §4.2.1 resolution order), `FLOOR` (§9.7a zero-relationship delivery floor, §9.4.1
  memory-hard-PoW floor), `FAILCLASS` (§10.7.0 failure classes) and `GWROLE` (§7.11.4/§9.11
  authorize-never-classify, §7.1b privilege separation). Partition: 46 vectored + 6 self-contained
  + 137 construction-todo + 5 manual-attestation.
- **§21.10 `0x070F` `ERR_POLICY_BELOW_FLOOR`** — referenced by §9.7a since the hardening pass but
  never allocated. The one code in the anti-abuse block whose fault is the recipient's *own* policy
  (`N_floor = 0`, or a VDF-only cold-contact requirement) rather than an inbound object. Registry:
  140 → 141 codes.

### Fixed

- `0x0311` (`ERR_MIX_DIRECTORY_STALE`) is **FAIL-QUEUED** per §10.7.0/§10.7.2, not
  `FAIL_CLOSED_BLOCK` — the registry still carried the pre-reclassification disposition, which is
  the exact "liveness failure handed a denial-of-service surface" error §10.7.0 exists to forbid.
- `0x030D` (`ERR_MIX_PATH_UNBUILDABLE`) now names the diversity-unmet case, not only the
  empty-layer one, and is scoped to the in-force profile's bar.
- Catalog rows that outlived their clauses: `DMTAP-PRIV-01` still declared the `{2,8,32,64}` KiB
  bucket ladder (cut to `{8,64}`), `DMTAP-PRIV-02` and the §21.12 condition matrix still spoke of a
  mix "directory authority" (deleted — the fleet view is derived).
- `conformance/README.md` stated 157 cases / 104 construction-todo, two waves behind.

## [0.1.0] — 2026-07-21

First versioned cut of the DMTAP specification — sovereign, end-to-end-encrypted, metadata-private mail/chat/files/identity over a peer-to-peer mesh. 22 numbered sections plus conformance vectors. Spec text is CC BY 4.0.
