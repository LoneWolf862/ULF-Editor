# ULF — Valheim Character Workshop

A local Python/PySide6 desktop editor with a Norse / WolfWorks theme. **Alpha 0.1**.

## Run on CachyOS / Linux

```bash
cd ULF
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
# or python run.py /path/to/character.fch
```

On Windows (PowerShell), activate with `.venv\Scripts\Activate.ps1` and use `python run.py`.

## Current features

- `.fch` reader/writer for profile versions **44/46**, player data **23–33**, inventory **109**, skills v2.
- Validates SHA-512 and **requires byte-identical round-trip before editing**.
- Eight-column / six-row inventory grid; change prefab, stack count, quality, durability and equipped status.
- Add/delete items; skill level/experience editor.
- **Save As only:** refuses to overwrite the loaded original. Exports verified by loading the result again.
- Preserves unrelated player data and profile metadata, including existing cheat-related fields; does not alter flags on existing items. Newly added items have an unset cheated-item bit.

## Known limitations

- The bundled catalog is a **small starter catalog**, not the entire Valheim prefab database. For an unrecognized item you can enter its exact prefab name. Unknown existing hashes show as `#123...`; changing them without knowing the prefab will replace that item.
- Character preview currently requires a profile in the supported versions. For older saves, additional adapters are needed.
- Inventory grid is fixed to 8×6 in the UI; files with items outside that grid are preserved but not displayed.
- No actual item artwork, drag/drop, built-in backup recovery, cloud sync conflict handling, or achievement verification yet.
- Save editing and avoiding console commands do **not** guarantee achievements; character/world/mod state can affect eligibility.
- Close Valheim before using or replacing saves; make an independent backup. The app itself never loads a character automatically.

The user's real character file is **not bundled**. A prior JSON export was used only to generate a small item-name lookup list, with no character-specific data included.

## Next milestones

Full item catalog; item artwork; drag-and-drop; more save formats; automated integration tests; eventually standalone web UI reusing the core through an API or a browser-native port.
