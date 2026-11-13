# ULF — Valheim Character Workshop

A local Python/PySide6 desktop editor with a Norse / WolfWorks theme. **Alpha 0.3.1** adds comprehensive vanilla catalog coverage, equipment statistics, Individual Repair and previewed Repair All for Valheim 1.0.21. The owner approved the tested repair/export/game-resave workflow. See the [release notes](docs/ALPHA_0.3.1_RELEASE.md) and [changelog](CHANGELOG.md) for scope and limitations.

This development branch implements **Alpha 0.4 inventory management**, ready for
owner testing within its documented supported scope. It is not a new release.
See the [implementation report and acceptance checklist](docs/ALPHA_0.4_INVENTORY_MANAGEMENT.md).

## Run on CachyOS / Linux

```bash
cd ULF-Editor
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
# or python run.py /path/to/character.fch
```

On Windows 10 (PowerShell):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

Installation needs the dependencies. Normal application use is offline. Python 3.12 is the baseline. Linux runtime acceptance remains open.

## Current features

- `.fch` reader/writer for Valheim 1.0.21 (**47 / 34 / 110 / 2**) and the existing legacy matrix (**44 or 46 / 23–33 / 109 / 2**), in profile / player / inventory / skills order.
- Validates SHA-512 and **requires byte-identical round-trip before editing**.
- Eight-column graphical inventory with variable display height and a separate item inspector. Edit verified items' stack count, quality (1–65,535) and durability. Preview supported equipment changes and all conflicting unequips.
- Transactional Move/Swap through drag/drop or a keyboard-accessible destination chooser, plus previewed Duplicate, Replace and Fill Stack actions. Replacement shows fresh metadata and recalculated durability explicitly.
- Visible Undo/Redo and Ctrl+Z, Ctrl+Y, Ctrl+Shift+Z for supported item, skill and inventory operations. Bulk actions occupy one history entry; unapplied drafts block history travel.
- Search item names and prefabs offline. Filter by category and inspect verified stack limits and source data.
- Edit skill levels with synchronized sliders and precise numeric inputs. Expand a row to edit experience explicitly.
- Apply item or skill drafts, review before/after values, and discard changes before exporting.
- Alpha 0.3.1 audits Valheim 1.0.21's complete ObjectDB registry and supports 927 ordinary inventory candidates with verified statistics (1,049 catalog entries including retained legacy records). Repair supports 285 equipment prefabs. See the [coverage and validation report](docs/ALPHA_0.3.1_ITEM_COVERAGE.md) for exact counts, exclusions, provenance and remaining acceptance checks.
- **Save As only:** refuses to overwrite the loaded original. Exports verified by loading the result again.
- Transactional item/skill validation; invalid proposals do not partially apply. Level edits preserve experience unless explicitly changed.
- Source/hard-link protection, external-change detection, closed temporary-file read-back, checksum/semantic checks and atomic target publication.
- Preserves unrelated player data and profile metadata, including existing cheat-related fields; does not alter flags on existing items. Newly added items have an unset cheated-item bit.

## Known limitations

- The bundled offline catalog has **1,049 entries**, including all **927 verified ordinary inventory candidates**, with **288 verified maximum durability definitions** and **285 repairable equipment types**. All 33 records in the tested 1.0.21 sample are identified. Unknown records remain read-only and are preserved exactly across unrelated edits. Eleven entries use prefab identifiers because friendly names are unavailable; 122 retained legacy entries lack verified statistics.
- Real-file evidence covers **46 / 33 / 109 / 2** and **47 / 34 / 110 / 2**. Other accepted legacy combinations have synthetic coverage. Unsupported versions are rejected.
- Character preview currently requires a profile in the supported versions. For older saves, additional adapters are needed.
- Creation is limited to the first six rows and, on 1.0.21, to the save's verified pocket capacity. Existing higher-row items remain visible. Ambiguous positions appear in inventory diagnostics.
- Item artwork uses original ULF silhouettes and category fallbacks. Automatic sorting, backup recovery, cloud sync conflict handling, and achievement verification remain outside the current interface work.
- Duplicate/Replace and equipment management require inventory v110. Copy/replacement rejects custom data, nonzero variants/world levels and flagged sources. Equipment supports verified saved-slot rules only; context-dependent torches, DLC ownership and unknown/modded equipment are unsupported. Existing records remain preserved.
- History is in-memory for the current session. Dependent organization changes require Undo or Discard All instead of selective discard. Alpha 0.4 native drag/drop and in-game load/resave acceptance are pending.
- Save editing and avoiding console commands do **not** guarantee achievements; character/world/mod state can affect eligibility.
- Close Valheim before using or replacing saves; make an independent backup. Open a character explicitly or supply its path when launching the app.
- Native Linux, the full Windows accessibility/DPI matrix and extreme-quality gameplay remain unverified. Statistics are build-specific item values, not final combat predictions; positive-world-level damage/armor and projectile effects are unavailable.

Real character files are **not bundled**. Checked-in tests use synthetic fixtures. Public reference notices and factual catalog provenance are in `docs/references/`; no game artwork or executables are included.

## Tests and stabilization evidence

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

On Linux use `.venv/bin/python -B -m unittest discover -s tests -v`. Desktop tests use Qt's offscreen platform. See [the stabilization report](docs/ALPHA_0.1.1_RESEARCH.md) for results, source evidence, limitations and the owner’s acceptance results. The optional `tools/inspect_game_items.py` research utility needs UnityPy 1.25.4; the editor itself does not.

Alpha 0.4: **126 passing tests, zero failures/skips** on Windows, including the
101-test release baseline. Native Linux and Alpha 0.4 game acceptance remain pending.

## Next milestones

Next gate: owner acceptance of Alpha 0.4 on disposable saves, including native
Windows/Linux, offline use, accessibility and Valheim load/resave. Recovery and
distribution hardening can follow acceptance. Automatic sorting and broader
metadata/equipment policies need separate scope approval. See
[the approved requirements](REQUIREMENTS.md); its baseline remains unchanged.
