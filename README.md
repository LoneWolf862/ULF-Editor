# ULF — Valheim Character Workshop

A local Python/PySide6 desktop editor with a Norse / WolfWorks theme. **Alpha 0.2.1** adds Valheim 1.0.21 save compatibility to the Alpha 0.2 interface. See the [compatibility report](docs/ALPHA_0.2.1_COMPATIBILITY.md) for verification and the in-game test checklist.

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
- Eight-column graphical inventory with variable display height and a separate item inspector. Edit verified items' stack count, quality (1–65,535), durability and equipped status. Replace an item through explicit removal and catalog creation.
- Search item names and prefabs offline. Filter by category and inspect verified stack limits and source data.
- Edit skill levels with synchronized sliders and precise numeric inputs. Expand a row to edit experience explicitly.
- Apply item or skill drafts, review before/after values, and discard changes before exporting.
- The Alpha 0.3 development branch previews verified 1.0.21 item statistics and stages individual or bulk durability repairs for supported prefabs. See the [item statistics report](docs/ALPHA_0.3_ITEM_STATS.md) for coverage and acceptance checks.
- **Save As only:** refuses to overwrite the loaded original. Exports verified by loading the result again.
- Transactional item/skill validation; invalid proposals do not partially apply. Level edits preserve experience unless explicitly changed.
- Source/hard-link protection, external-change detection, closed temporary-file read-back, checksum/semantic checks and atomic target publication.
- Preserves unrelated player data and profile metadata, including existing cheat-related fields; does not alter flags on existing items. Newly added items have an unset cheated-item bit.

## Known limitations

- The bundled offline catalog has **821 entries** with sourced stack limits. It identifies 30 of 33 items in the 1.0.21 sample. Unknown records remain read-only and are preserved exactly across unrelated edits.
- Real-file evidence covers **46 / 33 / 109 / 2** and **47 / 34 / 110 / 2**. Other accepted legacy combinations have synthetic coverage. Unsupported versions are rejected.
- Character preview currently requires a profile in the supported versions. For older saves, additional adapters are needed.
- Creation is limited to the first six rows and, on 1.0.21, to the save's verified pocket capacity. Existing higher-row items remain visible. Ambiguous positions appear in inventory diagnostics.
- Item artwork uses original ULF silhouettes and category fallbacks. Drag/drop, backup recovery, cloud sync conflict handling, and achievement verification remain outside the current interface work.
- Save editing and avoiding console commands do **not** guarantee achievements; character/world/mod state can affect eligibility.
- Close Valheim before using or replacing saves; make an independent backup. The app itself never loads a character automatically.

Real character files are **not bundled**. Checked-in tests use synthetic fixtures. Public reference notices and factual catalog provenance are in `docs/references/`; no game artwork or executables are included.

## Tests and stabilization evidence

```powershell
.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

On Linux use `.venv/bin/python -B -m unittest discover -s tests -v`. Desktop tests use Qt's offscreen platform. See [the stabilization report](docs/ALPHA_0.1.1_RESEARCH.md) for results, source evidence, limitations and the owner’s acceptance results. The optional `tools/inspect_game_items.py` research utility needs UnityPy 1.25.4; the editor itself does not.

## Next milestones

Alpha 0.2.1 still needs the owner’s in-game load and resave test, native Windows and Linux workflow checks, and comprehensive catalog verification. Advanced sorting, drag-and-drop and equipment management are post-MVP. See [the approved requirements](REQUIREMENTS.md).
