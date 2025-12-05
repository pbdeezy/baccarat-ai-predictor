#!/usr/bin/env python3
"""
baccarat shoe simulator with burn/cut support.

- configurable:
    - number of decks
    - cards burned / cut off the top of the shoe
    - max hands per shoe (e.g. ~40)
- outputs a csv of all hands:
    - shoe_id, hand_number, player_cards, banker_cards, player_total,
      banker_total, winner (P/B/T), natural (0/1)
"""

import argparse
import csv
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple


# ---------- data model ----------

@dataclass
class HandResult:
    shoe_id: int
    hand_number: int
    player_cards: List[int]
    banker_cards: List[int]
    player_total: int
    banker_total: int
    winner: str  # "P", "B", "T"
    natural: bool


# ---------- core baccarat logic ----------

def build_shoe(num_decks: int, rng: random.Random) -> List[int]:
    """
    build an n-deck shoe. we only care about ranks (1–13), suits don’t matter.
    """
    shoe: List[int] = []
    for _ in range(num_decks):
        for rank in range(1, 14):        # 1-13
            for _suit in range(4):       # four suits
                shoe.append(rank)
    rng.shuffle(shoe)
    return shoe


def baccarat_value(rank: int) -> int:
    """
    convert a rank to baccarat value.
    1-9 = 1-9, 10/J/Q/K = 0
    """
    return rank if rank < 10 else 0


def hand_total(cards: List[int]) -> int:
    return sum(baccarat_value(c) for c in cards) % 10


def deal_card(shoe: List[int], pos: int) -> Tuple[int, int]:
    if pos >= len(shoe):
        raise IndexError("shoe out of cards")
    return shoe[pos], pos + 1


def play_hand(shoe: List[int], pos: int) -> Tuple[HandResult, int]:
    """
    deal one baccarat hand from `shoe` starting at index `pos`.

    returns:
        (HandResult, new_pos)
    """

    # initial deal: P1, B1, P2, B2
    p_cards: List[int] = []
    b_cards: List[int] = []

    c, pos = deal_card(shoe, pos)
    p_cards.append(c)
    c, pos = deal_card(shoe, pos)
    b_cards.append(c)
    c, pos = deal_card(shoe, pos)
    p_cards.append(c)
    c, pos = deal_card(shoe, pos)
    b_cards.append(c)

    p_total = hand_total(p_cards)
    b_total = hand_total(b_cards)
    natural = False

    # natural check
    if p_total in (8, 9) or b_total in (8, 9):
        natural = True
        # no third cards
    else:
        # player action
        if p_total <= 5:
            # player draws third card
            c, pos = deal_card(shoe, pos)
            p_cards.append(c)
            p_total = hand_total(p_cards)

            # banker reacts based on player's third card
            p3_val = baccarat_value(c)
            b_total = hand_total(b_cards)

            if b_total <= 2:
                c, pos = deal_card(shoe, pos)
                b_cards.append(c)
            elif b_total == 3 and p3_val != 8:
                c, pos = deal_card(shoe, pos)
                b_cards.append(c)
            elif b_total == 4 and p3_val in (2, 3, 4, 5, 6, 7):
                c, pos = deal_card(shoe, pos)
                b_cards.append(c)
            elif b_total == 5 and p3_val in (4, 5, 6, 7):
                c, pos = deal_card(shoe, pos)
                b_cards.append(c)
            elif b_total == 6 and p3_val in (6, 7):
                c, pos = deal_card(shoe, pos)
                b_cards.append(c)
            # 7 stands, or conditions not met = stand
        else:
            # player stands on 6 or 7
            b_total = hand_total(b_cards)
            if b_total <= 5:
                c, pos = deal_card(shoe, pos)
                b_cards.append(c)

        # final totals after possible draws
        p_total = hand_total(p_cards)
        b_total = hand_total(b_cards)

    # decide winner
    if p_total > b_total:
        winner = "P"
    elif b_total > p_total:
        winner = "B"
    else:
        winner = "T"

    result = HandResult(
        shoe_id=-1,           # filled by caller
        hand_number=-1,       # filled by caller
        player_cards=p_cards,
        banker_cards=b_cards,
        player_total=p_total,
        banker_total=b_total,
        winner=winner,
        natural=natural,
    )
    return result, pos


# ---------- simulation wrappers ----------

def simulate_shoe(
    shoe_id: int,
    num_decks: int = 8,
    burn_cards: int = 0,
    max_hands: Optional[int] = None,
    rng_seed: Optional[int] = None,
) -> List[HandResult]:
    """
    simulate a single shoe.

    - num_decks: how many decks in the shoe
    - burn_cards: how many cards to remove from the top at the start
        (this is where you mirror "cut 10 cards" / "cut 8 cards")
    - max_hands: cap on number of hands dealt (e.g. 40)
    """

    rng = random.Random(rng_seed)
    shoe = build_shoe(num_decks, rng)
    pos = 0

    # burn/cut cards from top of shoe
    burn_cards = max(0, int(burn_cards))
    pos = min(len(shoe), pos + burn_cards)

    results: List[HandResult] = []
    hand_number = 1

    # loop while there are enough cards left to deal a worst-case hand (6 cards)
    while (max_hands is None or hand_number <= max_hands) and (pos + 6) <= len(shoe):
        res, pos = play_hand(shoe, pos)
        res.shoe_id = shoe_id
        res.hand_number = hand_number
        results.append(res)
        hand_number += 1

    return results


def simulate_many_shoes(
    num_shoes: int = 10,
    num_decks: int = 8,
    burn_cards: int = 0,
    max_hands: Optional[int] = 40,
    rng_seed: Optional[int] = None,
) -> List[HandResult]:
    """
    simulate multiple shoes and return a flat list of HandResult.
    """
    all_results: List[HandResult] = []
    rng = random.Random(rng_seed)

    for shoe_id in range(1, num_shoes + 1):
        # different seed per shoe for variety
        seed = rng.randint(0, 10**9)
        shoe_results = simulate_shoe(
            shoe_id=shoe_id,
            num_decks=num_decks,
            burn_cards=burn_cards,
            max_hands=max_hands,
            rng_seed=seed,
        )
        all_results.extend(shoe_results)

    return all_results


def export_to_csv(results: List[HandResult], path: str) -> None:
    """
    write results to a csv file.
    player_cards / banker_cards are stored as dash-separated ranks, e.g. "9-8-1"
    """
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "shoe_id",
            "hand_number",
            "player_cards",
            "banker_cards",
            "player_total",
            "banker_total",
            "winner",
            "natural",
        ])
        for r in results:
            writer.writerow([
                r.shoe_id,
                r.hand_number,
                "-".join(str(c) for c in r.player_cards),
                "-".join(str(c) for c in r.banker_cards),
                r.player_total,
                r.banker_total,
                r.winner,
                int(r.natural),
            ])


# ---------- cli ----------

def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="baccarat shoe simulator with burn/cut support.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--num-shoes",
        type=int,
        default=10,
        help="number of shoes to simulate.",
    )
    parser.add_argument(
        "--decks",
        type=int,
        default=8,
        help="number of decks in each shoe.",
    )
    parser.add_argument(
        "--burn-cards",
        type=int,
        default=0,
        help="number of cards burned / cut off the top at the start of each shoe.",
    )
    parser.add_argument(
        "--max-hands",
        type=int,
        default=40,
        help="maximum hands per shoe (caps shoes around ~40 hands).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="random seed for reproducibility.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="baccarat_shoes.csv",
        help="output csv path.",
    )

    args = parser.parse_args(argv)

    results = simulate_many_shoes(
        num_shoes=args.num_shoes,
        num_decks=args.decks,
        burn_cards=args.burn_cards,
        max_hands=args.max_hands,
        rng_seed=args.seed,
    )

    export_to_csv(results, args.output)
    print(f"simulated {args.num_shoes} shoes -> {len(results)} hands written to {args.output}")


if __name__ == "__main__":
    main()
