import sys
import queue
import json
import pycosat


class Solver:
    def __init__(self, nodes: dict, c: int, length: int):
        self.diff = [[0, 1], [1, 0], [-1, 0], [0, -1]]
        self.directions = [[[0, 1], [0, -1]],
                           [[1, 0], [-1, 0]],
                           [[-1, 0], [0, -1]],
                           [[-1, 0], [0, 1]],
                           [[1, 0], [0, -1]],
                           [[1, 0], [0, 1]]]
        self.nodes = nodes
        self.c = c
        self.length = length
        self.n = c * length**2
        self.cnf = []
        self.visited = []
        self.clauses = [] 
        self.output = []
        self.cycleClause = []

    def get_adjacent_neighbors(self, i, j):
        ret = []
        for element in self.diff:
            difference_x = i + element[0]
            difference_y = j + element[1]
            if 0 <= difference_x < self.length and 0 <= difference_y < self.length:
                ret.append([difference_x, difference_y])
        return ret

    def get_cell(self, x, y, color):
        return (x * self.length * self.c) + (y * self.c) + color + 1

    def get_direction(self, x, y, t):
        return self.n + (6 * x * self.length * self.c) + (6 * y) + t + 1

    def add_single_direction_clause(self, i, j):
        clause = []
        for t in range(6):
            clause.append(self.get_direction(i, j, t))
        self.cnf.append(clause)
        for t in range(6):
            for u in range(t + 1, 6):
                clause = [self.get_direction(i, j, t) * -1, self.get_direction(i, j, u) * -1]
                self.cnf.append(clause)

    def avoid_neighbor_cells(self, i, j, t):
        delta = self.directions[t]
        ret = []
        for [di, dj] in delta:
            ret.append([i + di, j + dj])
        return ret

    def add_direction_avoidance_clause(self, i, j, t):
        avoid = self.avoid_neighbor_cells(i, j, t)
        for cell in self.get_adjacent_neighbors(i, j):
            if cell not in avoid:
                for color in range(self.c):
                    clause = [self.get_direction(i, j, t) * -1, self.get_cell(i, j, color) * -1,
                              self.get_cell(cell[0], cell[1], color) * -1]
                    self.cnf.append(clause)

    def add_lr_clause(self, i, j):
        if 0 <= j - 1 < self.length and 0 <= j + 1 < self.length:
            self.add_direction_type_clause(0, [i, j], [i, j - 1], [i, j + 1])
            self.add_direction_avoidance_clause(i, j, 0)
        else:
            self.cnf.append([self.get_direction(i, j, 0) * -1])

    def add_tb_clause(self, i, j):
        if 0 <= i - 1 < self.length and 0 <= i + 1 <= self.length:
            self.add_direction_type_clause(1, [i, j], [i - 1, j], [i + 1, j])
            self.add_direction_avoidance_clause(i, j, 1)
        else:
            self.cnf.append([self.get_direction(i, j, 1) * -1])

    def add_tl_clause(self, i, j):
        if 0 <= i - 1 < self.length and 0 <= j - 1 < self.length:
            self.add_direction_type_clause(2, [i, j], [i - 1, j], [i, j - 1])
            self.add_direction_avoidance_clause(i, j, 2)
        else:
            self.cnf.append([self.get_direction(i, j, 2) * -1])

    def add_tr_clause(self, i, j):
        if 0 <= i - 1 < self.length and 0 <= j + 1 < self.length:
            self.add_direction_type_clause(3, [i, j], [i - 1, j], [i, j + 1])
            self.add_direction_avoidance_clause(i, j, 3)
        else:
            self.cnf.append([self.get_direction(i, j, 3) * -1])

    def add_bl_clause(self, i, j):
        if 0 <= i + 1 < self.length and 0 <= j - 1 < self.length:
            self.add_direction_type_clause(4, [i, j], [i + 1, j], [i, j - 1])
            self.add_direction_avoidance_clause(i, j, 4)
        else:
            self.cnf.append([self.get_direction(i, j, 4) * -1])

    def add_br_clause(self, i, j):
        if 0 <= i + 1 < self.length and 0 <= j + 1 < self.length:
            self.add_direction_type_clause(5, [i, j], [i + 1, j], [i, j + 1])
            self.add_direction_avoidance_clause(i, j, 5)
        else:
            self.cnf.append([self.get_direction(i, j, 5) * -1])

    def add_direction_type_clause(self, t, coord1, coord2, coord3):
        i1, j1, i2, j2, i3, j3 = coord1[0], coord1[1], coord2[0], coord2[1], coord3[0], coord3[1]
        for color in range(self.c):
            self.cnf.append([self.get_direction(i1, j1, t) * -1, self.get_cell(i1, j1, color) * -1,
                             self.get_cell(i2, j2, color)])
            self.cnf.append([self.get_direction(i1, j1, t) * -1, self.get_cell(i1, j1, color),
                             self.get_cell(i2, j2, color) * -1])
            self.cnf.append([self.get_direction(i1, j1, t) * -1, self.get_cell(i1, j1, color) * -1,
                             self.get_cell(i3, j3, color)])
            self.cnf.append([self.get_direction(i1, j1, t) * -1, self.get_cell(i1, j1, color),
                             self.get_cell(i3, j3, color) * -1])

    def add_direction_clause(self, i, j):
        self.add_single_direction_clause(i, j)
        self.add_lr_clause(i, j)
        self.add_tb_clause(i, j)
        self.add_tl_clause(i, j)
        self.add_tr_clause(i, j)
        self.add_bl_clause(i, j)
        self.add_br_clause(i, j)

    def add_cell_clause(self, i, j):
        clause = []
        for k in range(self.c):
            clause.append(self.get_cell(i, j, k))
        self.cnf.append(clause)
        for k in range(self.c):
            for l in range(k + 1, self.c):
                self.cnf.append([self.get_cell(i, j, k) * -1, self.get_cell(i, j, l) * -1])
        self.add_direction_clause(i, j)

    def add_endpoint_clause(self, i, j, color):
        self.cnf.append([self.get_cell(i, j, color)])
        for k in range(self.c):
            if k != color:
                self.cnf.append([self.get_cell(i, j, k) * -1])
        clause = []
        for [x, y] in self.get_adjacent_neighbors(i, j):
            clause.append(self.get_cell(x, y, color))
        self.cnf.append(clause)
        adjacent_neighbors = self.get_adjacent_neighbors(i, j)
        for idx, [x1, y1] in enumerate(adjacent_neighbors):
            for [x2, y2] in adjacent_neighbors[idx + 1:]:
                self.cnf.append([self.get_cell(x1, y1, color) * -1, self.get_cell(x2, y2, color) * -1])

    def generate_clauses(self):
        for i in range(self.length):
            for j in range(self.length):
                if (i, j) not in self.nodes:
                    self.add_cell_clause(i, j)
                else:
                    self.add_endpoint_clause(i, j, self.nodes.get((i, j))-1)

    def bfs(self, i, j):
        q = queue.Queue()
        q.put([i, j, []])
        while not q.empty():
            curr = q.get()
            if curr[:2] in self.visited:
                return [True, self.output[curr[0]][curr[1]]]
            self.visited.append(curr[:2])
            for k in self.get_adjacent_neighbors(curr[0], curr[1]):
                if self.output[curr[0]][curr[1]] == self.output[k[0]][k[1]] and k != curr[2]:
                    q.put(k[0], k[1], [curr[0], curr[1]])
            return [False]

    def construct_cycle_clauses(self, value):
        for i in range(self.length):
            for j in range(self.length):
                if self.output[i][j] == value:
                    self.clauses.append(self.get_cell(i, j, value-1) * -1)

    def detect_cycles(self):
        self.visited = []
        self.clauses = []
        for i in range(self.length):
            for j in range(self.length):
                if [i, j] not in self.visited:
                    output = self.bfs(i, j)
                    if output[0]:
                        self.construct_cycle_clauses(output[1])
                        return True
        return False

    def construct_table(self, solution):
        self.output.clear()
        for i in range(self.length):
            row = []
            for j in range(self.length):
                for color in range(self.c):
                    if self.get_cell(i, j, color) in solution:
                        row.append(color+1)
            self.output.append(row)

    def solve(self):
        self.generate_clauses()
        solution = pycosat.solve(self.cnf)
        if solution == "UNSAT":
            return solution
        self.construct_table(solution)
        while self.detect_cycles():
            self.cnf.append(self.clauses)
            solution = pycosat.solve(self.cnf)
            if solution == "UNSAT":
                return solution
            self.construct_table(solution)
        return solution

    def print_output(self):
        for row in self.output:
            print(row)


def solve_console():
    try:
        with open(sys.argv[1]) as file:
            nodes = {}
            data = json.load(file)
            for i in data.get("nodes"):
                nodes.update({(i[0], i[1]): i[2]})
            length = data.get("length")
            color = data.get("colors")
            solver = Solver(nodes, color, length)
            solver.solve()
            solver.print_output()
    except FileNotFoundError:
        print("%s: JSON file not found!" % (sys.argv[0]))
        exit(1)


def solve_server(state: dict):
    nodes = {}
    for i in state.get("nodes"):
        nodes.update({(i[0], i[1]): i[2]})
    length = state.get("length")
    color = state.get("colors")
    solver = Solver(nodes, color, length)
    solution = solver.solve()
    return {"nodes": solution}

def main():
    if len(sys.argv) < 3:
        print("%s: specify JSON file" % (sys.argv[0]))
        exit(1)
    solve_console()


if __name__ == '__main__':
    main()
    exit(0)
