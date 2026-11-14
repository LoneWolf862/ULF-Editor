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

Core milestone: 136 tests pass on Windows, zero failures/skips (126 baseline plus
10 new appearance tests with field/version/input subcases). UI, history integration
and final acceptance documentation follow. Native Linux and Alpha 0.5 in-game
acceptance have not been performed.
