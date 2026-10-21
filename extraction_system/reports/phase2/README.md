# Phase 2 runtime compatibility

Status: **FINAL INSTALLED SMOKE PENDING**. The user explicitly approved promotion
of the verified Linux/NVIDIA configuration. No scientific behavior is changed.

The supported CUDA descriptor is
`linux-cuda-create-deadline-profile.json`, identity
`ees-9c3d817bf294bab6b6335a362e5aed289f9d004401bdb67f915746a6dafc5ed8`.
The demonstrated host is Ubuntu 22.04 / AWS g4dn / Tesla T4. The descriptor binds
Linux, Python 3.11.16, PyTorch distribution 2.14.0 / module 2.14.0+cu130,
CUDA 13.0, the pinned official HunFlair2 artifact and the exact recorded isolated
inventory with two NVIDIA additions. This establishes configuration-bounded
compatibility, not universal GPU/CUDA equivalence. Existing runtime and provider
preflight, post-NER and postflight validation remains required.

The original CPU descriptor remains byte-identical with identity
`ees-cfeec6ccd400b9f44abbef35551944aa074ee3d79d3e5ec18dd7d7551c76e0de`.
Current Luna/CPU remains
`ees-35a70f202f4e6659fd1578a8df14243243bbabe011b3379ee154704dacf3d76f`.
Both CPU behavior and the default CPU device are preserved.

Retained evidence:

- [manifest.json](manifest.json): seven cases and designated `sfpq-full` smoke.
- [cpu-revalidation.json](cpu-revalidation.json): verified original CPU identity.
- [downstream-drift.json](downstream-drift.json): seven-case NUMERIC_ONLY result;
  downstream impact confined to score literals. No scientific quality claim.
- [luna-freeze.json](luna-freeze.json): Luna/max/requested Fast/background freeze.
- [luna-cuda-retry-smoke.json](luna-cuda-retry-smoke.json): real CUDA NER and RE;
  historical whole-batch role-repair blocker, superseded by the role repair.
- [sfpq-role-reliability.json](sfpq-role-reliability.json): 57/57 valid roles,
  zero repairs; exact evidence, contextual Species/Organism, deterministic order,
  unchanged 98-node/73-edge topology and source-aware Graph Contract v1 passed.

The final authorized gate builds a clean wheel and installs it outside the
checkout, provisions/attaches the recorded isolated runtime and pinned downloads,
and runs the public v1 path once on `sfpq-full`. Existing bounded repairs and
conservative submission accounting apply. Historical provider attempts remain
consumed. No quality investigation, comparison, repeat or next phase is authorized.
