# Proofline: case study

A personal R&D project on making an investigation agent trustworthy enough to put in front of a human reviewer. This document is about the reasoning. Nothing here describes a deployment, a customer or measured results: the prototype runs on synthetic data.

## The problem

When an upstream system flags an entity as risky, a person still has to find out whether the flag holds up. Most of that time goes to collecting records from several places, cross-checking numbers, and writing down what was found. It is repetitive work, which makes it a natural target for an LLM agent.

It is also work where being wrong is expensive. An agent that invents an invoice, rounds a total the wrong way, or phrases a suspicion as a conclusion produces something that looks like evidence and is not. In an investigation, a plausible and wrong statement is worse than no statement, because a reviewer may build on it.

## Why it matters

The goal is not to make the model smarter. It is to make the system's claims **checkable**: a reviewer should be able to ask of any sentence in the case file "where does this come from?" and get a record id, not an assurance. And the agent should be unable to do harm even when it is wrong: it can read, it cannot act.

## The approach

Treat the model, if there is one, as an untrusted author inside a pipeline of deterministic checks.

1. **One gate for every tool call.** Identity, role, read-only, purpose, scope, row limit. Denials are audited like approvals.
2. **Evidence before narrative.** Records become evidence items with provenance, and each is re-verified against the source before anything uses it.
3. **Claims are structured, not prose.** A claim carries the numbers it states, the evidence they come from, and the structural properties it relies on (a chain is closed, two invoices share a number). Code recomputes each.
4. **Rejection is a loop, not a failure.** Rejected claims go back with machine-readable reasons. After three rounds, whatever still fails is withheld and never published.
5. **A human decides.** The agent has no tool that changes anything, and a role check keeps it from recording a decision.

## Decisions and trade-offs

| Decision | Why | What it costs |
|---|---|---|
| Verify claims by recomputation instead of asking another model | Cheap, repeatable, and the reason for a rejection is exact (`claimed 37, actual 11`) | Claims must be expressible as recomputable facts, so prose is constrained. A claim the verifier cannot check cannot be published |
| Findings are *confirmed* or *candidate* | The first version of the demo case cannot see the invoice that closes the chain, and says so instead of guessing | More states to explain to a reviewer |
| Scope grows only on a reviewer request, justified by a validated record that names the entity | Prevents an agent from wandering across the dataset and keeps the audit trail meaningful | A reviewer round trip for each widening |
| Free-text fields never reach the narrator | A note in the demo data tries to give the agent instructions. Structural exclusion is more reliable than detecting every phrasing | Useful context in notes is lost to the narrator |
| Template narrator by default, model behind an interface | The safety properties can be tested without a model or a key | The prototype says nothing about how a real model would perform |
| Keyword check for legal conclusions | Enforces the "evidence, not verdict" boundary in a way a test can show | Blunt. A real deployment would pair it with reviewed phrasing templates |
| Plain state machine instead of an agent framework | Every transition is explicit and audited | Branching logic would need a framework eventually |
| Hash chain plus triggers for audit | Edits are detectable even by someone who can drop the triggers | Not tamper-proof until the head hash is anchored elsewhere |

## What came out of it

A runnable pipeline that, on synthetic data, finds five planted patterns, refuses to confirm a sixth until it has the evidence, catches two deliberately bad claims, and produces a case package whose every sentence links to records. 65 tests cover the gateway, the evidence checks, the verifier, the review loop and the audit chain; the exact commands and results are in [VERIFICATION.md](VERIFICATION.md).

What it does not show: accuracy on real data, how a real model behaves inside the loop, or how reviewers would use the output. Those need a real data source and real reviewers.

## What I would do next

1. Put a real model behind the narrator interface and measure how often the verifier rejects its drafts, on a held-out set of cases. That is the experiment this design exists to enable.
2. Move the policy to Open Policy Agent and the tool surface behind an MCP server, keeping the gateway's decisions and audit records identical.
3. Anchor the audit head hash outside the database, and export provenance as OpenLineage events.
4. Replace the scripted reviewer with a small review UI that shows each claim next to its evidence records.
5. Extend the claim language (ratios, time windows) so more of what an analyst would say is checkable.

## Skills this project demonstrates

- Designing a trust boundary around an LLM component instead of trusting its output.
- Policy enforcement, least privilege and auditability as code, with tests for the failure paths.
- Deterministic verification of structured claims, and honest handling of uncertainty (candidate findings, withheld claims).
- Threat modelling for prompt injection through data, and choosing structural defences over detection.
- Writing a prototype whose documentation separates what is built, tested and only designed.
