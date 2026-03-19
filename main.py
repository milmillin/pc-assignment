from pathlib import Path

from symexp import Model, LinExpr, BinVar, Var, Sense, VType
from symexp.solver import GurobiSolver, CuOptSolver, HighsSolver, ScipSolver

ROOM_NAMES_1 = ["Room_A", "Room_B", "Room_C", "Room_D"]  # round 1
ROOM_NAMES_2 = ["Room_X", "Room_Y"]                       # round 2
PLENARY = "Plenary"
ORPHANS = "Orphans"

lines = Path("assignments.csv").read_text().splitlines()
lines = [line.split(",") for line in lines[1:]]

if Path('virtuals.csv').exists():
    virtuals = Path('virtuals.csv').read_text().splitlines()
    virtuals = set([line.split(",")[0] for line in virtuals[1:]])
else:
    virtuals = set()

orphan_labels: set[str] = set()
id_map: dict[str, int] = {}
edges: list[tuple[int, ...]] = []
edges_label: list[str] = []
for label, a, b, *_ in lines:
    edge_ = []
    a = a.strip()
    b = b.strip()
    if a not in virtuals:
        if a not in id_map:
            id_map[a] = len(id_map)
        edge_.append(id_map[a])
    if b not in virtuals:
        if b not in id_map:
            id_map[b] = len(id_map)
        edge_.append(id_map[b])
    if len(edge_) == 0:
        orphan_labels.add(label)
    edges.append(tuple(edge_))
    edges_label.append(label)
id_imap: dict[int, str] = {v: k for k, v in id_map.items()}


def setup_model(
    n_people: int,
    n_groups: int,
    edges: list[tuple[int, ...]],
    group_diff: int = 5,
    paper_diff: int = 5,
) -> tuple[Model, list[list[BinVar]], list[LinExpr], list[LinExpr]]:
    """
    Returns
    - model
    - assignment_vars: (n_people, n_groups)
    - group_sizes: (n_groups,) number of people in each group
    - paper_sizes: (n_groups,) number of papers in each group
    """
    model = Model.create("Hello", LinExpr)
    assignment_vars: list[list[BinVar]] = []
    for i in range(n_people):
        vars_: list[BinVar] = []
        for j in range(n_groups):
            vars_.append(model.add_var(VType.BINARY, name=f"u_{i}_{j}"))
        # each person has exactly one assignment
        model.add_constraint(model.sum(vars_) == 1, name=f"u_{i}_sum")
        assignment_vars.append(vars_)

    # papers_assigned[group][id]
    papers_assigned = [
        [
            model.and_(*[assignment_vars[p][j] for p in people_]) if people_ else False
            for people_ in edges
        ]
        for j in range(n_groups)
    ]

    # cost = model.min_(
    #     *[
    #         model.and_(assignment_vars[a][j], assignment_vars[b][j])
    #         for a, b in edges
    #         for j in range(n_groups)
    #     ]
    # ).value

    # group size constraints
    group_sizes: list[LinExpr] = []
    for j in range(n_groups):
        group_sizes.append(model.sum(assignment_vars[i][j] for i in range(n_people)))

    # min_group_size = model.min_(*group_sizes, name="min_group_size").value
    # max_group_size = model.max_(*group_sizes, name="max_group_size").value
    # model.add_constraint(max_group_size - min_group_size <= group_diff, name="max_group_differ")

    # paper size constraints
    paper_sizes_per_group: list[LinExpr] = [model.sum(papers_assigned_to_group) for papers_assigned_to_group in papers_assigned]

    papers_assigned = model.sum(paper_sizes_per_group)

    cost = model.min_(*paper_sizes_per_group).value + papers_assigned / len(edges)

    # min_paper_size = model.min_(*paper_sizes, name="min_paper_size").value
    # max_paper_size = model.max_(*paper_sizes, name="max_paper_size").value
    # model.add_constraint(max_paper_size - min_paper_size <= paper_diff, name="max_paper_differ")

    model.set_objective(Sense.MAXIMIZE, cost)
    return model, assignment_vars, group_sizes, paper_sizes_per_group


N_GROUPS1 = 4
model1, asgn1, group1, paper1 = setup_model(
    n_people=len(id_map), n_groups=N_GROUPS1, edges=edges, group_diff=20, paper_diff=20
)

# solver = CuOptSolver(model1, time_limit=900)  # , time_limit=180)
solver = GurobiSolver(model1, time_limit=400)
# solver = ScipSolver(model1, time_limit=60, **{"display/freq": 10})
sol = solver.solve()
model1.set_solution(sol)

# number of people in each group
print([int(g) for g in group1])
# number of papers in each group
print([int(p) for p in paper1])

remaining_edges: list[tuple[int, ...]] = []
for people in edges:
    assigned = any(all(int(asgn1[p][j]) for p in people) if people else False for j in range(N_GROUPS1))
    if not assigned:
        remaining_edges.append(people)
N_GROUPS2 = 2
model2, asgn2, group2, paper2 = setup_model(
    n_people=len(id_map),
    n_groups=N_GROUPS2,
    edges=remaining_edges,
    # group_diff=20,
    # paper_diff=20,
)

solver = GurobiSolver(model2)
sol = solver.solve()
model2.set_solution(sol)

# number of people in each group
print([int(g) for g in group2])
# number of papers in each group
print([int(p) for p in paper2])

# remaining papers
print(len(edges) - sum(map(int, paper1)) - sum(map(int, paper2)))

# write output
paper_groups: list[str] = []
for people, label in zip(edges, edges_label):
    assigned = N_GROUPS1 + N_GROUPS2
    for j in range(N_GROUPS2):
        if people and all(int(asgn2[a][j]) for a in people):
            assigned = j + N_GROUPS1
            break
    for j in range(N_GROUPS1):
        if people and all(int(asgn1[a][j]) for a in people):
            assigned = j
            break
    if label in orphan_labels:
        room_name = ORPHANS
    elif assigned < N_GROUPS1:
        room_name = ROOM_NAMES_1[assigned]
    elif assigned < N_GROUPS1 + N_GROUPS2:
        room_name = ROOM_NAMES_2[assigned - N_GROUPS1]
    else:
        room_name = PLENARY
    paper_groups.append(room_name)
with Path("paper_rooms.csv").open("w") as f:
    f.write("paper_id,room\n")
    for paper, group in zip(edges_label, paper_groups):
        f.write(f"{paper},{group}\n")

with Path("people_rooms.csv").open("w") as f:
    f.write("email,room1,room2\n")
    for i in range(len(id_map)):
        group1_ = None
        for j in range(N_GROUPS1):
            if int(asgn1[i][j]):
                group1_ = j
                break
        assert group1_ is not None
        group2_ = None
        for j in range(N_GROUPS2):
            if int(asgn2[i][j]):
                group2_ = j
                break
        assert group2_ is not None
        g1 = ROOM_NAMES_1[group1_]
        g2 = ROOM_NAMES_2[group2_]
        f.write(f"{id_imap[i]},{g1},{g2}\n")

for i, (g, p) in enumerate(zip(group1, paper1)):
    print(ROOM_NAMES_1[i], int(p), "papers", int(g), "people")
for i, (g, p) in enumerate(zip(group2, paper2)):
    print(ROOM_NAMES_2[i], int(p), "papers", int(g), "people")
plenary_count = len(edges) - sum(map(int, paper1)) - sum(map(int, paper2)) - len(orphan_labels)
print(PLENARY, plenary_count, "papers")
print(ORPHANS, len(orphan_labels), "papers")
