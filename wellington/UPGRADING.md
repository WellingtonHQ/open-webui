# Wellington — Docker dependency upgrade runbook

Audience: **coding agents** (or humans) changing image versions or the mounted
Crawl4AI patches in `wellington/docker-compose.custom.yaml`.

Read this **before** touching any `image:` line, any `tools/c4ai-*-patch/` file, or
any `volumes:` mount on the `crawl4ai` service.

---

## Current pin matrix (as of 2026-08-20)

| Service | Image | Pinned? | Upgrade notes |
| --- | --- | --- | --- |
| `open-webui` | built from this repo (`build: ..`) | upstream commit | 12 modified core files — use the `sync.sh`/`sync.ps1` rebase workflow, see `README.md` |
| `docling-server` | `hwdsl2/docling-server:latest` | no | verify `DOCLING_API_KEY` + `POST /v1/convert` |
| `crawl4ai` | `unclecode/crawl4ai:0.9.2` | **YES** | two **version-pinned mounts** below — must be re-verified on every bump |
| `searxng` | `searxng/searxng:latest` | no | `settings.yml` placeholder expansion in the compose entrypoint |
| `searxng-mcp` | `isokoliuk/mcp-searxng:latest` | no | streamable HTTP `:3000/mcp` |
| `mcpo` | `ghcr.io/open-webui/mcpo:main` | no | connects to its MCP servers **once at startup and gives up** |

---

## Golden rules

1. **The two `crawl4ai` mounts are version snapshots.**
   - `tools/c4ai-monitor-patch/monitor.py` is a copy of the **pinned image's**
     `/app/monitor.py` with a 3-line diff (24h retention).
   - `tools/c4ai-llm-patch/` hooks `crawl4ai.content_filter_strategy.LLMContentFilter`
     and assumes `extra_args` is its 14th positional `__init__` parameter.
   Bumping the image tag without re-checking **both** is a *silent* regression.
2. **Restart `mcpo` after every `crawl4ai` (or `searxng-mcp`) recreate.** It does not
   reliably auto-reconnect; a stale session turns all `/crawl4ai/*` routes into
   403/500 (`"MCP session is not available"`).
3. **Never skip the post-upgrade verification checklist** (below). Several failures
   are silent: the LLM hook swallows its own exceptions; a missing monitor patch just
   reverts retention to 5 minutes with no error anywhere.

---

## Upgrade Crawl4AI (`unclecode/crawl4ai`)

### Steps

1. Pick the new tag (Docker Hub / upstream releases).
2. Extract the new image's `monitor.py` and overwrite the patch file:
   ```bash
   docker run --rm --entrypoint sh unclecode/crawl4ai:NEW -c "cat /app/monitor.py" \
     > wellington/tools/c4ai-monitor-patch/monitor.py
   ```
   (Avoid `docker cp` on Docker Desktop/Windows: copied files land read-only and
   in-container `rm`/`mv` can fail with EPERM.)
3. Re-apply the 3-line diff (table below) and confirm nothing else changed:
   ```bash
   git diff --no-index /dev/null wellington/tools/c4ai-monitor-patch/monitor.py   # sanity
   # or diff against the previous committed version:
   git diff wellington/tools/c4ai-monitor-patch/monitor.py
   ```
   Expected: exactly the 3 lines below differ from the pristine module.
4. Update the compose `image:` tag and the digest comment above it (lines ~50-53).
5. Recreate the service and **restart mcpo** (golden rule 2):
   ```bash
   docker compose -f wellington/docker-compose.custom.yaml up -d crawl4ai
   docker compose -f wellington/docker-compose.custom.yaml restart mcpo
   ```
6. Verify the LLM thinking hook (next section).
7. Run the **post-upgrade verification checklist**.

### The monitor patch — 3-line diff (re-apply on every bump)

Against pristine `0.9.2` `/app/monitor.py` (line numbers will drift — match on text):

| # | Pristine line | Patched line |
| --- | --- | --- |
| 1 | `self.completed_requests: deque = deque(maxlen=100)` | `self.completed_requests: deque = deque(maxlen=5000)  # Last 5000 (24h retention)` |
| 2 | `def _cleanup_old_entries(self, max_age_seconds: int = 300):` | `def _cleanup_old_entries(self, max_age_seconds: int = 86400):` |
| 3 | `self._cleanup_old_entries(max_age_seconds=300)` | `self._cleanup_old_entries(max_age_seconds=86400)` |

If the upstream module was refactored (renamed methods, different cleanup call),
adapt the intent: **`completed_requests` deque keeps ≥5000 entries, purge age = 86400 s**.
Re-derive the 3 lines from the new source; do not blindly sed.

### Verify the LLM thinking hook (`tools/c4ai-llm-patch`) on every bump

The hook (`c4ai_llm_thinking.py`) is fail-silent — a broken import produces **no log
output at all**. Check:

1. New image still has `crawl4ai/content_filter_strategy.py` with class
   `LLMContentFilter` and an `extra_args` parameter:
   ```bash
   docker run --rm --entrypoint sh unclecode/crawl4ai:NEW -c \
     "grep -n 'extra_args' /usr/local/lib/python3.12/site-packages/crawl4ai/content_filter_strategy.py | head"
   ```
   (site-packages path may differ — find it first:
   `sh -c "python -c 'import crawl4ai,os;print(os.path.dirname(crawl4ai.__file__))'"`.)
2. `extra_args` is still the **14th positional** `__init__` parameter (hook assumes index 13).
   If it moved, update the index in `c4ai_llm_thinking.py` (`len(args) >= 14`, `args[13]`,
   `args[:13] + (ea,) + args[14:]`).
3. Smoke-test `f:llm` through mcpo and confirm the filter runs (see checklist item 6).

---

## Upgrade mcpo (`ghcr.io/open-webui/mcpo`)

1. Bump the tag (or re-pull `:main`), then `up -d mcpo`.
2. Confirm auth still works with **`Authorization: Bearer <MCPO_API_KEY>`**
   (`X-API-Key` returns 401 — that is mcpo's expected behavior, not a bug).
3. If the MCP transport changed (SSE vs streamable HTTP), check the URLs in
   `wellington/mcpo.json` (crawl4ai: `http://crawl4ai:11235/mcp/sse`,
   searxng: `http://searxng-mcp:3000/mcp`) and the tool filters
   (crawl4ai: 5 tools filtered out; searxng: 3 tools filtered out).
4. `mcpo.json` supports **no env-var substitution** — the Crawl4AI Bearer token is
   pasted in there (gitignored; template: `mcpo.json.example`). Keep both in sync.
5. Run checklist items 4 and 5.

## Upgrade SearXNG / searxng-mcp

1. Bump, `up -d searxng searxng-mcp`, then **restart mcpo** (golden rule 2).
2. The compose entrypoint seds `__SEARXNG_SECRET__` / `__SEARXNG_BRAVE_API_KEY__` out of
   `wellington/searxng-config/settings.yml`. If the new SearXNG accepts the legacy
   `!process "env:…"` tag again you may revert to it — but keep the current mechanism
   working: placeholders must stay in the tracked file, and the generated
   `/run/searxng/settings.yml` must be non-empty or the container exits.
3. Run checklist item 5.

## Upgrade docling-server (`hwdsl2/docling-server`)

1. Bump, `up -d docling-server`.
2. Verify `POST /v1/convert` with `DOCLING_API_KEY` and that OpenWebUI's document
   pipeline still works (`DOCLING_API_URL=http://docling-server:5001/v1/convert`).

## Upgrade the OpenWebUI app itself

Not an image bump: `wellington/sync.sh --rebase` / `.\wellington\sync.ps1 -Rebase`
(rebase onto `upstream/main`, resolve conflicts in the 14 core files listed in
`README.md`), then rebuild:

```bash
docker compose -f wellington/docker-compose.custom.yaml build open-webui
docker compose -f wellington/docker-compose.custom.yaml up -d open-webui
```

Re-import Functions/Skills/Tools if they changed (see `README.md`).

---

## Post-upgrade verification checklist (run ALL, in order)

Environment for the snippets: PowerShell 5.1, Docker Desktop, CWD = repo root
(`.env` is at the repo root). Verified working 2026-08-20.

1. **Stack up; crawl4ai healthy:**
   ```powershell
   docker compose -f wellington/docker-compose.custom.yaml ps
   ```

2. **Monitor patch active in the running process** (expect `True | True`):
   ```powershell
   docker exec crawl4ai python -c 'import inspect,monitor; s=inspect.getsource(monitor); print("retention24h:", "86400" in s, "| maxlen5000:", "maxlen=5000" in s)'
   ```

3. **Retention survives >5 min** (the original bug — entries purged at 5 min):
   ```powershell
   $tok = (docker exec crawl4ai printenv CRAWL4AI_API_TOKEN).Trim()
   Invoke-RestMethod -Uri "http://localhost:11235/crawl" -Method Post -Headers @{ Authorization = "Bearer $tok" } -ContentType "application/json" -Body '{"urls": ["https://example.com"]}' | ConvertTo-Json -Depth 3
   Invoke-RestMethod -Uri "http://localhost:11235/monitor/requests?status=completed&limit=5" -Headers @{ Authorization = "Bearer $tok" }
   # wait >6 minutes, then re-run the /monitor/requests call — the entry must still be there
   ```

4. **mcpo → crawl4ai** (expect HTTP 200 + `markdown` in body):
   ```powershell
   $mcpo = ((Get-Content .env | Select-String "^\s*MCPO_API_KEY=").Line -replace "MCPO_API_KEY\s*=\s*","").Trim('"').Trim("'")
   Invoke-WebRequest -Uri "http://127.0.0.1:8085/crawl4ai/md" -Method Post -Headers @{ Authorization = "Bearer $mcpo" } -ContentType "application/json" -Body '{"url": "https://example.com"}' -UseBasicParsing
   ```

5. **mcpo → searxng** (expect HTTP 200 + results):
   ```powershell
   Invoke-WebRequest -Uri "http://127.0.0.1:8085/searxng/searxng_web_search" -Method Post -Headers @{ Authorization = "Bearer $mcpo" } -ContentType "application/json" -Body '{"query": "crawl4ai", "num_results": 2}' -UseBasicParsing
   ```

6. **LLM filter smoke test** (only if `LLM_REASONING_EFFORT` is set — expect the crawl
   to succeed; a `crawl4ai` log line showing the `f:llm` filter running confirms the hook):
   ```powershell
   Invoke-WebRequest -Uri "http://127.0.0.1:8085/crawl4ai/md" -Method Post -Headers @{ Authorization = "Bearer $mcpo" } -ContentType "application/json" -Body '{"url": "https://docs.crawl4ai.com/core/quickstart", "f": "llm"}' -UseBasicParsing
   ```

7. **Dashboard sanity** (human): `http://localhost:11235/monitor/` — "Requests" panel
   shows recent entries, not an empty list.

---

## Known gotchas (learned the hard way, 2026-08-20)

- **mcpo gives up after a failed first connect** to its MCP servers. Symptom: 403 on
  `/crawl4ai/*` (looks like auth!) and 500 `MCP session is not available`. Fix:
  restart mcpo **after** crawl4ai is healthy.
- **mcpo auth header** is `Authorization: Bearer <MCPO_API_KEY>`; `X-API-Key` → 401.
  Crawl4AI itself takes `Authorization: Bearer <CRAWL4AI_API_TOKEN>` (token value ==
  `CRAWL4AI_API_KEY` in `.env`).
- **Missing monitor patch = silent 5-min retention.** Symptom: dashboard "Requests"
  panel empty while "Endpoint Analytics" still has data (stats persist to Redis,
  requests are in-memory).
- **LLM hook is fail-silent** (`try/except: pass`) — absence of errors proves nothing;
  run checklist item 6.
- **Docker Desktop (Windows)**: `docker cp` into containers lands read-only; in-container
  `rm`/`mv`/`os.remove` can fail with EPERM (file-share quirk). Temp files left behind
  vanish on the next container recreate.
- **PowerShell quoting**: multi-line inline Python in `docker exec ... sh -c "..."` gets
  mangled; prefer single-quoted `python -c` one-liners or a script file.
- **PowerShell 5.1 (not pwsh 7)** on this host: `(Get-Date).UnixTimestamp` does not
  exist; use `[DateTimeOffset]::UtcNow` / `[DateTimeOffset]::FromUnixTimeSeconds(...)`.
- **`wellington/mcpo.json` has no env substitution** — paste the real token; keep the
  gitignored file and `mcpo.json.example` in sync.
- **searxng entrypoint**: if the sed expansion produces an empty
  `/run/searxng/settings.yml`, the container exits — keep the two
  `__SEARXNG_*__` placeholders in the tracked `settings.yml`.
