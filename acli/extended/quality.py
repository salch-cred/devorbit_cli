"""Developer quality workflow wrappers."""
from pathlib import Path
from acli.extended.shell import run_command

def quality_check(workspace: str, preset: str = 'auto') -> str:
    root=Path(workspace); commands=[]
    if preset=='auto':
        if (root/'pyproject.toml').exists() or list(root.glob('*.py')): commands=['python -m compileall -q .','python -m pytest -q']
        elif (root/'package.json').exists(): commands=['npm test -- --runInBand','npm run lint --if-present','npm run build --if-present']
        elif (root/'go.mod').exists(): commands=['go test ./...','go vet ./...']
        elif (root/'Cargo.toml').exists(): commands=['cargo test','cargo clippy -- -D warnings']
        else: commands=['git diff --check']
    else: commands=[preset]
    outputs=[]
    for cmd in commands:
        try: outputs.append('$ '+cmd+'\n'+run_command(workspace,cmd,300))
        except Exception as exc: outputs.append('$ '+cmd+'\nERROR: '+str(exc))
    return '\n\n'.join(outputs)

def generate_changelog(workspace: str, limit: int = 50) -> str:
    return run_command(workspace,"git log -"+str(max(1,min(limit,200)))+" --pretty=format:'- %s (%h)'",60)
