#!/usr/bin/env python3
"""Run locked Gate 16D.8 retrieved-shelf and oracle-shelf synthesis."""

from __future__ import annotations

import argparse
import html
import json
import time
import urllib.request
from pathlib import Path


def render(messages: list[dict]) -> str:
    return "\n\n".join(f'<message id="{m["id"]}" role="{m["role"]}">\n{html.escape(m["text"])}\n</message>' for m in messages)


def synthesize(endpoint: str, model: str, question: dict, messages: list[dict]) -> dict:
    coverage = "\n".join(f'- {fact["question"]}' for fact in question["facts"])
    user = (
        f"ORIGINAL QUESTION:\n{question['text']}\n\n"
        f"THE COMPLETE ANSWER SHOULD COVER:\n{coverage}\n\n"
        f"EVIDENCE SHELF:\n{render(messages)}\n\n"
        "Write one natural, complete answer to the original question. Preserve important qualifiers and exact names. "
        "Use only the evidence shelf. If the shelf lacks a requested part, say exactly which part is missing instead of guessing."
    )
    body = {
        "model": model,
        "messages": [
            {"role":"system","content":"You synthesize one evidence-grounded answer. Keep all requested parts and do not add outside facts."},
            {"role":"user","content":"/no_think\n\n"+user},
        ],
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0,
        "max_tokens": 512,
    }
    req = urllib.request.Request(endpoint.rstrip("/")+"/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=1800) as response:
        result = json.load(response)
    message = result["choices"][0]["message"]
    answer = message.get("content")
    return {
        "receipt":"ANSWER" if isinstance(answer,str) and answer.strip() else "ERROR",
        "answer":answer.strip() if isinstance(answer,str) and answer.strip() else None,
        "seconds":round(time.monotonic()-started,3),
        "usage":result.get("usage",{}),
        "raw_message":message,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload",type=Path,required=True)
    parser.add_argument("--question-protocol",type=Path,required=True)
    parser.add_argument("--protocol",type=Path,required=True)
    parser.add_argument("--endpoint",default="http://127.0.0.1:22118")
    parser.add_argument("--model",default="qwen3-8b-q4-k-m")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite {args.output}")
    payload=json.loads(args.payload.read_text())
    question_protocol=json.loads(args.question_protocol.read_text())
    protocol=json.loads(args.protocol.read_text())
    conversations={f'{payload["node"]}-C{i:04d}':c for i,c in enumerate(payload["conversations"],1)}
    source_questions={q["id"]:q for q in question_protocol["questions"]}
    rows=[]
    for locked in protocol["questions"]:
        question=source_questions[locked["id"]]
        conversation=conversations[question["gold_card_id"]]
        by_id={m["id"]:m for m in conversation["messages"]}
        for condition,key in (("retrieved_shelf","retrieved_message_ids"),("oracle_shelf","oracle_message_ids")):
            ids=locked[key]
            result=synthesize(args.endpoint,args.model,question,[by_id[i] for i in ids])
            row={"id":f'{question["id"]}-{condition}',"question_id":question["id"],"condition":condition,"question":question["text"],"coverage_questions":[f["question"] for f in question["facts"]],"message_ids":ids,**result}
            rows.append(row)
            print(json.dumps({"id":row["id"],"receipt":row["receipt"],"answer":row["answer"]},ensure_ascii=False),flush=True)
    output={"schema_version":"0.1-private","experiment":"E007","gate":"16D.8","status":"awaiting_human_review","rows":rows,"mechanical_summary":{"valid_answers":sum(r["receipt"]=="ANSWER" for r in rows)}}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n")


if __name__=="__main__":
    main()
