#!/usr/bin/env python3
"""Plan optimal lumber cuts from available boards, minimizing waste."""

import argparse
import sys
from dataclasses import dataclass, field
from typing import List


@dataclass
class BoardPlan:
    length: float
    index: int
    kerf: float
    cuts: List[float] = field(default_factory=list)

    @property
    def material_used(self) -> float:
        # Each cut costs its length + one kerf (the saw pass to separate it)
        return sum(self.cuts) + len(self.cuts) * self.kerf

    @property
    def scrap(self) -> float:
        return self.length - self.material_used

    def can_fit(self, length: float) -> bool:
        # Exact fit: no trailing kerf needed since scrap becomes zero
        if abs(self.scrap - length) < 1e-6:
            return True
        return self.scrap >= length + self.kerf

    def add_cut(self, length: float):
        self.cuts.append(length)

    def draw(self, width: int = 64, unit: str = '"') -> str:
        """ASCII bar showing cuts, kerfs, and scrap on this board."""
        if not self.cuts:
            inner = "─" * (width - 2)
            return f"  [{inner}]"

        bar = ""
        for i, cut in enumerate(self.cuts):
            seg_w = max(2, round(cut / self.length * width))
            label = f"{cut:g}{unit}"
            if seg_w >= len(label) + 2:
                bar += f"[{label:^{seg_w - 2}}]"
            else:
                bar += f"[{'':>{seg_w - 2}}]"
            if i < len(self.cuts) - 1 or self.scrap > 1e-6:
                bar += "╫"  # kerf mark

        if self.scrap > 1e-6:
            scrap_label = f"~{self.scrap:g}"
            scrap_w = max(1, width - len(bar))
            if scrap_w > len(scrap_label):
                bar += f"{scrap_label:~<{scrap_w}}"
            else:
                bar += "~" * scrap_w

        return f"  {bar}"


def parse_cut_arg(value: str) -> List[float]:
    """Parse 'LENGTH' or 'LENGTH:QTY' into a list of lengths."""
    if ":" in value:
        parts = value.split(":", 1)
        length = float(parts[0])
        qty = int(parts[1])
        if qty < 1:
            raise argparse.ArgumentTypeError(f"Quantity must be >= 1, got {qty}")
        return [length] * qty
    return [float(value)]


def plan_cuts(
    board_lengths: List[float], cut_lengths: List[float], kerf: float
) -> List[BoardPlan]:
    """Assign cuts to boards using best-fit decreasing heuristic."""
    for cut in cut_lengths:
        if all(cut > b - kerf for b in board_lengths):
            print(
                f"Error: cut of {cut:g} exceeds all available board lengths.", file=sys.stderr
            )
            sys.exit(1)

    sorted_cuts = sorted(cut_lengths, reverse=True)
    boards = [
        BoardPlan(length=l, index=i + 1, kerf=kerf)
        for i, l in enumerate(board_lengths)
    ]

    for cut in sorted_cuts:
        # Best fit: board where the cut leaves the least remaining scrap
        best_board = None
        best_remaining = float("inf")

        for board in boards:
            if board.can_fit(cut):
                remaining_after = board.scrap - cut
                if abs(board.scrap - cut) >= 1e-6:
                    remaining_after -= kerf
                if remaining_after < best_remaining:
                    best_remaining = remaining_after
                    best_board = board

        if best_board is None:
            print(
                f"Error: cut of {cut:g} does not fit in any remaining board space.",
                file=sys.stderr,
            )
            sys.exit(1)

        best_board.add_cut(cut)

    return boards


def print_plan(boards: List[BoardPlan], unit: str) -> None:
    total_length = sum(b.length for b in boards)
    total_scrap = sum(b.scrap for b in boards)
    efficiency = (1 - total_scrap / total_length) * 100 if total_length else 0

    print(f"\n{'═' * 68}")
    print(f"  LUMBER CUT PLAN")
    print(f"{'═' * 68}")

    for board in boards:
        cuts_str = ", ".join(f"{c:g}{unit}" for c in board.cuts) or "none"
        status = "UNUSED" if not board.cuts else f"scrap: {board.scrap:g}{unit} ({board.scrap / board.length * 100:.1f}%)"
        print(f"\n  Board {board.index}  [{board.length:g}{unit}]  —  {status}")
        if board.cuts:
            print(f"  Cuts: {cuts_str}")
        print(board.draw(unit=unit))

    print(f"\n{'─' * 68}")
    print(f"  Boards:     {len(boards)}")
    print(f"  Total:      {total_length:g}{unit}")
    print(f"  Scrap:      {total_scrap:.4g}{unit}  ({100 - efficiency:.1f}%)")
    print(f"  Efficiency: {efficiency:.1f}%")
    print(f"{'═' * 68}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Plan lumber cuts to minimize waste.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
BOARD lengths (-b): list multiple values or repeat the flag.
CUT lengths  (-c): LENGTH or LENGTH:QTY — list multiple values or repeat the flag.

Units are whatever you use consistently (inches, cm, mm, feet…).

Examples:
  # Two 8-foot boards (96"), four cuts listed together
  %(prog)s -b 96 96 -c 24 36 18 30

  # Mix board lengths, quantities with colon syntax, listed together
  %(prog)s -b 96 144 -c 24:3 36:2 18

  # Multiple boards and cuts listed together, custom kerf
  %(prog)s -b 240 240 120 -c 50:4 30:3 25 --kerf 3 --unit mm

  # Feet with 1/8" kerf expressed as decimal feet
  %(prog)s -b 8 10 12 -c 2.5:2 3.75 --kerf 0.0104 --unit ft
""",
    )
    parser.add_argument(
        "-b", "--board",
        nargs="+",
        metavar="LENGTH",
        action="append",
        required=True,
        help="Available board length(s). Repeat flag or list multiple values.",
    )
    parser.add_argument(
        "-c", "--cut",
        nargs="+",
        metavar="LENGTH[:QTY]",
        action="append",
        required=True,
        help="Required cut(s) as LENGTH or LENGTH:QTY. List multiple or repeat the flag.",
    )
    parser.add_argument(
        "--kerf",
        type=float,
        default=0.125,
        metavar="WIDTH",
        help='Saw blade kerf width (default: 0.125 — assumes inches)',
    )
    parser.add_argument(
        "--unit",
        default='"',
        metavar="LABEL",
        help='Unit label for display (default: \'"\')',
    )

    args = parser.parse_args()

    board_lengths: List[float] = [
        float(v) for group in args.board for v in group
    ]

    cut_lengths: List[float] = []
    for group in args.cut:
        for token in group:
            cut_lengths.extend(parse_cut_arg(token))

    if not board_lengths:
        parser.error("Provide at least one board length with -b.")
    if not cut_lengths:
        parser.error("Provide at least one cut with -c.")

    boards = plan_cuts(board_lengths, cut_lengths, args.kerf)
    print_plan(boards, args.unit)


if __name__ == "__main__":
    main()
