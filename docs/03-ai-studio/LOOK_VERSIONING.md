# Look Specification & Immutable Version DAG — ENG-07 / ENG-12

## Principle

A `LookSpec` is structured style intent (geometry, region, palette, care intensity, constraints), not image bytes. One specification may yield multiple previews and QA reports. A `LookVersion` freezes selected attributes, parent IDs, exact assets, prompts/model versions and edits.

## Example

```text
Original V0
├── Hair Color V1 (Warm Brunette)
│   ├── V1.1 (Cooler Tone)
│   └── V1.2 (Softer Highlights)
└── V2 (Dark Brown)
    └── V2.1 (Lower Contrast)
```

## Operations

- `CreateLookSpec`, `ReviseLookSpec`, `GeneratePreview`, `CompareVersions`, `LockSelectedLook`, `RevertToVersion`, `InvalidateDependentPlan`.
- Each revision records `parent_version_id`, `changed_attribute_paths`, `immutable_constraints`, `mask_id`, `generated_asset_id`, `qa_report_id`, `actor_id`, `created_at`.
- Undo/Redo moves the active pointer or creates explicit new revision metadata, never destroys historical versions.
- A newer out-of-order AI job cannot overwrite a newer selected look.
- Changing exact source image, selected version, critical evidence or approved SOP requires plan recheck and invalidation of earlier professional validation.

## Testing

Simulate ten consecutive changes, branching revisions, repeated requests, undo/redo, cancelled generation, model provider retry, stale write, incorrect parent, hard-lock edit and multi-region rollback. Preserve all accepted state while applying only requested deltas.
