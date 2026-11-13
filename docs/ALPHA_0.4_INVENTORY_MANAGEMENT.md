# Alpha 0.4 inventory management

Development branch: `feature/alpha-0.4-inventory-management`, based on approved
Alpha 0.3.1 `afd9bd8`. Owner instruction schedules advanced inventory work for
this milestone; REQUIREMENTS.md remains unchanged. This is development, not a
release or an in-game compatibility claim.

## Acceptance gates

- FR-019/091: move/swap atomically within verified writable pockets, preserve
  every non-coordinate byte, reject occupied/unknown/ambiguous targets.
- FR-020/043/072: undo restores exact serialized state and record identity;
  redo restores the validated result; bulk edits are one action; invalid edits
  do not enter history; drafts block history travel instead of being committed.
- FR-012–016/018/032/054: duplicate/replace/fill use verified limits, preserve
  unrelated records, show all effects, and reject opaque metadata policies.
- FR-090: preview supported equipment conflicts from pinned game evidence;
  do not guess unsupported hand/slot rules.
- FR-050–053/060, NFR-005: retain full safety regressions and export/reopen
  multi-operation results with unknown and cheat metadata intact.
- FR-017/071/073: visible actions, keyboard alternatives and drag/drop invoke
  the same transactions; review and selection follow undo/redo.

## Architecture and initial policies

`core/inventory_ops.py` implements core movement, swaps, duplicate, replacement
and fill. The desktop session validates commands on private candidates before
publishing. `core/history.py` is a widget-independent history of validated
transactions; command descriptions accompany private before/after mementos so
undo preserves raw encodings, source identities and skill float bits. It does
not decode a serialized snapshot and accidentally rebase source identities.
History is session-local and in memory. Export revision tracking is separate.

Movement changes only x/y. Unknown and ambiguous records cannot move or swap.
Existing out-of-pocket records are preserved, not relocated. Export independently
checks changed coordinates against source/destination bounds and still protects
all other metadata. New APIs do not grant arbitrary metadata mutation.

Duplication requires v110, verified identity/limits, legal quality/quantity and
nonnegative representable durability. It preserves quality, quantity, durability,
crafter ID/name, picked-up state and supported raw optional encodings; the copy
is unequipped with new identity and zero trailing flags. Source stays untouched.
Custom data, nonzero variant/world level or any trailing flag blocks duplication;
flags are never scrubbed to make an item eligible.

Replacement uses an explicit fresh-item policy: verified target, selected
quality/quantity, computed target maximum durability (zero for inapplicable
durability), unequipped, picked up, zero variant/world/trailing flags, empty
crafter/custom data. Opaque/custom/variant/world/flagged sources are rejected.
Crafter attribution loss must be visible in the preview. No metadata is assumed
transferable across prefabs. Fill Stack never reduces a preserved oversized stack.

Undo/redo is blocked while any form drafts exist. Invalid commands leave both
history directions intact; divergent accepted commands clear redo. Dependent
organization changes use Undo or Discard All; targeted discard fails explicitly
instead of replaying a partial swap/replacement. Existing simple discard remains.

## Validation progress

Baseline: 101 tests passed. Core/history milestone: **113 tests passed**, no
failures/skips. New synthetic tests cover all supported transaction history,
move/swap field preservation, invalid coordinates, unknowns, full inventory,
copy policy, replacement limits/maxima, divergent edits, drafts, long sequences,
late failures, source protection and export preservation. UI integration and
equipment validation follow in subsequent commits. Linux and in-game Alpha 0.4
acceptance have not been performed.
