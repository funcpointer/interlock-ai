# InterLock AI — Risk Register

Adversarial review of the Phase 13–17 plan against the existing baseline, with status updates as of v1.5-mvp-ready. Every entry: risk, likelihood, blast radius, detection, mitigation, owner, **outcome**.

**Outcome key:** `mitigated` (handled as designed) · `realized` (happened, and what we did) · `dropped` (scope-cut decision) · `pending` (still open at the time of writing).

---

## R-1 — Anthropic budget runaway

- **Risk:** Silent cache invalidator causes every demo run to re-pay full LLM input cost. Repeated dev iterations push spend past the $20 prepaid cap.
- **Likelihood (planned):** Medium.
- **Mitigation:** Cache invariant test `tests/llm/test_client.py::test_call_structured_cache_fires_on_repeat_with_large_cached_prefix` asserts `cache_read > 0` on second call. Diskcache wraps the Anthropic call so second hits don't even reach the API. Per-call cost ledger in `cost_event` table.
- **Outcome — mitigated.** Total Anthropic spend across Phase 13–14 build measured by `cost_event` aggregate: **~$0.20**. Far under cap. Voyage spend separately tracked, sub-dollar.

## R-2 — Entity refactor breaks v1.2's 159-test baseline

- **Risk:** Phase 14 `Entity` + `Claim` types break existing tests that construct `ParameterRecord` by hand.
- **Likelihood (planned):** High if rewrite-style, Low if additive.
- **Mitigation:** Additive layer — `Claim` wraps `ParameterRecord` (back-pointer preserves citation). Aligner uses `Claim` only when `use_claim_layer=True` (default off). Existing record-based path unchanged.
- **Outcome — mitigated.** Phase 14 landed with 43 new tests and zero existing-test regressions. Subsequent Phase 18 / 19 / 20 work preserved the same invariant. **Current test surface (v1.5-mvp-ready):** 261 passed, 83 deselected (slow + real-world live-API), mypy strict clean, ruff clean. v1.3 baseline preserved bit-for-bit when claim layer is off.

## R-3 — LLM extraction returns inconsistent shapes

- **Risk:** Pydantic `messages.parse` extracting Claim[] from prose may drift across runs.
- **Outcome — dropped (LLM extraction never built in v1.5).** Decision: only the **LLM significance judge** uses Pydantic-validated `messages.parse`, on a per-flag basis with disk-cached results. Extraction stays deterministic regex. LLM-assisted extraction is platform path (BACKLOG R-M prose extraction).

## R-4 — Tolerance bands aren't authoritative

- **Risk:** Per-attribute tolerance tables depend on standard edition, owner internal standards, equipment vintage, review phase, risk posture. We can't ship the right value for every project. AES engineers will ask first.
- **Outcome — mitigated, three-layer defense shipped:**
  1. Shipped values cite public sources inline (`src/interlock/detect/tolerances.py`): IEEE C57.12.00-2015 §9.1 Table 17, IEC 60076-1:2011 §5.3, IEEE Std 242 (Buff Book), NEMA TR 1-2013.
  2. Module docstring explicitly states values are "industry-typical starting defaults, not absolute truth" with five drivers of project-specific variance.
  3. Runtime override hook (`set_tolerance_overrides`) lets a reviewer load project-specific bands without forking. Overrides preserve their own source citation.
- **Honest framing in TDD §4B:** the value proposition is not "InterLock knows the right tolerance" but "InterLock makes the tolerance assumption visible, citable, and owned by the reviewer team." Per-project tolerance ontology UI is Phase 15 in `docs/BACKLOG.md`.

## R-5 — Demo recording fails under live load

- **Risk:** During screen recording, Voyage or Anthropic rate-limits or returns 500. Clean take ruined.
- **Outcome — pending.** Demo recording not yet done at the time of writing. Mitigation strategy stands: pre-warm caches, record locally if cloud flakes.

## R-6 — Streamlit Cloud cold start during reviewer click-through

- **Risk:** Reviewers click the deployed link and wait 30+ s for cold start; assume the app is broken.
- **Outcome — pending mitigation.** Keep a browser tab on the URL the 12 hours before submission. README notes cold start is expected on first visit.

## R-7 — Time estimate is wrong

- **Risk:** 22 h estimate (Phase 13–17) doesn't allow for any phase blowing up.
- **Outcome — mitigated.** Phase 13 landed in ~4 h, Phase 14 in ~5 h, Phase 17 in ~1 h. Phase 16 was scope-dropped at the multi-equipment fingerprinting realisation (see R-11) rather than blowing the time budget. Total elapsed ≈ 10 h vs 22 h estimate; margin retained for the demo recording.

## R-8 — Public repo leaks something private

- **Risk:** GitHub repo is public. Sensitive notes, API keys, or proprietary information accidentally tracked.
- **Outcome — mitigated, vigilance ongoing.** `.env` gitignored. `CLAUDE.md` gitignored. `.claude/` gitignored. Pre-submission scan still required (see checklist below).

## R-9 — PRD/TDD page bloat

- **Risk:** Brief says 1–2 pages each. Reviewer fatigue if longer.
- **Outcome — accepted, partially mitigated.** PRD 96 lines / TDD ~175 lines as of P21 manicure. PRD sits cleanly within 1–2 pages rendered. TDD intentionally exceeds the strict 2-page bar because § "Known limits" carries the honest-scope disclosure (Phase 19) that reviewers explicitly value over brevity. Architectural detail (diagrams, schema, operational metrics) is in ARCHITECTURE.md to keep TDD focused on decisions.

## R-10 — Synthetic Doc A credibility hit (Option 2)

- **Risk:** Funders see `spec_xfmr_001.pdf` is synthetic and discount the cross-doc demo.
- **Outcome — mitigated by honest framing.** `docs/AUTHORSHIP.md` discloses the synthetic spec upfront with the IEEE C57 / ANSI C57 nameplate convention it follows. Demo script frames Option 2 as a controlled cross-doc fixture. Real-spec curation (Option 4) is the next fixture engineering workstream.

## R-11 — Multi-equipment fixture demo

- **Risk:** Synthetic 3-equipment spec paired against implicit-entity Eaton study would over-flag because Eaton's implicit transformer matches any of XFMR-001/002 by tag.
- **Outcome — realized, Phase 16 dropped.** Discovered at Phase 16 build time: when one side has explicit equipment tags and the other has only implicit entities, the same-entity filter treats implicit as a wildcard (so Option 1 still works) but cannot distinguish which explicit entity the implicit side refers to. Resolution requires attribute-fingerprint entity binding (voltage class, power rating). Meaningful workstream rather than a 3-hour task. Phase 16 fixture and gold set were not shipped. v1.5 ships Option 1 + Option 2 only. Entity fingerprinting now tracked as `docs/BACKLOG.md` R-F.

## R-12 — Voyage embedding non-determinism

- **Risk:** Voyage `voyage-3` returns slightly different vectors on identical inputs across calls. Confidence values drift between runs.
- **Outcome — mitigated.** Diskcache namespace `voyage-embeddings` (see `src/interlock/align/embed.py`) hard-pins vectors per text. `tests/real_world/test_pipeline_behaviors.py::test_cross_doc_real_embedder_flag_set_is_stable` asserts flag-parameter *set* stability, not absolute confidence values.

## R-13 — Camelot slow on 56-page IEEE PDF

- **Risk:** Real-PDF extraction tests take 110+ s on IEEE guide.
- **Outcome — mitigated.** Perf budgets and IEEE-guide tests carry the `slow` pytest marker (`pyproject.toml::addopts = "-m 'not slow'"`), excluded by default. Full set runs with `uv run pytest -m slow`.

## R-14 — User burns out before May 22

- **Risk:** Long sessions, high stakes, sleep deprivation. Decision quality drops; mistakes compound.
- **Outcome — pending self-monitoring.** Phase ordering by ROI per hour (Phase 13 first) kept session lengths manageable. v1.5-mvp-ready ships well before EOD May 22; demo recording can wait if needed without slipping the deadline.

## R-15 — Multi-instance same-name false flags (realised in user testing)

- **Risk:** Pages with multiple `Fuse Designation` or `Transformer Rating` records (5+ fuses on a one-line diagram, 2–3 transformers per page) had no record identity beyond `name + page + y-coord`. Under OCR the y-coords collapse to whole-page bbox, and positional pairing degenerates to first-in-iteration order — cross-pairing `KRP-C-1600SP` (main bus fuse) against `LPS-RK-100SP` (motor branch fuse) and surfacing a fake 16:1 ampacity flag.
- **Likelihood (realised):** confirmed in user testing of OCR-vs-native fixture pair.
- **Outcome — mitigated, Phase 19.** Four-commit refactor: (1) `entity_tag` first-class field reading leading row markers; (2) honest unpaired-records surface in UI; (3) `pairing_confidence` per rule with `⚠️ weak pair` badge below 0.75; (4) OCR prompt v3 explicitly preserves Device IDs. Defense-in-depth ambiguity gates (family prefix, count mismatch, y-degeneracy) catch records without entity tags. Live verification on Option 2 surfaces exactly the 3 real engineering discrepancies a senior reviewer would flag; cross-doc validation confirms direction, severity, citations all correct.
- **Honest scope statement** in `docs/TDD.md` § "Known limits": the architecture generalises but the specific regexes are shaped to fuse-coordination tables; HVAC schedules / P&IDs / right-column-ID specs are untested.

## R-16 — OCR decimal-place hallucination (realised in user testing)

- **Risk:** Claude vision at 200 DPI hallucinated `5.75%Z` as `0.575%Z` on the scanned fixture — a decimal-place misread that downstream alignment then surfaced as a false flag.
- **Likelihood (realised):** confirmed in user testing.
- **Outcome — mitigated, Phase 20.** DPI bump 200 → 300 (~$0.10 vs ~$0.05 per OCR'd page) resolved the user-reported case on first pass. Two-pass plausibility loop ships as defense-in-depth: scan first-pass text for engineering tokens, validate against per-family sanity bands (wide enough to allow unusual-but-real values), re-OCR at 400 DPI with verification prompt only when an implausible value is detected. Pass with fewer implausible tokens wins; tie keeps pass 1. Live verification: re-OCR did not fire on any of 9 pages on the locked fixture; impedance set matches native almost exactly.
- **Honest scope statement:** both passes use the same model — multi-model consensus would catch model-specific failure modes but expands scope mid-submission. Tracked as R-D in `docs/BACKLOG.md`.

---

## Abort gates (planned vs realised)

| Gate | Plan | What happened |
|---|---|---|
| End of Phase 13 (target ~5h) | Tag `v1.3-tolerance` and ship if exhausted | Landed in ~4 h, green, tagged. Continued. |
| 8 h into Phase 14 | If LLM extraction unstable: revert, ship v1.3 | LLM extraction not built; Phase 14 was the entity-claim layer, landed in ~5 h additive, no regression. Tagged `v1.4-entity-claim`. |
| Phase 16 — 3 h in | If multi-equipment gold red: drop fixture | Multi-equipment cross-doc requires entity fingerprinting against implicit-side docs; not a 3-hour task. Phase 16 dropped. Phase 17 went straight to deliverables refresh. |
| 6 h before EOD May 22 | Hard freeze, merge what's green, tag | v1.5-mvp-ready tagged well before this gate. |

## Pre-submission checklist

- [ ] All branches merged to `main`, no stale phase branches
- [ ] All tags pushed: last is `v1.5-mvp-ready`; phase tags through `phase-20-ocr-quality`
- [ ] `uv run pytest --deselect tests/real_world` green — 261 passed, 83 deselected
- [ ] `uv run pytest -m slow` green (or documented skip; live-API costs ~$0.05–0.10 per run)
- [ ] `uv run ruff check .` clean
- [ ] `uv run mypy src` clean
- [ ] Streamlit Cloud URL responsive (cold start tested)
- [ ] Demo video < 5 min, uploaded, link added to README + DEMO_SCRIPT.md
- [ ] PRD rendered length checked (≤ 2 pages — currently 96 lines)
- [ ] TDD rendered length checked (intentionally exceeds 2 pages due to honest-limits disclosure, see R-9)
- [ ] AUTHORSHIP.md current (per-phase sections present: P11 → P12 → P13 → P14 → P18 → P19 → P20)
- [ ] `git ls-files` audited for accidental private content
- [ ] `git grep -E "sk-ant-|pa-bu[a-zA-Z0-9]|vlt_"` returns nothing in tracked files
- [ ] `eval/results/baseline.json` regenerated and committed
- [ ] `eval/results/ab_comparison.json` regenerated and committed
- [ ] README has deploy URL and demo video link
- [ ] GitHub repo description set; topics tagged
- [ ] Reviewer access notes in submission packet
- [ ] **Rotate** the Voyage API key pasted in chat early in development (still active in `.env`; was visible in chat transcripts that may have been logged)
- [ ] **Rotate** the Anthropic API key once accidentally hexdumped to chat in early development
