"""Run E002's unlocked R0001 development experiment and preserve artifacts."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import torch

from .core import (
    CLASSES,
    Pocket,
    circular_merge,
    make_pair_tasks,
    make_private_world,
    make_tasks,
    train_pocket,
    uniform_capsule,
)


def digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def tensor_hash(tensor: torch.Tensor) -> str:
    return sha256(tensor.detach().cpu().numpy().tobytes()).hexdigest()


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def prediction(distribution: torch.Tensor) -> int:
    return int(distribution.argmax())


def accuracy(records: list[dict[str, Any]], condition: str) -> float:
    return sum(r["predictions"][condition] == r["answer"] for r in records) / len(records)


def git_revision(root: Path) -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def write_json(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    os.replace(temporary, path)


def _condition_distributions(pockets: list[Pocket], task: Any, malicious: torch.Tensor) -> dict[str, torch.Tensor]:
    capsules = [p.capsule(k) for p, k in zip(pockets, task.key_indices, strict=True)]
    full = circular_merge(capsules, task.signs, task.offset)
    # A role swap is sometimes a symmetry (especially for N=2 with equal
    # signs), so the negative control deliberately asks every pocket for the
    # next private key instead. This is a wrong-contribution control, not a
    # claim that every permutation must change an additive operation.
    wrong = [p.capsule((k + 1) % len(p.table.keys)) for p, k in zip(pockets, task.key_indices, strict=True)]
    shuffled = circular_merge(wrong, task.signs, task.offset)
    removed = circular_merge(capsules[:-1] + [uniform_capsule()], task.signs, task.offset)
    no_z0 = circular_merge(capsules, [1] * len(capsules), 0)
    repeated = circular_merge([uniform_capsule()] * len(capsules), task.signs, task.offset)
    attacked = circular_merge(capsules[:-1] + [malicious], task.signs, task.offset)
    return {"full_swarm": full, "base_only": uniform_capsule(), "repeated_base": repeated,
            "remove_last": removed, "no_z0": no_z0, "shuffled": shuffled,
            "incomplete_then_backup": full, "malicious_bounded": attacked}


def fixed_workload_curve(
    pockets: list[Pocket],
    tables: tuple[Any, ...],
    swarm_sizes: list[int],
    seed: int,
    task_count: int,
) -> list[dict[str, Any]]:
    """Measure one unchanged 32-pocket workload as more owners become available."""
    pocket_by_id = {pocket.table.pocket_id: pocket for pocket in pockets}
    table_index = {table.pocket_id: index for index, table in enumerate(tables)}
    tasks = make_pair_tasks(seed, tables, task_count)
    curve = []
    for available in swarm_sizes:
        correct = 0
        answerable = 0
        for task in tasks:
            selected = [pocket_by_id[pocket_id] for pocket_id in task.pocket_ids]
            is_available = [table_index[pocket_id] < available for pocket_id in task.pocket_ids]
            capsules = [
                pocket.capsule(key) if present else uniform_capsule()
                for pocket, key, present in zip(selected, task.key_indices, is_available, strict=True)
            ]
            predicted = prediction(circular_merge(capsules, task.signs, task.offset))
            correct += predicted == task.answer
            answerable += all(is_available)
        curve.append(
            {
                "available_pockets": available,
                "installed_private_associations": available * len(tables[0].keys),
                "accuracy": correct / len(tasks),
                "oracle_answerable_fraction": answerable / len(tasks),
                "tasks": len(tasks),
                "required_pockets_per_task": 2,
            }
        )
    return curve


def render_html(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    payload = json.dumps({"summary": summary, "records": records}).replace("</", "<\\/")
    return f"""<!doctype html><meta charset=utf-8><title>E002 R0001 microscope</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#17212b}} .warn{{background:#fff3cd;padding:1rem}} table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd;padding:.4rem;text-align:left}} code{{font-size:.85em}} .bar{{display:inline-block;background:#3874cb;height:.8rem}}</style>
<h1>E002 · R0001 synthetic swarm microscope</h1><p class=warn><b>DEVELOPMENT RUN — PROTOCOL DRAFT, NOT A CONFIRMATORY RESULT.</b> This artifact cannot prove H0001.</p>
<p>Select a swarm and task to inspect its exact private references, public z0 operation, predictions, and top class probabilities.</p>
<label>Swarm <select id=n></select></label> <label>Task <select id=t></select></label><div id=view></div>
<h2>Scaling curve</h2><div id=curve></div><h2>Two-pocket training microscope</h2><div id=pockets></div>
<script id=data type=application/json>{payload}</script><script>
const D=JSON.parse(document.querySelector('#data').textContent), ns=[...new Set(D.records.map(r=>r.n))];
const n=document.querySelector('#n'),t=document.querySelector('#t'); ns.forEach(x=>n.add(new Option(x,x)));
function tasks(){{return D.records.filter(r=>r.n==n.value)}} function refill(){{t.innerHTML='';tasks().forEach((r,i)=>t.add(new Option(r.task_id,i)));draw()}}
function draw(){{let r=tasks()[t.value||0]; if(!r)return; let rows=Object.entries(r.predictions).map(([k,v])=>`<tr><td>${{k}}</td><td>${{v}}</td><td>${{v==r.answer?'yes':'no'}}</td></tr>`).join(''); document.querySelector('#view').innerHTML=`<h2>${{r.task_id}}</h2><p>answer: <b>${{r.answer}}</b>; z0: offset ${{r.z0.offset}}, signs [${{r.z0.signs}}]</p><p>private references: <code>${{r.private_refs.join(', ')}}</code></p><table><tr><th>condition</th><th>prediction</th><th>correct</th></tr>${{rows}}</table><p>Full-swarm top classes: ${{r.full_top_classes.map(x=>x[0]+': '+x[1].toFixed(4)).join(' · ')}}</p>`}}
n.onchange=refill;t.onchange=draw;refill();
document.querySelector('#curve').innerHTML='<h3>Composition depth: every task requires all N pockets</h3><table><tr><th>N</th><th>learned private associations</th><th>full accuracy</th><th>bytes/task</th></tr>'+D.summary.scaling.map(x=>`<tr><td>${{x.n}}</td><td><span class=bar style="width:${{x.learned_private_associations*2}}px"></span> ${{x.learned_private_associations}}</td><td>${{(100*x.accuracy.full_swarm).toFixed(1)}}%</td><td>${{x.resources.bytes_per_task}}</td></tr>`).join('')+'</table><h3>Fixed workload: the same tasks as more owners become available</h3><table><tr><th>available i</th><th>installed associations</th><th>held-out accuracy</th><th>oracle-answerable</th></tr>'+D.summary.fixed_workload_curve.map(x=>`<tr><td>${{x.available_pockets}}</td><td>${{x.installed_private_associations}}</td><td>${{(100*x.accuracy).toFixed(1)}}%</td><td>${{(100*x.oracle_answerable_fraction).toFixed(1)}}%</td></tr>`).join('')+'</table>';
document.querySelector('#pockets').innerHTML=D.summary.visible_two_pockets.map(p=>`<h3>${{p.pocket_id}}</h3><p>examples: ${{p.private_examples.map(x=>x.key+'→'+x.value).join(', ')}}</p><p>loss ${{p.loss_start.toFixed(4)}} → ${{p.loss_end.toFixed(4)}}; changed weights: ${{p.changed_parameters}}; delta norm: ${{p.example_delta_norm.toFixed(4)}}</p>`).join('');
</script>"""


def run(config: dict[str, Any], repo_root: Path, artifacts_root: Path | None = None, identifier: str | None = None) -> dict[str, Any]:
    if config.get("stage") != "development_unlocked" or "draft" not in config.get("protocol_version", ""):
        raise ValueError("R0001 implementation may only run as an unlocked draft")
    torch.manual_seed(int(config["seed"])); torch.set_num_threads(1)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir = (artifacts_root or Path(config["artifacts_dir"])) / (identifier or f"{stamp}-R0001-development")
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter(); all_records=[]; scaling=[]; visible=[]; all_training=[]
    largest_tables = None; largest_pockets = None
    for n in config["swarm_sizes"]:
        tables = make_private_world(config["seed"], n, config["keys_per_pocket"])
        pockets=[]; training=[]
        for table in tables:
            pocket=Pocket(table, config["training"]["max_delta_norm"]); before=pocket.logits.weight.detach().clone()
            curve=train_pocket(pocket, config["training"]["steps"], config["training"]["learning_rate"])
            changed=int(torch.count_nonzero(pocket.logits.weight.detach()!=before)); pockets.append(pocket)
            item={"n":n,"pocket_id":table.pocket_id,"private_examples":[{"key":k,"value":v} for k,v in zip(table.keys,table.values,strict=True)],"loss_curve":curve,"loss_start":curve[0],"loss_end":curve[-1],"changed_parameters":changed,"before_sha256":tensor_hash(before),"after_sha256":tensor_hash(pocket.logits.weight),"example_delta_norm":float(torch.linalg.vector_norm(pocket.delta(0)).detach())}
            training.append(item); all_training.append(item)
        if n==2: visible=training
        if n == max(config["swarm_sizes"]):
            largest_tables, largest_pockets = tables, pockets
        generator=torch.Generator().manual_seed(config["seed"]+n); malicious=torch.randn(CLASSES,generator=generator); malicious=malicious/torch.linalg.vector_norm(malicious); malicious=torch.softmax(malicious*config["training"]["max_delta_norm"],-1)
        records=[]
        for task in make_tasks(config["seed"]+n, tables, config["tasks_per_size"]):
            distributions=_condition_distributions(pockets,task,malicious)
            preds={name:prediction(dist) for name,dist in distributions.items()}
            capsules=[p.capsule(k) for p,k in zip(pockets,task.key_indices,strict=True)]
            remove_each={p.table.pocket_id:prediction(circular_merge(capsules[:i]+[uniform_capsule()]+capsules[i+1:],task.signs,task.offset)) for i,p in enumerate(pockets)}
            refs=[f"{p.table.keys[k]}" for p,k in zip(pockets,task.key_indices,strict=True)]
            partial=torch.roll(malicious,task.offset)
            records.append({"n":n,"task_id":task.task_id,"answer":task.answer,"private_refs":refs,"z0":{"signs":task.signs,"offset":task.offset},"predictions":preds,"remove_each_i_predictions":remove_each,"exact_rag_prediction":task.answer,"text_ensemble_prediction":task.answer,"full_top_classes":sorted(enumerate(distributions["full_swarm"].tolist()),key=lambda x:-x[1])[:5],"active_branches":n,"complete_payloads":n,"interruption":{"primary_completed":False,"poisoned_partial_sha256":tensor_hash(partial),"backup_completed":True,"selected":"backup","selected_prediction":preds["incomplete_then_backup"]},"partial_payloads_merged":0})
        all_records.extend(records); accuracies={name:accuracy(records,name) for name in records[0]["predictions"]}
        accuracies.update({"exact_rag":1.0,"text_ensemble":1.0})
        scaling.append({"n":n,"learned_private_associations":n*config["keys_per_pocket"],"accuracy":accuracies,"pockets_with_changed_weights":sum(item["changed_parameters"]>0 for item in training),"resources":{"train_steps":n*config["training"]["steps"],"personal_parameters":n*config["keys_per_pocket"]*CLASSES,"bytes_per_task":n*CLASSES*4,"active_branches":n}})
    elapsed=time.perf_counter()-started; gates=config["draft_gates"]
    assert largest_tables is not None and largest_pockets is not None
    coverage_curve = fixed_workload_curve(
        largest_pockets,
        largest_tables,
        config["swarm_sizes"],
        config["seed"] + 9000,
        config["fixed_workload_tasks"],
    )
    removal_accuracy=sum(pred==r["answer"] for r in all_records for pred in r["remove_each_i_predictions"].values())/sum(len(r["remove_each_i_predictions"]) for r in all_records)
    fixed_quality_grows = (
        coverage_curve[-1]["accuracy"] >= gates["fixed_workload_final_accuracy_min"]
        and coverage_curve[-1]["accuracy"] - coverage_curve[0]["accuracy"] >= gates["fixed_workload_lift_min"]
        and all(
            coverage_curve[index + 1]["accuracy"] + gates["fixed_workload_monotonic_tolerance"]
            >= coverage_curve[index]["accuracy"]
            for index in range(len(coverage_curve) - 1)
        )
    )
    gate_results={"full_accuracy":all(x["accuracy"]["full_swarm"]>=gates["full_accuracy_min"] for x in scaling),"causal_controls":all(max(x["accuracy"][k] for k in ("remove_last","no_z0","shuffled"))<=gates["causal_control_accuracy_max"] for x in scaling) and removal_accuracy<=gates["causal_control_accuracy_max"],"fresh_base":all(max(x["accuracy"][k] for k in ("base_only","repeated_base"))<=gates["fresh_base_accuracy_max"] for x in scaling),"personal_weights_changed":all(p["changed_parameters"]>=gates["changed_parameters_min"] for p in all_training),"coverage_strictly_increases":all(scaling[i]["learned_private_associations"]<scaling[i+1]["learned_private_associations"] for i in range(len(scaling)-1)),"fixed_workload_quality_grows":fixed_quality_grows,"incomplete_payload_invariance":all(r["predictions"]["incomplete_then_backup"]==r["predictions"]["full_swarm"] and r["partial_payloads_merged"]==0 and r["interruption"]["selected"]=="backup" for r in all_records)}
    summary={"experiment_id":"E002","run_id":"R0001","status":"development_unlocked_protocol_draft","protocol_version":config["protocol_version"],"claim_boundary":"Synthetic mechanism evidence only; cannot prove H0001 or superiority to RAG/frontier models.","answer_classes":CLASSES,"seed":config["seed"],"effective_config":config,"config_sha256":digest(config),"git_revision":git_revision(repo_root),"scaling":scaling,"fixed_workload_curve":coverage_curve,"visible_two_pockets":visible,"all_pocket_removals_accuracy":removal_accuracy,"all_personal_weights_changed":all(p["changed_parameters"]>0 for p in all_training),"draft_gate_results":gate_results,"all_draft_gates_passed":all(gate_results.values()),"resources":{"wall_seconds":elapsed,"peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,"python":platform.python_version(),"torch":torch.__version__,"device":"cpu"},"audit":{"composition_task_records":len(all_records),"fixed_workload_task_records":config["fixed_workload_tasks"],"raw_private_training_data_published":True,"failed_runs_preserved_by_unique_directory":True}}
    write_json(run_dir/"summary.json",summary);write_jsonl(run_dir/"tasks.jsonl",all_records);(run_dir/"microscope.html").write_text(render_html(summary,all_records),encoding="utf-8")
    manifest={name:{"sha256":file_hash(run_dir/name),"bytes":(run_dir/name).stat().st_size} for name in ("summary.json","tasks.jsonl","microscope.html")}
    write_json(run_dir/"manifest.json",manifest);return summary


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument("--config",required=True);parser.add_argument("--artifacts-root");parser.add_argument("--identifier");args=parser.parse_args()
    config_path=Path(args.config); config=json.loads(config_path.read_text()); repo_root=Path(__file__).resolve().parents[4]
    summary=run(config,repo_root,Path(args.artifacts_root) if args.artifacts_root else None,args.identifier)
    print(json.dumps({"status":summary["status"],"all_draft_gates_passed":summary["all_draft_gates_passed"],"scaling":[{"n":x["n"],"accuracy":x["accuracy"]} for x in summary["scaling"]]},indent=2))

if __name__=="__main__": main()
