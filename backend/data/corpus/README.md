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
(`baai/bge-m3`) is multilingual, so a Hindi, Tamil, or Punjabi query matches
English source text directly, and the LLM translates the final advisory into
the farmer's selected language. Maintaining 11 translations of every document
is unnecessary.

Keep each document factual and attributable. Retrieved text is injected into
the prompt as authoritative source material, so anything inaccurate here
becomes an inaccurate recommendation to a farmer.

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
