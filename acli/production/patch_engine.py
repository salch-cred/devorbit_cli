"""Auditable unified-diff preview/apply with automatic checkpoint and rollback."""
import subprocess
from pathlib import Path
from acli.extended.checkpoints import create_checkpoint, restore_checkpoint

def _patch_path(workspace,diff_text):
    path=Path(workspace)/".devorbit-pending.patch"; path.write_text(diff_text,encoding="utf-8"); return path

def preview_patch(workspace: str, diff_text: str) -> str:
    if not diff_text.strip().startswith(("diff --git","--- ")): raise ValueError("Expected a unified diff")
    patch=_patch_path(workspace,diff_text)
    result=subprocess.run(["git","apply","--check","--stat",str(patch)],cwd=workspace,capture_output=True,text=True)
    return "check_exit="+str(result.returncode)+"\n"+(result.stdout+result.stderr)[-12000:]+"\n\nDIFF:\n"+diff_text[:20000]

def apply_patch(workspace: str, diff_text: str, run_check: str = "") -> str:
    checkpoint=create_checkpoint(workspace,"before-patch").split()[-1]
    patch=_patch_path(workspace,diff_text)
    check=subprocess.run(["git","apply","--check",str(patch)],cwd=workspace,capture_output=True,text=True)
    if check.returncode: raise RuntimeError("Patch check failed:\n"+check.stderr)
    applied=subprocess.run(["git","apply","--whitespace=fix",str(patch)],cwd=workspace,capture_output=True,text=True)
    if applied.returncode: raise RuntimeError("Patch application failed:\n"+applied.stderr)
    if run_check:
        test=subprocess.run(run_check,cwd=workspace,shell=True,capture_output=True,text=True,timeout=600)
        if test.returncode:
            restore_checkpoint(workspace,checkpoint)
            return "Patch rolled back because validation failed.\n"+(test.stdout+test.stderr)[-12000:]
    return "Patch applied. Rollback checkpoint: "+checkpoint
