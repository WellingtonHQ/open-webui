# Wellington — custom OpenWebUI fork

A fork of [open-webui/open-webui](https://github.com/open-webui/open-webui) that adds
search, web-fetch, and document tooling. It is built to stay easy to sync with upstream
while keeping all customizations.

Every customization lives in exactly one of two places:

1. **This folder (`wellington/`)** — self-contained configs, assets, and tooling.
   Moving it never touches the upstream tree.
2. **A small, fixed set of core-file edits** — the only files modified inside the
   upstream source tree (kept minimal so rebase conflicts stay small and predictable).

---

## Layout

```
wellington/
├── functions/            # OpenWebUI Function(s) — import via Admin → Functions
│   └── better_qwen3_8.py
├── skills/               # OpenWebUI Skill(s) — import via Admin → Skills
│   └── search_the_web.md
├── tools/                # OpenWebUI Tool specs + helpers
│   ├── web_search.spec.json
│   ├── crawl4ai.spec.json
│   ├── make_inline_specs.py
│   ├── c4ai-llm-patch/     # Crawl4AI thinking/LLM hook (site-packages .pth)
│   └── c4ai-monitor-patch/ # Crawl4AI monitor retention patch (24h, version-pinned)
├── searxng-config/
│   └── settings.yml      # SearXNG config template (__SEARXNG_*__ placeholders, expanded at start)
├── docker-compose.custom.yaml   # full stack (owui + docling + crawl4ai + searxng + mcpo)
├── mcpo.json             # MCP→OpenAPI bridge config (Holds the Crawl4AI Bearer token) [gitignored]
├── mcpo.json.example     # committed template for mcpo.json
├── .env.example          # template for the REPO-ROOT .env (all custom vars + placeholders)
├── memory.md             # local agent notes [gitignored]
├── sync.ps1              # Windows: status / rebase onto upstream/main
├── sync.sh               # Linux/macOS: status / rebase onto upstream/main
├── UPGRADING.md          # Docker dependency upgrade runbook (for coding agents)
└── README.md
```

The live secrets live in the **repo-root `.env`** (one directory up), which is gitignored.

---

## Core edits (the only upstream files modified)

These are the *only* files outside `wellington/` that differ from upstream. They are the
entire sync-conflict surface. Preserve them on every rebase.

| File | Change |
| --- | --- |
| `Dockerfile` | `NODE_OPTIONS=--max-old-space-size=8192` (SvelteKit build heap bump) |
| `backend/open_webui/utils/middleware.py` | Crawl4AI markdown-surfacing fix + MCP tool-result citation parsing (see below) |
| `backend/open_webui/models/automations.py` | persistent-chat automation |
| `backend/open_webui/utils/automations.py` | persistent-chat automation logic |
| `backend/open_webui/routers/tasks.py` | automation / title-generation task wiring |
| `src/lib/apis/automations/index.ts` | automations API client |
| `src/lib/components/AutomationModal.svelte` | automations UI |
| `src/lib/components/automations/AutomationEditor.svelte` | automation editor UI |
| `src/lib/components/automations/ChatTargetDropdown.svelte` | chat-target picker (new file) |
| `src/lib/components/common/Select.svelte` | select component tweak |
| `src/lib/components/layout/Sidebar/ChatItem.svelte` | generated-title display |
| `src/lib/components/chat/Messages/Citations.svelte` | cited-only filter for web sources (see below) |
| `src/lib/components/chat/Messages/ResponseMessage.svelte` | passes message text into Citations |
| `src/lib/i18n/locales/en-US/translation.json` | i18n strings |

> Note: `requirements.txt`, `backend/open_webui/retrieval/web/utils.py`,
> `backend/open_webui/tools/builtin.py`, `backend/open_webui/config.py`, and
> `src/lib/components/admin/Settings/WebSearch.svelte` were **reverted to pristine
> upstream** (the earlier Scrapling web-fetcher was removed). They no longer count
> against the conflict surface.

### MCP sources — cited-only display

Web search now runs on an MCP server (see `skills/search_the_web.md`) instead of the
built-in `search_web` tool, but citations only existed for built-in tools — so answers
that used it showed no Sources list at all. The table rows above restore that:

- **Backend** (`get_citation_source_from_tool_result`, MCP branch; helpers
  `_collect_url_entries` / `_build_url_citation_sources` / `_parse_markdown_url_citations`):
  any result with `tool_type == 'mcp'` is scanned for wellisearch-style markdown blocks
  (`Title:` / `URL:` / `Snippet:`) and turned into one citation per URL, labeled
  `<server>/<tool>`. The gate keys on the MCP tool *type*, not a specific server: any other
  MCP tool that returns the same block format gets citations for free. Tools with a
  different result shape deliberately get **no** citations rather than guessed ones — add a
  small adapter branch per tool if one of them needs sources (generic "extract every URL"
  was rejected to avoid false positives and `[n]` positional drift).
- **Frontend** (`Citations.svelte`, plus the `content` prop in `ResponseMessage.svelte`):
  for URL sources, the Sources pill + expandable list show **only the URLs the model
  actually cited** as `[n]` in its answer; the pill is hidden entirely when it cites
  nothing. The unfiltered list still drives positional chip lookups (clicking a `[n]` opens
  that source). Knowledge-base / file sources keep their original show-all behavior.

---

## Setup

### 1. Environment secrets — repo-root `.env`

Create `<repo>/.env` from the template (do **not** commit it):

```bash
cp wellington/.env.example .env
# then edit .env and fill in real values
```

Required variables (and who consumes them):

| Variable | Used by |
| --- | --- |
| `WEBUI_SECRET_KEY` | OpenWebUI (JWT signing) |
| `MCPO_API_KEY` | mcpo REST bridge auth |
| `CRAWL4AI_API_KEY` | Crawl4AI MCP server **and** the Bearer token in `wellington/mcpo.json` |
| `DOCLING_API_KEY` | docling-server |
| `SEARXNG_SECRET` | SearXNG `server.secret_key` |
| `SEARXNG_BRAVE_API_KEY` | SearXNG `braveapi` engine key |

### 2. `wellington/mcpo.json` (Crawl4AI token)

mcpo does **not** support env-var substitution in its JSON config, so the real
`CRAWL4AI_API_KEY` must be pasted in here:

```bash
cp wellington/mcpo.json.example wellington/mcpo.json
# replace CHANGE-ME-CRAWL4AI_API_KEY with the SAME value as CRAWL4AI_API_KEY in .env
```

`wellington/mcpo.json` is gitignored; `wellington/mcpo.json.example` is the committed template.

### 3. SearXNG config

`wellington/searxng-config/settings.yml` is a **template**: the two SearXNG secrets are
`__SEARXNG_SECRET__` / `__SEARXNG_BRAVE_API_KEY__` placeholders (current SearXNG no longer
supports the legacy `!process "env:…"` YAML tag, which used to crash-loop the container).
The compose `entrypoint` expands them from the `SEARXNG_SECRET` / `SEARXNG_BRAVE_API_KEY`
env vars (injected from the repo-root `.env`) into a container-local file at start, then
execs the image's entrypoint. No real secrets are stored in the tracked file.

### 4. Crawl4AI LLM patch (optional)

`wellington/tools/c4ai-llm-patch/` contains a thinking/LLM hook for Crawl4AI's LLM content
filter (`f:llm`). It is **already mounted** by the compose file: a `.pth` in site-packages
auto-loads `c4ai_llm_thinking.py`, which injects Qwen3.8 thinking control
(`LLM_REASONING_EFFORT` etc.) into litellm's `extra_body`. The hook is a no-op unless
`LLM_REASONING_EFFORT` is set, and it swallows its own import errors — so after a Crawl4AI
version bump you must *verify* it still works (see `UPGRADING.md`).

### 5. Crawl4AI monitor patch (retention)

`wellington/tools/c4ai-monitor-patch/monitor.py` is a **version-pinned snapshot** of the
`unclecode/crawl4ai:0.9.2` image's `/app/monitor.py`, with a 3-line change: request/error
history is now kept for **24h** instead of 5 minutes. Without it, the monitor's in-memory
deques are purged every 5 min (`server.py` `_timeline_updater`), so the dashboard's
"Requests" panel is empty whenever you look at it (only the Redis-backed endpoint stats
survive). The file is bind-mounted over the container's `/app/monitor.py`.

**Bumping the `unclecode/crawl4ai` image tag without re-applying this patch silently
reverts retention to 5 minutes** — see `UPGRADING.md` for the re-apply steps.

---

## Run

Run from the **repo root** so Docker Compose reads the repo-root `.env`:

```bash
docker compose -f wellington/docker-compose.custom.yaml up -d
```

Services started:

| Service | Purpose |
| --- | --- |
| `open-webui` | the app (built from the repo-root `Dockerfile`; `build.context: ..`) |
| `docling-server` | document conversion (PDF/DOCX → markdown) |
| `crawl4ai` | web → markdown crawler (exposed as the `md`/`crawl` tools via mcpo) |
| `searxng` | metasearch engine (JSON API) |
| `searxng-mcp` | SearXNG MCP server |
| `mcpo` | MCP → OpenAPI/REST bridge that exposes the above as OpenWebUI tools |

The in-app **web-fetch engine is `safe_web`** (set in the compose `environment`).
The earlier Scrapling stealth fetcher was removed; Crawl4AI is the heavy web-fetch
tool, reachable through mcpo as the `md` / `crawl` tools.

> **mcpo caveat:** mcpo opens its MCP sessions (crawl4ai, searxng-mcp) **once at
> startup and gives up on failure** — it does not reliably auto-reconnect. If the
> `crawl4ai` (or `searxng-mcp`) container is ever recreated, restart mcpo afterwards
> (`docker compose -f wellington/docker-compose.custom.yaml restart mcpo`), otherwise
> the `/crawl4ai/*` and `/searxng/*` routes return 403/500 ("MCP session is not
> available") until the next mcpo start.

---

## Re-importing functions / skills / tools

OpenWebUI loads Functions, Skills, and Tools **from its database, not from these files**.
The files in `wellington/functions|skills|tools` are the source of truth. After a fresh
install or a rebase, re-import them through the UI:

- **Functions** → Admin → Functions → import `wellington/functions/*.py`
- **Skills** → Admin → Skills → import `wellington/skills/*.md`
- **Tools** → Admin → Tools → import `wellington/tools/*.spec.json`
  (regenerate with `python wellington/tools/make_inline_specs.py` if you change them —
  run it from the `wellington/` directory)

---

## Syncing with upstream

The branch tracks `upstream/open-webui` (`origin` is your fork). Use the helper:

```bash
# Windows (PowerShell)
.\wellington\sync.ps1                 # status + fetch only
.\wellington\sync.ps1 -Rebase         # rebase onto upstream/main

# Linux / macOS
bash wellington/sync.sh               # status + fetch only
bash wellington/sync.sh --rebase      # rebase onto upstream/main
```

Or manually:

```bash
git fetch upstream
git rebase upstream/main
# resolve conflicts in the 14 core files listed above, then:
git rebase --continue
```

**Why this stays easy:**
- All custom assets are in `wellington/` (untracked-by-upstream), so upstream never
  conflicts with them.
- Only the 14 core files above can conflict, and each change is small and localized.
- The helper refuses a dirty tree unless you explicitly `--force`/`-Force`
  (it then stashes and restores your uncommitted work).

**After a rebase, always:**
1. Rebuild the image (`docker compose -f wellington/docker-compose.custom.yaml build`).
2. Re-import any Functions/Skills/Tools if you changed them.
3. `git grep -in "scrapling\|patchright\|browserforge\|curl-cffi" backend src Dockerfile`
   should return nothing (Scrapling must stay removed).
4. If any image tag changed, re-verify the version-pinned Crawl4AI patches and the
   mcpo restart rule — see `UPGRADING.md`.

---

## Secrets checklist

- Repo-root `.env` — **gitignored** (all six custom secrets).
- `wellington/mcpo.json` — **gitignored** (Crawl4AI Bearer token).
- `wellington/memory.md` — **gitignored** (local notes).
- `wellington/searxng-config/settings.yml` — contains **no** raw secrets (uses `!process "env:…"`).
- Committed templates (safe to share): `wellington/.env.example`, `wellington/mcpo.json.example`.

If you ever `git diff` a tracked file and see a real key, treat it as an incident:
rotate the key, move it to `.env`, and keep only the placeholder in the committed file.
