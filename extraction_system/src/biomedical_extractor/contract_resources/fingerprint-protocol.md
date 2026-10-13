# EES-INPUT-V1

Use strict UTF-8 without BOM or normalization. Missing title equals empty title;
null, non-string and unpaired-surrogate input is invalid. Document ID is separate.
source_sha256 = lowercase SHA256(UTF8(text)).
extraction_input_sha256 = lowercase SHA256 of the exact bytes:
ASCII("EES-INPUT-V1") || UINT64_BIG_ENDIAN(byte_length(text)) || UTF8(text)
|| UINT64_BIG_ENDIAN(byte_length(title)) || UTF8(title).
Prefix is exactly 12 bytes without a delimiter; lengths must fit UINT64.
The companion fingerprint-examples.json contains the three normative vectors.
Mention offsets count Unicode code points, start inclusive and end exclusive;
JavaScript/Java/.NET UTF-16 indexing must be translated.
