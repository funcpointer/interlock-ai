# InterLock AI — Risk Register (Adversarial Review for May 22 EOD Delivery)

Adversarial review of the Phase 13–17 plan and the existing v1.2 baseline. Every entry has: risk, likelihood, blast radius, detection, mitigation, owner.

Ranked by impact × probability. **Read top to bottom; the first 6 are the ones that could actually kill the submission.**

---

## R-1 — Anthropic budget runaway

- **Risk:** A cache silent-invalidator causes every demo run to re-pay full LLM input cost. Repeated dev iterations during Phase 13/14 push spend past the $20 prepaid cap.
- **Likelihood:** Medium. Silent invalidators are subtle (timestamps, unsorted JSON, varying tool sets).
- **Blast radius:** $5–$50 wasted; demo recording blocked if quota exhausted.
- **Detection:** Pytest `test_call_structured_cache_fires_on_repeat_with_large_cached_prefix` asserts `cache_read > 0` on second call. Run before every commit on `phase-13-llm-pipeline`.
- **Mitigation:** Layer the diskcache *outside* the Anthropic call so the second run never even hits the API. Set Anthropic console usage limit to $20 / 48h. Watch `cost_event` table.
- **Owner:** Pipeline orchestrator (Phase 15).

## R-2 — Entity refactor breaks v1.2's 159-test baseline

- **Risk:** Phase 14 introduces `Entity` + `Claim` types. Existing tests construct `ParameterRecord` by hand and don't know about claims. A naive refactor breaks 30+ tests.
- **Likelihood:** High if approached as a rewrite. Low if approached additively.
- **Blast radius:** Hours of regression chasing. Risk of shipping with red tests.
- **Detection:** `pytest -q` after each Phase 14 task.
- **Mitigation:** **Make Entity + Claim an additive layer.** `Claim` *wraps* a `ParameterRecord` (not replaces). Aligner and detector accept either. Existing tests stay green; new tests exercise the claim layer. See ARCHITECTURE.md §5 (claim table has back-pointer to source record).
- **Owner:** Phase 14 implementation.

## R-3 — Phase 14 LLM extraction returns inconsistent shapes

- **Risk:** Even with Pydantic `messages.parse`, LLM extraction on the synthetic spec vs the Eaton study may surface different entity types / attribute names, breaking downstream alignment.
- **Likelihood:** Medium-high. LLM output drift is real even at temperature=0.
- **Blast radius:** Gold set fails; demo regresses below v1.2.
- **Detection:** Phase 14 has a "snapshot" pytest that pins the extracted Claim list against a fixture-locked golden. Any drift fails CI.
- **Mitigation:** Strict Pydantic schemas. Prompt explicitly enumerates allowed attribute names (closed vocabulary). Diskcache aggressively — once a Claim list is captured for a doc hash + prompt version, it's frozen until prompt bump.
- **Owner:** Phase 14.

## R-4 — Tolerance bands aren't authoritative

- **Risk:** Phase 13 needs per-attribute tolerance tables (±5 % impedance, ±2 % voltage, etc.) but we don't have IEEE-cite-grade authority. A funder asks "where did these come from?" and the answer is "industry common sense."
- **Likelihood:** High that someone asks.
- **Blast radius:** Credibility hit.
- **Detection:** Internal review of every tolerance value before commit.
- **Mitigation:** Tolerance bands live in `src/interlock/detect/tolerances.py` with **inline citations** to IEEE C57.12.00, IEC 60076, or NEMA TR-1. Where the standard doesn't pin a value, mark `source: "industry typical, see BACKLOG.md item X"` and acknowledge in TDD §6 that production needs project-specific tolerance configs.
- **Owner:** Phase 13.

## R-5 — Demo recording fails under live load

- **Risk:** During screen recording, Voyage or Anthropic rate-limits or returns 500. The clean take is ruined; recording session runs over.
- **Likelihood:** Low-medium. Both providers are stable but never zero.
- **Blast radius:** 30–60 min lost.
- **Detection:** Pre-warm run before recording.
- **Mitigation:** **Pre-warm the cache** — run the demo flow once to populate diskcache and the Anthropic prompt cache. The recording run then hits caches throughout and never depends on the live API. Worst case, record locally with all caches warm and skip the deployed URL clip.
- **Owner:** Phase 17 (recording).

## R-6 — Streamlit Cloud cold start during demo / submission review

- **Risk:** Reviewers click the deployed link and wait 30+ s for cold start; assume the app is broken.
- **Likelihood:** Medium. Free tier sleeps after inactivity.
- **Blast radius:** First-impression failure.
- **Detection:** Test the URL right before submitting.
- **Mitigation:** Keep a browser tab open on the URL for the 12 h before submission (pings the app, prevents sleep). README has a `<details>` block explaining cold start is expected on first visit.
- **Owner:** Pre-submission checklist.

## R-7 — Time estimate is wrong

- **Risk:** 22 h estimate (Phase 13–17) doesn't allow for any phase blowing up. We hit Phase 14 LLM extraction quirks and burn 8 h instead of 7.
- **Likelihood:** Medium-high. Phase 14 is the highest unknown.
- **Blast radius:** Submission slips past EOD May 22.
- **Detection:** Wall-clock at end of each phase vs estimate.
- **Mitigation:** **Phase ordering by ROI per hour.** Phase 13 (tolerance + severity) is high-confidence and lands the biggest demo lift; do it first. Phase 14 is the risk; if it blows up past 8 h, ship without it and reframe Entity as Phase 19+ in BACKLOG. v1.2 + Phase 13 alone is still a strong submission.
- **Owner:** Daily 4-hour checkpoints. Phase 14 abort gate at 8 h.

## R-8 — Public repo leaks something private

- **Risk:** GitHub repo is public. Competition brief, sensitive notes, API keys, or proprietary information accidentally tracked.
- **Likelihood:** Low — .env is gitignored, brief notes are gitignored, CLAUDE.md is gitignored. But every new commit is a fresh chance.
- **Blast radius:** Could surface in funder background check.
- **Detection:** `git ls-files` audit before submission.
- **Mitigation:** Pre-submission gate: scan for any string matching `sk-ant-`, `pa-`, or known project file patterns. Use `git secrets` or equivalent. Already corrected once; remain vigilant.
- **Owner:** Pre-submission checklist.

## R-9 — PRD/TDD page bloat

- **Risk:** PRD and TDD currently exceed 2 pages each. Brief says 1–2 pages. Funders won't read 5-page docs.
- **Likelihood:** Confirmed — PRD is ~2.5 pages, TDD is ~3 pages.
- **Blast radius:** Format violation; reviewer fatigue.
- **Detection:** Render and count.
- **Mitigation:** Phase 17 trim. Move detail to ARCHITECTURE.md (no length constraint) and BACKLOG.md. PRD = persona + workflow + wedge + platform path. TDD = ingest + extract + align + detect + eval + architecture pointer.
- **Owner:** Phase 17.

## R-10 — Synthetic Doc A credibility hit (Option 2)

- **Risk:** Funders see `spec_xfmr_001.pdf` is synthetic and discount the cross-doc demo.
- **Likelihood:** Medium. Engineers can spot a generated spec quickly.
- **Blast radius:** Cross-doc demo loses weight; submission falls back to revision-diff only.
- **Detection:** N/A — funder-side.
- **Mitigation:** Authorship note discloses upfront. Demo script frames Option 2 as "controlled cross-doc fixture proving the alignment path works; Option 4 in the backlog applies the same pipeline to real manufacturer data sheets." Honest framing beats apology.
- **Owner:** Phase 17 demo script + AUTHORSHIP.md (done).

## R-11 — Multi-equipment fixture (Phase 16) reveals hidden assumptions

- **Risk:** Synthetic 3-equipment spec (XFMR-001, XFMR-002, P-101) trips the aligner — it pairs P-101 attributes with XFMR-001 because the canonical glossary doesn't disambiguate. Demo regresses.
- **Likelihood:** Medium. Multi-entity is precisely what we haven't tested.
- **Blast radius:** Phase 16 doesn't ship; we drop the multi-equipment story.
- **Detection:** Phase 16 has its own gold set; if it fails, abort the multi-equipment fixture before merging.
- **Mitigation:** Entity ID is required for any claim that mentions a tagged equipment (regex captures `[A-Z]+-\d+` patterns into entity_id). Cross-entity alignment is suppressed. If the test still fails, Phase 16 is dropped; v1.3 ships with Option 1 + Option 2 only.
- **Owner:** Phase 16. Abort gate at 3 h if gold set fails.

## R-12 — Voyage embedding non-determinism

- **Risk:** Voyage `voyage-3` returns slightly different vectors on identical inputs across calls. Confidence values drift between runs.
- **Likelihood:** Known issue — tested and pinned in test_pipeline_behaviors.
- **Blast radius:** Eval test flakes; would block CI.
- **Detection:** Already detected.
- **Mitigation:** Tests assert flag-parameter *set* stability, not absolute confidence. JSON-backed embedding cache (Phase 13 prep) hard-pins vectors per text — once cached, no further variance.
- **Owner:** L3 cache implementation.

## R-13 — Camelot slow on 56-page IEEE PDF in CI

- **Risk:** Real-PDF extraction tests take 110+ s when IEEE guide is included. CI timeout or developer impatience.
- **Likelihood:** Confirmed and accepted.
- **Blast radius:** Slow test suite, not correctness.
- **Detection:** Time logs.
- **Mitigation:** IEEE guide tests are part of full regression, run on demand. CI `slow` marker excludes them by default (matches the perf tests in v1.2).
- **Owner:** Already mitigated in v1.2.

## R-14 — User burns out before May 22

- **Risk:** Long sessions, high stakes, sleep deprivation. Decision quality drops; mistakes compound.
- **Likelihood:** High.
- **Blast radius:** Worst class of risk — can affect everything.
- **Detection:** Self-monitoring.
- **Mitigation:** Phase 13 first (highest ROI per hour). Sleep is non-negotiable. The MVP is shippable today; everything from here is upside. **v1.2 + Phase 13 alone is a credible submission. Phase 14–16 are stretch. If exhaustion sets in, stop, ship v1.2.5, and let Phase 14+ wait.**
- **Owner:** Human-in-the-loop (you).

---

## Abort gates (when to stop and ship)

| Gate | Condition | Action |
|---|---|---|
| End of Phase 13 (target ~5h in) | Tolerance + severity working, gold set still 100/0 | Tag `v1.3-tolerance` and ship if exhausted |
| 8 hours into Phase 14 | LLM extraction not stable, gold set red | Revert Phase 14 branch, ship `v1.3-tolerance` |
| Phase 16 — 3 hours in | Multi-equipment gold set red | Drop Phase 16, ship `v1.3-tolerance + entity-layer-only` |
| 6 hours before EOD May 22 | Anything unmerged on the branch | Hard freeze, merge what's green, tag, deploy |

## Pre-submission checklist (final 2 hours)

- [ ] All branches merged to `main`, no stale phase branches
- [ ] All tags pushed
- [ ] `pytest -q` green
- [ ] `pytest -m slow` green (or documented skip)
- [ ] `ruff check .` clean
- [ ] `mypy src` clean
- [ ] Streamlit Cloud URL responsive (cold start tested)
- [ ] Demo video < 5 min, uploaded, link in DEMO_SCRIPT.md
- [ ] PRD ≤ 2 pages rendered
- [ ] TDD ≤ 2 pages rendered
- [ ] AUTHORSHIP.md current (mentions Phase 13–17 additions)
- [ ] `git ls-files` audited for accidental private content
- [ ] No `sk-ant-` or `pa-` or `vlt-` strings in any tracked file
- [ ] `data/results/baseline.json` regenerated and committed
- [ ] `data/results/ab_comparison.json` regenerated and committed
- [ ] README has deploy URL and demo video link
- [ ] GitHub repo description set; topics tagged
- [ ] Reviewer access notes in submission packet
