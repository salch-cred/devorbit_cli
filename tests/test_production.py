import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from acli.production.observability import AuditLog, redact
from acli.production.recovery import RunState
from acli.production.patch_engine import preview_patch, apply_patch
from acli.production.sandbox import sandbox_status, run_isolated
from acli.production.native_sandbox import validate_command
from acli.production.diagnostics import language_diagnostics

class ProductionTests(unittest.TestCase):
    def test_redaction(self):
        self.assertNotIn('nvapi-secret', redact('token=abc nvapi-secret'))
    def test_recovery_atomic(self):
        with tempfile.TemporaryDirectory() as d:
            state=RunState(d); state.save({'recoverable_run':True,'stage':'test'})
            self.assertEqual(state.load()['stage'],'test'); state.clear(); self.assertIsNone(state.load())
    def test_patch_preview_and_apply(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(['git','init','-q'],cwd=d,check=True)
            subprocess.run(['git','config','user.email','test@example.com'],cwd=d,check=True)
            subprocess.run(['git','config','user.name','Test'],cwd=d,check=True)
            Path(d,'a.txt').write_text('old\n',encoding='utf-8')
            subprocess.run(['git','add','.'],cwd=d,check=True); subprocess.run(['git','commit','-qm','init'],cwd=d,check=True)
            diff='diff --git a/a.txt b/a.txt\nindex 3367afd..3e75765 100644\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n'
            self.assertIn('DIFF:',preview_patch(d,diff)); self.assertIn('Patch applied',apply_patch(d,diff)); self.assertEqual(Path(d,'a.txt').read_text(),'new\n')
    def test_audit_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            audit=AuditLog(d); audit.write('tool_succeeded',{'token':'secret'})
            self.assertEqual(audit.metrics()['events'],1)
    def test_restricted_native_runner(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'check.py').write_text('print(123)\n')
            args=validate_command(d, 'python check.py')
            self.assertEqual(Path(args[0]).name, 'python')
            result=run_isolated(d, 'python check.py', timeout=20)
            self.assertIn('123',result)
            with self.assertRaises(PermissionError): validate_command(d, 'python x.py | more')
            with self.assertRaises(PermissionError): validate_command(d, 'git reset --hard')
            with self.assertRaises(PermissionError): validate_command(d, 'python -c "print(123)"')
    def test_diagnostics_and_sandbox_status(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'x.py').write_text('x=1\n')
            self.assertIn('compileall',language_diagnostics(d))
        self.assertIn('docker_installed',sandbox_status())

if __name__=='__main__': unittest.main()
