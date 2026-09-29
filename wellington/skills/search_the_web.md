Use this workflow whenever you need current or external information from the web.

## Tools available to you

All three come from wellisearch — it wraps both search providers and page crawling, so these are the only web tools you use.

- `search_web` — web search. By default it checks the local index first (zero cost, instant), then falls back to a provider gateway (tavily → brave → searxng) on a miss. Parameters:
  - `query` (required — the exact parameter name).
  - `search_mode` (optional, default `auto` — controls where results come from):
    - `auto` — local index first; provider gateway on a miss; degraded local-only fallback if all providers fail.
    - `provider` — bypass the local index entirely and force a live provider lookup (wider net, fresher results).
    - `local` — local index only; returns an error if there are no local rows (no provider fallback).
  - `num_results` (optional, default 5; pass `10` for the full list).
  - `max_age_days` (optional — ignore locally-indexed pages crawled more than N days ago; use for fast-moving topics).
  - `max_crawl` (optional — how many result URLs wellisearch indexes in the background on a miss; default 5, leave it alone).
  Returns a `results` Markdown block (Title/URL/Snippet, `---` separated) plus metadata: `source` (`local` | `tavily` | `brave` | `exa`), `degraded` (bool), `count`, and `last_crawled` dates for local hits.
- `fetch_page` — read one URL as clean Markdown. Parameters: `url` (required), `max_chars` (optional cap). Returns `{ok, url, title, markdown}`. Indexed pages return instantly from the local index; unknown URLs are crawled on demand and stored — the first read of a new URL can take a few seconds.
- `fetch_pages` — read several URLs in ONE call under a shared total character budget. Parameters: `urls` (required, array), `max_chars` (optional total budget — omit for full content), `per_page_chars` (optional per-page cap), `strategy` (optional: `smart` default, `head`, `tail`, `even`, `priority`). Returns one combined Markdown document, one clearly delimited section per page (URL/Title/---/content); each trimmed page carries a `[truncated — N chars omitted, strategy=X]` marker — treat trimmed content as incomplete.

## Workflow

1. **Search** — call `search_web` with a concise query and `num_results: 5`. It returns up to 5 candidate links (title, URL, snippet) — no page content.
   - Use 1–3 precise keywords; add a year if the topic is time-sensitive (e.g. "Debian AI code ban 2026").
    - If `degraded: true`, all live providers failed and the results are local-only: rephrase the query once and retry; if it is still thin, tell the user about the limitation.
    - If the results are poor or off-topic, reformulate the query (different keywords, or `max_age_days` for recency) and search again — at most 1–2 reformulations.
    - If you got local results but they are not relevant to the question, reissue the query with `search_mode: provider` to force a live provider lookup. Only do this when you genuinely want a wider net and/or more up-to-date results than the local index can provide — it costs provider credits and is slower.
2. **Evaluate** — pick the 2–5 most promising URLs from the snippets, preferring primary sources (official sites, project pages, changelogs, original publications) over aggregators and SEO content farms.
3. **Read** — for one page call `fetch_page(url)`; for several pages (up to ~5) call `fetch_pages(urls, ...)` in ONE call:
   - `max_chars`: total budget across all pages — 4000–8000 for a quick check, 15000+ only when you need deep detail.
   - `strategy`: `smart` (default) for general reading; `head` when the facts are at the top; `tail` for endings/conclusions; `even` for equal slices; `priority` for mixed content.
   Base your answer strictly on the returned content; never invent page content. If a read fails for a URL, skip it and try the next candidate.
4. **Synthesize** — answer the user's question using the retrieved content. Cite sources as inline Markdown links. If sources conflict, say so and present both positions rather than picking silently. For time-sensitive topics, prefer recent sources and mention the source date when known — wellisearch's `last_crawled` tells you how fresh each local page is.

## Rules

- Do not rely on just a search snippet. ALWAYS read at least 3 search results (one `fetch_pages` call, or `fetch_page` each) to get a detailed answer.
- Do not use `fetch_pages` for a single URL — use `fetch_page`.
- Prefer primary sources (official docs, original publications); ignore ads, aggregators, and redirect links.
- If no page can be read, tell the user which URLs failed instead of guessing the content.
