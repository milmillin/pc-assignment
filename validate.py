import csv
from pathlib import Path
from collections import defaultdict


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    assignments = load_csv("assignments.csv")
    virtuals_rows = load_csv("virtuals.csv")
    paper_rooms = load_csv("paper_rooms.csv")
    people_rooms = load_csv("people_rooms.csv")

    virtuals = set(row["Email Link"].strip() for row in virtuals_rows)

    # Build people room lookup: email -> (room1, room2)
    people_map = {}
    for row in people_rooms:
        people_map[row["email"].strip()] = (row["room1"].strip(), row["room2"].strip())

    # Build paper room lookup: paper_id -> room
    paper_map = {}
    for row in paper_rooms:
        paper_map[row["paper_id"].strip()] = row["room"].strip()

    # Determine round 1 and round 2 rooms from people_rooms
    room1_set = sorted(set(v[0] for v in people_map.values()))
    room2_set = sorted(set(v[1] for v in people_map.values()))
    all_paper_rooms = sorted(set(paper_map.values()))
    unassigned_rooms = sorted(set(all_paper_rooms) - set(room1_set) - set(room2_set))

    print(f"Round 1 rooms: {room1_set}")
    print(f"Round 2 rooms: {room2_set}")
    if unassigned_rooms:
        print(f"Unassigned room(s): {unassigned_rooms}")
    print()

    errors = []
    warnings = []

    # Constraint 1: Each person appears exactly once in people_rooms
    emails_seen = defaultdict(int)
    for row in people_rooms:
        emails_seen[row["email"].strip()] += 1
    for email, count in emails_seen.items():
        if count > 1:
            errors.append(f"Person {email} appears {count} times in people_rooms.csv")

    # Constraint 2: Each paper appears exactly once in paper_rooms
    papers_seen = defaultdict(int)
    for row in paper_rooms:
        papers_seen[row["paper_id"].strip()] += 1
    for pid, count in papers_seen.items():
        if count > 1:
            errors.append(f"Paper {pid} appears {count} times in paper_rooms.csv")

    # Constraint 3: All papers from assignments.csv are in paper_rooms.csv
    for row in assignments:
        pid = row["Obfuscated ID"].strip()
        if pid not in paper_map:
            errors.append(f"Paper {pid} missing from paper_rooms.csv")
    for pid in paper_map:
        if pid not in {row["Obfuscated ID"].strip() for row in assignments}:
            warnings.append(f"Paper {pid} in paper_rooms.csv but not in assignments.csv")

    # Constraint 4: All non-virtual people from assignments.csv are in people_rooms.csv
    all_people = set()
    for row in assignments:
        for col in ["Primary Email", "Secondary Email"]:
            email = row.get(col, "").strip()
            if email and email not in virtuals:
                all_people.add(email)
    for email in sorted(all_people):
        if email not in people_map:
            errors.append(f"Non-virtual person {email} missing from people_rooms.csv")

    # Constraint 5: For each paper assigned to a round-1 or round-2 room,
    # ALL non-virtual reviewers must be in that room (in the corresponding round)
    paper_group_count = defaultdict(int)
    for row in assignments:
        pid = row["Obfuscated ID"].strip()
        room = paper_map.get(pid)
        if room is None:
            continue
        paper_group_count[room] += 1

        reviewers = []
        for col in ["Primary Email", "Secondary Email"]:
            email = row.get(col, "").strip()
            if email and email not in virtuals:
                reviewers.append(email)

        if room in room1_set:
            for email in reviewers:
                if email in people_map and people_map[email][0] != room:
                    errors.append(
                        f"Paper {pid} in room {room} (round 1) but reviewer "
                        f"{email} is in room {people_map[email][0]}"
                    )
        elif room in room2_set:
            for email in reviewers:
                if email in people_map and people_map[email][1] != room:
                    errors.append(
                        f"Paper {pid} in room {room} (round 2) but reviewer "
                        f"{email} is in room {people_map[email][1]}"
                    )
        elif room == "Orphans":
            # Both reviewers must be virtual
            for col in ["Primary Email", "Secondary Email"]:
                email = row.get(col, "").strip()
                if email and email not in virtuals:
                    errors.append(
                        f"Paper {pid} in Orphans but reviewer "
                        f"{email} is not virtual"
                    )
        elif room in unassigned_rooms:
            pass  # unassigned papers, no constraint
        else:
            warnings.append(f"Paper {pid} assigned to unknown room {room}")

    # Print results
    print("=== Papers per room ===")
    for room in sorted(paper_group_count):
        print(f"  Room {room}: {paper_group_count[room]} papers")
    total = sum(paper_group_count.values())
    print(f"  Total: {total} papers")
    print()

    if errors:
        print(f"=== ERRORS ({len(errors)}) ===")
        for e in errors:
            print(f"  [ERROR] {e}")
    else:
        print("=== All constraints satisfied! ===")

    if warnings:
        print(f"\n=== WARNINGS ({len(warnings)}) ===")
        for w in warnings:
            print(f"  [WARN] {w}")


if __name__ == "__main__":
    main()
