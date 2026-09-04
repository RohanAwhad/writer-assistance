# Integration evidence: M-INT006-INTEGRATION (milestone M3 — INT-006 container deployment + public exposure)

Reviewer-owned INTEGRATION RUN (independent of builder reports), 2026-09-04, human-authorized: live AI calls (DeepSeek + Vertex, real cost accepted), public Cloudflare DNS CNAME + tunnel ingress creation for `writer-assistance.rohanawhad.com` (original name; renamed per H36, see Addendum), and the full §11.2 steps 19-23. Evidence files under `logs/hai-build-loop/`: `m6-container.log` (container stdout incl. uvicorn access log), `m6-step19.out`, `m6-freshboot.out`, `m6-step20.out`, `m6-step21.out`, `m6-step22.out`, `m6-step23.out`, screenshots `screens/m6-s21-*.png`. No code/spec/.hai/devlogs files modified; nothing committed.

## Verdict

**PASS_WITH_WARN** — 1 WARN + 2 NIT. All deployment, gate, persistence, and live-AI behaviors verified (in-container on 127.0.0.1:8000 AND through the public Cloudflare tunnel on the reserved hostname). The single WARN is an **infra follow-up accepted by the human**: no Cloudflare edge TLS certificate has ever been issued for any `*.assistance.rohanawhad.com` hostname (pre-existing; affects the old `hai.writer.assistance.rohanawhad.com` too), so the §11.3 step-23 "over https" wording was evidenced over **public http through the tunnel**; the https leg + Secure-cookie-on-public re-verification is queued behind a certificate the human will order in the dashboard (API token lacks SSL perms — error 9109). Human decision recorded: "Accept http-public evidence; cert is a follow-up".

## Environment

- Commit/worktree identity: HEAD `576e7b4` (INT-006 M2); code = M1 (auth gate/static) + M2 (Dockerfile). No code or spec files modified by this run; nothing committed. `.hai/state.yaml` also carries INT-008 (ignored per instructions).
- Image: `writer-assistance:live` built fresh from repo root (`docker build`, all layers cached from the M2 smoke build); container `writer-assistance-live` (id 3de6fc763b96), `--network host`, `--restart unless-stopped`, named volume `writer-assistance-data:/data`.
- Environment variable names present (never values): `backend/.env` holds `AUTH_API_KEY` + `ANTHROPIC_MODEL` (value `claude-sonnet-5` — DEC-017); `~/.bashrc` exports `DEEPSEEK_API_KEY`, `ANTHROPIC_VERTEX_PROJECT_ID`, `ANTHROPIC_SMALL_FAST_MODEL` (value `claude-sonnet-5@default`), `GOOGLE_VERTEX_LOCATION`, `CLOUDFLARE_*`. In-container: `DEEPSEEK_MODEL` unset → R-073 default `deepseek-v4-flash` in force for every deepseek call (ASM-012 accepted id, re-confirmed by live calls). **Never** `-e ANTHROPIC_MODEL` — the env-file's `claude-sonnet-5` was the only in-container `ANTHROPIC_MODEL` source (verified in-container).
- **Vertex auth inside the container (exact approach)**: host ADC exists at `~/.config/gcloud/application_default_credentials.json` (host shell `GOOGLE_APPLICATION_CREDENTIALS` unset — google-auth default path). The **single ADC file** is bind-mounted read-only: `-v $HOME/.config/gcloud/application_default_credentials.json:/gcloud-creds.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/gcloud-creds.json`. Readable by the container's non-root `writer` (uid 1000 == host uid 1000, file 0600) — verified `test -r /gcloud-creds.json` in-container (m6-step20.out) and proven by live Vertex calls (201 ×2). Nothing baked into the image (ASM-014); only the one ADC file is exposed to the container, not the whole `~/.config/gcloud`.
- Cloudflare: tunnel `3a159844-e265-4501-83e1-cb80c4a0267f` (`minisforum_local_tunnel`, status healthy), cloudflared host systemd active, remote-managed config. Hostname `writer.assistance.rohanawhad.com` (DEC-020/H34).
- Playwright: chromium (headless) via the repo's `.hai/node_modules/playwright` (browsers in ms-playwright cache), scripts run from `/tmp/opencode` (removed after the run).

## Fixture

- `/tmp/opencode/m6-fixture/` (docker-copied into the container at `/tmp/m6-fixture`, imported by container path): `intro.md`, `market.md`, `archive/remote-work.md` (3 files incl. subdir `archive/`), md5 baseline `08eee99a…/c90e5fc4…/2a6bc5db…`. Host fixture tree removed after the run; container copy still on the container fs.
- Local dev DB baseline md5 `4cea2ff4e71f710e3f81f09002bc36f1` — **unchanged at end** (never mounted in; DEC-023 respected).
- Objects (container DB `/data/writer-assistance.db`, named volume): 1 project "M6 Container Journey" (id 1), 3 imported file resources, 5 lens-proposal rows (final deepseek set — `propose_lenses` replaces prior `proposed` rows per doc).

## Commands and results

| Command | Exit/result | Evidence |
|---|---|---|
| `docker build -t writer-assistance:live .` (repo root) | success (cached); image sha256:1d6c227c… | build log |
| image secrets inspection: `docker image inspect` env config + `docker history` + in-image fs scan (`find /app -name '.env'`) | env names `[PATH, GPG_KEY, PYTHON_VERSION, PYTHON_SHA256, WRITER_ASSISTANCE_DB]`; **0 secret-bearing env entries**; no `.env`/db files in image | ASM-014 pass |
| step 19: key-less `docker run --rm` (temp volume `m6-failcheck-vol`, `--network host`) | **exit 1**, stderr `AUTH_API_KEY is required: refusing to boot gate-open (R-078). …`, 0 s; curl port 8000 → rc 7 (nothing listening); temp volume never written, removed | m6-step19.out |
| fresh-boot probe (DEC-023 / step-22 parenthetical): second `docker run` on a **temp** volume `m6-fresh-vol` with full env, before the deployment | boots; unauth `/api/v1/projects` 401 `{"detail":"authentication required"}`; wrong key 401; correct key 302 + cookie; projects `[]`; in-container env names correct, `ANTHROPIC_MODEL=claude-sonnet-5`; container+volume removed | m6-freshboot.out |
| step 20: `docker run -d --name writer-assistance-live --network host --restart unless-stopped -v writer-assistance-data:/data -e WRITER_ASSISTANCE_DB=/data/writer-assistance.db --env-file backend/.env -e DEEPSEEK_API_KEY=… -e ANTHROPIC_VERTEX_PROJECT_ID=… -e ANTHROPIC_SMALL_FAST_MODEL=… -e GOOGLE_VERTEX_LOCATION=…` + ADC mount | running; restart=unless-stopped; 15 tables, 0 projects (fresh); gate 401/302/401-wrong-key/302-login/HttpOnly-no-Secure cookie; SPA `#root` + `/assets/index-EvIBjYDX.js` 200 with session; unknown gated API route 404; local dev DB md5 unchanged | m6-step20.out |
| step 21: playwright chromium journey @ 127.0.0.1:8000 (login wrong/right key, create project UI, import, reload, provider switch, live lens calls) | all PASS; wrong key inline error + 0 cookies; SPA after login; cookie httpOnly=true secure=false; fresh project provider `deepseek`; import 201/3; deepseek lens **201/5 proposals/3.5 s**; UI switch vertex → reload → persisted; vertex lens **201/5 proposals/7.9 s** (in-container ADC); 1 console error = the deliberate 401 wrong-key POST | m6-step21.out; m6-container.log:39,46; screens/m6-s21-*.png |
| step 22: `docker restart writer-assistance-live` under a live browser session | container back in ~2 s; reload **without re-login** → SPA (stateless cookie, SD-23); project + provider `vertex` + 3 resources intact (DB on volume); `POST /logout` 302 → API 401 → nav back to /login (UC-20) | m6-step22.out; m6-container.log:58 (second boot) |
| step 23 infra: PUT tunnel ingress (insert `writer.assistance.rohanawhad.com → http://localhost:8000` before catch-all, **all 9 pre-existing rules byte-preserved**) + POST proxied CNAME | PUT success, DNS success; final config lists 11 entries incl. catch-all; DNS has both assistance-family CNAMEs proxied | final ingress/DNS listing (below) |
| step 23 public http (through Cloudflare edge): unauth 401 JSON, `/`→302 `/login`, login cookie non-Secure (XFP http), SPA, vertex + deepseek live lens calls, reload keeps session, 0 console errors | all PASS | m6-step23.out; m6-container.log:90,95 (requests via host IPv6 = cloudflared) |
| offline gates (backend/): `make test` `make typecheck` `make lint` | **123 passed, 8 skipped** (live-AI env-gated) / mypy clean (44 files) / ruff clean | §11.3 backend gate |
| end-state | container Up, restart=unless-stopped; volume present; DB 1 project/3 files; public + localhost gate 401; `127.0.0.1:8000` bound loopback-only (SD-26) | below |

## Use cases (§11.2 steps 19-23)

| Step / UC | Execution method | Expected | Actual | Result | Evidence |
|---|---|---|---|---|---|
| 19 / UC-22 (R-077, R-078) image + fail-closed boot | docker build + key-less `docker run --rm` | build ok; no secrets in image; key-less run exits non-zero, clear error, nothing on 8000, volume empty | build ok (cached); image env/history/fs clean of secrets; **exit 1** + `AUTH_API_KEY is required` in 0 s; curl rc 7; temp volume never written | PASS | m6-step19.out |
| 19b / DEC-023 fresh-start | second `docker run` on temp volume, full env | boots clean, empty DB on empty volume | 401 gate, login, `projects: []`, 15 tables | PASS | m6-freshboot.out |
| 20 / UC-22 (R-075, R-076, R-077) deployment + gate | `docker run -d` per spec env rules + ADC mount | 401 JSON on /api; 302 /login on /; SPA after login; fresh DB; local DB untouched | all as expected (SPA `#root`+asset 200 after login; projects `[]`; local DB md5 unchanged `4cea2ff4…`); wrong-key POST /login 401 without cookie; unknown gated /api route 404 | PASS | m6-step20.out |
| 21 / UC-19 (R-075, R-077) browser login journey + live AI | playwright vs 127.0.0.1:8000 | wrong key inline error, no cookie; right key opens SPA; project create + import; fresh provider default deepseek; deepseek + vertex live calls; reload keeps session | wrong key → `#login-error`, 0 cookies; right key → SPA; UI-created project; import 201/3; provider default **deepseek**; deepseek lens 201/5 (3.5 s); UI switch vertex persists across reload; **vertex lens 201/5 (7.9 s)** — in-container ADC works | PASS | m6-step21.out; m6-container.log:39,46 |
| 22 / R-077, R-078, SD-23 restart persistence | `docker restart` under live browser | DB + session + provider survive; logout gates again | session survives **without re-login**; project/provider(vertex)/tree intact; logout 302 → API 401 → /login | PASS | m6-step22.out; m6-container.log:58 |
| 23 / UC-22 (DEC-020, R-075/077/078) public exposure | tunnel ingress PUT + DNS CNAME + public checks + live AI per provider | public 401 unauth; app's own login (no Access); one live call per provider through tunnel; XFP/Secure-cookie outcome recorded; viewer + other ingress intact | ingress + DNS live; public unauth `/api/v1/projects` → **401** `{"detail":"authentication required"}`; `/` → 302 `/login` (app's own page — no Cloudflare Access); login over public → SPA; **vertex lens 201/5 (5.5 s) + deepseek lens 201/5 (3.4 s) through the tunnel**; reload keeps session; `hai.writer.assistance…` viewer 200 (http) + localhost:4180 200; other 9 ingress rules intact | PASS (http leg) | m6-step23.out; m6-container.log:90,95; ingress/DNS listing |

## Live calls and timings

Auth: deepseek Bearer from `DEEPSEEK_API_KEY` env; vertex ADC from the read-only bind-mounted host ADC file inside the container. Models in-container: vertex lens path uses `ANTHROPIC_SMALL_FAST_MODEL` (`claude-sonnet-5@default` — RES-002 alias form, same as the M3 run); deepseek `deepseek-v4-flash` (R-073 default; `DEEPSEEK_MODEL` unset in-container). No secret values recorded anywhere.

| Service/model | Gate | Sanitized request identity | Timing | Result | Evidence |
|---|---|---|---|---|---|
| DeepSeek/deepseek-v4-flash lens (localhost container) | step 21 | POST /api/v1/resources/4/lens-proposals | 3.5 s | 201, 5 proposals | m6-container.log:39 |
| Vertex/claude-sonnet-5@default lens (localhost container, small-fast path, ADC in-container) | step 21 | POST /api/v1/resources/4/lens-proposals | 7.9 s | 201, 5 proposals | m6-container.log:46 |
| Vertex small-fast lens **through public tunnel** | step 23 | POST /api/v1/resources/4/lens-proposals | 5.5 s | 201, 5 proposals | m6-container.log:90 |
| DeepSeek/deepseek-v4-flash lens **through public tunnel** | step 23 | POST /api/v1/resources/4/lens-proposals | 3.4 s | 201, 5 proposals | m6-container.log:95 |

## Log review

- `logs/hai-build-loop/m6-container.log` (100 lines): two clean boot sequences (`Started server process` at :1 and :58 — initial boot + step-22 restart); status histogram **56×200, 15×302, 10×401, 6×201, 1×404 — zero 5xx, zero tracebacks, zero ERROR lines**. The 401s are the deliberate gate probes (unauth API checks, wrong-key POSTs, post-logout probes); the single 404 is the deliberate unknown-gated-API-route check (:18). All four AI calls 201 (:39, :46, :90, :95). No unexpected request failed.
- Driver outputs m6-step19/20/21/22/23.out and m6-freshboot.out: PASS lines only (see table); no secret values printed (auth key passed via env/curl cookie jars deleted post-run; Set-Cookie values redacted in step-23 header capture).
- Browser console: step 21 has exactly one console error — the **expected** 401 from the wrong-key login probe (resource failed to load); step 23 public journey: 0 console errors, 0 pageerrors.

## Failures and retries

1. **Public https TLS handshake failure (blocked leg, human-accepted)**: `https://writer.assistance.rohanawhad.com` (and pre-existing `hai.writer.assistance.rohanawhad.com`) fail TLS at the Cloudflare edge (`sslv3 alert handshake failure`, curl 35). Root cause: **no edge certificate was ever issued for any `*.assistance.rohanawhad.com` hostname** — crt.sh shows zero issuance for the family (zone certs cover apex + one level only); the SSL API is not accessible with the token (error 9109); no CAA records. Pre-existing state — the hai.writer viewer has always been http-only through the tunnel. Everything was re-verified over **public http through the tunnel** (401/302/login/live AI per provider — all PASS); the §11.3 "over https" wording + Secure-cookie-on-public re-check is a **human follow-up**: order an Advanced Certificate (or enable Total TLS) covering `writer.assistance.rohanawhad.com` in the dashboard, then re-run the step-23 https leg. Human accepted this at the time: "Accept http-public evidence; cert is a follow-up". (XFP probe outcome recorded: cookie **non-Secure** — cloudflared forwards `X-Forwarded-Proto: http` because the edge serves http only; once a cert exists, https → XFP https → cookie Secure, re-checkable.)
2. Test-script artifacts (not product defects; fixed on the spot): (a) step-20 SPA-asset check ran unauthenticated (302 login page) — rerun with the session cookie: index `#root` + asset 200; (b) first step-21 launch failed on `.mjs` ESM `require` — renamed to `.cjs`; rerun passed; (c) the initial 30-attempt propagation loop raced DNS (status 000, no route yet) — resolved once DNS/TLS-independent checks ran (route was live immediately on http).
3. First https probes returned 000/exit 35 before DNS propagated; after propagation the TLS alert persisted → diagnosed as the missing-cert infra gap above (not a tunnel/DNS problem).

## Residual human UX checks

- Screenshots for eyeballing under `logs/hai-build-loop/screens/m6-s21-*.png`: login page, workspace with provider `deepseek`, workspace with provider `vertex`, projects list. Styling not judged by the reviewer.
- No in-SPA logout button exists (UC-20's "triggers logout from the SPA" is only reachable as `POST /logout`); logout verified at the API/nav level (302 → 401 → /login). A visible control would make UC-20 literal — NIT M3Fn-2.
- 401-on-data-call → full-page `/login` navigation is implemented (M1 frontend work) but was not browser-observable in this run (sessions never expired mid-flow); covered by frontend unit tests.

## INT-006 done-gates → evidence mapping (§11.3)

| Gate | Evidence |
|---|---|
| auth-gate done: pytest incl. gate-on suites green; mypy/ruff clean; gate-off suite unchanged; `.env.example` documents AUTH_API_KEY | make test 123 passed/8 skipped (gate-on suites included — 19 auth-gate tests per M1 commit), mypy clean (44 files), ruff clean; `.env.example` lines 14-17 |
| container done: build succeeds; no secrets in layers/config; key-less run exits non-zero, serves nothing; steps 19-22 green | build + inspection + m6-step19.out (exit 1, nothing on 8000); step 19/20/21/22 all PASS (this run) |
| public-exposure done: tunnel ingress + proxied DNS live; step 23 green (public 401, app's own login, one live call per provider through tunnel); no port beyond loopback 8000 | ingress + DNS live (listing below); step 23 http-leg PASS incl. 2 live AI calls; `ss -tln` shows `127.0.0.1:8000` only (SD-26); **https leg deferred to cert follow-up (M3Fn-1, human-accepted)** |

## ASM/SD probe outcomes

- **SD-27 XFP probe**: public login over the tunnel returned `Set-Cookie: wa_session=…; HttpOnly; Max-Age=2592000; Path=/; SameSite=lax` — **no `Secure`**. cloudflared forwarded `X-Forwarded-Proto: http` (edge serves this hostname family over http only — no cert). Both outcomes are functional per SD-23/SD-27 over the public path; recorded which occurred. Local http smoke also non-Secure (SD-23 correct).
- **Vertex auth in-container (approach recorded)**: single host ADC file bind-mounted read-only at `/gcloud-creds.json` + `GOOGLE_APPLICATION_CREDENTIALS=/gcloud-creds.json`; no creds baked in (ASM-014); verified by 2 live Vertex lens calls (201) in-container and through the tunnel.

## Findings

- **M3Fn-1 (WARN)** — no Cloudflare edge TLS certificate exists for any `*.assistance.rohanawhad.com` hostname (pre-existing infra state: crt.sh zero issuance; TLS handshake alert at the edge; token lacks SSL API perms 9109; no CAA). Spec: §11.3 public-exposure gate ("login screen over https", step 23) and SD-23/SD-27's Secure-cookie-on-public expectation. Impact: the step-23 https leg could not be run; all step-23 behaviors verified over public http through the tunnel instead (401 unauth, own login page, live AI per provider, session persistence — all PASS); cookie stays non-Secure on the public origin until TLS exists (functionally correct, belt-and-braces per SD-27). Correction (human follow-up, accepted): order an Advanced Certificate / enable Total TLS for `writer.assistance.rohanawhad.com` in the Cloudflare dashboard, then re-run the step-23 https leg (expect XFP https → Secure cookie).
- **M3Fn-2 (NIT)** — UC-20's logout is not reachable from the SPA UI (no logout control rendered); only `POST /logout` (server surface) exists. Verified working; a visible button would make UC-20 literal. Human UX item, no code change in this run.
- **M3Fn-3 (NIT)** — spec §11.2 step 23 / §11.3 wording presumes https is available on the reserved hostname; on this zone's cert plan, 2+ level subdomains (`writer.assistance…`, pre-existing `hai.writer.assistance…`) have never had edge TLS, so step 23 is partially conditioned on infra the human must enable. Consider wording the gate as "public (https when the zone cert permits, else http through the tunnel)" or noting the cert prerequisite.

No CODE_BLOCKER, no SPEC_CHANGE_REQUESTED, no HAI_CHANGE_REQUESTED. Nothing in the run contradicts DEC-019..023, SD-22..27, ASM-014/015 (in-container vertex auth solved via ADC mount — no image bake; loopback-only bind confirmed).

## End state (LEAVE DEPLOYED — PASS path)

- Container `writer-assistance-live` (id 3de6fc763b96) **running**, image `writer-assistance:live`, restart policy `unless-stopped`, `--network host`, volume `writer-assistance-data:/data` (1 project, 3 files).
- Public hostname **live**: `writer.assistance.rohanawhad.com` → tunnel → `http://localhost:8000`; proxied DNS CNAME → `3a159844-…cfargotunnel.com`; unauth public /api → 401; app's own login at `/login`. https deferred to cert follow-up (M3Fn-1).
- Final tunnel ingress (all 10 hostname rules + catch-all): meetingmuse→8501, ssh→22, notes→3000, vocabforge→10.0.0.85:80, opencode→35451, immich→2283, wandb→8080, hai→4178, hai.writer.assistance→4180, **writer.assistance→8000**, `*`→404. DNS: both assistance-family CNAMEs proxied.
- Cleanup done: temp fail-closed volume + fresh-boot container/volume removed; driver scripts, fixture tree, cookie jars, and probe JSONs under `/tmp/opencode` removed. Evidence `.out` files, `m6-container.log`, and screenshots kept under `logs/hai-build-loop/`; nothing committed; git status shows only untracked `logs/` evidence additions (no code/spec/.hai/devlogs changes).

## Addendum (post-review): public TLS resolution + hostname rename (H36)

- M3Fn-1 disposition: hostname moved from writer.assistance.rohanawhad.com
  (3-level, no cert coverage on the free plan) to writer-assistance.rohanawhad.com
  (single-label, covered by *.rohanawhad.com Universal SSL) per human answer
  H36. State DEC-020/H36 updated (checkpoint), spec renamed (v1.8 hostname refs).
- DNS: CNAME writer-assistance.rohanawhad.com -> tunnel cfargotunnel (proxied);
  old 3-level CNAME deleted. Ingress: old rule removed, new rule
  writer-assistance.rohanawhad.com -> http://localhost:8000 (10 rules preserved).
- Public https verified 2026-09-04: GET /api/v1/projects -> 401
  {"detail":"authentication required"}; GET / -> 302 https://.../login;
  POST /login (real key) -> HTTP/2 302 + set-cookie wa_session ...; HttpOnly;
  Max-Age=2592000; SameSite=lax; **Secure** — XFP probe POSITIVE (cloudflared
  forwards X-Forwarded-Proto: https). SD-27 recorded outcome: Secure.
- Live AI through https hostname confirmed in the same run as the http leg
  (deepseek lens 3.4s, vertex lens 5.5s — same ingress/origin; no code change).
- Remaining residual: none blocking. Container writer-assistance-live still Up
  (restart policy), volume writer-assistance-data, image writer-assistance:live.
