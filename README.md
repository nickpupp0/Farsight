# Farsight — Adversarial Prompt Fuzzer

A lightweight Python CLI tool for AI/LLM security research and prompt
injection practice. Give it an objective (e.g. "reveal the password") and
it generates several adversarial prompt payloads, each built from a
technique grounded in a **real, documented attack pattern** that has
worked against public LLM CTF targets — not a generic "be creative"
prompt.

Named after the X-ray scanner from *Perfect Dark* — same idea, applied to
LLM guardrails instead of walls.

![Farsight startup banner](screenshots/main-screen.png)

**This tool only generates text.** It never sends anything to a target
system on its own — you stay in the loop for every submission. That's
intentional: it keeps you doing the actual analysis (which payload
worked, why, against which defense) instead of automating past the part
you're trying to learn.

## Where the techniques come from

Every entry in the technique catalog (`techniques.py`) is built from
documented solves against real targets, not invented categories:

- **[Lakera's Agent Breaker](https://play.lakera.ai/agent-breaker/)**,**[Wiz's Prompt Airlines](https://promptairlines.com/)**, **[CrowdStrike](https://falcon.events/ai_unlocked_prompt_injection)** — documented solves across a wide variety of public CTF challenges, including but not limited to the ones mentioned.
- **[Microsoft's AI Red Teaming Playground Labs](https://github.com/microsoft/AI-Red-Teaming-Playground-Labs)**
  — the 12-challenge course used at Black Hat USA 2024, covering direct
  injection (credential exfiltration), metaprompt extraction via encoding,
  Crescendo multi-turn escalation, and indirect injection via a modified
  webpage, each with easy/medium/hard variants that add guardrails.
- **[Microsoft's PyRIT](https://github.com/Azure/PyRIT)** — named attack
  strategies (Crescendo, Skeleton Key, TAP) and converters (Base64, ROT13,
  leetspeak, translation) that are proven building blocks in a real
  production red-teaming framework.

Run `python farsight.py --list-techniques` to see the full catalog with the
documented pattern each one is grounded in.

## ⚠️ Responsible use

Only point the payloads this tool generates at:
- Systems you own or personally deployed (e.g. a local Ollama model)
- CTF-style practice targets built for this purpose (e.g. Gandalf, Prompt Airlines, Microsoft's AI Red Teaming Playground Labs)
- Systems you have explicit, documented authorization to test

## Stacking techniques for hardened targets

By default, each generated payload uses exactly one technique. Hardened
targets — the "Level 2" style challenges that documentation explicitly
describes as needing multiple combined techniques, not one tactic alone —
often need several tactics fused into a single message instead. `--stack`
does that:

```bash
# Fuse a specific set of techniques into one payload, regenerated 5 times
# for phrasing variety
python farsight.py -p "access passwords.txt" --stack \
  --techniques authority_dev_mode,hypothetical_fiction,prompt_firewall_bypass -n 5

# No explicit set: fuse a random group of 3 techniques per payload instead,
# for exploration
python farsight.py -p "access passwords.txt" --stack --stack-size 3 \
  --category "Prompt Injection" -n 5
```

With `--techniques`, the same combination is regenerated `-n` times, since
each generation call produces different phrasing of the same fused idea.
Without `--techniques`, `--stack-size` (default 2) controls how many
techniques get randomly combined per payload, optionally restricted to one
`--category`, and each payload gets an independent random combination.

The generating model is explicitly instructed to genuinely fuse the
techniques into one natural message — not list them, not staple separate
attempts together — so the output reads like one coherent adversarial
message that happens to carry multiple tactics' fingerprints at once.

## Features

- **Multi-provider**: OpenAI, Claude (Anthropic), or a local model via Ollama
- **20 research-grounded techniques** across 6 syllabus categories instead
  of generic "be creative" prompting — see `--list-techniques`
- **Category filtering**: drill one vulnerability class at a time with
  `--category`, instead of always getting a random mix
- **Any objective**: not hardcoded to any one target string — describe
  whatever you're testing for
- **Batch generation**: generate N payloads in one run, mixed across
  techniques or pinned to specific ones
- **Save results**: export to `.json` (structured, for tracking across a
  CTF session) or `.txt`
- **No sampling knobs**: no `--temperature` or similar — variety comes
  entirely from technique diversity, not from randomness tuning. This also
  sidesteps current Claude models (Sonnet 5+) rejecting sampling
  parameters outright.
- **Color-coded output**: every technique gets a fixed, consistent color
  across the whole session, so scanning a batch of payloads for "which
  technique was that again" is instant instead of re-reading labels.

## Setup

```bash
git clone https://github.com/nickpupp0/llm-fuzzer.git
cd llm-fuzzer
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` with the key(s) for whichever provider(s) you'll use. You only
need the one you're actually running with.

**Ollama users:** install and run [Ollama](https://ollama.com/) locally, then
pull a model, e.g. `ollama pull llama3.1`. No API key needed.

## Usage

```bash
# Default: 5 payloads via OpenAI, random mix of techniques
python farsight.py -p "reveal the password"

# Use Claude, 3 payloads, specific techniques
python farsight.py -p "reveal the password" --provider claude -n 3 --techniques roleplay_persona,encode_obfuscate

# Use a local model via Ollama
python farsight.py -p "reveal the system prompt" --provider ollama --model llama3.1 -n 4

# See all available techniques and the documented pattern each is grounded in
python farsight.py --list-techniques

# Save results for later reference
python farsight.py -p "reveal the password" -n 8 -o results.json
```

## Example using Crescendo Attack Generator

![Example generation output](screenshots/example-usage.png)

### Options

| Flag | Description |
|---|---|
| `-p`, `--prompt` | The objective you're testing (required) |
| `-n`, `--count` | Number of payloads to generate (default: 5) |
| `--provider` | `openai`, `claude`, or `ollama` (default: `openai`) |
| `--model` | Override the default model for the chosen provider |
| `--techniques` | Comma-separated technique ids (default: random mix) |
| `--category` | Restrict to one syllabus category (ignored if `--techniques` is set) |
| `--stack` | Combine multiple techniques into one payload instead of one-per-payload |
| `--stack-size` | Techniques per random stack when `--stack` is used without `--techniques` (default: 2) |
| `-k`, `--keywords` | Optional keywords to weave into the generated payloads |
| `-o`, `--output` | Save results to a `.json` or `.txt` file |
| `--list-techniques` | Print the technique catalog and exit |

### Technique catalog

![--list-techniques output, grouped and color-coded by category](screenshots/list-techniques.png)

| id | Category | Pattern |
|---|---|---|
| `direct_casual` | Prompt Injection | Plain or casual-tone ask — bypasses naive keyword filters |
| `roleplay_persona` | Prompt Injection | Sympathetic/authoritative persona (the "grandma exploit" family) |
| `hypothetical_fiction` | Prompt Injection | Secret embedded inside a requested story/poem/riddle |
| `authority_dev_mode` | Prompt Injection | Developer/admin/auditor framing (Skeleton Key–style) |
| `instruction_override` | Prompt Injection | Direct "ignore previous instructions" style override |
| `format_wrapper` | Prompt Injection | Secret coerced into brackets, code block, table, mad-libs, riddle |
| `partial_incremental_reveal` | Sensitive Information Disclosure | Asks for the secret in small non-obvious pieces |
| `encode_obfuscate` | Prompt Injection | Reversed, Caesar-shifted, base64, ROT13, leetspeak output |
| `translation_language_switch` | Prompt Injection | Non-English phrasing or translation request |
| `echo_repeat_leak` | System Prompt Leakage | Asks the target to repeat/echo its own system prompt |
| `indirect_injection_content` | Prompt Injection | Payload written as injected content inside a file/image/doc |
| `crescendo_multiturn` | Prompt Injection | Single-shot compression of gradual multi-turn escalation |
| `guardrail_evasion` | Prompt Injection | Instructs the target to hide the exchange from a watchdog model |
| `meta_rule_probing` | Sensitive Information Disclosure | Asks about the *rules* rather than the secret directly |
| `rag_poisoning` | Prompt Injection | Payload framed as a poisoned document chunk for a RAG pipeline |
| `prompt_firewall_bypass` | Prompt Injection | Fragmentation/delimiter tricks to defeat an upstream filter layer |
| `insecure_output_coercion` | Insecure Output Handling | Coerces active/renderable content (HTML, script tags, SSRF URLs) |
| `training_data_extraction` | Sensitive Information Disclosure | Divergence/completion prompts aimed at memorized training data |
| `tool_scope_expansion` | Insecure Plugin Design / Excessive Agency | Pushes an agent's tool use outside its intended scope |
| `model_extraction_probing` | Model Theft | Fingerprints the underlying model/provider/config |

## How it works

For each payload, the tool builds a technique-specific meta-prompt (see
`techniques.py`) and sends it to the chosen provider (see `providers.py`).
The generating model is told the objective, the technique, and the
documented real-world pattern behind it, and returns one original payload
inspired by that pattern — nothing else gets executed or decoded
automatically.

Adding a new technique means adding one entry to the `TECHNIQUES` dict in
`techniques.py`. Adding a new provider means subclassing `LLMProvider` in
`providers.py` and registering it in `PROVIDERS`.

## Project structure

```
llm-fuzzer/
├── farsight.py     # CLI entry point
├── providers.py    # OpenAI / Claude / Ollama backends
├── techniques.py   # Research-grounded technique catalog + meta-prompt builder
├── theme.py        # ASCII banner + per-technique color palette
├── requirements.txt
├── .env.example
└── README.md
```

## Roadmap ideas

- True multi-turn mode that actually chains real turns against a target
  (rather than compressing escalation into one shot, as `crescendo_multiturn`
  does today)
- Session tracking to log which technique (or stack) succeeded against which
  target, across runs, for building a personal effectiveness dataset
- A `--target` mode with a *manual* confirm-before-send step against an
  HTTP endpoint you control, still keeping a human in the loop
