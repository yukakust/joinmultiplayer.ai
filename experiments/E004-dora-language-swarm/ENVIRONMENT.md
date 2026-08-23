# E004 development environment — Gate 1

Status: `READY FOR PINNED MODEL DOWNLOAD · NO MODEL TRAINING`

Checkpoint 1 was accepted by the owner on 2026-08-23. This gate prepares only
the reversible development environment for a two-surrogate smoke.

## Host boundary

- host: `yukabox`
- CPU: AMD Ryzen AI 9 HX 470, 24 logical CPUs
- RAM visible to Linux: 59 GiB
- experiment ceiling: 22 CPU threads and 52 GiB RAM
- accelerator: not enabled; the first smoke is CPU-only
- timezone: `Europe/Berlin`
- allowed heavy-work window: 08:00–23:45 local time
- hard stop: 23:55 local time
- blackout: 00:00–08:00 local time

## Frozen base candidate

- repository: `Qwen/Qwen3-0.6B-Base`
- Hugging Face revision: `da87bfb608c14b7cf20ba1ce41287e8de496c0cd`
- license: Apache-2.0
- architecture: Qwen3 causal LM, 28 layers, 0.6B parameters
- state at Gate 1: metadata pinned; weights not yet downloaded

The base remains unchanged during the first smoke. Any personal training must
be stored separately and must be attributable to exactly one surrogate pocket.

## Python environment

The existing repository `.venv` is used. The complete installed package lock is
in `requirements-lock.txt`. Important direct versions are:

- Python 3.14.4
- PyTorch 2.13.0+cpu
- Transformers 5.15.1
- PEFT 0.20.0
- Accelerate 1.14.0
- Hugging Face Hub 1.28.0
- Safetensors 0.8.0

Imports have been verified. No model files, adapters, private books, optimizer
states, or locked evaluation records were created in Gate 1.

## Next permitted action

Download only the pinned base revision, record every downloaded file and
SHA-256 digest, then stop for a measured frozen-base inference check.
