"""Parallel-ish cited web research using DuckDuckGo and page extraction."""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from acli.tools.web_tools import web_search, fetch_web_page

def research_web(query: str, settings, max_sources: int = 5) -> str:
    raw=web_search(query,max_sources,settings=settings)
    urls=re.findall(r'https?://\S+',raw)[:max_sources]
    results=[]
    with ThreadPoolExecutor(max_workers=min(5,len(urls) or 1)) as pool:
        futures={pool.submit(fetch_web_page,u,5000,settings):u for u in urls}
        for future in as_completed(futures):
            url=futures[future]
            try: text=future.result(); results.append((url,text[:5000]))
            except Exception as exc: results.append((url,'ERROR: '+str(exc)))
    body=['RESEARCH QUERY: '+query,'SEARCH RESULTS:\n'+raw]
    for i,(url,text) in enumerate(results,1): body.append('SOURCE ['+str(i)+'] '+url+'\n'+text)
    return '\n\n'.join(body)[:30000]
