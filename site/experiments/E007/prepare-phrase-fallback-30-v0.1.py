#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, os, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; sys.path.insert(0,str(ROOT/'desktop'))
from pocket_i_app.bridge import MemoryRuntime, _question_centered_excerpt

def load(name, alias):
 s=importlib.util.spec_from_file_location(alias,HERE/name); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
BASE=load('anchor-search-ab-v0.1.py','anchor30'); PHRASE=load('phrase-search-ab-v0.1.py','phrase30')

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--data-dir',type=Path,default=BASE._default_data_dir()); a=ap.parse_args()
 protocol=json.loads((HERE/'phrase-fallback-30-protocol-v0.1.json').read_text()); rows=[]
 rt=MemoryRuntime(data_dir=a.data_dir,on_progress=lambda x: print(f"{x.get('phase')} {x.get('completed','')}/{x.get('total','')}",file=sys.stderr,flush=True)); rt.connect(); idx,lib=rt.index,rt.library
 by={c.conversation_id:c for c in lib.conversations}
 flat=[(group,q,e) for group,items in protocol['groups'].items() for q,e in items]
 for n,(group,q,expected) in enumerate(flat,1):
  print(f'Preparing {n}/30…',flush=True)
  base_ids,anchors,anchor_scores=BASE.candidate_route(idx,q,top_k=5)
  full_ids,_a,phrases,combined=PHRASE.phrase_route(idx,q,top_k=len(idx._conversation_ids))
  fallback=next((x for x in full_ids if x not in base_ids),None)
  chosen=list(BASE.candidate_hits(idx,q,base_ids,anchor_scores,per_conversation=1))
  if fallback: chosen+=list(BASE.candidate_hits(idx,q,(fallback,),combined,per_conversation=1))
  sources=[]
  for i,(cid,pos) in enumerate(chosen,1):
   msg=by[cid].messages[pos]; sources.append({'source_id':f'S{i}','text':_question_centered_excerpt(msg.text,q),'conversation':cid[:12],'position':pos+1,'fallback':cid==fallback})
  rows.append({'number':n,'group':group,'question':q,'expected':expected,'phrases':list(phrases),'sources':sources})
 a.output.parent.mkdir(parents=True,exist_ok=True); fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f: json.dump({'schema_version':'e007-fallback30-private-input-v0.1','rows':rows},f,ensure_ascii=False,indent=2)
 print(f'PRIVATE_INPUT: {a.output}')
if __name__=='__main__': main()
