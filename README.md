# ULF — Valheim Character Workshop

A local Python/PySide6 desktop editor with a Norse / WolfWorks theme. The **Alpha 0.2 interface** is available on the development branch. Alpha 0.1.1 passed initial Windows and in-game acceptance. See the [Alpha 0.2 implementation report](docs/ALPHA_0.2_UI_IMPLEMENTATION.md) for test results and outstanding acceptance.

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

- `.fch` reader/writer for profile versions **44/46**, player data **23–33**, inventory **109**, skills v2.
- Validates SHA-512 and **requires byte-identical round-trip before editing**.
- Eight-column graphical inventory with variable display height and a separate item inspector. Edit verified items' stack count, quality (1–65,535), durability and equipped status. Replace an item through explicit removal and catalog creation.
- Search item names and prefabs offline. Filter by category and inspect verified stack limits and source data.
- Edit skill levels with synchronized sliders and precise numeric inputs. Expand a row to edit experience explicitly.
- Apply item or skill drafts, review before/after values, and discard changes before exporting.
- **Save As only:** refuses to overwrite the loaded original. Exports verified by loading the result again.
- Transactional item/skill validation; invalid proposals do not partially apply. Level edits preserve experience unless explicitly changed.
- Source/hard-link protection, external-change detection, closed temporary-file read-back, checksum/semantic checks and atomic target publication.
- Preserves unrelated player data and profile metadata, including existing cheat-related fields; does not alter flags on existing items. Newly added items have an unset cheated-item bit.

## Known limitations

- The bundled offline catalog has **821 entries**, all with sourced stack limits; it is not the entire current game database. All 76 records in the two local compatibility samples are recognized. Their 62 distinct prefabs were checked directly against installed Valheim 1.0.21 (Steam build 26249040). Unknown items are preserved unchanged; editing/removal and unverified item creation are blocked.
- Real-file compatibility evidence covers profile 46 / player 33 / inventory 109 / skills 2. Older accepted versions have synthetic coverage only, not independent historical game validation. Unsupported versions are rejected.
- Character preview currently requires a profile in the supported versions. For older saves, additional adapters are needed.
- Creation is limited to the first six rows. Existing higher-row items are visible and editable when verified. Ambiguous positions appear in inventory diagnostics.
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

Alpha 0.2 acceptance still needs native Windows and Linux workflow checks and comprehensive catalog verification. Advanced sorting, drag-and-drop and equipment management are post-MVP. See [the approved requirements](REQUIREMENTS.md).
