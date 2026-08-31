# Meridian RAG Evaluation Set

Ground-truth question set for evaluating retrieval-augmented generation
over the `company/` knowledge base (Meridian Data — a fictional 102-file
corpus with deliberate imperfections: stale docs, terminology drift,
aliases, contradictions, indirect meeting-note facts).

- **File:** `meridian_rag_eval.jsonl`
- **Count:** 70 questions
- **Format:** one JSON object per line

## Schema

```jsonc
{
  "id": "Q-023",                       // stable identifier, never renumber
  "question": "...",                   // user query, phrased naturally
  "expected_answer": "...",            // compact reference answer
  "answer_facts": ["..."],             // atomic facts a correct answer must contain
                                       //   (case-insensitive substring check)
  "gold_sources": ["company/..."],     // docs the answer is grounded in
                                       //   (retrieval must hit at least one)
  "supporting_sources": ["company/..."], // additional supporting docs (bonus, not required)
  "distractor_sources": ["company/..."], // docs that look relevant but carry stale,
                                         //   wrong, or contradictory info
                                         //   (hitting these should lower the score)
  "category": "conflict_resolution",   // see taxonomy below
  "difficulty": "easy|medium|hard",
  "notes": "..."                       // free-text: what makes this hard, why
}
```

## Category taxonomy (70 questions)

| Category | Count | What it tests |
|---|---|---|
| `single_doc_factual` | 12 | Baseline retrieval — the answer sits cleanly in one doc. |
| `multi_doc_synthesis` | 9 | Answer requires stitching 2–3 docs together. |
| `conflict_resolution` | 10 | Older doc contradicts newer doc; RAG must prefer the current one. |
| `temporal_current_vs_deprecated` | 7 | Deprecated-flagged docs vs current. |
| `cause_effect_chain` | 7 | Incident → postmortem → ADR → service change. |
| `ownership` | 5 | "Who owns X?" — including deliberate ambiguity (Aurora). |
| `alias_resolution` | 5 | Aurora = ingest-api = events-api; workspace = tenant = organization. |
| `indirect_meeting_only` | 5 | Facts appearing ONLY in meeting notes. |
| `numeric_precision` | 5 | Exact figures where different docs disagree on granularity. |
| `unanswerable` | 5 | Plausible-sounding queries the KB does NOT cover. Refusal expected. |
| **total** | **70** | |

## Recommended metrics

The eval is grader-agnostic. Suggested defaults for a local pipeline
running Qwen 2.5 7B as the generator:

**Retrieval (most important — this is where a simple local RAG usually fails):**

- `recall@k` — fraction of questions where at least one `gold_sources` doc
  is in the top-k retrieved chunks. Report for k ∈ {3, 5, 10}.
- `precision@k` — fraction of top-k retrievals that are gold or supporting.
- `mrr` — mean reciprocal rank of the first gold source across the set.
- `distractor_hit_rate` — % of retrievals that surface a `distractor_sources`
  doc in the top-k. Lower is better; this is where the messy KB earns its
  keep.

**Generation (deterministic, fast, works fine for a 7B model):**

- `answer_fact_coverage` — for each question, fraction of `answer_facts`
  present as case-insensitive substrings in the generator's output.
  Aggregate as mean over the set.
- `refusal_precision` on the `unanswerable` bucket — % where the answer
  contains a refusal marker (from `answer_facts`) AND does not assert a
  fabricated concrete fact.

**Optional (only if you wire it up later):**

- LLM-as-judge scoring the generator's answer against `expected_answer`.
  If used, the judge model MUST be stronger than the generator — do NOT
  grade Qwen-7B with Qwen-7B.

Break every metric down by `category` and by `difficulty` — that's where
the interesting failure modes show up.

## Runner sketch (retriever-agnostic)

```python
import json, pathlib

records = [json.loads(l) for l in open("evals/meridian_rag_eval.jsonl")]

def evaluate(records, retrieve, generate, k=5):
    """
    retrieve(question: str) -> list[str]           # returns doc paths, top-k first
    generate(question: str, contexts: list[str])   # returns the model's answer
    """
    stats = {"recall_at_k": 0, "fact_cov": 0.0, "distractor_hits": 0, "refusal_ok": 0}
    per_cat = {}

    for r in records:
        retrieved = retrieve(r["question"])[:k]
        answer = generate(r["question"], retrieved).lower()

        gold = set(r["gold_sources"])
        distractors = set(r["distractor_sources"])
        hit_gold = bool(gold & set(retrieved)) if gold else True
        hit_distractor = bool(distractors & set(retrieved))

        fact_cov = (
            sum(f.lower() in answer for f in r["answer_facts"]) / len(r["answer_facts"])
            if r["answer_facts"] else 0.0
        )

        if r["category"] == "unanswerable":
            refused = any(f.lower() in answer for f in r["answer_facts"])
            stats["refusal_ok"] += int(refused)
        stats["recall_at_k"] += int(hit_gold)
        stats["distractor_hits"] += int(hit_distractor)
        stats["fact_cov"] += fact_cov
        per_cat.setdefault(r["category"], []).append(fact_cov)

    return stats, per_cat
```

Plug your FAISS/Qdrant retriever and Qwen generator in, run over the
JSONL, and print `stats` normalised by count plus per-category means.

## Housekeeping

- Every path in `gold_sources` / `supporting_sources` / `distractor_sources`
  is a repo-relative POSIX path under `company/`.
- Rerun validity after any doc rename:
  ```bash
  python -c "
  import json, pathlib
  for line in open('evals/meridian_rag_eval.jsonl'):
      r = json.loads(line)
      for k in ('gold_sources','supporting_sources','distractor_sources'):
          for p in r.get(k, []):
              assert pathlib.Path(p).exists(), (r['id'], p)
  print('ok')
  "
  ```
- `id`s are stable: never renumber, only append. If a question is
  retired, mark it in `notes` but keep the id.

## Coverage hotspots baked in

The eval targets these deliberate messes in the KB (see `company/_CANON.md`
§13 for the full list):

- ClickHouse cluster size (4 vs 6 nodes)
- Ledger usage-counter source of truth (Redis → Postgres, ADR-0044)
- API v2 EOL date (2026-05-20 in ADR-0051 vs 2026-11-01 currently)
- Deploy process (Jenkins vs ArgoCD; both runbooks retained)
- Auth service naming (identity-service / Sentry codename → Gatekeeper)
- Aurora ownership ambiguity (Platform / Ingest / Data)
- Terminology drift (workspace / organization / tenant / account)
- "Project Kraken" (ClickHouse — not the EKS migration)
- Observability stack (New Relic → Datadog)
- Incident financial numbers (round in canon, precise in incident/postmortem docs)
- Meeting-only nuggets (SEC-217 Aurora rate-limit bypass; Sunday Ledger CPU)
