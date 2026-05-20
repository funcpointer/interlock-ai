# InterLock AI — PRD

## 1. Reviewer user

A senior electrical engineer or discipline lead at an AES-type owner organization (or an EPC reviewer) accountable for cross-checking an engineering submittal at a 30/60/90 design-review milestone. Technically sophisticated, time-constrained, regulated context. Currently downloads PDFs from SharePoint, opens them side by side, manually checks for inconsistent parameters, annotates discrepancies in PDF comments, uploads back. The bottleneck is **their** time — they are the only ones who can judge whether a cross-document mismatch is real, but most of their review hour is spent **finding** mismatches, not adjudicating them.

InterLock targets the finding step. Adjudication stays human.

## 2. Why this fits the existing workflow

InterLock is a **pre-review layer** on top of SharePoint/DMS, not a replacement. Three workflow facts that keep adoption low-friction:

- **No behavior change in upload.** Engineers continue uploading to SharePoint. InterLock pulls (or accepts uploads of) the same files.
- **Pre-marked PDFs are respected.** Annotated and highlighted PDFs round-trip without losing the annotation layer.
- **Flagging is suggestive, not assertive.** Every finding reads "potential mismatch, review" — never "this is wrong." Confidence-scored, dismissible, exportable. Engineers retain authority.

A typical reviewer session: open InterLock, drop two PDFs, run review (~30–90 s), triage flag list (typical case: ≤ 10 high-confidence candidates), click through to bbox-highlighted source for any flag of interest, accept or dismiss, export the accepted-flag JSON for audit. Total minutes saved per review: roughly the time the reviewer was spending diff-reading by hand.

## 3. The wedge

**Cross-document parameter discrepancy detection with directional citations for energy infrastructure documents.**

- **Cross-document:** flags surface only when two documents disagree on the same parameter (not stylistic, not formatting).
- **Directional:** every flag declares which document is authoritative for that parameter family and which is deviating. Symmetric "conflict between A and B" findings are explicitly forbidden — they push the cognitive load back to the reviewer.
- **Cited:** every flag carries a tuple of (document, page, section, exact quoted text, bbox). The reviewer can verify in one click.
- **Consequential errors only:** the bar is "would a senior engineer care during a design review?" Grammar, formatting, headings-only changes are suppressed by construction.

The canonical MVP scenario is the 60% → 90% phase-revision review: a coordination study revised between milestones, where the reviewer needs to know what changed and whether the changes are justified. The system surfaces value-level deviations with confidence, anchored to source text. The MVP fixture (Eaton sample coordination study + 6 documented mutations) shows TP-1 (decimal-shifted transformer impedance), TP-2 (decimal-shifted fault current), and TP-3 (decimal-shifted transformer rating) being flagged at confidence 1.0, while the FP-1 unit-equivalent trap (150 kVA vs 0.15 MVA) is correctly suppressed by Pint unit normalization.

## 4. Wedge-to-platform path

| Platform feature | What it adds | Why a downstream review team pays for it |
|---|---|---|
| Cross-doc semantic alignment (heterogeneous docs) | Spec ↔ study ↔ one-line ↔ panel schedule | Catches inconsistencies invisible inside a single doc |
| Configurable authority hierarchy | Reviewer declares "data sheet beats study beats one-line" before run | Removes hardcoded assumption; supports diverse project types |
| Phase-to-phase comparison (30 → 60 → 90 → IFC) | Multi-document review session | Surfaces parameter drift between phases that today only senior eyes catch |
| Standards-as-authority | IEEE / IEC / NERC compliance pass | Substitutes a slow manual standard cross-reference with automation |
| Audit log + reviewer e-signature | Regulatory traceability | Mandatory for nuclear / high-voltage / utility filings |
| DMS integration (SharePoint, Bentley ProjectWise, Autodesk Docs) | Automated ingest on doc check-in | InterLock runs in-line with existing engineering operations |
| CAD geometry comparison | 2D/3D mismatch detection | Closes the gap with bananaz.ai-style tools; consolidates spend |

## 5. Why now

AES alone has 5 GW under construction out of an 11.1 GW PPA backlog, tripling renewables capacity through 2027, and a full coal exit by end of 2025. Each MW in construction generates hundreds of cross-referenced engineering documents. EPC contractors produce design basis, calcs, specs, vendor packages, IFC drawing sets, O&M manuals — all flowing to owner-side reviewers at AES-like organizations. A misplaced decimal in a transformer spec almost cost a multi-million-dollar loss in the example the AES engineer shared with us. Industry-documented patterns confirm: cross-discipline coordination failures, decimal errors in load calcs, and missing/superseded standards references are the leading sources of costly design-review misses. The market has plenty of CAD comparison tools (bananaz.ai), plenty of textual diff tools (Adobe Acrobat), and plenty of DMS (SharePoint, Bentley). None do parameter-level, semantics-aware, directionally-cited discrepancy detection across heterogeneous engineering documents. **That is the open field.**
