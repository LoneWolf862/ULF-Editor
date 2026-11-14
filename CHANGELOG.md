# Changelog

## Alpha 0.4 — Unreleased

Owner acceptance recorded 2026-11-14: successful Windows manual testing and
Valheim in-game load/save verification for the tested Alpha 0.4 workflow.
Awaiting PR review and explicit approval before merge, tag or publication.

- General Undo/Redo for supported item/skill edits and inventory transactions.
- Validated Move/Swap with previewed drag/drop and keyboard alternatives.
- Duplicate, explicit fresh-item Replacement and verified Fill Stack previews.
- Conservative equipment conflict management, equipped badges and overview.
- Complete affected-record previews and net change review; stale proposals fail
  without applying. Existing Save As and unknown/cheat metadata protections retained.
- 126 passing Windows automated tests (rerun 2026-11-14), zero failures/skips,
  including offscreen Qt tests. Native Linux, broader accessibility/DPI coverage
  and untested gameplay edge cases remain pending.

Scope, rejected metadata/equipment cases and owner checklist:
[Alpha 0.4 report](docs/ALPHA_0.4_INVENTORY_MANAGEMENT.md). No release tag or main merge.

## Alpha 0.3.1 — 2026-11-13

Owner-approved release, tag `v0.3.1-alpha`. Includes the Alpha 0.3 statistics
work and Alpha 0.3.1 catalog and validation work.

- Comprehensive vanilla catalog audit: 1,522 registered prefabs classified;
  927/927 verified ordinary inventory candidates supported, 1,049 total entries.
- 288 verified maximum durability definitions and 285 repairable equipment types.
- Current/maximum durability, percentage, quality-scaled equipment statistics,
  Individual Repair and transactional Repair All with preview and skip reasons.
- Recognizes Moose Hide Cape, Ice, Thunderblood Sword and Lightning Strike.
- Retains Valheim 1.0.21 compatibility, SHA-512 and exact no-op checks, original/
  alias protection, verified Save As and unrelated/cheat metadata preservation.
- 101 passing automated tests; owner-confirmed identification, repair, export,
  game load, repaired-equipment persistence and reopening after game save.

Native Linux, broader native accessibility/DPI checks and extreme-quality
gameplay remain untested. Full scope and limitations: [release notes](docs/ALPHA_0.3.1_RELEASE.md).

Earlier milestone evidence: [Alpha 0.2.1](docs/ALPHA_0.2.1_COMPATIBILITY.md),
[Alpha 0.3](docs/ALPHA_0.3_ITEM_STATS.md), [Alpha 0.3.1 audit](docs/ALPHA_0.3.1_ITEM_COVERAGE.md).
