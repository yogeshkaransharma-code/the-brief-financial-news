"""One authoritative offline validation entry point; no model or source requests."""
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks=[['ai_newsroom.py','--self-test'],['ai_cost_guard.py'],['source_retrieval.py'],['first_party_sources.py'],['source_trace.py'],['same_day_policy.py'],['fresh_sources.py'],['newsroom_v2.py','--self-test'],['financial_consistency.py'],['editorial_gate.py','--self-test'],['test_publishing.py'],['test_editorial_benchmark.py'],['test_autonomous.py'],['test_rebuild.py'],['verify_approved_articles.py']]
for c in checks:
    subprocess.run([sys.executable,str(root/'scripts'/c[0])]+c[1:],check=True,cwd=root)
print('OFFLINE_CHECKS_PASSED:',len(checks))
