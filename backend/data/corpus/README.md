# Knowledge corpus

Markdown files here are chunked, embedded, and indexed into the retrieval
corpus on backend startup. This is where real agricultural reference material
belongs — ICAR package-of-practices extracts, KVK advisories, state
agriculture department circulars, NDMA guidance.

## Layout

The containing directory sets the document's retrieval category:

```
data/corpus/
├── agronomy/     crop diseases, nutrition, irrigation, pest management
├── scheme/       government schemes, subsidies, insurance
├── health/       farm first aid, pesticide safety
├── disaster/     flood, lightning, cyclone preparedness
└── education/    tutorials and training material
```

A file in any other directory is indexed as `agronomy`.

## Format

Plain markdown. The first `# Heading` becomes the document title and is used as
the citation label shown to farmers; without one, the filename is used. Files
are split on paragraph boundaries into ~800-character chunks with ~120
characters of overlap, so a passage spanning a boundary stays retrievable from
either side.

Write in **English even when the target audience is not**. The embedding model
(`EMBED_MODEL`) is multilingual, so a Hindi, Tamil, or Punjabi query matches
English source text directly, and the LLM translates the final advisory into
the farmer's selected language. Maintaining 11 translations of every document
is unnecessary.

Keep each document factual and attributable. Retrieved text is injected into
the prompt as authoritative source material, so anything inaccurate here
becomes an inaccurate recommendation to a farmer.

## Structured guides: adding a dashboard card without code

A file can also define a card the agents select and render: a first-aid
protocol, a disaster alert, a scheme, or a tutorial. Give it front matter with
a `guide_key`, plus the `##` sections that card type needs:

| Folder | Card | Required sections | Front matter |
|---|---|---|---|
| `health/` | First-aid protocol | `## First aid steps` (numbered list) | `guide_key` |
| `disaster/` | Disaster alert | `## Steps` (numbered list) | `guide_key`, optional `damage_estimate` |
| `scheme/` | Scheme card | `## Benefits`, `## Eligibility`, `## Documents required` (list), `## How to apply` (numbered list) | `guide_key` |
| `education/` | Tutorial | `## Summary` | `guide_key`, `duration`, optional `quiz_id`, `crop` |

```markdown
---
guide_key: dog_bite
---
# Dog and Animal Bites: Rabies Prevention

Intro paragraph...

## First aid steps
1. Wash the wound with soap and running water for 15 minutes.
2. ...

## Do not
- Sections without a recognised name stay searchable text only.
```

The card shows the list items exactly as written, so keep each step short and
self-contained. Other sections such as `## Do not` or `## Prevention` are not
rendered on the card, but the knowledge agent retrieves them as grounding for
the advisory text.

A file whose `guide_key` matches an entry in `app/core/seed_data.py` replaces
that entry everywhere, so the corpus never holds two competing versions of one
guide. The seed keys are `snake_bite`, `pesticide_poisoning`, `heat_stroke`,
`lightning`, `flood`, `tut_1`, `tut_2`, and for schemes `pm_kisan`,
`pm_fasal_bima_yojana` and `subsidized_agriculture_machinery_scheme`. The
seed data remains the fallback when no file overrides it.

A file without a `guide_key` is searchable reference material only, like
`health/pesticide_safe_handling.md`.

For a new health or disaster guide to be reachable when the embedding model
misreads a short colloquial query, add its keywords to the keyword fallback in
`app/agents/agents.py` (the planner's `health_kw` list and the agent's
`keyword_rules`).

## Do not put volatile data here

Mandi prices, weather readings, and sensor telemetry change constantly and are
served live by their own agents. A price embedded into the vector store is a
price the system will still be quoting months later.

## Applying changes

Added or edited files are picked up on backend restart. Only new or modified
text costs API quota — document vectors are cached on disk in
`backend/.rag_cache/`, keyed by content hash.

Verify what was indexed:

```bash
curl "http://localhost:8000/api/rag/status"
curl "http://localhost:8000/api/rag/search?q=your+test+query"
```
