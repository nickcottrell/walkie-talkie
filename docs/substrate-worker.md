# Substrate-Worker Pattern

> Note — this doctrine originated in the maestro policy stack and ships
> here with the walkie-talkie implementation it informs. The maestro
> derivation chain (`c2d2-architecture` → `dumb-by-design`) is recorded
> for provenance; the doctrine stands on its own for readers outside that
> ecosystem.

**Status:** Active
**Scope:** Small/local/chip-resident agents that route and fill slots rather than compose freely. Walkie-talkie itself is one instance of the pattern; future small-model integrations should follow the same shape.

---

## Purpose

Generalize the C2D2 architecture pattern beyond the geometric-reasoning case. Define what makes a "substrate worker" — a small agent whose job is to route, fill slots, and operate within an authored response-shape vocabulary rather than to compose free-form output. Name the design contract so any future small-model integration follows the same shape.

---

## Core Principle

**The dumber the model, the more it routes rather than thinks.** A substrate worker does not generate; it *fills shapes*. The intelligence in the system lives upstream (in the substrate it routes against, in the tool manifest it can call, in the response-shape library it draws from). The worker's job is to identify which shape applies and populate it from primitives — never to invent structure.

This is the operational realization of `dumb-by-design` in the agent layer: the simplest, most durable agent is the one that requires the least intelligence to operate. Simplicity here is the output of authored upstream artifacts (shapes, manifests, primitive vocabularies), not the absence of them.

---

## Three Properties

A substrate worker has three properties. All three must hold; missing any one collapses the pattern back to a free-form agent.

### 1. Tool list IS the action surface

The tool manifest enumerates every action the worker can take. No tool, no action. The worker cannot improvise an action that is not in the manifest. The manifest is read-only at runtime.

**Why:** Action enumeration is the authority boundary. A free-form agent decides what it can do; a substrate worker is told what it can do. This is the constitutional axiom of enumerated powers applied to small models.

**Realization in this repo:**
- `cli.py` subcommands (`encode` / `decode` / `roundtrip`) are the walkie-talkie action surface
- An agent invoking walkie-talkie can do exactly those operations and nothing else

### 2. Pre-canned response shapes with slots

Output is templated, not composed. A response-shape library declares the prose forms the worker can emit; runtime populates slots from primitives + records + tool returns. The worker does not write new prose structure.

Mail-merge analogue: the templates are written once by an author; the worker fills `{name}`, `{date}`, `{amount}` from a record. Templates are versioned, reviewed, owned. Slot vocabularies are a defined namespace.

**Why:** Semantic content travels through the *shape*, not through the model's generative capacity. This is what lets a small model carry meaning that would otherwise require a much larger model — the structure is borrowed from the authored library.

**Realization in this repo:**
- `shapes.py` is a v0 shape library
- Each shape declares a `when` predicate + a `render` callable; the library is ordered, the first match wins, the default fallback always matches
- New shapes are added by editing the library, not by retraining or reprompting the model

### 3. Prose budget near zero

The worker's output is mostly tool calls + labeled fields. Free-form prose is the exception, not the rule. When prose appears at all, it is short and structural (a one-line gloss, a refusal reason, an audit note).

**Why:** Prose is the most expensive output in tokens, in determinism, and in policy compliance. Constraining a substrate worker's prose budget forces it to express itself through structure — which is verifiable, compressible, and cheap to transport across the capability ladder.

**Realization in this repo:**
- The encoder emits a JSON record (geometric primitives + hex addresses + structured fields)
- The renderer emits a structural header line + scrubbed prose body — the prose body fills slots, it is not freely composed
- A tiny-tier consumer can read the JSON record directly, with no prose at all

---

## Trade-Off

The substrate-worker pattern shifts the IP location:

- **Smart-prompt era:** value lives in the prompt (the artful instruction that coaxes a large model into useful output)
- **Substrate-worker era:** value lives in the **response-shape library + tool manifest + primitive vocabulary**

Templates become load-bearing. The shape library is an authored, defensible artifact — a 3DMATH artifact, not a model artifact. Small models commoditize quickly; authored shape libraries do not, because they encode domain-specific structural decisions.

This is also why substrate workers travel cleanly across model swaps. A new small model with the same tool manifest and same shape library produces equivalent output. The worker is interchangeable; the substrate is not.

---

## When To Reach For This Pattern

Use the substrate-worker pattern when:

- The agent runs locally, on a chip, on a small model, or under tight latency / cost / privacy constraints
- The agent's output must be auditable (templates are reviewable; free-form generation is not)
- The agent needs to emit content in multiple languages or formats (shapes can be re-rendered in any language; free-form output cannot)
- Cross-tier propagation matters (a substrate worker's output is structurally compatible with the tier above and below, because both consume the same shape library)

Do **not** use this pattern when:

- The agent's job is genuinely creative composition (writing prose, generating ideas, exploring unbounded spaces)
- The shape library would need to be infinite to cover the action surface
- A large model is available, latency-acceptable, and creative output is the goal

The substrate-worker is for the routing-and-filling case, not for the composing case.

---

## Anti-Patterns

- **Free-form prose from a substrate worker.** If the output diverges from any shape in the library, the worker is no longer a substrate worker — it is doing something the pattern does not authorize.
- **Inventing slot vocabulary at runtime.** Slot names are namespace; if the worker names a slot that the library does not declare, downstream consumers cannot fill it.
- **Adding tools dynamically.** The tool manifest is read-only at runtime. Hot-loading tools defeats the enumerated-authority property.
- **Treating shape libraries as throwaway scaffolding.** They are the IP; they get versioned, reviewed, owned, evolved deliberately.
- **Skipping the shape library and just using the encoder.** The encoder produces structural primitives; without a shape library to render them, the output is geometry only — fine for tiny-tier consumers, lossy for human/big-model consumers. The shape library is what makes the primitives consumable across tiers.

---

## Provenance (maestro policy lineage)

This doctrine derives from two policies in the maestro chassis:

- **C2D2 Architecture** — the original instance of this pattern, applied to geometric reasoning over a Jeff data substrate
- **Dumb by Design** — simplicity as the output of engineering: the simplest, most durable solution requires the least intelligence to operate

Adjacent policies inside the maestro ecosystem (Maximal Geometric Language, Instance Roles, MCP Tool Lifecycle) refine the pattern further but are not preconditions for applying it elsewhere.

---

## The Test

Before classifying an agent as a substrate worker, ask:

1. Can the agent take an action that is not in its tool manifest? (Should be: no.)
2. Does the agent's prose output come from a templated shape with named slots? (Should be: yes.)
3. Is the prose budget bounded? Could a tiny model produce the same output? (Should be: yes.)

If all three are yes, the agent fits the pattern. If any are no, the agent is something else — a free-form agent, a coordinator, or a composer — and this policy does not apply.

---

**Established:** 2026-05-07
**Author:** Nick Cottrell / 3DMATH
**Origin:** Captured in the maestro substrate as the `dumb_model_substrate_worker` token (2026-05-07), then extracted to this repo alongside the walkie-talkie implementation.
