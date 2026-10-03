import re,html,subprocess,sys,os
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
import datetime
CACHE=os.environ.get("BRIEF_CACHE") or "/Users/ed/ed-news-briefing/cache/"+datetime.date.today().isoformat()
def clean(s):
    s=s.replace('\\u0026','&').replace('\\"','"').replace('\\\\','\\').replace('\\n','\n')
    s=re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1),16)), s)
    return html.unescape(re.sub('<[^>]+>','',s)).strip()
def paras(t):
    out=re.findall(r'\\"type\\":\\"paragraph\\".{0,80}?\\"text\\":\\"(.*?)\\"(?=,\\"|\})', t, re.S)
    if len(out)<3: out=re.findall(r'"type":"paragraph".{0,80}?"text":"(.*?)"(?=,"|\})', t, re.S)
    if len(out)<3: out=re.findall(r'<p[^>]*>(.*?)</p>', t, re.S)
    seen=[];res=[]
    for p in out:
        c=clean(p)
        if len(c)>30 and c not in seen and 'document.' not in c and 'function' not in c:
            seen.append(c);res.append(c)
    return res
for line in sys.stdin.read().strip().split('\n'):
    if not line.strip() or line.startswith('#'): continue
    slug,meta,url=line.split('||')
    t=subprocess.run(["curl","-sL","-A",UA,url.strip()],capture_output=True,text=True,errors='replace').stdout
    ps=paras(t)
    path=os.path.join(CACHE,slug.strip()+".txt")
    with open(path,'w') as f:
        f.write("URL: "+url.strip()+"\n"+meta.strip()+"\n\n"+"\n\n".join(ps[:45]))
    print(f"{slug.strip():<52} {len(ps):>3} paras {len(open(path).read()):>6}b")
