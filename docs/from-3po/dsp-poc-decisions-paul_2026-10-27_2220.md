# DSP POC: Paul's decisions for the HLD

2026-10-27 22:20, from 3PO after working through `dsp-poc-decision-brief-for-3PO-2026-10-27.md` with Paul. Replaces the 22:06 version.
For R3: draw the HLD (DTE-152, due 10/28 12:00 standup) from this file. **In progress:** decisions not listed as decided below are still open; use R3's own recommendation and mark them open in the HLD.

**Team-facing doc:** Paul also has a Claude Doc, "DSP v1 Pipeline POC: What Monday Delivers" (https://claude.ai/artifact/NkYA4RSMWk4QCFtyC4dUr7), with summary, purpose, flow diagram, infrastructure, decisions, success criteria, out of scope and open questions. Keep the HLD consistent with it.

## Design principle (unchanged, reaffirmed)

Double POC, one pipeline: one transform, two writers. **A (Parquet contract) never depends on B (S3 Tables experiment).** B depends only on the shared transform. Draw A solid and B as the time-boxed trial branch (dashed). Nothing on A's path may read from B's storage.

## Decisions

| # | Decision | Paul's call | Notes for R3 |
|---|---|---|---|
| 4 | Where the D5 dataset-wide transaction_id check reads history from | **Id ledger on the contract (A) side.** Not the lake (would make A depend on B); not prior Parquet outputs (they hold only kept-publisher rows, so they miss reuse by blank-publisher/Test Account rows, e.g. today's Veradigm case). | See "#4 design" below. |
| 1 | Outputs per hour | **One Parquet file per canonical publisher (6), marked "to confirm" with Jesse.** | Publisher list + label mapping in one config file (6 to 3, or adding AdKernel publishers, is a config edit). **Write a file for every configured publisher every hour, zero rows if empty** (practiceehr has 43 rows in 2 years); otherwise "all output files exist" never holds and FindWork reprocesses those hours forever. Empty file = "nothing came in", not "file missing". |
| 2 | What the lake (B) holds | **`events` only for the POC**, mirroring A's outputs. | Quarantine goes to the team's existing `rhde-quarantine-<env>/manifests/...` + `failed-keys/` format (sandbox copy) on A's side, not a lake table. Draw `raw_events` and a lake quarantine view dashed, labelled "next, if Iceberg is kept". |
| 3, 5, 6, 7, 8 | | Open: use R3's recommendation, marked open/proposed | |

### #4 design

- **Ledger:** on every run, before filtering, the transform writes one small Parquet file per hour covering **all** rows: `transaction_id`, raw publisher label, row hash, `source_file`, `event_ts`. Framed as raw-per-run storage (same pattern as Cillian's email pipeline), not job state.
- **Check:** DuckDB reads only `transaction_id` from the ledger, as a semi-join against the incoming hour's ids (memory scales with the hour, not the history).
- **Replays (D12):** exclude rows from the same `source_file`, or a replayed hour quarantines itself.
- **Concurrency:** the Map runs 2 hours in parallel; run the id check once over the batch of hours (or concurrency 1 for that step) so the same id in two parallel hours isn't missed.
- **Seed:** one-time load of the ~40M historical ids from `raw-data/dsp_raw.duckdb` as monthly files sorted by `transaction_id` (~25 files).
- **Compaction:** monthly roll-up of hourly ledger files into one sorted file. Not needed for the 11/02 POC; add by the 11/07 pipe version.
- **Window:** `id_check_window` is a config value. **Default: full history** (matches D5 as Jesse stated it). Do not shrink it until Jesse answers Q-A/Q-B below; then it is a config change, no redesign.
- **Lake:** B's `events` is loaded from the transform output; a future `raw_events` could load from the ledger (one-way A to B).
- **Phase 0 addition:** time the ledger check against the seeded 40M ids.

## Questions for Jesse (new from this session; do not lose)

- **Q-A. Age-based archive:** Is there (or should there be) an age-based archive for DSP data, i.e. how long does data stay in the active table before it's archived? I'll set the id-check window to match. (Today's archive tool only moves outputs on a replay, not by age.) Context: reused ids seen up to 278 days apart; ~13 months would cover all observed cases and EHR's calendar-year campaigns.
- **Q-B. Warehouse key retention:** How long does the warehouse (Redshift) keep DSP history, and does it treat `publisher-transaction_id` as unique? The key's uniqueness has to hold as long as the longest-lived copy, so the window can't be shorter than that.
- **Outputs (#1):** when asking 6 vs 3, ask about Relevate Games (57% of kept rows) and Office Ally (14%) by name.
- **O2 framing (add when asking O2):** if both sides of an id conflict are quarantined, a later conflict has to pull an already-delivered row, which under D12 means replaying the earlier hour's whole file.

Existing "to confirm with Jesse" items from the brief still stand: drop test-NPI step (D11); Python Lambda vs Node channel; DTE-147 access; O1; O2; file-level reject threshold (~0.5%); owner of the AdKernel reused-id report.
