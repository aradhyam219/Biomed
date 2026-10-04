# Contract 11P — Single Chunk Transport Retry

- Status: `timeout`
- Paper/chunk: `PMCID:PMC10770459` / `chunk_001` (`0:9153`, 9,153 characters)
- Execution baseline: `extraction_system_v2@7f388368a8bd06f35f60eda37eb2ccdce711eed8`
- Source 11P baseline: `extraction_system_v2@1f12923ce54ab6718a00b8d8e8126536285dc6a8`
- Model: `gpt-6-luna`; OpenAI Responses API; reasoning `max`; max output tokens `128000`.
- Contract 10 prompt/schema/parser/validator; structural repair budget `2`; provider retries `0`.
- Frozen source, entity packet, entity input, system prompt, structured schema, and chunk prompt checksums all matched the original 11P artifacts.

## Result

- Provider responses received: 0.
- Provider attempts: 1; repair attempts: 0.
- Elapsed time: 600.031 seconds; the external watchdog was 600 seconds.
- Input tokens: unavailable; output tokens: unavailable.
- Validated relations: 0; unique evidence spans: 0.
- Exact final error: `Worker exceeded the 600-second wall-clock ceiling and was terminated; no manual rerun was made.`
- The only scheduled job was `chunk_001`; execution stopped after the watchdog. No further retries or chunks were run.
- Scientific quality was not assessed.

## Verified input checksums

- Full paper source SHA-256: `5b58cb81f2add5f1295313b08c07e575bffffa8c1a871f32436d278735b209a4`
- Chunk source SHA-256: `2a3ad71cb9f149cceda87dc8bc9af582a3982e98d5bf7f7b2dd21c161597d2fd`
- Frozen entity packet file SHA-256: `938cdc238e47c46ae7773129e3f0196027f5f676f74864f1fe72b845a79ca8c0`
- Chunk absolute entity packet SHA-256: `9d4e6bf6629747bca0d6aaf3042d59de1d43b30b1793cfa7132fc6e3b642259b`
- Chunk provider entity packet SHA-256: `5aa94f7600639835755a899f2b4513cbd735f281b7111557c84c08457e396f6b`
- Contract 10 prompt SHA-256: `13f38a6e94db74b534eb0df0b139287ace2e714fc908276ce4c3572f9b25836f`
- Structured schema SHA-256: `023435da3fa18abb77987313626636eff7bedda28739603db54a2f2c8137c945`
- Chunk prompt SHA-256: `7689a3d8df557f93560b712dc758cbe51351d800c5e02c70201807ca68e2b3f1`

## Artifacts

- `preflight.json`: original configuration plus retry execution and checksum verification.
- `chunk_manifest.json`: one selected frozen chunk only.
- `chunks/chunk_001.json`: final timeout record and frozen entity packet.
- `chunks/chunk_001.progress.json`: provider-attempt progress captured when the watchdog terminated the worker.
- `summary.json`: machine-readable retry status and requested metrics.
