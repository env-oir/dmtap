# 12. Operators, the Seam & Sustainability

DMTAP is deployed in one of two modes, and the boundary between them is a small, explicit
**operator seam**. This section is partly *informative* (business/licensing intent) and partly
*normative* (the inviolable rule and the seam's guarantees).

## 12.1 Two deployment modes

| Mode | Who runs it | Cost | Limits |
|------|-------------|------|--------|
| **Self-host** | The user, on their own box | $0 | none — fully functional, unrestricted |
| **Hosted operator** | A provider (e.g. a commercial control-plane) | paid | plan quotas on *operations* only |

The OSS is a **complete product on its own**. Self-host is not a crippled tier: it has every
protocol, client, and privacy feature. A hosted operator adds *convenience* (someone else runs
the box, warms the IPs, manages the domain), not *capability*.

## 12.2 The operator seam

The seam is the clean boundary the OSS exposes so an operator can add billing and multi-tenant
management **without forking or patching the protocol**. It is four capabilities (reference
crate: `crates/dmtap-seam`, contract: its `CONTRACT.md`):

- **Metering** — the OSS emits usage events at the real cost centers (gateway egress, storage,
  relay bytes, message counts, vanity domains).
- **Provisioning** — create/suspend accounts and `@`-addresses across onboarding tiers A/B/C
  (§3.8).
- **Policy** — per-account quotas/entitlements on operations (storage caps, send caps, domain
  counts, rate limits).
- **GatewayAuthz** — authorize legacy egress with per-identity-token accountability (§9),
  preserving sealed sender.

Each capability has a **self-host default that is unlimited/no-op**, so with no operator the
OSS runs unrestricted. A hosted operator implements the same capabilities — in-process (Rust
traits) or out-of-process (HTTP/events) — to add billing and quotas.

**Fail-open to function, fail-safe on security (MUST):** if the operator is unreachable, the OSS
MUST NOT break user-facing mail/chat/files. Metering queues and retries (usage may under-count
during an outage), and quota **Policy** falls back to allow (a billing concern, not a security
one). **GatewayAuthz is different and MUST NOT fail open to "allow."** GatewayAuthz is a security
control (§9): the accountability it enforces is exactly what prevents unattributable legacy
egress — the open-relay failure mode §7.7 exists to avoid. On operator-unreachable, GatewayAuthz
MUST fall back to a **safe default**: permit legacy egress only to **already-established
contacts** and to senders carrying a valid **proof-of-work solution** (§9.4) — the one anti-abuse
proof that is genuinely **verifiable without any operator** — and **deny cold/unproven legacy
egress** for the outage window. **Postage is deliberately excluded from this fallback:** a stamp
requires an **online issuer redemption check** against the issuer's endpoint or signed spent-list
(§9.5.1), and is treated as *unverified* whenever that issuer is unreachable, so it is **not**
operator-independent and MUST NOT be accepted on faith during an outage (it is only usable here if
the postage issuer happens to be independently reachable at redemption time). Established contacts
plus operator-independent PoW are therefore the genuinely operator-independent egress path; a
generic "fail-open to allow" for this capability is prohibited.

## 12.3 The inviolable rule (normative)

Privacy, cryptography, metadata privacy, and recovery MUST NEVER be behind the seam or a
paywall. There MUST be no seam hook, quota, or plan gate capable of disabling encryption,
weakening the mixnet, reducing metadata privacy, or denying a user access to their own keys or
mailbox. The seam meters and limits **operations and organizational concerns only**. Premium is
for *running it*, never for *protection*.

A conformant operator implementation MUST NOT expose any control that violates this rule; a
conformant OSS build MUST NOT consult the seam for any privacy/crypto decision.

## 12.4 Business & licensing model (informative)

DMTAP follows an **open-software + paid-operations** model — the GitLab-style split done cleanly,
without a crippled free tier:

- **Everything a user touches, and everything trust depends on, is open** — protocol, spec,
  node, gateway, client, crypto. Shipped under the **MIT license** (Apache-2.0 dual-licensing is
  under consideration for its explicit patent grant, relevant to novel mechanisms such as
  anti-abuse postage/tokens). Libraries other implementations embed are permissively licensed
  to maximize adoption.
- **The paid layer is a thin, private control-plane** (a *hosted operator*) that implements the
  seam contract and bills **operations**: hosted nodes, storage, legacy egress / IP reputation,
  vanity domains, org/SLA. It withholds no protocol, client, or privacy feature.
- **The moat is reputation + network + being the best operator**, not the code. Because openness
  is what lets the network grow large enough to be worth hosting, full openness costs little and
  is itself a trust requirement for a privacy product (a closed client cannot credibly claim
  "we can't read your mail"). Competitors hosting DMTAP grow the network the operator is central
  to.

## 12.5 Honest limits

- **Free-rider economics:** paying (convenience) customers subsidize free self-hosters. Intended
  and viable (the convenience majority pays; the sovereign minority self-hosts), provided the
  paid tier genuinely covers cost + margin.
- **Commoditization:** open software means thin margins on the software itself; margin comes
  from operations and scale, not licenses.
- **No protocol control:** required for adoption, but it means an operator can be out-executed —
  the defense is execution and trust, not a license.
- **The open-core temptation recurs:** pressure to move "just one" feature behind the paywall
  will appear. The inviolable rule (§12.3) is the bright line; drift there is fatal to the
  brand and is prohibited for privacy/crypto features.

## 12.6 Organization administration & the seam (normative)

Org / domain administration (§3.10) is an **organizational concern**, so it lives squarely on the
operator seam (§12.2) — and the inviolable rule (§12.3) draws the honest line through it:

- **Provisioning maps to the seam's Provisioning capability (§12.2).** Creating, suspending, and
  offboarding `name@abc.com` and org groups (§5.8.7) is exactly the seam's **Provisioning** hook
  across onboarding tiers A/B/C (§3.8). A hosted operator running the domain supplies the admin
  console; a self-hosted domain authority (§3.10.1) uses the same operations against the
  unlimited/no-op self-host default (§12.2) — an org can self-administer its own domain with no
  operator at all.
- **Directory, roles, and quotas are behind the seam; keys and crypto are NOT.** Curating the GAL
  (§3.10.3), assigning admin roles (§13.5.1), and per-member quotas are org/operations concerns the
  seam MAY meter and gate (**Policy**, §12.2). But the inviolable rule (§12.3) forbids any seam
  hook that would disable a member's encryption, weaken metadata privacy, or deny a member access
  to **their own keys or mailbox**. In particular, a **sovereign** member's key (§3.10.2(a)) is never
  a seam-controllable object: no operator plan, quota, or admin action can read it, escrow it, or
  lock the member out of it. The org controls the **name and the operations**, never a sovereign
  member's key.
- **Org-managed escrow is a disclosed member arrangement, not a seam backdoor.** The org-managed
  model (§3.10.2(b)) lets the *org* hold a member's key for compliance — but that is an explicit,
  disclosed, per-account arrangement visible to the user (`custody = "org-managed"`, §18.4.7),
  **not** a hidden operator hook and **not** applied to sovereign accounts. It does not violate
  §12.3 because it disables nothing in the protocol and hides nothing: the member is told, at
  provisioning, that this account's key is org-held. A conformant operator MUST NOT offer a control
  that escrows a **sovereign** account's key, or that presents an org-managed account as sovereign.

This keeps a real management console fully expressible on the seam while the sovereignty ethic
holds: **admin power and premium are for running the domain and its operations, never for reaching
into a member's keys** (§12.3).

## 12.7 Gateway billing is auditable via transport-path provenance (normative)

The seam meters **gateway operations** — legacy sends/receives — as a real cost center (§12.2
Metering; §7.9). Transport-path provenance (§7.8) makes that billing **auditable to the user**,
closing the gap between "the operator says you used the gateway" and "you can verify you did."

- **Billing attaches to gateway operations only, never to native mesh delivery.** A message that
  crossed a legacy gateway carries (inbound) or produced (outbound) the mandatory §7.2a
  attestation; a **pure-mesh** DMTAP↔DMTAP message carries none (§7.8.1(b)) and is, by
  construction, **not a gateway operation**. Per the inviolable rule (§12.3), native delivery and
  every privacy/crypto path are **never** metered or gated. A self-hoster reaching only DMTAP
  correspondents therefore incurs **zero** gateway billing (§7.9).
- **Every billable legacy operation is provenance-backed.** Because each gateway-touched message
  bears a verifiable `GatewayAttestation` (§18.3.11) naming the gateway `domain` and receipt time,
  a user can match each metered charge to a real message that **actually used the gateway** — the
  message's own `ProvenanceRecord` (§18.8.1) is the receipt. A charge with no corresponding
  attested message, or a **pure-mesh** message appearing on a gateway bill, is a **detectable
  billing error**, not something the user must take on faith.
- **Self-host authorization is a `GatewayAuthz` policy matter, disclosed.** A self-hoster's use of
  a *third-party* gateway is governed by the operator's `GatewayAuthz` policy (§12.2) plus the
  DKIM-delegation / MX pointing the user performs (§7.3, §7.9), all of which are visible to the
  user (a DNS act they take, an accountable identity token they present, §9). No hidden operator
  hook can bill a user for traffic that did not cross the operator's gateway, and the attestation
  chain is what makes that guarantee **checkable**, not merely promised.

This is metering as **transparency**: the operator bills exactly the gateway operations the
protocol makes cryptographically visible, and the user can independently audit the bill against the
messages' own provenance — consistent with §12.3 and the honest-limits ethic (§12.5).
