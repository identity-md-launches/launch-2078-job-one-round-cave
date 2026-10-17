#!/usr/bin/env python3
"""Rebuild the single-file gallery and goals from explicit workspace records."""
from pathlib import Path
import html
import json


def main():
    root = Path('dist')
    goals = [{'line': n, 'goal': Path(f'line-{n}/GOAL.md').read_text().strip()} for n in range(1, 5)]
    (root/'goals.json').write_text(json.dumps(goals, indent=2)+'\n')
    groups = []
    for folder in ['line-1','line-2','line-3','line-4','gathering']:
        records = []
        for path in sorted((root/folder).glob('[0-9][0-9].json'), reverse=True):
            record = json.loads(path.read_text())
            records.append({'number':int(path.stem), 'path':path.relative_to(root).as_posix(), **record})
        groups.append({'name':folder.replace('-', ' ').title(), 'records':records})
    data = json.dumps(groups,separators=(',',':')).replace('<','\\u003c')
    goal_html = ''.join(f'<li><b>Line {g["line"]}:</b> {html.escape(g["goal"])}</li>' for g in goals)
    page = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Crystal — Pepeolithic</title><style>
:root{color-scheme:dark}body{margin:0;background:#20170f;color:#f1dfbf;font:17px/1.55 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:28px}h1,h2{color:#edb267}a{color:#edb267}nav{display:flex;gap:18px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:22px}article{padding:14px;background:#302319;border-radius:8px}img{width:100%;aspect-ratio:1;object-fit:cover;border-radius:4px}h3{margin:8px 0}p{margin:8px 0}.pending{opacity:.8}small{color:#c1ad8e}button{font:inherit;color:inherit;background:#4c3420;padding:6px 12px;border:1px solid #b08a57;border-radius:4px}section{margin:36px 0}[hidden]{display:none!important}
</style><main><h1>Crystal</h1><p>Four useful capabilities, one gathering. Every record is listed by wall, newest number first. Unpainted slots show the bare cave.</p>
<nav><a href="#line1">Line 1</a><a href="#line2">Line 2</a><a href="#line3">Line 3</a><a href="#line4">Line 4</a><a href="#gathering">Gathering</a><a href="goals.json">Goals JSON</a></nav>
<ul>GOALS</ul><p><button id="toggle" aria-pressed="false">Show unpainted slots</button></p><div id="walls"></div><noscript>This gallery needs JavaScript to render its embedded records. Numbered JSON records and JPEG previews are available beside this page.</noscript>
<p><small>Images use their content-addressed artifact URLs. Local 512-pixel previews are used if an uploaded image cannot load. No external scripts, fonts or styles are needed.</small></p></main>
<script id="records" type="application/json">DATA</script><script>
const groups=JSON.parse(document.getElementById('records').textContent),host=document.getElementById('walls');
for(const [i,group] of groups.entries()){
 const section=document.createElement('section');section.id=i<4?'line'+(i+1):'gathering';
 const title=document.createElement('h2');title.textContent=group.name;section.append(title);
 const grid=document.createElement('div');grid.className='grid';section.append(grid);
 for(const r of group.records){
  const pending=r.name==='Not painted yet',card=document.createElement('article');
  if(pending){card.className='pending';card.hidden=true;}
  const img=document.createElement('img');img.loading='lazy';img.src=r.image;img.alt=r.name;
  if(!pending)img.onerror=()=>{img.onerror=null;img.src=r.path.replace(/\.json$/,'.jpg');};
  const h=document.createElement('h3');h.textContent=String(r.number).padStart(2,'0')+' · '+r.name;
  const desc=document.createElement('p');desc.textContent=(r.attributes.find(a=>a.trait_type==='Meaning')||{}).value||'Reserved for a future Pepe.';
  const link=document.createElement('a');link.href=r.path;link.textContent='Record JSON';
  card.append(img,h,desc,link);grid.append(card);
 }
 host.append(section);
}
document.getElementById('toggle').onclick=function(){const show=this.getAttribute('aria-pressed')!=='true';this.setAttribute('aria-pressed',String(show));this.textContent=show?'Hide unpainted slots':'Show unpainted slots';document.querySelectorAll('.pending').forEach(c=>c.hidden=!show);};
</script></html>'''.replace('GOALS',goal_html).replace('DATA',data)
    raw=page.encode()
    if len(raw)>100000: raise ValueError('gallery exceeds file limit')
    (root/'index.html').write_bytes(raw)
    print(f'Gallery: {sum(len(g["records"]) for g in groups)} records, {len(raw)} bytes')


if __name__=='__main__': main()
