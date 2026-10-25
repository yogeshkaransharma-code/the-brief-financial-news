"""One authoritative offline validation entry point; no model or source requests."""
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
checks=[['ai_newsroom.py','--self-test'],['ai_cost_guard.py'],['source_retrieval.py'],['first_party_sources.py'],['source_trace.py'],['same_day_policy.py'],['fresh_sources.py'],['newsroom_v2.py','--self-test'],['financial_consistency.py'],['editorial_gate.py','--self-test'],['test_publishing.py'],['test_editorial_benchmark.py'],['test_autonomous.py'],['test_rebuild.py'],['test_launch_canary.py'],['verify_approved_articles.py']]
checks.insert(-1,['test_launch_edition.py'])
checks.insert(-1,['numeric_evidence.py'])
checks.insert(-1,['market_coverage.py'])

checks.insert(-1,['test_editorial_selection.py'])
checks.insert(-1,['test_editorial_omission.py'])
checks.insert(-1,['test_launch_mandate.py'])
checks.insert(-1,['publication_scope.py'])
checks.insert(-1,['test_regulatory_sources.py'])
checks.insert(-1,['test_feed_relevance.py'])
for c in checks:
    subprocess.run([sys.executable,str(root/'scripts'/c[0])]+c[1:],check=True,cwd=root)
print('OFFLINE_CHECKS_PASSED:',len(checks))

