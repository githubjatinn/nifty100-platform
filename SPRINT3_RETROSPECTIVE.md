\# Sprint 3 Retrospective — Screener \& Peer Comparison Engine



\## What worked

Filter engine, 6 presets, composite scoring, peer percentile rankings, radar charts,

and both Excel exports (screener\_output.xlsx, peer\_comparison.xlsx) were all built

and verified end-to-end against the real database. All 14 legacy Sprint 1/2 data

quality tests still pass, and all 12 new Sprint 3 unit tests pass.



\## What broke and got fixed

\- Guessed column names didn't match the real schema (financial\_ratios, sectors,

&#x20; market\_cap, peer\_groups are separate tables, not one flat table)

\- financial\_ratios.year was a fiscal-year string ('2024-03') while market\_cap.year

&#x20; was a calendar-year integer — the join silently failed until the string was cast

\- SELECT fr.\* duplicated company\_id (already pulled from companies), which only

&#x20; surfaced once DataFrames were merged in the pipeline

\- Preset filters were initially additive instead of exclusive, causing some presets

&#x20; to return 0 results and others to return identical counts

\- One company name contained a stray newline character, breaking Windows file paths

&#x20; for radar chart PNGs



\## What I'd do differently

Verify the exact schema — table names, column names, year format — before writing

any filter or join logic, rather than debugging it in through trial and error.

