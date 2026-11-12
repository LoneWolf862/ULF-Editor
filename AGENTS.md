# ULF Editor development guidelines

## Project overview

ULF Editor is a Python/PySide6 desktop application for editing Valheim `.fch` character saves. It draws inspiration from Viking Editor's functionality and visual design and uses original Wolf/Ulf styling. A self-hosted web edition is a deferred option.

## Requirements authority

- [REQUIREMENTS.md](REQUIREMENTS.md) is the authoritative specification for ULF Editor and is approved for MVP development. Read the relevant requirements before implementing a feature, fixing a bug, or changing the architecture.
- Reference requirement IDs in implementation plans and completion reports. Preserve approved requirements and obtain an explicit owner decision before changing, removing, or reinterpreting them.
- Surface conflicting or ambiguous requirements before implementing a potentially incompatible change. If the authoritative specification is missing, flag the gap.

## Architecture

- Keep the binary save-file engine independent of PySide6 and other graphical interface code.
- Prioritize a reliable, fully offline desktop application for Windows 10 and Linux, including catalog lookup, loading, editing, and export.
- Keep core interfaces reusable. Implement web infrastructure, APIs, hosting, or browser interfaces only when explicitly requested.
- Complete and stabilize MVP functionality against its acceptance criteria before implementing post-MVP features.
- Schedule advanced inventory sorting, movement/swapping, drag-and-drop, and equipment management after MVP.
- Prefer maintainable modules with clear responsibilities over large monolithic files.

## Primary features

- Edit item quality, including unusually high upgrade levels within the save format's supported range.
- Edit inventory stack quantities.
- Add items using valid prefab identifiers and remove items from the inventory.
- Edit character skill levels and experience.

## Inventory safety

- Enforce each item's verified maximum stack size and the serialization limits for quantity edits and item creation. Reject oversized stacks.
- Preserve unknown inventory records byte-for-byte, including unrecognized modded items. Allow only explicit quantity edits backed by a verified item maximum, and preserve every other field. Never guess a stack limit or silently clamp a preserved quantity. Block item creation without verified limits.

## Save-file safety

- Use Save As for MVP exports. Overwriting the original `.fch` file is prohibited, including through a file alias.
- Always validate the save's SHA-512 checksum and reject unsupported save versions.
- Require the unmodified save to serialize byte-for-byte identically to the input before allowing edits.
- Preserve unrelated character data and metadata, including existing cheat-related records and item flags.
- Leave cheated-item flags unset when creating inventory items.
- Reopen and validate the written export before reporting success.
- Use the two locally provided vanilla character saves for read-only compatibility investigations. Keep the files local and omit personal character data from diagnostic reports.
- Never commit actual character saves, backups, or personally identifying save data. Use synthetic fixtures for checked-in regression tests.

## Development workflow

- Define measurable acceptance criteria tied to requirement IDs before implementing changes.
- Create automated regression tests for serialization changes, bug fixes, and new functionality.
- Report which requirement IDs the work satisfies and distinguish implemented, tested, partially implemented, and unimplemented requirements.
- Document significant architectural decisions.

## Git development policy

### Branches and repository protection

- Develop substantial changes on dedicated feature, fix, or milestone branches. Keep `main` as the stable, reviewed baseline.
- Never commit or push directly to `main` during autonomous development. All merges, releases, and version tags require explicit owner approval.
- Never force-push during autonomous development. Rewriting published history requires explicit owner approval.
- Changes to approved requirements require owner review and explicit approval. Never modify original character saves or discard uncommitted work without approval.

### Autonomous commits and GitHub synchronization

- Once the owner approves the proposed breakdown and synchronization of the existing Alpha 0.2 and 0.2.1 work, this policy provides standing authorization for commits and pushes within approved milestone scope. The initial policy setup and breakdown review do not authorize committing or pushing the existing work.
- Commit each meaningful, tested change on the approved development branch. Keep completed features, fixes, regression test groups, compatibility changes, and substantial documentation updates in focused commits. Use conventional messages such as `feat:`, `fix:`, `test:`, `refactor:`, and `docs:`.
- After each meaningful, tested commit, push to the same approved development branch in `LoneWolf862/ULF-Editor`. Keep pushes scoped to that branch. Do not create or delete remote branches outside the approved scope.
- If authentication fails, report the failure and leave the commits local. Do not repeatedly retry with different credentials.

### Checks and reporting

- Before committing, inspect the staged diff. Before pushing, inspect the staged state and review the full outgoing commit range. Verify that no real `.fch` saves, backups, private character data, credentials, tokens, or temporary files are included, and that unrelated files and existing work are preserved.
- Run the relevant automated tests before each commit and push. Record known failures and resolve relevant failures before proceeding. Do not bypass failing tests to produce a commit or push.
- After each major development phase, report the current branch, recent commit SHAs, completed work, test results, remaining tasks, and GitHub synchronization status.

## Interface design

- Use PySide6 for the desktop application.
- Maintain a dark, Norse-inspired design with bronze accents and subtle Wolf/Ulf theming.
- Treat usability as an MVP requirement. Prefer graphical, slot-based inventory management over spreadsheet-style editing.
- Pair skill level sliders with synchronized numeric inputs for precise entry.
- Keep the interface functional at ordinary desktop resolutions.
- Prioritize usability and reliable editing over purely decorative elements.
