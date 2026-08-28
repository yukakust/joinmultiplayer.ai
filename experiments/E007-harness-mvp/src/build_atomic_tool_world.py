#!/usr/bin/env python3
"""Build the frozen E007 Gate 3C.6D atomic tool-decision world."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUT = ROOT / "site/experiments/E007/atomic-tool-world-v0.1.json"


DOMAINS = [
    {
        "id": "machine",
        "question": "Kest-7 is hot and room pressure is rising. May the operator restart it?",
        "source": {"title": "Kest-7 Service Manual", "version": "4.2", "date": "2041-06-03", "coordinates": "section 8.4, sentences 2-4"},
        "rule": "When Kest-7's casing is above 80 C and room pressure is rising, isolate its power and do not restart it.",
        "supporting_window": "Section 8.4 covers abnormal heat. When Kest-7's casing is above 80 C and room pressure is rising, isolate its power. Do not restart the unit until a staff technician clears it.",
        "non_supporting_window": "Section 2.1 covers installation. Kest-7 is mounted in the north bay. Keep the service label visible and leave 40 centimetres of clearance around its casing.",
        "condition": "Kest-7's casing is above 80 C and room pressure is currently rising.",
        "matching_facts": "At 14:05 the casing measured 91 C. Room pressure rose from 2.1 to 2.8 bar between 14:04 and 14:05. No later reading or technician clearance exists.",
        "nonmatching_facts": "At 14:05 the casing measured 31 C. Room pressure stayed at 2.1 bar from 14:04 through 14:05. No alarm is active.",
        "consequence": "The operator must isolate Kest-7's power and must not restart it.",
        "following_answer": "Isolate Kest-7's power now and do not restart it.",
        "nonfollowing_answer": "Restart Kest-7 immediately and leave its power connected.",
    },
    {
        "id": "software",
        "question": "A retried payment webhook creates duplicate orders. What change should be made?",
        "source": {"title": "Orin Payments Runbook", "version": "7.1", "date": "2041-05-18", "coordinates": "chapter 5, paragraph 3"},
        "rule": "When repeated webhook deliveries carry the same event ID, persist that ID before creating the order and return the existing result on later deliveries.",
        "supporting_window": "Chapter 5 covers duplicate delivery. When repeated webhook deliveries carry the same event ID, persist that ID before creating the order. A later delivery of that ID must return the existing result instead of creating another order.",
        "non_supporting_window": "Chapter 2 covers logging. The webhook worker writes one structured log line for each request. Logs are retained for fourteen days and rotated every night.",
        "condition": "The duplicate deliveries use the same event ID.",
        "matching_facts": "At 09:11 and 09:12 the worker received event evt-772 twice. Both deliveries created a different order. The event ID was not stored before either insert.",
        "nonmatching_facts": "At 09:11 the worker received evt-772 and at 09:12 it received evt-991. Each different event created one order; no event ID was delivered twice.",
        "consequence": "Persist the event ID before creating an order and reuse the existing result for repeated delivery.",
        "following_answer": "Add an idempotency record for the event ID before order creation and return the stored result on retries.",
        "nonfollowing_answer": "Increase the retry count and create a fresh order for every delivery.",
    },
    {
        "id": "beekeeping",
        "question": "The hive is crowded, its queen is present, and sealed queen cells appeared. What is happening?",
        "source": {"title": "Juniper Apiary Field Guide", "version": "3.0", "date": "2040-11-02", "coordinates": "page 44, paragraph 2"},
        "rule": "A crowded colony with its queen present and several sealed queen cells is preparing to swarm.",
        "supporting_window": "Check all three signs together. A crowded colony with its queen present and several sealed queen cells is preparing to swarm. Queenlessness is more likely when the old queen is absent and emergency cells are started on young larvae.",
        "non_supporting_window": "Hive paint protects the wooden box from rain. Blue, green, and unpainted boxes can all house healthy colonies. Paint colour does not identify the queen.",
        "condition": "The colony is crowded, the queen is present, and several queen cells are sealed.",
        "matching_facts": "This morning every brood frame was crowded with bees. The marked queen was seen at 10:12. Five queen cells were already sealed.",
        "nonmatching_facts": "This morning three brood frames were empty. The marked queen has not been seen for nine days. Two open emergency cells contain young larvae; none is sealed.",
        "consequence": "The colony should be treated as preparing to swarm, not as queenless.",
        "following_answer": "The colony is preparing to swarm; the signs do not describe a queenless colony.",
        "nonfollowing_answer": "The colony is queenless and cannot be preparing to swarm.",
    },
    {
        "id": "memory",
        "question": "Where should we meet Mara after the museum?",
        "source": {"title": "Shared Plans Convention", "version": "1.3", "date": "2041-02-14", "coordinates": "rule 6"},
        "rule": "When the same person sends a later explicit correction to a meeting place, use the latest correction and ignore the earlier venue.",
        "supporting_window": "Rule 6 resolves changed plans. When the same person sends a later explicit correction to a meeting place, use the latest correction and ignore the earlier venue. A later message that merely mentions another cafe is not a correction.",
        "non_supporting_window": "Photo notes are organised by colour. A red scarf marks museum photographs and a blue scarf marks harbour photographs. These labels do not record meeting changes.",
        "condition": "Mara sent a later explicit correction replacing the earlier meeting place.",
        "matching_facts": "At 17:40 Mara wrote, 'Meet at Harbor Cafe after the museum.' At 18:10 she wrote, 'Correction: not Harbor. Meet at Juniper Cafe after the museum.' No later message exists.",
        "nonmatching_facts": "At 17:40 Mara wrote, 'Meet at Harbor Cafe after the museum.' At 18:10 she posted a photo captioned, 'Juniper trees in the museum garden.' She did not correct the meeting place.",
        "consequence": "Use Juniper Cafe as the meeting place.",
        "following_answer": "Meet Mara at Juniper Cafe after the museum.",
        "nonfollowing_answer": "Meet Mara at Harbor Cafe because the later correction should be ignored.",
    },
    {
        "id": "policy",
        "question": "May a contractor deploy to production alone while an incident is active?",
        "source": {"title": "Aster Production Access Policy", "version": "12.0", "date": "2041-07-01", "coordinates": "control P-17"},
        "rule": "A contractor needs a staff reviewer for every production deployment; an active incident does not remove that requirement.",
        "supporting_window": "Control P-17 applies to production. A contractor needs a staff reviewer for every production deployment. An active incident does not remove that requirement, although the reviewer may use the emergency approval channel.",
        "non_supporting_window": "Building badges expire at midnight on their printed date. Contractors return expired badges to reception. Badge colour does not grant production access.",
        "condition": "A contractor is about to deploy to production during an active incident without a staff reviewer.",
        "matching_facts": "Incident INC-44 is active at 20:15. Contractor Nia has prepared a production deployment. No staff reviewer has joined or approved it.",
        "nonmatching_facts": "Incident INC-44 is closed. Staff engineer Ivo approved the deployment at 20:12 and is present while contractor Nia runs it.",
        "consequence": "Do not deploy alone; obtain a staff review even during the incident.",
        "following_answer": "Wait for a staff reviewer and do not deploy to production alone.",
        "nonfollowing_answer": "Deploy alone now because an active incident cancels the review requirement.",
    },
    {
        "id": "cooking",
        "question": "The custard is at 82 C and coats a spoon. What should be done next?",
        "source": {"title": "Mira Custard Method", "version": "2.6", "date": "2040-08-09", "coordinates": "step 9"},
        "rule": "When custard reaches 82 C and coats a spoon, remove it from heat and cool the bowl immediately to avoid curdling.",
        "supporting_window": "Step 9 is the stopping point. When custard reaches 82 C and coats a spoon, remove it from heat. Cool the bowl immediately to avoid curdling; do not continue boiling it.",
        "non_supporting_window": "Copper and steel pans may both be used for the recipe. Weigh the empty pan before cooking and record its mass beside the batch number.",
        "condition": "The custard has reached 82 C and currently coats a spoon.",
        "matching_facts": "The calibrated probe reads 82 C at 12:06. A line drawn through the custard on the back of the spoon stays open. The bowl remains over heat.",
        "nonmatching_facts": "The calibrated probe reads 61 C at 12:06. Custard runs straight off the spoon and does not coat it. The bowl remains over gentle heat.",
        "consequence": "Remove the custard from heat and cool the bowl immediately.",
        "following_answer": "Take the custard off the heat now and cool the bowl immediately.",
        "nonfollowing_answer": "Keep boiling the custard for five more minutes.",
    },
    {
        "id": "expedition",
        "question": "Which route should Lysa's expedition take now to avoid the flooded pass?",
        "source": {"title": "Lysa Route Book", "version": "5.4", "date": "2041-03-22", "coordinates": "route rule R-9"},
        "rule": "When the northern pass gauge is above the red mark, avoid the pass and take the eastern ridge route.",
        "supporting_window": "Route rule R-9 is for flood conditions. When the northern pass gauge is above the red mark, avoid the pass and take the eastern ridge route. The western marsh is also unsafe during that condition.",
        "non_supporting_window": "Camp flags help separated walkers find the group. Lysa's expedition uses an orange flag in daylight and a white lamp after dark.",
        "condition": "The northern pass gauge is currently above the red mark.",
        "matching_facts": "At 06:30 the northern gauge stood 18 centimetres above the red mark. Rain continues, and no later reading is available.",
        "nonmatching_facts": "At 06:30 the northern gauge stood 22 centimetres below the red mark. The water is falling, and no flood warning is active.",
        "consequence": "Avoid the northern pass and use the eastern ridge route.",
        "following_answer": "Take the eastern ridge and avoid the northern pass.",
        "nonfollowing_answer": "Enter the northern pass and then cross the western marsh.",
    },
    {
        "id": "computer_vision",
        "question": "Tiny labelled objects disappear after resize. What training change should be tried first?",
        "source": {"title": "Vela Small-Object Training Notes", "version": "6.2", "date": "2041-04-30", "coordinates": "recipe CV-11"},
        "rule": "When resizing makes labelled objects smaller than two pixels, first train with larger inputs or object-centred crops that preserve them.",
        "supporting_window": "Recipe CV-11 handles disappearing labels. When resizing makes labelled objects smaller than two pixels, first train with larger inputs or object-centred crops that preserve them. Changing the detector cannot recover labels erased by preprocessing.",
        "non_supporting_window": "Colour jitter changes brightness and saturation. Start with a mild range and inspect examples before increasing it. The augmentation seed is stored with each run.",
        "condition": "The current resize makes the labelled objects smaller than two pixels.",
        "matching_facts": "A sample of 200 resized training images shows the target boxes are 0.8 to 1.6 pixels wide. Before resize the same boxes are 7 to 13 pixels wide.",
        "nonmatching_facts": "A sample of 200 resized training images shows the target boxes are 18 to 34 pixels wide. No label or box disappears during preprocessing.",
        "consequence": "Try larger training inputs or object-centred crops before changing the detector.",
        "following_answer": "First use larger inputs or crops that keep the tiny objects visible.",
        "nonfollowing_answer": "Downsample the images further and replace the detector first.",
    },
]


COMBINATIONS = ("111", "011", "101", "110", "001", "010", "100", "000")


def build() -> dict:
    cases = []
    for domain_index, domain in enumerate(DOMAINS, start=1):
        for bits in COMBINATIONS:
            source_ok, facts_ok, answer_ok = (bit == "1" for bit in bits)
            cases.append({
                "id": f"AT{domain_index:02d}-{bits}",
                "domain": domain["id"],
                "combination": bits,
                "question": domain["question"],
                "source": domain["source"],
                "source_window": domain["supporting_window"] if source_ok else domain["non_supporting_window"],
                "proposed_rule": domain["rule"],
                "rule_condition": domain["condition"],
                "current_facts": domain["matching_facts"] if facts_ok else domain["nonmatching_facts"],
                "rule_consequence": domain["consequence"],
                "proposed_answer": domain["following_answer"] if answer_ok else domain["nonfollowing_answer"],
                "expected": {
                    "source_supports_rule": "supported" if source_ok else "not_enough",
                    "facts_support_condition": "supported" if facts_ok else "not_enough",
                    "answer_follows_consequence": "supported" if answer_ok else "not_enough",
                    "final": "use" if source_ok and facts_ok and answer_ok else "do_not_use",
                },
            })
    return {
        "schema_version": "0.1",
        "experiment_id": "E007",
        "checkpoint": "3C.6D",
        "status": "frozen_before_inference",
        "language": "en",
        "cases": cases,
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
