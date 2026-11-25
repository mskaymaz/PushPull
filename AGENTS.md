# Repository Engineering Protocol — PushPull

> **SSOT (Single Source of Truth):** Binding engineering rules for all AI coding agents (Antigravity, Codex, Copilot, Claude Code) working on `PushPull`.

## 1. Session & Scope Shorthands
- **Bismillah / Eko:** Inspect and verify the exact current state of relevant files and `git fetch` / `git status -sb` first. Report briefly in bullets:
  1. Local vs. remote repo status (1-2 lines).
  2. Where the previous session ended.
  3. Next task in `tasks.md`.
  4. Readiness to proceed.
- **Eko Tek Madde (Strict Scope Lock):** Work ONLY on the single explicitly requested task/item. Do NOT scan unrelated files, do NOT expand scope autonomously, and do NOT proceed to the next item until the current one is verified.
- **Session Title (`YYMMDD-Index`):** Format every new session title as `YYMMDD-Index Topic Summary` (e.g., `261123-0 ...`).
- **Consultation Gate:** When the user asks for opinions or discusses design, do NOT modify or create files until explicit confirmation (`Bismillah başla`, `başlayalım`, `yap`, `proceed`).
- **Anti-Flattery & Honesty:** Act as an objective, rigorous engineer. No praise or filler. State risks, flaws, and better technical alternatives directly.

## 2. Token Economy & SafePatch Protocol (SPP)
- Keep replies concise, bulleted, and **strictly <= 10 lines total** (1-3 lines for Yes/No, max 1-2 lines/single sentence per bullet). No unrequested elaboration unless asked.
- Read ONLY target files and immediate context; avoid repo-wide scans for small/targeted tasks.
- **SPP:** 1) Verify target files and exact lines -> 2) Apply smallest safe patch -> 3) Verify diff/run/tests -> 4) Report briefly. Fail-fast on errors; NEVER guess.
- **`>150` Line Diff-Only Rule:** For any file longer than 150 lines, NEVER rewrite the whole file; edit ONLY the affected functions or blocks.
- **Root Cause Mandate:** During debugging, identify and fix the root cause; NEVER patch symptoms by guessing.
- **File Line Limits:**
  - `350-400` lines: Early warning / responsibility split check (do NOT over-fragment cohesive logic into micro-files).
  - `450` lines: Hard limit for components, services, workers, and helpers.
  - `600` lines: Absolute ceiling for complex stateful screens/windows.
- Explicit user permission required before: repo-wide refactoring, adding/removing dependencies, or editing core config files.

## 3. Git Workflow & Quality Gate
- Active development runs directly on **`main`** unless the user explicitly requests a feature branch. Verify branch and `git status` before starting.
- Use **SSH** (`git@github.com:...`) for remotes; verify `user.name` / `user.email` before commits.
- **Local-First Verification:** Every change must be verified locally (run app / real git command test / diff check). Mock-only tests are NOT accepted as Done.
- NEVER run `git commit`, `git push`, or merge/rebase without explicit user approval.
- **Commit Format:** Summarize the change clearly in Turkish followed by `(yy/mm/dd_hh.mm)` (e.g., `Yeni kural eklendi (26/11/25_15.42)`).

## 4. Universal Multilingual & Interface Base
- **Mandatory i18n (`TR / EN / AR`):** Application MUST support **TR, EN, and AR (Arabic)** from day one across all UI strings, tooltips, and status badges.
- **RTL / BiDi:** Use logical layout directions (`Qt.LayoutDirection` / `start`/`end`, never hardcoded `left`/`right`) for full Arabic RTL support from day one.
- **Language Labels:** NEVER use flag emojis or country codes (`TRTR`, `GBEN`, `SAAR`). Render plain **`TR`**, **`EN`**, **`AR`** only.

## 5. Project Context — PushPull
- **Scope & Isolation:** Standalone Python desktop application (`D:\Code\mskaymaz\PushPull`). Do NOT couple with other ecosystem repos or run a `localhost`/HTTP server.
- **Tech Stack:** **Python 3.11+** + **PySide6** (Qt for Python). Standard `subprocess` for `git` CLI execution inside `QThread` / `QRunnable` workers so the UI never freezes.
- **Core UI Layout:**
  - Compact vertically-scrollable repo table (`15-20+` repos) with Add/Remove and Up/Down reordering.
  - Columns: `Repo` | `Fetch` | `Analyze` | `Stash` | `Pull` | `Commit` | `Push` | `Status`.
  - **Accordion Log Drawer:** Clicking a repo row/status badge expands an inline drawer directly beneath that row showing its independent git/analysis output and errors.
  - **Commit Message Popover:** Checking `Commit` opens an inline/floating text input; if left empty, auto-generates `Auto-commit: YYYY-MM-DD HH:MM`.
- **Safe Execution Pipeline:** Fixed per-repo order: `Fetch` -> `Analyze (ahead/behind + dirty count)` -> `Stash (if selected)` -> `Pull` -> `Commit` -> `Push`. Stop subsequent steps for that repo on failure and auto-expand its accordion.
- **Persistence:** Store repo list, display order, and preferences in a local `repos.json` file.

## Ekosistem Telemetri & Dağıtım Kuralı (IST-013 / IST-016 / IST-017)
- Uygulama güncelleme veya yeni sürüm yayınlama işlerinde kök dizindeki `ECO_TELEMETRY_GUIDE.md` (ve merkezi `D:\Code\istisare\istisareler\017-eco-sdk-istemci-entegrasyon-rehberi.md`) kuralları **zorunlu** olarak uygulanır.
- Kapanışta telemetri atılmaz; açılışta `launch_count` biriktirilip ilk/yeniden kurulumda, sürüm değişiminde ve 7 günde 1 gönderilir. Ayarlara opt-out anahtarı/pop-up konulmaz (mağaza uygulamalarında `privacy.html` & Data Safety beyanı korunur).
