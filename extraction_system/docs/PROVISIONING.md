# Provisioning the current dual runtime

Use uv sync --locked for the main runtime. The isolated Python 3.11.16 HunFlair2 environment and pinned artifacts are recorded in provisioning/baseline.json and provisioning/hunflair2-installed.json. Supply OPENAI_API_KEY externally; research environments and caches are not delivery dependencies. Run fixed-stage tests before live extraction.
