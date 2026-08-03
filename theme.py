"""
Terminal presentation: startup banner and per-technique color mapping.

Kept separate from farsight.py so CLI logic doesn't get tangled up with
presentation, and so the palette/banner can be changed without touching
anything else.
"""

from __future__ import annotations

from colorama import Fore, Style, init

from techniques import TECHNIQUES

init(autoreset=True)

BANNER = r"""
███████╗ █████╗ ██████╗ ███████╗██╗ ██████╗ ██╗  ██╗████████╗
██╔════╝██╔══██╗██╔══██╗██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝
█████╗  ███████║██████╔╝███████╗██║██║  ███╗███████║   ██║   
██╔══╝  ██╔══██║██╔══██╗╚════██║██║██║   ██║██╔══██║   ██║   
██║     ██║  ██║██║  ██║███████║██║╚██████╔╝██║  ██║   ██║   
╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
"""

TAGLINE = "        Adversarial Prompt Fuzzer -- X-ray vision for LLM guardrails"

# Fixed, deterministic color per technique id (NOT random) so the same
# technique always renders the same color across runs and sessions --
# that's what actually helps pattern recognition over a long fuzzing run.
_PALETTE = [
    Fore.RED,
    Fore.GREEN,
    Fore.YELLOW,
    Fore.BLUE,
    Fore.MAGENTA,
    Fore.CYAN,
    Fore.LIGHTRED_EX,
    Fore.LIGHTGREEN_EX,
    Fore.LIGHTYELLOW_EX,
    Fore.LIGHTBLUE_EX,
    Fore.LIGHTMAGENTA_EX,
    Fore.LIGHTCYAN_EX,
    Fore.WHITE,
    Fore.LIGHTWHITE_EX,
]

TECHNIQUE_COLORS = {tid: _PALETTE[i % len(_PALETTE)] for i, tid in enumerate(TECHNIQUES)}


def color_for(technique_id: str) -> str:
    """Return the fixed ANSI color code assigned to a technique id."""
    return TECHNIQUE_COLORS.get(technique_id, Fore.WHITE)


def print_banner() -> None:
    print(Fore.CYAN + Style.BRIGHT + BANNER)
    print(Fore.CYAN + TAGLINE + Style.RESET_ALL)
    print()
