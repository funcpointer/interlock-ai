# InterLock AI MVP — Demo Script

Target length: **2 minutes** (hard cap 5 per brief). Plain screen recording, voice-over.

---

## 0:00–0:15 — Frame the problem

> "Engineering teams at companies like AES review hundreds of cross-referenced documents on every project. A misplaced decimal in a transformer spec almost cost them a multi-million-dollar loss — caught only because a senior engineer happened to spot it during a 60% review. InterLock AI is a review assistant that catches that kind of cross-document discrepancy automatically, with citations."

Visual: the README diagram or just the InterLock title page.

## 0:15–0:30 — Show the upload

> "Reviewer uploads two PDFs from the same project. Doc A is the 60% baseline coordination study. Doc B is the 90% revision under review."

Action: drop both PDFs into the Streamlit page. Click **Run review**.

## 0:30–0:55 — Show the flag list, severity-grouped

> "InterLock surfaces four directional flags. All four group under **critical** severity — decimal-shift class deviations exceed the IEEE C57.12.00 tolerance bands by an order of magnitude."

Visual: the flag list, grouped by severity icon. Point at:
- TP-1: `%Z: 5.75 % (authoritative, p3) ≠ 0.575 % (deviation, p3)` — the canonical AES decimal-shift example. Severity tag: **CRITICAL**.
- TP-2: `Fault Current: 20,000 A (authoritative, p2) ≠ 200,000 A (deviation, p2)`. **CRITICAL**.
- TP-3 (×2): `Transformer Rating: 1000 kVA ≠ 100 kVA`. **CRITICAL**.

> "Every flag declares which document is authoritative and which is deviating. Severity tier is computed from relative deviation against per-attribute tolerance bands sourced from IEEE C57.12.00, IEC 60076-1, and NEMA TR 1. Within-tolerance changes — say a 5.75 % impedance drifting to 5.77 % — would classify as **info** and be suppressed by default. That's the noise reduction that keeps reviewer trust."

## 0:50–1:15 — Click into a citation

Action: expand the impedance flag.

> "Both sides show a bbox-highlighted snippet of the source page. The reviewer can verify the finding in seconds without leaving InterLock."

Visual: both snippet PNGs side by side, red boxes on the spans.

## 1:15–1:30 — Accept and dismiss

Action: click Accept on TP-1, Dismiss on one of the TP-3 duplicates.

> "Reviewer triages. Accepted flags export as JSON for the audit log."

Action: click **Export accepted flags**. Show the file.

## 1:30–1:50 — Show what didn't flag

Action: scroll to the "suppressed" expander.

> "Two false-positive traps were deliberately planted. 150 kVA vs 0.15 MVA — same physical value, different unit — Pint normalizes them. A heading rephrase with no parameter change — never enters the flag list at all. Zero false positives on the locked gold set."

## 1:50–2:00 — Wedge to platform

> "Today: cross-document parameter mismatch detection with **tolerance-aware severity tiers** and an **Entity + Claim layer** persisted in SQLite. Next: per-project tolerance ontology UI, revision lineage, coupled-effect graph traversal — when a transformer impedance changes, the system flags every downstream claim that depended on it. The wedge is the AES decimal-error problem. The platform is the engineering consistency operating system."

End on the README's "Phase tags" block — 12 phase tags, 294 tests, TDD throughout, audit-traceable engineering.

Optional 5-second LLM judge segment (skip if recording over budget):

> "Toggle 'Use LLM significance judge'. Each flag gets an engineering rationale plus downstream-effect propagation, computed by Claude Opus 4.7 with prompt-cached ontology. Cached, so the second run costs effectively zero."

---

## Optional second segment — cross-doc demo (Option 2)

If video budget allows another 60 seconds, follow Option 1 with the cross-doc fixture to demonstrate the semantic-alignment path:

> "Same pipeline, different fixture. Now Doc A is an equipment data sheet — a transformer nameplate spec. Doc B is the coordination study. Different document types, different layouts, different parameter naming."

Action: toggle **Cross-document mode** in the UI. Upload `spec_xfmr_001.pdf` and `doc_a_60pct.pdf`.

> "Three flags surface. The spec says `Rated Power: 1100 kVA`; the study references `1000 kVA`. The spec says `Rated Impedance: 5.7 %`; the study references `5.75 %Z`. InterLock's canonical glossary maps `%Z` to impedance, `Rated Power` to transformer rating, and the embedding alignment carries the rest. Adobe Acrobat can't do this. This is the cross-document wedge."

Show the A/B JSON briefly:

```
uv run python scripts/run_ab.py
```

> "A/B comparison: Option 1 surfaces flags via layout-anchored exact matching. Option 2 surfaces flags via semantic alignment. Both correct, both cited, both directional."

---

## Pre-recording checklist

- [ ] `.env` has both `VOYAGE_API_KEY` and `ANTHROPIC_API_KEY` populated.
- [ ] `uv run streamlit run src/interlock/ui/app.py` opens without errors.
- [ ] Both `fixtures/pdfs/doc_a_60pct.pdf` and `fixtures/pdfs/doc_b_90pct.pdf` accessible from the desktop for the upload drag-drop.
- [ ] Browser zoom set so the flag list is visible without scrolling on a 1080p screen.
- [ ] Mic test, audio level checked.
- [ ] One dry-run end-to-end before recording.

## Recording URL

(Add the YouTube / Loom / direct-file link after recording.)
