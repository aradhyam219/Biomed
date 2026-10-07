import importlib.util,json
from pathlib import Path
p=Path(__file__).with_name('smoke.py')
s=importlib.util.spec_from_file_location('smoke',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
packet=json.loads(m.PACKET.read_text(encoding='utf-8'));f=m.FrozenEntities(packet)
assert len(f.entities)==41 and len(m.assemble_document_entities(f.entities,f.source).document_entities)==20
assert all(f.source[e.start:e.end]==e.text for e in f.entities)
m.run()
