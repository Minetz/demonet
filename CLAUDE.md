# CLAUDE.md — Project Context for AI Contributors

Read `MANIFESTO.md` first. Every technical decision answers to those values.

## Project: The World's Take

A global opinion network where AI is the intermediary — anonymizing identity, preserving substance, and connecting perspectives across every boundary humans have drawn.

## MVP: "The World's Take" — One Question, The Whole Planet Answers

### What it is

A single-page application. One question displayed prominently (changes weekly). Anyone on Earth writes their take. AI processes it — anonymizes, translates, vectorizes, signs it with a hash. The user gets back:

1. **Their opinion signature** — a portable hash (`worldstake.org/a7f3c9`) and a generative visual fingerprint derived from the semantic shape of their take
2. **A live visualization** — a constellation/globe of opinion dots, clustered by semantic similarity, updating in real-time
3. **"Your closest mind, furthest away"** — the most semantically similar opinion from the most geographically distant contributor
4. **A shareable card** — screenshot-ready, links back to the platform

### Why this specific MVP

- No cold-start problem. 1 user gets a signature. 10 users see clusters. 1000 users see something mesmerizing.
- Viral by design. The opinion fingerprint and "closest mind, furthest away" are shareable artifacts.
- Tests the core hypothesis: do people want to share opinions anonymously and discover unexpected global connections?
- Every opinion submitted seeds the future network. Every hash issued is a future user.
- The weekly question cadence creates return visits and shareable moments.

### What it is NOT

- Not a social network. No profiles, no follows, no feeds, no accounts.
- Not a poll. Free-text opinions, not multiple choice.
- Not a debate platform. Understanding, not argument.

## Architecture Principles

### Identity & Trust

- **No accounts required.** Participation is frictionless.
- **PII stripping is mandatory.** Every opinion passes through an anonymization layer before storage. Names, locations, identifying phrases — removed. Semantic content — preserved.
- **Probabilistic trust scoring.** Device fingerprint + location entropy + behavioral patterns + participation history = "realness score." No single signal is conclusive. The combination is robust.
- **Anti-sybil graph analysis.** Detect closed validation loops and astroturfing rings through topology, not identity.
- **Progressive trust tiers.** Anonymous by default. Optionally link to identity providers later for higher trust. Trust is visible to others; identity never is.
- **Pluggable ID provider interface.** Today: behavioral trust. Tomorrow: government digital ID, World ID, or whatever wins. The interface is stable; providers are swappable.

### The Opinion Signature

- **Sign any text.** Opinion, speech transcription, long-form post. Output: a public hash.
- **Cross-platform reputation.** Users can optionally grant access to public social accounts. We vectorize their full history into an "opinion fingerprint" — not what they said, but the shape of how they think (consistency, nuance, evolution, good faith).
- **Portable hash as passport.** Post your hash on Twitter, Reddit, a forum, anywhere. Anyone can look it up and see: trust score, opinion consistency, engagement quality — never your name.
- **Agent reputation.** AI agents inherit their owner's reputation hash. Agent actions affect owner reputation. Agent opinions are labeled as agent-mediated.

### AI Role

- **Translation.** Any language in, any language out. Opinions are stored language-agnostic (as embeddings) with original text preserved.
- **Vectorization.** Every opinion is embedded for semantic clustering. We use this to find bridges, not to profile.
- **Clustering.** Semantic grouping, not demographic bucketing. Let surprising alignments surface.
- **Expression assistance.** AI can help users articulate their take more clearly. It never changes the substance.
- **Bridging.** Specifically surface opinions from people you'd least expect to agree with.
- **Summarization.** "What does the world think about X?" answered by synthesizing real submitted opinions, not training data.

### Data & Privacy

- Raw text with PII stripped stored at rest, encrypted.
- Embeddings stored separately from text — no reconstruction path from embedding to original.
- Geographic data stored at region granularity (country/region), never precise location.
- No behavioral tracking beyond what's needed for trust scoring.
- All data processing is auditable. If we can't explain it, we don't ship it.

## Technical Stack (MVP)

This is a starting point, not a prescription. Choose what gets us to a working MVP fastest.

- **Frontend:** Single page. Interactive visualization (three.js, d3, or similar). Mobile-first.
- **Backend:** Lightweight API. Endpoints: submit opinion, get current question, get visualization data, get opinion by hash, query opinions (for agents).
- **AI/ML:** Embedding API for vectorization (OpenAI, Anthropic, or open-source). Nearest-neighbor search for clustering. PII detection and stripping.
- **Storage:** Opinions, embeddings, trust scores. Nothing exotic — start with what's simple.
- **API for agents:** RESTful. `GET /question/current`, `POST /opinion`, `GET /opinions/cluster`, `GET /opinion/{hash}`. MCP server wrapper for AI agent platforms.

## API Design (Agent-Facing)

Agents are first-class citizens. The API should be useful to an AI agent helping someone reason about a topic.

```
GET  /question/current          → current question + metadata
POST /opinion                   → submit opinion, receive hash + signature
GET  /opinion/{hash}            → retrieve signed opinion + trust metadata
GET  /opinions/current          → clustered opinions for current question
GET  /opinions/current/summary  → AI-synthesized summary of global opinion
GET  /opinions/bridge/{hash}    → "closest mind, furthest away" for a given opinion
```

## Development Guidelines

- **Ship the simplest thing that tests the hypothesis.** Resist the urge to build infrastructure before we know people want this.
- **Every feature must answer to the manifesto.** If it doesn't serve understanding, transparency, or privacy — it doesn't ship.
- **AI never manipulates.** No engagement optimization. No recommendation algorithms that create bubbles. No dark patterns.
- **Open source everything.** Code, algorithms, data formats. The community should be able to audit and rebuild anything.
- **Test trust, not just functionality.** Every feature that touches identity, anonymization, or reputation needs adversarial testing. Assume bad actors from day one.
- **Internationalization from the start.** The first user might be in Tokyo or Lagos. Design for it.

## Priority Roadmap

### Phase 1: The Seed (1-2 days)
- Single-page MVP: one question, submit opinion, get hash + visual signature
- Live visualization of opinion clusters
- "Closest mind, furthest away" feature
- Basic API for agent integration
- Deploy and publish to AI agent directories

### Phase 2: The Roots (weeks)
- Weekly question rotation with archive
- Cross-platform reputation (link social accounts, build opinion fingerprint)
- Trust scoring system (behavioral + device + history)
- MCP server for AI agent platforms
- Shareable opinion cards with open graph metadata

### Phase 3: The Network (months)
- Free-form topics beyond the weekly question
- Opinion evolution tracking (how your own views shift over time)
- Structured deliberation mode (guided question trees)
- Anti-sybil graph analysis
- Pluggable identity provider interface
- Local-to-global zoom (neighborhood → city → country → world)

## Red Lines

These are not flexible. They are the project's immune system.

1. We never sell opinion data.
2. We never link opinions to real identities in any system we control.
3. We never optimize for engagement over understanding.
4. AI never steers opinion.
5. Every algorithm is auditable.
6. If we can't explain how something works, we don't ship it.
