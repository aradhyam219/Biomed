# CONTRACT 11T — GPT-5.6 MAX CONTROL

## BASELINE

HEAD: fd66f9bb6d1a5c41ae147abfb5a7994c5bddae6c
Production parity: clean. Production diff: empty.

## SCHEMA

Semantic SHA: `023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945`
Transport SHA: `b0506680756b7ad8332d976a419cdee57a81e1051dd115f291f65d77bd656510`

## SYNTHETIC CONTROL

```json
{
  "result": "success",
  "response_ids": [
    "resp_021e6dcf29c8d82c006ac16e79ca9087d1a8cad1bcc880edf8"
  ],
  "create_latency_seconds": 1.547,
  "initial_status": "queued",
  "terminal_status": "completed",
  "background_elapsed_seconds": 3.609,
  "total_wall_seconds": 5.266,
  "polls": 1,
  "poll_errors": 0,
  "usage": [
    {
      "input_tokens": 1029,
      "input_tokens_details": {
        "cache_write_tokens": 1026,
        "cached_tokens": 0
      },
      "output_tokens": 149,
      "output_tokens_details": {
        "reasoning_tokens": 76
      },
      "total_tokens": 1178
    }
  ],
  "repairs": 0,
  "validated_relations": 1,
  "unique_evidence_spans": 1,
  "structured_output_received": true,
  "cancellation_result": null,
  "error": null
}
```

## REAL PASSAGE AND SIDE-BY-SIDE

```json
{
  "gpt-5.6-luna max": {
    "result": "success",
    "response_ids": [
      "resp_00cfbe85255146fa006ac16e7e7fac87d1b514a902571f69d5"
    ],
    "create_latency_seconds": 0.86,
    "initial_status": "queued",
    "terminal_status": "completed",
    "background_elapsed_seconds": 479.562,
    "total_wall_seconds": 480.531,
    "polls": 137,
    "poll_errors": 0,
    "usage": [
      {
        "input_tokens": 5223,
        "input_tokens_details": {
          "cache_write_tokens": 5220,
          "cached_tokens": 0
        },
        "output_tokens": 56702,
        "output_tokens_details": {
          "reasoning_tokens": 54383
        },
        "total_tokens": 61925
      }
    ],
    "repairs": 0,
    "validated_relations": 17,
    "unique_evidence_spans": 10,
    "structured_output_received": true,
    "cancellation_result": null,
    "error": null
  },
  "gpt-6-luna max": {
    "result": "background_timeout_cancelled",
    "response_ids": [
      "resp_061ba37b3ed116e2006ac1665dc4f087d18406d79290020103"
    ],
    "create_latency_seconds": 0.906,
    "initial_status": "queued",
    "terminal_status": "cancelled",
    "background_elapsed_seconds": 481.0,
    "total_wall_seconds": 482.0,
    "polls": 138,
    "poll_errors": 0,
    "usage": [
      null
    ],
    "repairs": 0,
    "validated_relations": 0,
    "unique_evidence_spans": 0,
    "structured_output_received": false,
    "cancellation_result": {
      "id": "resp_061ba37b3ed116e2006ac1665dc4f087d18406d79290020103",
      "status": "cancelled"
    },
    "error": null
  }
}
```

## INTEGRITY

Production code unchanged: yes
Production default unchanged: gpt-5.6-luna
Existing 11S / 11S-R reports preserved: yes (file hashes checked)
Nothing committed or pushed: yes

This is a descriptive feasibility control; no scientific-quality ranking is assigned.

The exact frozen workload completed and validated on GPT-5.6 Luna max within 480 seconds from background-ID receipt. The recorded GPT-6 Luna max run did not complete within that deadline. No scientific-quality ranking. Total phase wall time includes initial creation and validation; the 480-second limit starts at receipt of the background ID.
