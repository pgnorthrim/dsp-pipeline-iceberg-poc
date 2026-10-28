# DSP POC plan: queued edits (NOT applied - wait for Paul's go-ahead)

Target: `dsp-poc-plan-2026-10-28.md` (+ regenerate .docx; check Word lock first).

1. **Lambda timing wording.** Lambda cap is 15 min; the 5-min target comes from the lock budget
   (6 hours/run, 2 at a time = 3 waves inside the 25-min state-machine timeout).
   - A1 (line ~128): "One scheduled run (up to 6 hours, 2 at a time) finishes inside the 25-minute lock
     timeout, so each hour needs to finish in about 5 minutes. Lambda's own cap is 15 minutes. Phase 0
     measures this first." Fallback: tune config, then split within the hour, then Fargate.
   - Checklist (line ~145): "A full run of 6 hours finishes inside the 25-minute lock timeout (about
     5 minutes per hour in Lambda), or a contingency (config, split-hour or Fargate) is shown to work."
2. **Contingencies in section 9** (cheapest first): (1) config - fewer hours/run, MaxConcurrency, Lambda
   memory up to 10 GB; (2) split within the hour - Split -> Map over chunks (Parquet parts per publisher)
   -> Finalize per hour (whole-hour duplicate check + id-ledger check + 6 final files, temp->final);
   Distributed Map ItemReader could replace Split but gzip support unverified; (3) Fargate. Optional
   small diagram. Note: ~4 MB/hour today, likely unnecessary.
3. **Phase 0: sizing test** subsection under Path A: per-step timings in the manifest; file 1x/10x/100x
   (replicated rows, new ids); ledger 10M/40M/100M/200M; Lambda 2/4/10 GB; fit
   time = fixed + a*rows_in + b*ledger_rows; output a headroom table (today N rows, T s; ceiling M rows
   or L ledger ids; headroom Kx) vs Scott's 20-25% growth. Ledger (history) is the long-term limiting
   factor, id-check window config is the safety valve. Do NOT claim it covers the 100,000x stream
   (separate streaming solution). ~half day, a few dollars.
4. **Cillian lock pattern** (when he replies on Slack): update lines ~58/87/108/188, add a "how the
   lock works" note in section 5, cite his source. If his lock is Glue's max-concurrent-runs setting,
   reword to "same discard-if-running rule, done in Step Functions."
5. Assumptions table "#" column width fix in the .docx.
6. **Two-path overview figure** (`diagrams/dsp-poc-two-paths-2026-10-28.png`): insert in section 5 "What the POC is"
   (or section 1 Summary) once Paul OKs the picture.
