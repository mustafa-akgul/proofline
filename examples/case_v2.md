# Case CASE-RISK-2026-0001 (version 2)

**Status:** APPROVED  
**Entity under review:** E017  
**Risk category:** invoice-flow-anomaly (upstream score 0.91, synthetic input)  
**Authorized scope:** E017, E021, E022

> This package assembles evidence for a human reviewer. It makes no legal finding, does not declare any party guilty of anything, and triggers no external action.

## Summary of verified claims

- **C-001** (observation): In 2026-10, Orchid Trading Ltd (E017) issued 11 invoices, against a median of 3 per month over the 5 preceding months of record.
- **C-002** (observation): 3 invoices issued between 2026-10-06 and 2026-10-21 form a closed chain E017 -> E021 -> E022 -> E017, totalling 1,425,000.00 currency units, none with a matching payment in the collected transaction records.
- **C-003** (observation): Of 12 invoices issued or received by Orchid Trading Ltd (E017) in 2026-10, 6 have no matching payment in the collected transaction records, totalling 1,027,740.29 currency units.
- **C-004** (observation): 3 invoices issued by Orchid Trading Ltd (E017) carry a tax amount that differs from the reference-rate amount: INV-0258, INV-0261, INV-0264.
- **C-005** (observation): Invoice number ORC-2026-0107 appears on 2 invoices issued by Orchid Trading Ltd (E017) with different amounts (INV-0260, INV-0266).

## Findings

| Finding | Status | Evidence records |
|---|---|---|
| Invoice volume above the entity's own baseline | confirmed | 6 |
| Closed chain of invoices returning to the origin | confirmed | 3 |
| Invoices with no matching payment in the collected records | confirmed | 34 |
| Tax amount differs from the reference rate | confirmed | 3 |
| One invoice number used on invoices with different amounts | confirmed | 2 |

## Evidence matrix

| Claim | Kind | Evidence | By kind | Key records |
|---|---|---|---|---|
| C-001 | observation | 6 | monthly_summary 6 | agg:monthly:E017:2026-10, agg:monthly:E017:2026-05, agg:monthly:E017:2026-06, agg:monthly:E017:2026-07, agg:monthly:E017:2026-08 ... |
| C-002 | observation | 3 | invoice 3 | invoices:INV-0267, invoices:INV-0268, invoices:INV-0269 |
| C-003 | observation | 34 | invoice 12, transaction 22 | invoices:INV-0257, invoices:INV-0258, invoices:INV-0267, invoices:INV-0259, invoices:INV-0260 ... |
| C-004 | observation | 3 | invoice 3 | invoices:INV-0258, invoices:INV-0261, invoices:INV-0264 |
| C-005 | observation | 2 | invoice 2 | invoices:INV-0260, invoices:INV-0266 |

## Verification

- Draft round 1: 7 claims drafted, 5 verified, 2 rejected.
  - Rejected C-006: "In 2026-10, E017 issued 37 invoices, a sharp jump." (fact_value_mismatch:invoices in month:claimed 37 actual 11)
  - Rejected C-007: "E017 committed tax fraud through a circular invoice scheme." (legal_conclusion:committed; legal_conclusion:fraud; no_evidence_cited; uncited_record_id:E017)
- Draft round 2: 5 claims drafted, 5 verified, 0 rejected.

## Timeline (analysis window)

| Date | Event | Amount | Evidence |
|---|---|---|---|
| 2026-10-02 | Invoice INV-0257 E017 -> E001 | 12,133.15 | EV-0018 |
| 2026-10-05 | Invoice INV-0258 E017 -> E004 | 21,157.16 | EV-0019 |
| 2026-10-06 | Invoice INV-0267 E017 -> E021 | 480,000.00 | EV-0020 |
| 2026-10-08 | Invoice INV-0259 E017 -> E007 | 13,687.75 | EV-0021 |
| 2026-10-11 | Invoice INV-0260 E017 -> E010 | 27,555.72 | EV-0022 |
| 2026-10-14 | Invoice INV-0261 E017 -> E013 | 21,489.34 | EV-0023 |
| 2026-10-14 | Invoice INV-0268 E021 -> E022 | 475,000.00 | EV-0058 |
| 2026-10-17 | Invoice INV-0262 E017 -> E016 | 16,738.48 | EV-0024 |
| 2026-10-17 | Payment TXN-0221 E001 -> E017 | 14,559.78 | EV-0046 |
| 2026-10-20 | Invoice INV-0263 E017 -> E020 | 14,207.91 | EV-0025 |
| 2026-10-21 | Invoice INV-0269 E022 -> E017 | 470,000.00 | EV-0026 |
| 2026-10-22 | Payment TXN-0222 E004 -> E017 | 25,388.59 | EV-0047 |
| 2026-10-22 | Payment TXN-0224 E013 -> E017 | 25,787.21 | EV-0048 |
| 2026-10-23 | Invoice INV-0264 E017 -> E025 | 16,871.61 | EV-0027 |
| 2026-10-26 | Invoice INV-0265 E017 -> E003 | 12,814.06 | EV-0028 |
| 2026-10-28 | Invoice INV-0266 E017 -> E003 | 34,500.00 | EV-0029 |
| 2026-10-31 | Payment TXN-0223 E010 -> E017 | 33,066.86 | EV-0049 |
| 2026-10-31 | Payment TXN-0225 E020 -> E017 | 17,049.49 | EV-0050 |
| 2026-10-31 | Payment TXN-0226 E025 -> E017 | 20,245.93 | EV-0051 |

## Entity relationships (invoices in the window)

| From | To | Invoices | Total |
|---|---|---|---|
| E017 | E001 | 1 | 12,133.15 |
| E017 | E003 | 2 | 47,314.06 |
| E017 | E004 | 1 | 21,157.16 |
| E017 | E007 | 1 | 13,687.75 |
| E017 | E010 | 1 | 27,555.72 |
| E017 | E013 | 1 | 21,489.34 |
| E017 | E016 | 1 | 16,738.48 |
| E017 | E020 | 1 | 14,207.91 |
| E017 | E021 | 1 | 480,000.00 |
| E017 | E025 | 1 | 16,871.61 |
| E021 | E022 | 1 | 475,000.00 |
| E022 | E017 | 1 | 470,000.00 |

## Missing evidence and uncertainty

- Absence of a payment is judged only against the collected transaction records

## Evidence integrity notes

- EV-0026 (invoices:INV-0269): instruction_like_text:note. free-text field excluded from narrative input; record kept as evidence.

## Review history

- 2026-11-02T09:02:55Z reviewer-01: approve (Evidence package accepted for follow-up.)

## Audit

43 audit records, chain valid: True, head `bf0c8bde2040814b...`
