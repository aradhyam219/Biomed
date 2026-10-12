"""Acquire and verify the accepted model, then provision its tokenizer cache.

Run inside the isolated environment from extraction_system. Only external model
artifacts are downloaded; no research environment or cache is read or copied.
"""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/hunflair2"
manifest = json.loads((ROOT / "provisioning/baseline.json").read_text(encoding="utf-8"))
identity = manifest["hunflair2"]
os.environ["FLAIR_CACHE_ROOT"] = str(CACHE / "flair")
os.environ["HF_HOME"] = str(CACHE / "huggingface")
os.environ["TRANSFORMERS_CACHE"] = str(CACHE / "huggingface")
os.environ["FLAIR_DEVICE"] = "cpu"

import requests

model_cache = CACHE / "flair/models/hunflair2-ner"
artifact = model_cache / "models--hunflair--hunflair2-ner/snapshots" / identity["model_revision"] / "pytorch_model.bin"
artifact.parent.mkdir(parents=True, exist_ok=True)
if not artifact.is_file():
    url = f"https://huggingface.co/{identity['model_identifier']}/resolve/{identity['model_revision']}/pytorch_model.bin"
    partial = artifact.with_suffix(".download")
    with requests.get(url, stream=True, timeout=(15, 60)) as response:
        response.raise_for_status()
        with partial.open("wb") as stream:
            for chunk in response.iter_content(1024 * 1024):
                stream.write(chunk)
    downloaded_digest = hashlib.sha256()
    with partial.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            downloaded_digest.update(chunk)
    if downloaded_digest.hexdigest() != identity["model_artifact_sha256"]:
        raise RuntimeError("Downloaded HunFlair2 artifact does not match accepted baseline")
    partial.replace(artifact)
digest = hashlib.sha256()
with artifact.open("rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != identity["model_artifact_sha256"]:
    raise RuntimeError("Downloaded HunFlair2 artifact does not match accepted baseline")
# The existing runner discovers this exact immutable snapshot through refs/main.
reference = model_cache / "models--hunflair--hunflair2-ner/refs/main"
reference.parent.mkdir(parents=True, exist_ok=True)
reference.write_text(identity["model_revision"], encoding="utf-8")
from flair.nn import Classifier
from flair.splitter import SciSpacySentenceSplitter
Classifier.load(str(artifact))
SciSpacySentenceSplitter()
print("Pinned HunFlair2 artifact and tokenizer/splitter provisioned independently.")
