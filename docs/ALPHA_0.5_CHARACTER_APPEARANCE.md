# Alpha 0.5 character appearance

Development branch: `feature/alpha-0.5-character-appearance`, from Alpha 0.4
`056808d83fc5717c60a4c8fa20fedcf82a234166`, verified against `v0.4.0-alpha`.
Baseline: 126 passing Windows tests. Owner assignment explicitly schedules
FR-092; REQUIREMENTS.md remains unchanged. No merge or release is authorized.

## Measurable acceptance criteria

- FR-092: typed model, hair/beard and two RGB vectors; explicit compatibility
  validation, searchable offline styles, grouped edits and field-level review.
- FR-005/015/032/060: no-op is byte-identical; changing one field preserves all
  other raw strings, float components, inventory, skills, progression and flags.
- FR-020/072: one validated appearance batch is one history action, invalid
  batches are atomic, drafts block history/export, mixed inventory/skill history
  restores exact serialized state.
- FR-050–054: only verified appearance spans may differ at export; source and
  aliases protected, atomic temporary output/read-back checks retained.
- FR-071/073/080: keyboard-accessible desktop controls, independent core model,
  readable current/proposed values. Native Linux and game acceptance are separate.

## Independent local research

Valheim 1.0.21, Steam build 26249040. Assembly SHA-256:
`9f959c0396ec4240d47fcbe5d0d062c428cc627244506db5ea567f9d77b2b769`.
Prefab bundle `c4210710` SHA-256:
`84f55cfb24af51b9f0494fd9d1a355bf009e08545ff8ccf607c7d88d2e4e1ec8`.
English labels from resources.assets SHA-256:
`892db5626808f6929c7f3c5dd3997e965100074b0a493d7ce54eb2489f0cdd6f`.
Assemblies/assets and inspection dumps remain local; only minimal factual
identifiers, labels, compatibility facts and hashes are bundled. No proprietary
implementation, models, textures or personal saves are redistributed.

The three Viking Editor research reports were inspected directly on their
research branch. They informed field-specific preservation tests; no research
branch merge or implementation copying is involved.

`Player.Save` writes beard then hair strings, skin then hair Vector3, then model
int32. These occur after known-text pairs and before the food list, not at fixed
file offsets. Each string is UTF-8 with a 7-bit encoded byte length. Vectors are
three little-endian IEEE-754 float32 values; model is little-endian signed int32.
`Player.Load` gates styles at player >=4, vectors >=5 and model >=11. All layouts
already accepted by ULF (player 23–34) include these fields; there are no optional
appearance fields in that supported range. Writes are deliberately restricted
to current profile47/player34/inventory110/skills2. Legacy views remain read-only.

`Player.SetPlayerModel` changes only the saved model and calls visual equipment.
The installed Player prefab has two visual models. The customization UI uses
male/female toggles and explicitly resets beard when selecting model1. ULF does
not reset it: a proposal targeting model1 must explicitly include BeardNone if
the current beard is incompatible. Unknown existing values remain visible and
unchanged when editing unrelated colors. Model/style edits require a verified
target model; no unknown hair token is silently replaced.

`PlayerCustomizaton.LoadHair` selects customization item type10 with Hair/Beard
prefix and excludes identifiers containing `_`. The local scan yielded 39 hair
and 27 beard options including HairNone and BeardNone. Hair applies to both
verified models; nonempty beards are offered under the supported model0 policy.
No DLC restriction was present in these selected prefab records. Tool-tier facts
are retained; this save editor does not claim a style is unlocked at a particular
in-game barber tier. Names are the English localization values, not invented labels.

## Colors and preservation architecture

Game setters store Vector3 directly. The vanilla customization UI uses
`Color.Lerp(skinColor0, skinColor1, skinHue)` for skin, and a hair-tone color lerp
multiplied by a brightness lerp for hair. Those UI formulas are not a serialized
8-bit palette. ULF exposes direct normalized RGB editing, not a claim to replicate
the vanilla tone slider or its asset-specific endpoints. Presets/tone sliders
are deferred rather than inventing endpoints or silently projecting a saved
color onto that palette. The proposed editor range is finite [0,1] per component;
existing nonfinite/out-of-range values are preserved until explicitly replaced.
This is an editor write policy, not a claim that the game rejects all other RGB.

`Appearance` is a frozen typed value object. The parser records appearance spans
while traversing the existing validated structure. Serialization replaces only
changed fields and preserves unchanged components' raw bytes, including signed
zero, NaNs and noncanonical string-length prefixes. No-op float32-quantized edits
do not produce a binary difference. Opaque before/after regions remain intact.
Export reparses the output independently, validates the changed-field allowlist
and compares the entire expected targeted middle section against the result.

## Character-name investigation

`PlayerProfile.SavePlayerToDisk` writes display name before player ID and start
seed. Character creation separately derives a lower-case profile file key.
`Player.GetItemUpgradeChance` initializes a missing upgrade seed from the player
name's stable hash plus the relevant key. Thus changing the display name may
affect future upgrade behavior even if existing seed entries are preserved.
Complete rename/file-key/platform name-validation invariants have not been
established. Name remains read-only, as explicitly permitted by the assignment;
no IDs, seeds, historical names or world records are rewritten.

## Development validation

**147 tests pass on Windows, zero failures/skips**, running
`.venv/Scripts/python.exe -m unittest discover -s tests -q`.
The 126-test release baseline remains included, with 15 appearance/core/history
tests and 6 desktop tests added. Parameterized subcases cover fields, versions,
invalid inputs and raw-byte encodings. The first core checkpoint passed 136 tests;
the final integration includes the remaining history, UI and export tests.

Tests cover both verified model indices, explicit model1/BeardNone resolution,
hair/beard search and selection, normalized colors, invalid/nonfinite values,
unknown styles/models, legacy read-only controls, grouped edits, mixed
inventory/skill/appearance history, divergent history, no-op edits, drafts,
review/discard, source protection and export reopen. Raw-preservation tests
include NaN payload bytes, signed zero and noncanonical string-length encoding.
Export rejects direct attempts to change unverified appearance or progression.

The local designated experimental save also passed exact no-op and five separate
appearance export/reopen cases (hair, beard, model with explicit beard resolution,
hair RGB and skin RGB). Source hash and all inventory/skill, identity, progression,
opaque and cheat metadata checks passed. Outputs remain ignored and local; no
personal data or actual saves are committed. This is serialization evidence,
not an in-game acceptance claim.

Desktop automation uses Qt offscreen. Synthetic 1210×760 and 800×600 renders were
visually inspected; the form scrolls to expose all controls. Native Windows
interaction, complete accessibility/high-DPI coverage, native Linux and Alpha
0.5 in-game load/resave acceptance remain pending.

## Completed application integration

The Appearance tab includes read-only identity/version/current-value overview,
two verified body choices, searchable hair/beard selectors, current/proposed
color swatches, RGB inputs, a visual color picker, per-color revert, a complete
change preview, Apply Changes and Revert Draft. Global Undo/Redo and Review
Changes remain available in the shell. Unknown current styles/models stay
visible; selecting a supported replacement is explicit. Search alone never
changes a draft. Legacy saves expose values but disable appearance editing.

RGB inputs use shortest float32-roundtripping text rather than silently rounding
the original values to 8-bit channels. Swatches are approximate screen previews;
picker acceptance explicitly proposes its returned RGB values, which are shown
before applying. Canceling the picker leaves drafts untouched. Invalid proposals
show an explanation and disable Apply. The preview does not claim a game render.

`Session` adds appearance commands to the existing history. A grouped appearance
apply publishes one validated candidate. Draft state is separate from the applied
working state and survives unrelated item edits and editor refreshes. Appearance
drafts block Undo/Redo and export and can be reached from Review Changes. Undo
restores field bytes and the editor values; redo reproduces the accepted state.
The review has a distinct Appearance group with every changed field. Discard
restores the original appearance as one group; existing dependent inventory
operations still require Undo or Discard All. No separate appearance history or
export bypass exists.

Files: `core/appearance.py`, `core/appearance_catalog.json`, targeted additions to
`core/fch.py` and `core/export.py`; `desktop/appearance.py`, session and shell
integration; synthetic fixture extension and appearance/desktop regression tests.
No dependencies or approved requirements were changed.

## Limits and proposed policy amendments

- Appearance writes are supported only for 47/34/110/2. Existing accepted legacy
  formats remain readable and preserve their original appearance exactly.
- Unknown styles/models are not creation choices. Unrelated edits preserve them;
  style edits require a supported model. Model1 requires BeardNone explicitly.
- Normalized RGB [0,1] is the conservative editor write policy. Out-of-range or
  nonfinite existing vectors remain preserved until explicitly replaced with a
  supported vector. Vanilla palette/tone presets are deferred because their
  asset-specific endpoints were not established. No gamut or brightness behavior
  is guessed. Ratification/expansion of this policy is proposed for owner review.
- Model1 beard restrictions follow the verified customization UI; existing
  unusual combinations are preserved on load. Mod-specific style compatibility
  and changes outside the verified combination policy remain unsupported.
- Character name remains read-only. Future rename work requires a separate
  decision on name/file-key validation and future upgrade-seed effects, never
  rewriting historical seeds to hide a rename.
- No 3D renderer, game artwork, thumbnails, color-management guarantee, barber
  unlock editing, skin palette presets or Alpha 0.6 features are included.
- History remains session-local and unbounded, as in Alpha 0.4. Linux, native
  accessibility/high-DPI and actual game behavior remain acceptance tasks.

Implemented and regression-tested: FR-092 for the supported fields/layout;
FR-020/072 history and staging; FR-005/015/032/050–054/060 preservation/export;
FR-080 UI-independent core. FR-071/073 have automated UI coverage only and
remain partial pending native accessibility/platform acceptance. Name editing,
legacy appearance writes and advanced rendering are explicitly unimplemented.
The above policies supplement the owner's milestone assignment as proposals;
they do not silently amend REQUIREMENTS.md.

## Required owner acceptance

Use a disposable copy and independent backup, with Valheim closed while editing.

1. On native Windows, open a current save and verify displayed body, hair/beard
   identifiers/names and colors. Inspect unknown values without changing them.
2. Search styles with keyboard and pointer. Apply/revert each hair/beard change.
   Change body model; verify incompatible beard proposals fail and only an
   explicit BeardNone selection resolves model1. Check no silent style resets.
3. Use RGB entry and the visual picker for hair and skin. Cancel/revert, test
   invalid input, and inspect current/proposed swatches and numeric preview.
4. Apply a grouped change, mix it with inventory and skill edits, then Undo/Redo
   through the sequence. Check drafts, Review Changes and exported-state markers.
5. Save As a separate disposable file, reopen in ULF, load it in Valheim 1.0.21,
   inspect actual appearance and equipment/skills, save in-game and reopen in ULF.
   Check unrelated progression/metadata and confirm the original stayed intact.
6. Check ordinary and high-DPI layouts, keyboard focus, scrolling and screen
   reader labels. Repeat the supported offline workflow natively on Linux.
7. Record Windows, Linux and game outcomes separately. Prior Alpha 0.4 acceptance
   does not establish Alpha 0.5 appearance compatibility.

**READY FOR OWNER TESTING** within the documented conservative scope. No final
in-game compatibility, release approval, merge or tag is claimed.
