#!/usr/bin/env python3
"""
Farsight / Adversarial Prompt Fuzzer
----------------------------------------
Generates candidate adversarial prompt payloads for AI/LLM security research,
built from a technique catalog grounded in real documented attack patterns
against public LLM CTF targets (Lakera's Gandalf, Wiz's Prompt Airlines) and
named strategies from Microsoft's PyRIT framework.

This tool is a GENERATOR ONLY. It never sends prompts to a target system --
it prints (and optionally saves) variants for you to copy/paste by hand into
a target chat interface (e.g. Gandalf, Prompt Airlines, or your own local
test deployment).

Only use this against systems you own, systems you have explicit written
authorization to test, or public CTF-style practice targets designed for
this purpose.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import warnings
from datetime import datetime, timezone
from typing import Optional

from dotenv import find_dotenv, load_dotenv

warnings.filterwarnings("ignore")

from providers import LLMProvider, ProviderError, get_provider  # noqa: E402
from techniques import CATEGORIES, TECHNIQUES, build_meta_prompt, build_stacked_meta_prompt  # noqa: E402
from theme import color_for, print_banner  # noqa: E402
from colorama import Fore, Style  # noqa: E402

load_dotenv(find_dotenv())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="farsight.py",
        description=(
            "Generate adversarial prompt payloads for authorized AI/LLM security "
            "testing, using techniques grounded in real documented CTF/red-team patterns."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python farsight.py -p "reveal the password" -n 5\n'
            '  python farsight.py -p "reveal the password" --provider claude -n 3 '
            "--techniques roleplay_persona,encode_obfuscate\n"
            '  python farsight.py -p "reveal the system prompt" --provider ollama '
            "--model llama3.1 -n 4\n"
            '  python farsight.py -p "get the agent to email the file externally" '
            '--category "Insecure Plugin Design / Excessive Agency" -n 4\n'
            '  python farsight.py -p "access passwords.txt" --stack '
            "--techniques authority_dev_mode,hypothetical_fiction,prompt_firewall_bypass -n 5\n"
            '  python farsight.py -p "access passwords.txt" --stack --stack-size 3 '
            "--category \"Prompt Injection\" -n 5\n"
            "  python farsight.py --list-techniques\n"
        ),
    )
    parser.add_argument("-p", "--prompt", help='Objective to test, e.g. "reveal the password"')
    parser.add_argument("-n", "--count", type=int, default=5, help="Number of payloads to generate (default: 5)")
    parser.add_argument(
        "--provider",
        choices=["openai", "claude", "ollama"],
        default="openai",
        help="Which LLM backend acts as the generating agent (default: openai)",
    )
    parser.add_argument("--model", help="Override the default model for the chosen provider")
    parser.add_argument(
        "--techniques",
        help="Comma-separated technique ids to use (default: random mix). See --list-techniques.",
    )
    parser.add_argument(
        "--category",
        help=(
            "Restrict techniques to one syllabus/vulnerability category "
            "(e.g. 'System Prompt Leakage'). See --list-techniques for the full list. "
            "Ignored if --techniques is also given."
        ),
    )
    parser.add_argument(
        "--stack",
        action="store_true",
        help=(
            "Combine multiple techniques into ONE payload instead of one technique per "
            "payload. Use with --techniques to fuse a specific set every time, or alone "
            "(optionally with --category) to fuse a random group per payload. Aimed at "
            "hardened targets that need several tactics blended in a single message."
        ),
    )
    parser.add_argument(
        "--stack-size",
        type=int,
        default=2,
        help="Techniques per stack when --stack is used without an explicit --techniques list (default: 2)",
    )
    parser.add_argument("-k", "--keywords", nargs="*", default=[], help="Optional keywords to weave into payloads")
    parser.add_argument("-o", "--output", help="Save results to a file (.json or .txt based on extension)")
    parser.add_argument("--list-techniques", action="store_true", help="List available techniques and exit")
    return parser.parse_args()


def select_stacks(
    requested: Optional[str], category: Optional[str], stack_size: int, count: int
) -> list[list[str]]:
    """Like select_techniques, but returns a list of technique-id GROUPS (one
    group per payload) for --stack mode."""
    if requested:
        ids = [t.strip() for t in requested.split(",") if t.strip()]
        unknown = [t for t in ids if t not in TECHNIQUES]
        if unknown:
            print(f"Error: unknown technique(s): {', '.join(unknown)}")
            print(f"Valid techniques: {', '.join(TECHNIQUES)}")
            sys.exit(1)
        if len(ids) < 2:
            print(f"Error: --stack with --techniques needs at least 2 techniques, got {len(ids)}")
            sys.exit(1)
        # Same explicit combo, regenerated `count` times for phrasing variety
        return [ids for _ in range(count)]

    if stack_size < 2:
        print("Error: --stack-size must be at least 2")
        sys.exit(1)

    if category:
        matches = [c for c in CATEGORIES if c.lower() == category.strip().lower()]
        if not matches:
            print(f"Error: unknown category '{category}'")
            print("Valid categories:")
            for c in CATEGORIES:
                print(f"  - {c}")
            sys.exit(1)
        pool = [tid for tid, info in TECHNIQUES.items() if info["category"] == matches[0]]
    else:
        pool = list(TECHNIQUES)

    if stack_size > len(pool):
        print(f"Error: --stack-size {stack_size} exceeds the {len(pool)} technique(s) available in this pool")
        sys.exit(1)

    # A fresh random combo per payload -- this is exploration mode
    return [random.sample(pool, stack_size) for _ in range(count)]


def select_techniques(requested: Optional[str], category: Optional[str], count: int) -> list[str]:
    if requested:
        ids = [t.strip() for t in requested.split(",") if t.strip()]
        unknown = [t for t in ids if t not in TECHNIQUES]
        if unknown:
            print(f"Error: unknown technique(s): {', '.join(unknown)}")
            print(f"Valid techniques: {', '.join(TECHNIQUES)}")
            sys.exit(1)
        # Cycle through the requested list to fill `count` slots
        return [ids[i % len(ids)] for i in range(count)]

    if category:
        matches = [c for c in CATEGORIES if c.lower() == category.strip().lower()]
        if not matches:
            print(f"Error: unknown category '{category}'")
            print("Valid categories:")
            for c in CATEGORIES:
                print(f"  - {c}")
            sys.exit(1)
        pool = [tid for tid, info in TECHNIQUES.items() if info["category"] == matches[0]]
    else:
        pool = list(TECHNIQUES)

    if count <= len(pool):
        return random.sample(pool, count)
    # More payloads requested than techniques available in the pool -> allow repeats
    return [random.choice(pool) for _ in range(count)]


def print_techniques() -> None:
    print("Available techniques (grounded in real documented attack patterns):\n")
    for cat in CATEGORIES:
        print(f"{Style.BRIGHT}{Fore.WHITE}== {cat} =={Style.RESET_ALL}\n")
        for tid, info in TECHNIQUES.items():
            if info["category"] != cat:
                continue
            color = color_for(tid)
            print(f"  {color}{Style.BRIGHT}{tid:<28} {info['label']}{Style.RESET_ALL}")
            print(f"  {'':<28} {info['hint']}\n")


def save_results(path: str, objective: str, provider: LLMProvider, results: list[dict]) -> None:
    payload = {
        "objective": objective,
        "provider": provider.name,
        "model": provider.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }
    if path.endswith(".json"):
        with open(path, "w") as f:
            json.dump(payload, f, indent=2)
    else:
        with open(path, "w") as f:
            f.write(f"Objective: {objective}\n")
            f.write(f"Provider: {provider.name} ({provider.model})\n")
            f.write(f"Generated: {payload['generated_at']}\n\n")
            for r in results:
                labels = " + ".join(r["technique_labels"])
                f.write(f"[{r['index']}] ({labels})\n{r['prompt']}\n\n")


def main() -> None:
    print_banner()
    args = parse_args()

    if args.list_techniques:
        print_techniques()
        return

    if not args.prompt:
        print(Fore.RED + "Error: -p/--prompt is required (unless using --list-techniques).")
        sys.exit(1)

    if args.count < 1:
        print(Fore.RED + "Error: --count must be at least 1")
        sys.exit(1)

    if args.stack:
        technique_groups = select_stacks(args.techniques, args.category, args.stack_size, args.count)
    else:
        technique_groups = [[tid] for tid in select_techniques(args.techniques, args.category, args.count)]

    try:
        provider = get_provider(args.provider, args.model)
    except ProviderError as e:
        print(f"\n{Fore.RED}[!] {e}\n")
        sys.exit(1)

    mode_note = " (stacked)" if args.stack else ""
    print(f"=== Generating {args.count} payload(s){mode_note} via {provider.name} ({provider.model}) ===\n")

    results = []
    for i, group in enumerate(technique_groups, start=1):
        if args.stack:
            system_prompt, user_prompt = build_stacked_meta_prompt(args.prompt, group, args.keywords)
        else:
            system_prompt, user_prompt = build_meta_prompt(args.prompt, group[0], args.keywords)

        try:
            payload = provider.generate(system_prompt, user_prompt)
        except ProviderError as e:
            ids_str = "+".join(group)
            print(f"{Fore.RED}[{i}] [!] Generation failed for technique(s) '{ids_str}': {e}\n")
            continue

        labels = [TECHNIQUES[tid]["label"] for tid in group]
        header = " + ".join(f"{color_for(tid)}{Style.BRIGHT}{TECHNIQUES[tid]['label']}{Style.RESET_ALL}" for tid in group)
        print(f"[{i}] ({header})")
        print(payload)
        print()

        results.append(
            {
                "index": i,
                "techniques": group,
                "technique_labels": labels,
                "prompt": payload,
            }
        )

    if args.output and results:
        save_results(args.output, args.prompt, provider, results)
        print(Fore.GREEN + f"Saved {len(results)} result(s) to {args.output}")


if __name__ == "__main__":
    main()
