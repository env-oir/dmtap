# 8. Client Access

The node is a multi-protocol front-end over one MOTE store. Every protocol is a *view* of the
same mailbox. Client-facing protocols terminate **on the node**; the node is reached through
the mesh (SNI/stream routing over the relay/mesh) so no static IP is needed.

## 8.1 JMAP (native)

- The node exposes **JMAP** (RFC 8620 / RFC 8621) over a local HTTP endpoint (and, for remote
  devices, over an authenticated mesh stream).
- JMAP is the modern sync surface: `query`, `get`, `set`, `changes`, push. It maps directly
  onto the MOTE store and the device-cluster CRDT (§5.6).
- New DMTAP-native clients SHOULD prefer JMAP + the native MOTE/MLS APIs, which expose DMTAP-only
  features (identity verification, postage, privacy tier, file manifests).

## 8.2 IMAP / POP / SMTP-submission (compatibility)

To let existing mail clients (Apple Mail, Outlook, Thunderbird, mutt) work unchanged:

- The node runs **IMAP**, **POP3**, and **SMTP-submission** servers locally, projecting the
  MOTE store as folders/flags and accepting outbound submissions.
- Reached through the mesh (SNI-passthrough / stream routing); the node terminates TLS and
  speaks the legacy protocol; the relay/mesh never decrypts.
- **Auth = app-passwords**: the node issues app-specific passwords mapped to the identity, so
  legacy clients authenticate without touching the keypair.
- **Encryption is transparent to the owner's own client**: the node decrypts MOTEs and presents
  normal RFC 5322/MIME to the authenticated client. The E2E boundary is between *parties*, not
  between the owner and their own device.
- Outbound submission → the node converts to a MOTE (native) or routes to a gateway (legacy
  destination).

Compatibility support MAY be deprecated over time (like SMTP) as native clients mature; it is
not required for conformance, but is RECOMMENDED for adoption.

## 8.3 Multi-device

Devices form the owner's personal MLS cluster (§5.6); each runs its own client surface and
syncs the mailbox/flags/labels/file-index via encrypted CRDT over the mesh. The always-on node
anchors receipt while other devices sleep.

## 8.4 Calendar & contacts (first-class, decentralized)

Calendar and contacts are **not** separate central services — they are additional **MOTE kinds**
stored in the same node, end-to-end encrypted, synced across the device cluster (§5.6), and
shared/invited via the same MLS groups (§5) as everything else. They inherit the full
decentralized model: your node holds them, no provider can read them, and there is no central
CalDAV/CardDAV server.

- **Native:** calendar events and contacts are represented as **JSCalendar (RFC 8984)** and
  **JSContact (RFC 9553)** MOTEs, synced via **JMAP** (Calendars/Contacts) alongside mail (§8.1).
  Calendar invitations and scheduling (iTIP-style) ride as MOTEs between participants — no
  central scheduling server; free/busy and RSVP are messages, not a server query.
- **Compatibility:** the node exposes **CalDAV (RFC 4791)** and **CardDAV (RFC 6352)** servers on
  `localhost`/over the mesh, projecting the calendar/contact MOTE store as iCalendar (RFC 5545)
  and vCard (RFC 6350) so existing clients (Apple Calendar/Contacts, Thunderbird, DAVx⁵) work
  unchanged — reached through the mesh with app-passwords, exactly like IMAP (§8.2).

Compatibility DAV surfaces MAY be deprecated over time like the mail ones; native JMAP + MOTE is
the forward path.

## 8.5 The decentralization invariant (all data classes)

Every data class DMTAP carries — **mail, chat, files, calendar, contacts, identity, and login
(§13)** — obeys the same rule: it lives on the **user's node**, is **end-to-end encrypted**,
syncs across the user's **device cluster**, shares via the same **MLS groups**, and routes over
the same **mesh/mixnet** — with **no central server** for any of it. Legacy protocols
(IMAP/POP/SMTP/CalDAV/CardDAV) and the OIDC bridge (§13.6) are **edge-compat surfaces only**;
they never become a central store or a required intermediary. The node is the authority for
*everything*, uniformly. There is no data class that quietly depends on a central service.

Silent grants that would **redirect or delegate** that data — **auto-forward rules**, new
**capability delegations** (§13.5), and new **RP-session authorizations** (§13.4) — MUST be
surfaced to the owner's device cluster and logged to KT self-monitoring (§3.5), so a
business-email-compromise-style silent redirect or delegation is owner-visible, not covert.

## 8.6 Surfacing the transport-path (UX guidance)

The node exposes a per-message **`ProvenanceRecord`** (§18.8.1) over the client surface (JMAP,
§8.1; mapped in §19.9), and a client **SHOULD surface the transport-path** so a user can see, for
any message, **how it reached them and which trust boundaries it crossed** (§7.8). This is
implementer UX guidance, not a wire requirement.

- **Render a transport-path graph:** `sender → tier (hops) → gateway? → recipient`. Draw the
  arrival **tier** (`private`/mixnet vs `fast`/direct), the **coarse hop descriptor** (the profile
  floor, e.g. "≥ 3 mix hops" — **never** individual mix nodes, which the node does not know and
  MUST NOT invent, §6.8), and the **gateway leg** if one exists.
- **Make pure-mesh vs. gateway-touched visually unmistakable.** A **pure-mesh** message (no
  attestation, `origin = 0`) SHOULD be shown as **end-to-end, never plaintext at a gateway**; a
  **gateway-touched / legacy-origin** message (`origin = 1`) SHOULD be shown as having crossed a
  named gateway (`GatewayAttestation.domain`, its receipt time, and — for inbound — the legacy
  sender), clearly marked **not E2E before the gateway** (§7.2a). Chained gateways (§7.8.3) render
  as ordered hops, with any unverified-domain hop flagged as such.
- **Do not over-claim on `private`.** While the mix fleet is small the client MUST honour the
  §6.6/§4.4.11 disclosure and MUST NOT present `private` as absolute anonymity; the graph shows the
  **boundary crossings**, not a node-by-node trace.
- **Tie it to billing transparency.** For a gateway-touched message the client MAY let the user
  confirm the attestation against the operator's metered legacy operation (§7.9, §12.7) — "this
  message used the gateway, which is why it was billed" — and MUST NOT show a pure-mesh message as
  a billable gateway operation.

## 8.7 Deniable mode, org administration & device attestation (UX guidance)

The hardening mechanisms of §5.2.1, §3.10 and §1.2a each have a **client surface** a conforming
node SHOULD expose. This is implementer UX guidance, not a wire requirement, but the **fail-closed
choices are normative** where cited.

- **Deniable-mode selection (§5.2.1).** A client offering the deniable 1:1 mode MUST present it as
  an **explicit, per-conversation user choice**, never a silent default, and MUST show that a
  deniable thread **repudiates authorship** (no transferable proof) while still authenticating the
  key agreement. When the counterpart has **not** advertised the `deniable-1:1` capability
  (`ERR_DENIABLE_MODE_UNAVAILABLE`, `0x040E`), the client MUST **surface the choice** — send
  non-deniable (MLS 1:1) or don't send — and MUST NOT silently downgrade the user's *expectation of
  deniability*. Clients SHOULD indicate that deniable threads **sync per-device** (Sesame fan-out,
  §5.2.1(d)) rather than through the shared MLS tree, that **one-way** threads do not self-heal
  (PCS needs a reply, §5.2.1(b)), and — on device loss — that the session was **re-established**
  (§5.2.1(f)).
- **Org-admin console (§3.10, §13.5.1).** For a domain admin, the client SHOULD surface a
  member/directory console driving `provision-member` / `publish-directory` / `query-directory` /
  `offboard` (§19.1.5) and capability `delegate`/`revoke` (§19.6.6). It MUST render an
  **`org-managed` (escrowed-key) account honestly** — visibly distinct from a sovereign one, never
  presented as equivalent (`ERR_ORG_MANAGED_UNDISCLOSED`, `0x0115`) — and MUST show every
  grant/revocation as an **owner/authority-visible, KT-logged event** (the BEC-defense
  self-monitoring path, §13.5), so a silently installed admin grant or auto-forward rule is
  alertable.
- **Attestation enrollment prompts (§1.2a).** During device enrollment the client SHOULD prompt to
  generate the device key in a **hardware keystore** and attach attestation evidence
  (`attest-enroll`, §19.1.6), and SHOULD surface when a relying context **requires** attestation and
  the device lacks it (`0x0116`) or its evidence has **expired / the root retired** (`0x0118`,
  prompt to **re-attest**). The client MUST make clear attestation is **advisory hardening** — it
  never overrides the owner's §1.4 authorization — and that verifying it trusts a **vendor
  attestation root** (a disclosed TTP, §1.2a).
