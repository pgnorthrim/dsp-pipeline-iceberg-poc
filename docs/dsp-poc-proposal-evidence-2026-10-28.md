---
title: "DSP POC proposal: what Jesse and Scott said (evidence notes)"
date: "2026-10-28"
---

**Prepared for:** Paul Guidry (source notes for the POC plan doc; not for sending).
**Sources:** transcripts in `/mnt/hgfs/dev-shared/rh_meeting_transcripts/` (times = minutes into the recording) and the meeting notes in `Docs/status-meetings/`. Quotes are transcript wording, lightly trimmed; transcript spelling is approximate.

## 1. Jesse asked for this POC (10/23 standup, ~0:37-0:52)

| # | What Jesse said | Use in the doc |
|---|---|---|
| J1 | "The thing I'd be most interested in for you, Paul, is maybe play with S3 Tables along the way ... you have the most experience with Iceberg ... you're the best bet for somebody to play with the newfangled Iceberg thing and see if we like it." (~0:37) | Path B exists because Jesse asked for it |
| J2 | "We pick on one thing that you'll try ... if you just want to do Step Functions, cool ... it does need to be able to originate from the heartbeat." (~0:37-0:38) | Why Step Functions; heartbeat stand-in |
| J3 | "Every hour you pick up a generic DSP file that's a gzipped CSV and you output three Parquet files, one for Veradigm, one for CareCloud and one for DoseSpot ... checking for duplicate ids ... very syntactical cleanup, and then you put out Parquet. That would be perfectly wonderful." (~0:38-0:39) | Path A is exactly this; 6 vs 3 question |
| J4 | Restatement today = delete the output file, archive it, record the forced regeneration; "if you have something better but kind of keeps the spirit of we replaced the file, I'm okay with that." (~0:40-0:41) | Whole-file replacement (D12) |
| J5 | "I am nervous about separate state on actual job runs ... I would probably steer you towards the manifests." (~0:41) | No job-state table; manifest + output files |
| J6 | Historical load on a tag, active pipeline without dead code ("the Eric pattern"). (~0:43-0:44) | Backfill design |
| J7 | "I would avoid MWAA ... if the cron sends an event that triggers a Step Function, I could deal with that." (~0:45) | Alternatives considered |
| J8 | Lock: "the Step Function will handle the lock ... if the Step Function is still running it will discard, and that's actually what Cillian's [Glue jobs] did." (~0:49-0:50) | CheckLock design |
| J9 | "You are responsible for enrichment ... use Cillian's factory endpoint" (~0:50-0:52); the EC2 "is huge, you can run whatever you want on that EC2" (~0:52-0:53) | Enrichment stub; EC2 fallback is a real option |

## 2. Jesse's cautions (the objections the doc must answer)

| # | What Jesse said | When |
|---|---|---|
| C1 | "You're not building a data lake, you're building a pipeline to take a file and enrich it ... and that goes for you too, Paul: file in, file out." | 10/23 ~0:06 |
| C2 | "We need to be intentional with where we experiment ... Paul might also run into this brick wall where ... we're going out really far afield for a 1.5 ... do we just do it easy? And then you get to play." | 10/26 ~0:21-0:22 |
| C3 | Iceberg's usual append convention: "No, bro. We need to actually just replace the whole goddamn file. That's what the data warehouse expects right now." | 10/26 ~0:37 |
| C4 | Iceberg niceties matter where there are upserts, slicing and tags on terabytes (Jeff's work), "where you're dealing with, oh my gosh, the four megabyte file." Parquet is for when something else reads it. | 10/27 ~0:42-0:43 |
| C5 | "Your first pipeline ... there is no upsert, you have nothing to upsert to. And we will be putting out Parquet files, which is as far as we push the organization so far." | 10/20 ~0:58-0:59 |
| C6 | Email (10/21 00:31): the new DSP will be "night and day"; what Paul is working on now "will not transfer"; keep it separate. | 10/21 email |

## 3. Jesse's direction and goals (why the work matters)

| # | What Jesse said | When |
|---|---|---|
| G1 | "There will be a data lake, as to whether or not we want to roll S3 Tables or Iceberg ourselves or put Snowflake on ... that's the conversation that, after you guys build your first couple pipelines, I want to have." | 10/20 ~0:48 |
| G2 | "After we get through this pipeline, though, we need to get off the single node runtime." | 10/23 ~0:23 |
| G3 | "This is all built into this one monolith. It can't stay a monolith forever." Fanning out from the Node code is OK. | 10/23 ~0:52 |
| G4 | 1.5 vs 2.0: "For 1.5 we're giving to you what we got" (to the warehouse); filtering such as NPI belongs in a later, separate step across all pipelines. | 10/27 ~0:22-0:26 |
| G5 | Like-for-like consistency is the business risk: going from 95% to 90% flagged "I can't really accept that variance ... single-digit shifts in the top-level metric are a really big shift for business delivery." | 10/27 ~0:23-0:24 |
| G6 | Quarantine with a reason, in the standard format, not a new data store. "What do we actually look at? I look at the quarantine, both the record and the manifest." | 10/26 ~0:17; 10/27 ~0:42 |
| G7 | DevEx and readability decide formats: "when we need to open a file and figure out what you produced, you could actually read it." | 10/27 ~0:43 |
| G8 | "Long term, for the data lake, I do plan on just straight piping everything from BigQuery ... getting it out of BigQuery into our system." | 10/23 ~0:57 |
| G9 | "We don't plan here." (joke) — but wants "more rapid prototyping energy" and a shared tools repo. | 10/27 ~0:16; 10/26 ~0:23 |

## 4. Scott: business context and the go-ahead

| # | What Scott said | When |
|---|---|---|
| S1 | Iceberg is "not a don't do it ... it's a matter of figuring out what that lag is going to be ... if it takes too long, let's do the fast, simple path, and then we'll start playing with the other tools." | 10/27 standup ~1:03 |
| S2 | Iceberg not on hold; DSP pipe version ~11/07, final mid-November; Paul's Monday 11/02 POC plan "should work". Wants to "put a bow on" the DSP. | 10/27 1:1 ~0:03-0:05 |
| S3 | The DSP is a priority because EHR is a big part of the business and the DSP diversifies supply. | 10/27 1:1 ~0:16 |
| S4 | EHR projects 20-25% growth next year; the new DSP's full clinical-signal stream could be ~100,000 times bigger than today (its own streaming solution). | 10/27 1:1 ~0:21-0:24 |
| S5 | ~150 EHR campaigns renew in about six weeks; clients hard to reach from mid-November; no year-end freeze. | 10/27 1:1 ~0:19-0:21 |
| S6 | Hourly, time-based trigger: event-based makes a missing file hard to see. Two quarantine levels (bad rows vs bad file); threshold ~0.5% floated, not settled. | 10/27 1:1 ~0:24-0:30 |
| S7 | Slice-to-warehouse migration is Scott's main initiative; DSP data into the warehouse by mid-November. | 10/14 notes |
| S8 | AdKernel signed 10/19; nothing live before 2027; Audiencelogy may be turned off in January; one schema going forward so a column means the same for every vendor. | 10/20 1:1 notes |

## 5. Data examples (Paul's findings, cite the source query)

| # | Example | Source |
|---|---|---|
| E1 | 87 transaction ids shared across publishers, 1 to 278 days apart; 7,270 of 7,357 repeated ids were same-millisecond double-fires | `status-followups-2026-10-21.md`, transaction-id-verdict-2026-10-20 |
| E2 | Shared ids carry different NPIs (IQM 86 ids / 677 extra rows, Veradigm 1 id / 8 rows) — not "same row, publisher forgotten" | 10/20 notes, section 3 |
| E3 | September 2026 is 99.28% kept publishers | status-followups-2026-10-21 |
| E4 | ~40M historical rows (load_duckdb rows=40,319,181) | BUILD-HISTORY 10/27 |
| E5 | Relevate Games 57% / Office Ally 14% of kept rows; practiceehr 43 rows in 2 years | 3PO decisions file 10/27 (verify against the publisher counts query) |
| E6 | Blank-publisher rows historical only, last 2026-01-27 | status-followups-2026-10-21 |
| E7 | Cillian's enrichment fails ~4% of the time today (being fixed) | 10/23 ~0:51 |

## 6. Tensions to handle honestly in the doc

1. **"File in, file out, not a data lake" (C1, C5) vs "play with S3 Tables" (J1).** Path A is file in, file out. Path B is a trial branch Jesse asked for, and never on A's path.
2. **"Will not transfer" (C6).** The schema and publisher mapping may not transfer to AdKernel; the pattern does (lock, manifest, quarantine, replays, id ledger, Step Functions harness), and G2/G3 say the team wants to move off the single-node monolith anyway.
3. **Iceberg at 4 MB (C4).** B's value is not performance at today's size; it's evidence for the data-lake decision Jesse plans after the first pipelines (G1), at near-zero extra cost because the transform is shared. Volume growth (S4) is the longer-term reason.
4. **Like-for-like (G5).** The POC must show A's counts reconcile with today's raw files (pass-through, no NPI filtering, D11), so nothing shifts the business metrics.
5. **Scott's time-box (S1).** The doc needs a real time-box number for B and a stop rule.
