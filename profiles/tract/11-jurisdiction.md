# 11. Jurisdiction

> **Drafting status.** This section is scoped but not yet normative. It states what it will
> specify, which existing standards it profiles, and the decisions still open. Nothing here is
> implementable yet; text becomes normative when the RFC 2119 keywords appear.

## 11.1 Scope

Making the legally responsible party explicit, and getting tax anchors right by construction.

## 11.2 The four anchors

The most common commerce-tax error is conflating party location with where a supply happens. These
are four distinct fields, derived from four different places:

| Anchor | Derived from | Governs |
|---|---|---|
| seller establishment | seller identity | licensing, seller-side registration |
| buyer residence | buyer disclosure at order | consumer-protection rights (generally non-waivable) |
| **place of supply** | **the Fulfilment axis (§4)** | VAT/GST, especially services and events |
| delivery destination | the shipping leg (§8) | customs, duty, product-safety regimes |

The forcing example: an event held in one country, sold by a seller in another, to a buyer in a
third. Admission to events is generally taxed where the event physically takes place, so only the
Fulfilment object knows the answer.

## 11.2a What the law actually says, as far as anyone has checked (§21.11)

This section previously answered its central question by assertion. A narrow legal pass has now
checked one of the five questions it rests on, and the answer is **structurally favourable, more
limited than assumed, and entirely untested**. The other four remain unresearched after three
passes — including the GDPR erasure conflict, which is still the most likely hard blocker.

**The argument that survives.** Every representative US state facilitator test is *conjunctive and
gated on a contract with the seller*: Cal. Rev. & Tax. Code §6041(b) — "a person who **contracts
with** marketplace sellers … **and** who does both of the following" — puts even its infrastructure
prong inside that gate. A gateway no seller has contracted with is outside the definition on its
face, whatever it runs. No court has ever tested this.

**Three corrections this section has to absorb.**

*There is a marketplace.* The term is medium-agnostic and expressly enumerates a catalog and a
dedicated sales software application, so a signed catalogue feed and a buyer-side cart client are
within it. The available argument is that there is **no facilitator** — never that there is no
marketplace.

*Escrow is the trigger, and in two states it is enough alone.* Tex. Tax Code §151.0242(a)(2) catches
"directly or indirectly processes sales or payments" with no carve-out; N.Y. Tax Law §1101(e)(1)(B)
catches a person who "contracts with a third party to collect" receipts, so routing checkout through
the gateway's own provider suffices even if its balance sheet never holds the money. §9's "escrow is
an operator class" understates this: escrow is also what most likely makes that operator a **tax**
facilitator.

*Render-only is not a safe posture.* It holds in New York and Texas and is likely caught in
Washington and California through the listing and order-taking prongs. Two states of roughly fifty
is not a US position.

*One thing is confirmed:* a self-hosted seller taking direct payment for their own goods is never a
facilitator, because every definition requires sales by persons **other than** the operator of the
medium.

## 11.2b The EU rule written to defeat this argument

Art 5b of Council Implementing Regulation (EU) 282/2011 treats an interface as not facilitating only
if, cumulatively, it sets **none** of the terms directly or indirectly, is **not** involved in
authorising the charge, and is **not** involved in ordering or delivery. Carrying out even one may
suffice to make it a deemed supplier.

The Commission's Explanatory Notes then name this design's central claim and reject it: the
indication "that the contract is concluded between the underlying supplier and the customer **is not
sufficient**" to escape deemed-supplier status, because the concept "goes beyond the contractual
relationship and looks at the **economic reality** and in particular the **influence** exercised".
The words "indirectly" and "any" are stated to exist precisely to prevent "artificial splitting of
rights and obligations between the electronic interface and the underlying suppliers".

"The contract is between two keypairs" is the argument that text anticipates. A protocol asserting a
contractual arrangement does not escape a test that measures influence rather than declarations.

**The scope limit, given plainly rather than as reassurance:** Art 14a bites on imported consignments
of intrinsic value ≤ €150 and on intra-EU supplies by non-EU-established sellers. It is not a general
rule for all EU commerce. Where it applies, no protocol design argues its way out, and this section
does not pretend one could.

## 11.3 What this section will specify

- **Responsibility follows the money**: every order names seller of record, facilitator (the
  gateway, if it settled), importer of record, in-region responsible person, and escrow/rail.
- Geo-availability on offers, and fail-closed construction when a required in-region role is absent.
- Tax treatment categories (not rates — see §5.5).

## 11.4 Regimes this section must accommodate

South Africa (electronic-transaction disclosure and cooling-off, consumer protection, POPIA, VAT,
payment-side KYC); the EU (GDPR, platform trader traceability, consumer rights, in-region
responsible person for product safety, VAT one-stop schemes, platform reporting); other African
markets (national data-protection acts, local VAT registration, regional trade frameworks); New
Zealand (privacy, fair trading, consumer guarantees, GST on low-value imports); the Americas (US
economic nexus and marketplace-facilitator rules, seller-traceability legislation, Canadian and
Brazilian privacy law).

The protocol guarantees the **facts** a regulator asks for are present, signed and attributable.
It does not make any deployment compliant, and must not be read as legal advice.

## 11.5 The erasure conflict, resolved structurally

Published objects are irrevocable; erasure rights cannot be satisfied against them. Therefore **no
personal data enters the public quadrant** (§0.5.1). Orders and everything identifying a person are
sealed and deletable at the edges. Reviews are the single bounded exception (§10.4).
