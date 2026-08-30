#!/usr/bin/env python3
"""Run Gate 16D.9 Qwen exact-quote claims and DeBERTa grounding checks."""

from __future__ import annotations

import argparse
import html
import json
import time
import urllib.request
from pathlib import Path


CLAIMS_SCHEMA = {
    "type":"object",
    "properties":{"claims":{"type":"array","minItems":1,"maxItems":10,"items":{"type":"object","properties":{"claim":{"type":"string"},"source_id":{"type":"string"},"quote":{"type":"string"}},"required":["claim","source_id","quote"],"additionalProperties":False}}},
    "required":["claims"],
    "additionalProperties":False,
}


def render(messages: list[dict]) -> str:
    return "\n\n".join(f'<message id="{m["id"]}" role="{m["role"]}">\n{html.escape(m["text"])}\n</message>' for m in messages)


def generate(endpoint: str, model: str, question: dict, messages: list[dict]) -> dict:
    coverage="\n".join(f'- {fact["question"]}' for fact in question["facts"])
    prompt=(
        f"ORIGINAL QUESTION:\n{question['text']}\n\nCOVERAGE CHECKLIST:\n{coverage}\n\nSOURCE SHELF:\n{render(messages)}\n\n"
        "Return atomic claims that answer the original question. Write each claim in English for an English NLI checker. "
        "For every claim, cite one source_id and copy one exact, character-for-character quote from that message which supports the claim. "
        "Do not claim anything absent from the shelf. If a checklist part is absent, omit it."
    )
    body={
        "model":model,
        "messages":[{"role":"system","content":"You produce evidence-grounded atomic claims with exact quotes."},{"role":"user","content":"/no_think\n\n"+prompt}],
        "chat_template_kwargs":{"enable_thinking":False},"temperature":0,"max_tokens":1536,
        "response_format":{"type":"json_schema","json_schema":{"name":"grounded_claims","strict":True,"schema":CLAIMS_SCHEMA}},
    }
    req=urllib.request.Request(endpoint.rstrip("/")+"/v1/chat/completions",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    started=time.monotonic()
    with urllib.request.urlopen(req,timeout=1800) as response:
        result=json.load(response)
    message=result["choices"][0]["message"]
    row={"seconds":round(time.monotonic()-started,3),"usage":result.get("usage",{}),"raw_message":message}
    try:
        parsed=json.loads(message.get("content") or "")
        claims=parsed["claims"]
        if not isinstance(claims,list) or not claims:
            raise ValueError("claims missing")
        row.update(receipt="CLAIMS",claims=claims)
    except (KeyError,TypeError,ValueError,json.JSONDecodeError) as error:
        row.update(receipt="ERROR",claims=[],error=str(error))
    return row


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload",type=Path,required=True)
    parser.add_argument("--question-protocol",type=Path,required=True)
    parser.add_argument("--protocol",type=Path,required=True)
    parser.add_argument("--endpoint",default="http://127.0.0.1:22118")
    parser.add_argument("--model",default="qwen3-8b-q4-k-m")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload=json.loads(args.payload.read_text()); questions=json.loads(args.question_protocol.read_text()); protocol=json.loads(args.protocol.read_text())
    conversations={f'{payload["node"]}-C{i:04d}':c for i,c in enumerate(payload["conversations"],1)}
    question_by_id={q["id"]:q for q in questions["questions"]}
    rows=[]
    for condition in protocol["conditions"]:
        question=question_by_id[condition["question_id"]]; conversation=conversations[question["gold_card_id"]]; by_id={m["id"]:m for m in conversation["messages"]}
        messages=[by_id[i] for i in condition["message_ids"]]
        generated=generate(args.endpoint,args.model,question,messages)
        claims=[]
        for index,claim in enumerate(generated["claims"],1):
            source=by_id.get(claim.get("source_id")); quote=claim.get("quote"); exact=bool(source and isinstance(quote,str) and quote in source["text"])
            claims.append({"id":f'C{index:02d}',**claim,"known_source_id":source is not None,"exact_quote":exact,"nli":None})
        row={"id":f'{question["id"]}-{condition["condition"]}',"question_id":question["id"],"condition":condition["condition"],"question":question["text"],"coverage_questions":[f["question"] for f in question["facts"]],"message_ids":condition["message_ids"],"source_messages":{m["id"]:m["text"] for m in messages},**{k:v for k,v in generated.items() if k!="claims"},"claims":claims}
        rows.append(row); print(json.dumps({"id":row["id"],"receipt":row["receipt"],"claims":len(claims),"exact":sum(c["exact_quote"] for c in claims)}),flush=True)

    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    spec=protocol["nli"]
    tokenizer=AutoTokenizer.from_pretrained(spec["repository"],revision=spec["revision"],local_files_only=True)
    nli_model=AutoModelForSequenceClassification.from_pretrained(spec["repository"],revision=spec["revision"],local_files_only=True,dtype=torch.float32).eval()
    for row in rows:
        for claim in row["claims"]:
            if not claim["exact_quote"]: continue
            encoded=tokenizer(claim["quote"],claim["claim"],return_tensors="pt",truncation=True)
            with torch.inference_mode(): probs=torch.softmax(nli_model(**encoded).logits[0],dim=-1)
            scores={nli_model.config.id2label[i].lower():round(float(p),8) for i,p in enumerate(probs)}
            decision=max(scores,key=scores.get)
            claim["nli"]={"decision":decision,"probabilities":scores,"input_tokens":int(encoded["input_ids"].shape[-1])}
            claim["accepted"]=decision=="entailment"
        row["accepted_claims"]=[c["claim"] for c in row["claims"] if c.get("accepted")]
    result={"schema_version":"0.1-private","experiment":"E007","gate":"16D.9","status":"awaiting_human_review","rows":rows,"mechanical_summary":{"valid_structured_answers":sum(r["receipt"]=="CLAIMS" for r in rows),"claims":sum(len(r["claims"]) for r in rows),"exact_quotes":sum(c["exact_quote"] for r in rows for c in r["claims"]),"nli_accepted":sum(bool(c.get("accepted")) for r in rows for c in r["claims"])}}
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__": main()
