"""Repository map and SQLite FTS project index."""
import sqlite3
from pathlib import Path

TEXT_EXT={'.py','.js','.ts','.tsx','.jsx','.go','.rs','.java','.kt','.c','.cpp','.h','.md','.txt','.json','.yaml','.yml','.toml','.html','.css','.sql'}
SKIP={'.git','node_modules','.venv','__pycache__','.devorbit-checkpoints'}

def repo_map(workspace: str, max_files: int = 1000) -> str:
    root=Path(workspace); lines=[]
    for path in root.rglob('*'):
        if path.is_file() and not any(p in SKIP for p in path.parts):
            lines.append(str(path.relative_to(root)))
            if len(lines)>=max_files: lines.append('...truncated'); break
    return '\n'.join(lines) if lines else '(empty repository)'

def build_index(workspace: str) -> str:
    root=Path(workspace); db=root/'.devorbit-index.sqlite'; con=sqlite3.connect(db)
    con.execute('CREATE VIRTUAL TABLE IF NOT EXISTS files USING fts5(path, content)'); con.execute('DELETE FROM files')
    count=0
    for path in root.rglob('*'):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXT or any(p in SKIP for p in path.parts): continue
        if path.stat().st_size>1_000_000: continue
        con.execute('INSERT INTO files(path,content) VALUES (?,?)',(str(path.relative_to(root)),path.read_text(encoding='utf-8',errors='ignore'))); count+=1
    con.commit(); con.close(); return 'Indexed '+str(count)+' files at '+str(db)

def search_index(workspace: str, query: str, limit: int = 10) -> str:
    db=Path(workspace)/'.devorbit-index.sqlite'
    if not db.exists(): return build_index(workspace)+'\nRun the search again.'
    con=sqlite3.connect(db)
    try: rows=con.execute('SELECT path, snippet(files,1,"[","]","...",20) FROM files WHERE files MATCH ? LIMIT ?',(query,max(1,min(limit,50)))).fetchall()
    finally: con.close()
    return '\n\n'.join(p+'\n'+s for p,s in rows) if rows else 'No indexed matches.'
