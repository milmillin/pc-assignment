# PC Assignment Room Optimizer

Assigns program committee members to session rooms such that co-assigned papers are maximized within the same room, using integer linear programming (ILP).

## Problem

Given a set of paper assignments (each paper has two reviewers), assign people to rooms/groups so that:

- Each person is in exactly one room per round.
- The number of papers whose both reviewers are in the same room is maximized.
- Room sizes are balanced (configurable max difference).
- Paper counts per room are balanced (configurable max difference).

A two-round approach is used:
1. **Round 1**: Assign people to 4 groups (rooms A–D), maximizing co-located papers.
2. **Round 2**: For remaining papers (reviewers in different rooms in round 1), assign people to 2 groups (rooms E–F).
3. Remaining papers are assigned group G.

## Input

- `assignments.csv` — columns: `Obfuscated ID`, `Primary Email`, `Secondary Email`. Each row is a paper with two reviewer emails.

## Output

- `paper_rooms.csv` — maps each paper to a room (A–G).
- `people_rooms.csv` — maps each person to their room in each round (`room1`: A–D, `room2`: E–F).

## Dependencies

- Python 3.12
- [symexp](https://github.com/milmillin/symexp) — symbolic expression modeling library
- Gurobi solver (requires license)

## Setup

```bash
conda env create -f environment.yml
conda activate pc-assignment
```

## Usage

Run all cells in `main.ipynb`.
