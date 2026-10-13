"""Embed a clean source revision in wheels; editable builds use source checks."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if self.target_name != 'wheel' or version == 'editable':
            return
        root = Path(self.root)
        status = subprocess.check_output(['git','status','--porcelain','--untracked-files=all','--','.'], cwd=root, text=True)
        if status.strip():
            raise RuntimeError('Release wheel requires a clean committed extraction_system source tree')
        revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=root, text=True).strip()
        package = root/'src/biomedical_extractor'
        digests = {str(p.relative_to(package)).replace('\\','/'):sha256(p.read_bytes()).hexdigest()
                   for p in package.rglob('*') if p.is_file() and (p.suffix in ('.py','.json','.md')) and '__pycache__' not in p.parts and p.name != 'release.json'}
        self._temporary = tempfile.TemporaryDirectory(prefix='ees-build-')
        identity = Path(self._temporary.name)/'release.json'
        identity.write_text(json.dumps({'version':self.metadata.version,'revision':revision,'source_sha256':digests},sort_keys=True),encoding='utf-8')
        build_data['force_include'][str(identity)] = 'biomedical_extractor/contract_resources/release.json'

    def finalize(self, version, build_data, artifact_path):
        if hasattr(self, '_temporary'):
            self._temporary.cleanup()
