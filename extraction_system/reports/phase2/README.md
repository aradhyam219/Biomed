# Phase 2 runtime compatibility

Status: **PHASE 2 COMPLETE** after the explicitly authorized one-target closure
repair described below. See [closure.json](closure.json). The user approved promotion
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

The final authorized gate built a clean wheel from `029be54988d46ce99d13ddf36912495320dbfbff`
and installed it outside the checkout. Fresh external main and isolated runtimes,
pinned model provisioning, installed resources/provenance and 60 current focused
tests passed. Checkout/Git access was forbidden during the installed public smoke.

Exactly one public `sfpq-full` invocation performed real Tesla T4 CUDA NER (460
mentions), accepted 105 relations without repairs and naturally requested 54 roles.
The initial role output retained 51 valid records. One targeted repair requested
only `doc_e_033`, `doc_e_072`, `doc_e_073`; 53 roles were then valid, but
`doc_e_033` still failed verbatim evidence validation. The historical shared repair
cap reached **4/4**, so its guard prevented a second role repair before submission.
No grounding rule or budget was weakened. Three new submissions completed:
initial RE, initial roles, one role repair. All requested Luna/max/Fast/background;
Fast was observed as `priority`.

Before the closure exception, final v1 export was not reached. A deterministic
replay of captured installed NER/RE outputs validates the pre-role graph
(98 nodes / 99 edges) against source.
That replay is evidence preservation, not another smoke or final v1 completion.
That was the retained blocked result, before the explicit closure exception.

The user then authorized exactly one additional repair for `doc_e_033` only,
separately from the exhausted **4/4** shared allowance. That single response
validated, including exact/verbatim evidence. The original 53 accepted roles were
preserved exactly and the completed 54/54 set was merged in original target order.
No NER, assembly, RE, initial roles or previous repair was rerun. Attachment kept
98 nodes / 99 edges unchanged, and final source-aware Graph Contract v1 passed
using the same installed wheel. Requested Fast was observed as `priority`.

Accounting now records 12 Phase 2 ledger submissions plus four separately tracked
role-reliability attempts: 16 relevant attempts total. Historical shared repairs
remain 4/4, with one separately authorized/consumed closure-exception repair.
The general policy and CPU/CUDA profiles are unchanged. Phase 2 is complete;
no further execution or next phase is authorized.
