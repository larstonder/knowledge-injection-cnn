#@author: Mattia Silvestri

"""
    Utility script with several methods and classes to manage the PLS problem.
"""

import numpy as np
import random
import pandas
import sys
import tensorflow as tf
from ortools.sat.python import cp_model
from datasetgenerator.dataprocessing import state_to_string
import csv
import seaborn as sns
import matplotlib.pyplot as plt
import argparse


class PLSInstance:
    """
    Create an instance of the Partial Latin Square Constrained Problem with n numbers, one-hot encoded as
    an NxNxN numpy array. Each cell of the PLS represents a variable whose i-th bit is raised if number i is assigned.
    """
    def __init__(self, n=10, leave_columns_domains = False):
        # problem dimension
        self.n = n
        # problem instance
        self.square = np.zeros((n, n, n), dtype=np.int8)
        # variables domains
        self.__init_var_domains__()
        self.remove_columns_domains = not leave_columns_domains

    def copy(self):
        """
        Create an instance which is equal to the current one.
        :return: PLSInstance.
        """

        obj = PLSInstance()
        obj.n = self.n
        obj.square = self.square.copy()
        obj.remove_columns_domains = self.remove_columns_domains
        return obj

    def __init_var_domains__(self):
        """
        A method to initialize variables domains to [0, N]
        :return:
        """
        # (n, n) variables; n possible values; the index represents the value; 1 means removed from the domain
        self.domains = np.zeros(shape=(self.n, self.n, self.n), dtype=np.int8)

    def set_square(self, square, forward=False):
        """
        Public method to set the square.
        :param square: the square as numpy array of shape (dim, dim, dim)
        :param forward: True if you want to apply forward checking
        :return: True if the assignement is feasible, False otherwise
        """

        self.square = square
        feas = self.__check_constraints__()
        if feas and forward:
            self.__init_var_domains__()
            self.__forward_checking__()

        return feas

    def __check_constraints__(self):
        """
        Check that all PLS constraints are consistent.
        :return: True if constraints are consistent, False otherwise.
        """
        multiple_var = np.sum(self.square, axis=2)
        rows_fail = np.sum(self.square, axis=1)
        cols_fail = np.sum(self.square, axis=0)

        if np.sum(multiple_var > 1) > 0:
            #print("Multiple variable assignment")
            #exit(1)
            return False

        if np.sum(rows_fail > 1) > 0:
            #print("Unconsistent rows assignment")
            #exit(1)
            return False

        if np.sum(cols_fail > 1) > 0:
            #print("Unconsistent columns assignment")
            #exit(1)
            return False

        return True

    def __check_constraints_type__(self):
        """
        Check that all PLS constraints are consistent.
        :return: a list of three integers, one for each constraint type (multiple assignment, row violation,
        columns violation), representing violiations metric.
        """
        # how many times a value has been assigned to the same variable
        multiple_var = np.sum(self.square, axis=2)
        # how many times a value appears in the same row
        rows_fail = np.sum(self.square, axis=1)
        # how many times a value appears in the same columns
        cols_fail = np.sum(self.square, axis=0)

        constraint_type = [0, 0, 0]

        # how many times there is a multiple or lacking assignment
        constraint_type[0] = np.sum(multiple_var != 1)

        # how many equals values are there in a single row?
        constraint_type[1] = np.sum(rows_fail != 1)

        # how many equals values are there in a single column?
        constraint_type[2] = np.sum(cols_fail != 1)

        return constraint_type

    def get_assigned_variables(self):
        """
        Return indexes of assigned variables.
        :return: a numpy array containing indexes of assigned variables.
        """
        return np.argwhere(np.sum(self.square, axis=2) == 1)

    def __forward_checking__(self):
        """
        Method to update variables domain with forward_checking
        :return:
        """

        for i in range(self.n):
            for j in range(self.n):
                # find assigned value to current variable
                assigned_val = np.argwhere(self.square[i, j] == 1)
                assigned_val = assigned_val.reshape(-1)
                # check if a variable is assigned
                if len(assigned_val) != 0:
                    # current variable is already assigned -> domain is empty
                    self.domains[i, j] = np.ones(shape=(self.n,))
                    # remove assigned value to same row and column variables domains
                    for id_cols in range(self.n):
                        self.domains[i, id_cols, assigned_val] = 1
                    if self.remove_columns_domains:
                        for id_row in range(self.n):
                            self.domains[id_row, j, assigned_val] = 1

    def assign(self, cell_x, cell_y, num):
        """
        Variable assignment.
        :param cell_x: x coordinate of a square cell
        :param cell_y: y coordinate of a square cell
        :param num: value assigned to cell
        :return: True if the assignment is consistent, False otherwise
        """

        # create a temporary variable so that you can undo inconsistent assignment
        tmp_square = self.square.copy()

        if num > self.n-1 or num < 0:
            raise ValueError("Allowed values are in [0,{}]".format(self.n))
        else:
            self.square[cell_x, cell_y, num] += 1

        if not self.__check_constraints__():
            self.square = tmp_square.copy()
            return False

        return True

    def unassign(self, cell_x, cell_y):
        """
        Variable unassignment
        :param cell_x: x coordinate of a square cell
        :param cell_y: y coordinare of a square cell
        :return:
        """

        var = self.square[cell_x, cell_y].copy()
        assigned_val = np.argmax(var)
        self.square[cell_x, cell_y, assigned_val] = 0

    def visualize(self):
        """
        Visualize PLS.
        :return:
        """
        vals_square = np.argmax(self.square, axis=2) + np.sum(self.square, axis=2)

        print(vals_square)

########################################################################################################################


class PLSSolver():
    def __init__(self, board_size, square, specialized=False, size=54, num=1, type="checker"):
        """
        Class to build a PLS solver.
        :param board_size: number of variables
        :param square: numpy array with decimal assigned values
        :param specialized: True if you want to check feasibility on an additional constraint
        :param size: number of constraint indexes to consider
        :param num: forbidden number
        :param type: constraint to add
        """

        self.board_size = board_size

        # create solver
        self.model = cp_model.CpModel()

        # Creates the variables.
        assigned = []
        for i in range(0, board_size ** 2):
            if square[i] > 0:
                assigned.append(self.model.NewIntVar(square[i], square[i], 'x%i' % i))
            else:
                assigned.append(self.model.NewIntVar(1, board_size, 'x%i' % i))

        # Creates the constraints.
        # all numbers in the same row must be different.
        for i in range(0, board_size ** 2, board_size):
            self.model.AddAllDifferent(assigned[i:i+board_size])

        # all numbers in the same column must be different
        for j in range(0, board_size):
            colmuns = []
            for idx in range(j, board_size ** 2, board_size):
                colmuns.append(assigned[idx])

            self.model.AddAllDifferent(colmuns)

        self.vars = assigned.copy()

        # Add eventual additional specializing constraint
        if specialized:

            assert type in ["checker", "checker-v2", "square"], "{} type is not recognized".format(type)

            # find checker indexes
            if type == "checker":
                rule_idxs = __checker_rule__(size)
            elif type == "checker-v2":
                rule_idxs = __checker_rule_v2__(size)
            else:
                rule_idxs = __square_rule__(size)

            # variables in checker positions must be different from num
            for i in rule_idxs:
                self.model.Add(assigned[i] != num)

    def solve(self):
        """
        Find a feasible solution.
        :return: True if a feasible solution was found, 0 otherwise
        """
        # create the solver
        solver = cp_model.CpSolver()
        # set time limit to 30 seconds
        solver.parameters.max_time_in_seconds = 30.0

        # solve the model
        status = solver.Solve(self.model)

        return status == cp_model.FEASIBLE


########################################################################################################################

def visualize(square):
    """
    Visualize PLS.
    :return:
    """
    vals_square = np.argmax(square, axis=2) + np.sum(square, axis=2)

    print(vals_square)

########################################################################################################################


def load_dataset(filename, problem, max_size=10000, mode="onehot", save_domains=False,
                 domains_filename=None, save_partial_solutions=False, partial_sols_filename=None,
                 assignments_filename=None):
    """
    Load solutions from a txt file in the PLS instance.
    :param filename: name of the file; as string
    :param problem: problem instance used to check feasibility; as PLSProblem
    :param max_size: set max_size to prevent saturating the memory; as integer
    :mode: onehot, if you want to load a bit representation of variables; string, if you want to load as string of 0-1; as string
    :param save_domains: True if you want to compute variables domains and save them in a CSV file; as boolean
    :param domains_filename: filename for variables domains; as string
    :param save_partial_solutions: True if you want to save partial solutions in a CSV file; as boolean
    :param partial_sols_filename: filename for partial solutions; as string
    :return: input instances and labels; as numpy array
    """

    assert mode in ["onehot", "string"], "Unsupported mode"

    X = []
    Y = []
    P = []

    with open(filename, mode="r") as file:
        domains_file = None
        if save_domains:
            domains_file = open(domains_filename, "w", newline='')
            csv_writer = csv.writer(domains_file, delimiter=',')
        if save_partial_solutions:
            partial_sols_file = open(partial_sols_filename, "w")
            csv_writer_sols = csv.writer(partial_sols_file, delimiter=',')
            assignments_file = open(assignments_filename, "w") 
            csv_writer_assignments = csv.writer(assignments_file, delimiter=',')

        dim = problem.n

        # count number of solutions
        count = 0

        # each line is the partial assignment and the successive assignment separated by "-" character
        while True and count < max_size:

            line = file.readline()
            if line is None or line is "":
                break

            solutions = line.split("-")

            # first element is the partial assignment, then the assignment
            label = False

            for sol in solutions:
                # temporary problem instance
                tmp_problem = problem.copy()

                # remove end of line
                if "\n" in sol:
                    sol = sol.replace("\n", "")

                # check solution len is dim * dim * dim
                assert len(sol) == dim ** 3, "len is {}".format(len(sol))

                # dim * dim variables of dimension dim
                if mode == "onehot":

                    '''# assigned variables mean character 1
                    assigned_vars = [m.start() for m in re.finditer("1", sol)]
                    assignment = np.zeros(shape=(dim ** 3), dtype=np.int8)
                    assignment[assigned_vars] = 1'''

                    assignment = np.asarray(list(sol), dtype=np.int8)

                    # check feasibility of loaded solutions
                    reshaped_assign = np.reshape(assignment, (dim, dim, dim))
                    if not label:
                        feasible = tmp_problem.set_square(reshaped_assign.copy(), not label and save_domains)
                        assert feasible, "Solution is not feasible"
                    #tmp_problem.visualize()
                    #_ = input("Press to continue...")

                    #assert np.array_equal(assignment.reshape(-1), tmp_problem.square.copy().reshape(-1)), "not equals"

                if not label:
                    if mode == "onehot":
                        X.append(assignment.copy())
                        if save_domains:
                            #P.append(tmp_problem.domains)
                            csv_writer.writerow(tmp_problem.domains.reshape(-1))
                        if save_partial_solutions:
                            csv_writer_sols.writerow(assignment.reshape(-1))
                    else:
                        X.append(sol)

                    # increase solutions counter
                    count += 1
                    if count % 10000 == 0:
                        print("Loaded {} examples".format(count))
                        print(
                            "Memory needed by X:{} | Memory needed by Y: {}".format(sys.getsizeof(X), sys.getsizeof(Y)))
                else:
                    if mode == "onehot":
                        Y.append(assignment.copy())
                        if save_partial_solutions:
                            csv_writer_assignments.writerow([np.argmax(assignment.reshape(-1))])
                    else:
                        Y.append(sol)

                # first element is the partial assignment, then the assignment
                label = True

        file.close()
        if save_domains:
            domains_file.close()
        if save_partial_solutions:
          partial_sols_file.close()

        # check assignment is feasible
        if mode == "onehot":
            prob = PLSInstance()
            for x, y in zip(X, Y):
                square = np.reshape((x + y), (dim, dim, dim))
                assert prob.set_square(square), "Assignment is not feasible"

        # return a numpy array
        X = np.asarray(X)
        Y = np.asarray(Y)
        '''if save_domains:
            P = np.asarray(P, dtype=np.float32)'''

        X = X.reshape(X.shape[0], -1)
        Y = Y.reshape(Y.shape[0], -1)
        '''if save_domains:
            P = P.reshape(P.shape[0], -1)
            np.savetxt(domains_filename, P, delimiter=",", fmt='%0.0f')'''

        print("Memory needed by X:{} | Memory needed by Y: {}".format(sys.getsizeof(X), sys.getsizeof(Y)))

        return X, Y
########################################################################################################################


def __pack_row__(*row):
    return tf.stack(row, 1)

########################################################################################################################


def load_dataset_with_tf(filename, column_types, batch_size):
    ds = tf.data.experimental.CsvDataset(filename, record_defaults=column_types, header=False)
    ds = ds.shuffle(10000, seed=1)
    ds = ds.batch(batch_size).map(__pack_row__)

    return ds


########################################################################################################################

def visualize_dataset(X, Y, exit_end=True):
    """
    Method to visualize partial solutions distributions.
    :param X: training instances
    :param Y: training labels
    :param exit_end: True if you want exit the main after visualization
    :return:
    """

    df = pandas.DataFrame({'partial solution': X[:, 0], 'assignment': Y[:, 0]})
    df_ps = df.groupby('partial solution').count()
    print(df_ps)
    print("Mean: {} | Max: {} | Min: {}".format(df_ps['assignment'].mean(), df_ps['assignment'].max(),
                                                df_ps['assignment'].min()))
    df_as = df.groupby('assignment').count()
    print(df_as)
    print("Mean: {} | Variance: {} | Min: {} | Max: {}".format(df_as['partial solution'].mean(),
                                                               df_as['partial solution'].var(),
                                                               df_as['partial solution'].min(),
                                                               df_as['partial solution'].max()))

    if exit_end:
        exit(0)

########################################################################################################################


def create_empty_board_partial_solutions_file(save_to, max_size=10):
    """
    Create empty board partial solutions csv file which will be used by plstest.py.
    Each row is a partial solution where variable are represented in one-hot encoding and are separated by comma.
    :param save_to: name of the file where partial solutions are saved
    :param max_size: max number of partial solution to save in the file.
    :return:
    """

    count = 0

    empty_board = ['0' for i in range(1000)]

    # csv writer
    with open(save_to, mode="w") as save_file:
        csv_writer = csv.writer(save_file)

        # each line is the partial assignment and the successive assignment separated by "-" character
        while True and count < max_size:

            csv_writer.writerow(empty_board)
            count += 1
            print(count)


########################################################################################################################

def balance_dataset(X, Y, filename):
    """
    Method to pruned the dataset in order to have balanced assignments and write it in a new file.
    :param X: training instances
    :param Y: training labels
    :param filename: filename to which save the so created dataset
    :return:
    """

    df = pandas.DataFrame({'partial solution': X[:, 0], 'assignment': Y[:, 0]})
    df_as = df.groupby('assignment').count()

    min_assigned = df_as['partial solution'].min()

    pruned_X = []
    pruned_Y = []
    count_assignment = {}

    for partial_sol, assign in zip(X[:, 0], Y[:, 0]):
        if assign not in count_assignment.keys():
            count_assignment[assign] = 0
        if count_assignment[assign] < min_assigned:
            pruned_X.append(partial_sol)
            pruned_Y.append(assign)
            count_assignment[assign] += 1

    with open("datasets/pruned_{}".format(filename), "w") as file:
        for x, y in zip(pruned_X, pruned_Y):
            row = '{}-{}\n'.format(x, y)
            file.write(row)

        file.close()

########################################################################################################################


def random_assigner(dim, domains):
    """
    Return a random assignment
    :param dim: one-hot encoding  dimension of the assignment problem
    :param domains: variables' domains coming from forward checking as numpy array of shape (batch_size, 10, 10, 10)
    :return: assigned variable index
    """
    if domains is None:
        return random.randint(0, dim-1)
    else:
        allowed_assignments = np.argwhere(domains == 0)
        idx = random.randint(0, len(allowed_assignments)-1)
        return allowed_assignments[idx]

########################################################################################################################


class VarArraySolutionPrinterWithLimit(cp_model.CpSolverSolutionCallback):
    """Print and save  solutions."""

    def __init__(self, variables, limit):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__solution_count = 0
        self.__solution_limit = limit
        self.solutions = []

    def on_solution_callback(self):
        """
        Invoked each time a solution is found.
        :return:
        """
        self.__solution_count += 1
        sol = np.zeros(shape=(100, ), dtype=np.int8)
        i = 0
        for v in self.__variables:
            sol[i] = self.Value(v)
            i += 1
            #print('%s=%i' % (v, self.Value(v)), end=' ')
        #print("Found {} solutions".format(self.__solution_count))
        if len(self.solutions) >= self.__solution_limit:
            print('Stop search after %i solutions' % self.__solution_limit)
            self.StopSearch()

        if self.solution_count() % 1000 == 0:
            self.solutions.append(sol)
            print(len(self.solutions))

    def solution_count(self):
        """
        Accessor to count of solutions.
        :return:
        """
        return self.__solution_count

########################################################################################################################


def __checker_rule__(size):
    """
    Method to find indexes for checker rule.
    0  8  1  9
    10  2 11  3
     4 12  5 13
    14  6 15  7
    :param size: number of indexed to be considered
    :return: indexes as numpy array
    """
    # checker indexes
    checker_idxs = np.arange(0, 100)
    first_checker_idxs = checker_idxs[(checker_idxs % 2 == ((checker_idxs // 10) % 2))]
    second_checker_idxs = checker_idxs[(checker_idxs % 2 != ((checker_idxs // 10) % 2))]
    checker_idxs = np.append(first_checker_idxs, second_checker_idxs)
    checker_idxs = checker_idxs[0:size]

    return checker_idxs

########################################################################################################################


def __checker_rule_v2__(size):
    """
    Method to find indexes for checker rule.
    Method to find indexes for checker rule version 2.
    Example of checker rule version 2 indexes for 4x4 PLS.
    8  0  9  1
    2 10  3 11
   12  4 13  5
    6 14  7 15
    :param size: number of indexed to be considered
    :return: indexes as numpy array
    """
    # checker indexes
    checker_idxs = np.arange(0, 100)
    second_checker_idxs = checker_idxs[(checker_idxs % 2 == ((checker_idxs // 10) % 2))]
    first_checker_idxs = checker_idxs[(checker_idxs % 2 != ((checker_idxs // 10) % 2))]
    checker_idxs = np.append(first_checker_idxs, second_checker_idxs)
    checker_idxs = checker_idxs[0:size]

    return checker_idxs

########################################################################################################################


def __square_rule__(size):
    """
    Method to find indexes for square rule.
    :param size: number of indexed to be considered
    :return: indexes as numpy array
    """

    # square indexes
    square_idxs = np.arange(0, 100)
    square_idxs = square_idxs.reshape(10, 10)
    square_idxs = square_idxs[:size, :size]
    square_idxs = square_idxs.reshape(-1)

    return square_idxs[:size]

########################################################################################################################


def generate_solutions_by_checker_rule(type, n=10000, board_size=10, size=54, num=1):
    """
    Generate PLS solutions using Google ortools.
    :param type: checker or square rule
    :param n: number of solutions
    :param board_size: size of board for PLS problem
    :param size: number of checker indexes to be considered
    :param num: forbidden number
    :return: solution as list of numpy array of shape (100, )
    """

    assert type in ["checker", "square"], "{} type is not recognized".format(type)

    # create solver
    model = cp_model.CpModel()

    # find checker indexes
    if type == "checker":
        rule_idxs = __checker_rule__(size)
    else:
        rule_idxs = __square_rule__(size)

    # Creates the variables.
    assigned = []
    for i in range(0, board_size ** 2):
        assigned.append(model.NewIntVar(1, board_size, 'x%i' % i))

    # Creates the constraints.
    # all numbers in the same row should be different.
    for i in range(0, board_size ** 2, board_size):
        model.AddAllDifferent(assigned[i:i + board_size])

    # all numbers in the same column should be different
    for j in range(0, board_size):
        colmuns = []
        for idx in range(j, board_size ** 2, board_size):
            colmuns.append(assigned[idx])

        model.AddAllDifferent(colmuns)

    # variables in checker positions must be different from num
    for i in rule_idxs:
        model.Add(assigned[i] != num)


    # Create a solver and solve.
    solver = cp_model.CpSolver()
    solution_printer = VarArraySolutionPrinterWithLimit(assigned.copy(), n)
    status = solver.SearchForAllSolutions(model, solution_printer)
    #print('Status = %s' % solver.StatusName(status))
    #print('Number of solutions found: %i' % solution_printer.solution_count())
    #assert solution_printer.solution_count() <= n

    solutions = solution_printer.solutions
    i = 0
    # check solutions feasibility and transform to one-hot string
    str_solutions = []
    for s in solutions:
        i += 1
        #print("Examined {} solutions".format(i))
        _, counts = np.unique(s, return_counts=True)
        assert len(counts) == 10
        if np.sum(counts == 10) != 10:
            print("CSP-SAT found unfeasible solution")
            print()
            print(counts)
            print()
            print(s.reshape(10, 10))
            exit(1)

        one_hot = from_decimal_to_one_hot(s)
        assert one_hot.shape == (1000, )
        str_solution = state_to_string(one_hot)
        str_solutions.append(str_solution)

    # write solutions in a csv file
    with open("solutions.csv", "w", newline="") as csvfile:
        csv_writer = csv.writer(csvfile)
        for s in str_solutions:
            csv_writer.writerow(s)

    return solutions

########################################################################################################################


def from_decimal_to_one_hot(int_array):
    """
    Convert an array of decimal number to a one-hot encoding.
    :param int_array: array of decimal number to be converted
    :return: numpy array of size 10
    """

    one_hot = np.zeros((int_array.size, int_array.max()), dtype=np.int8)
    one_hot[np.arange(int_array.size), int_array-1] = 1

    return one_hot.reshape(-1)

########################################################################################################################


def read_solutions_from_csv(filename, max_size=10000, constraint=None, size=0, num=1):
    """
    Utility method to read solutions from a csv file.
    :param filename: file path. Solutions are in CSV file where each row is a solution and each column is a
        single variable
    :param max_size: max number of solutions to select
    :param constraint: checker or square
    :param size: indexes size
    :param num: forbidden number
    :return: solutions as list of numpy arrays of shape (10, 10, 10)
    """

    solutions = []
    if constraint == "checker":
        constraint_idxs = __checker_rule__(size)
    else:
        constraint_idxs = __square_rule__(size)

    

    with open(filename, "r") as file:
        csv_reader = csv.reader(file)
        count = 0
        for row in csv_reader:
            square = np.zeros(1000, )
            if count == max_size:
                break
            assigned = [i for i,x in enumerate(row) if x=='1']
            square[assigned] = 1
            
            square = square.reshape((10, 10, 10))
            problem = PLSInstance()
            assert problem.set_square(square), "Solution must be feasible"
            solutions.append(square)
            count += 1

            constraint_satfisfied = True
            square_tmp = square.copy()
            square_tmp = np.argmax(square_tmp, axis=2)
            square_tmp += 1
            square_tmp = square_tmp.reshape(-1).copy()
            for idx in constraint_idxs:
                if square_tmp[idx] == num:
                    constraint_satfisfied = False
                    break

            assert constraint_satfisfied, "{} rule must be satisfied".format(constraint)

        return solutions
########################################################################################################################


def prune_solutions_by_checker_rule(solutions, size=54, num=1):
    """
    Method to select only solution that satisfy the checker rule and save them in a csv file
    :param solutions: solutions as list
    :param size: number of checker indexes to consider
    :param num: forbidden number
    :return:
    """

    checker_idxs = __checker_rule__(size)
    pruned_sols = []

    for sol in solutions:
        decimal_square = np.argmax(sol, axis=2)
        decimal_square = decimal_square.reshape(-1)
        decimal_square += 1
        if np.sum(decimal_square[checker_idxs] == num) == 0:
            pruned_sols.append(sol)

    return pruned_sols


########################################################################################################################


def compute_variance(square):
    """
    Compute single variable variance.
    :param square: Numpy array of shape (?, 100) representing variable assignment in decimal format
    :return: numpy array of shape(100, ) with computed variance for each variable
    """
    return np.var(square, axis=0)

########################################################################################################################


def read_domains_from_csv(filename, max_size=10000):
    """
    Read variables domains from a CSV file.
    :param filename: name of the file from which read the domains; as string
    :param max_size: maximum number of partial assignment domain to be read; as integer
    :return: partial assignment domains; as numpy array
    """

    domains = []

    with open(filename, "r") as file:
        csv_reader = csv.reader(file)
        count = 0
        for row in csv_reader:
            if count == max_size:
                break

            row = np.asarray(row)
            row = row.astype(np.int8)
            domains.append(row)

            if count % 10000 == 0:
                print("Loaded {} domains instances".format(count))
                print("Memory needed by domains:{} ".format(sys.getsizeof(domains)))

            count += 1

        file.close()

    return np.asarray(domains)
########################################################################################################################


def read_solutions_from_csv(filename, dim, max_size=100000):
    """
    Method to read solutions from a csv file and check if it is feasible and which constraints are not satisfied
    :param filename: name of the file from which to read the solutions
    :param dim: problem dimension; as integer
    :param max_size: maximum number of solutions to be loaded
    :return:
    """
    with open(filename, "r") as file:
        csv_reader = csv.reader(file)
        # count of feasible solutions
        count_feasible_sols = 0
        # count single assignment violations
        count_single_assign_violations = 0
        # count of rows constraint violations
        count_rows_violations = 0
        # count of columns constraint violations
        count_columns_violations = 0
        # count of examined solutions
        count_solutions = 0

        for line in csv_reader:
            if len(line) != dim ** 3:
              continue
            assert len(line) == dim**3
            one_hot_sol = [int(c) for c in line]
            one_hot_sol = np.asarray(one_hot_sol)
            num_assigned_vars = np.sum(one_hot_sol)
            reshaped_sol = np.reshape(one_hot_sol, (dim, dim, dim))
            #print("Number of assigned variables: {}".format(np.sum(one_hot_sol)))
            problem = PLSInstance()
            problem.set_square(reshaped_sol.copy())
            #problem.visualize()
            #print()
            constraints_satisfied = problem.__check_constraints_type__()
            count_solutions += 1
            count_single_assign_violations += constraints_satisfied[0]
            count_rows_violations += constraints_satisfied[1]
            count_columns_violations += constraints_satisfied[2]
            if constraints_satisfied[0] == 0 and constraints_satisfied[1] == 0 and constraints_satisfied[2] == 0:
                count_feasible_sols += 1

            if count_solutions == max_size:
                break

        print("Count of feasible solutions: {}".format(count_feasible_sols))
        print("Count of solutions: {}".format(count_solutions))
        print("Count of single variable assignment violations: {}".format(count_single_assign_violations))
        print("Count of rows constraint violations: {}".format(count_rows_violations))
        print("Count of columns constraint violations: {}".format(count_columns_violations))


########################################################################################################################

def compute_solutions_similarity(filename_first_pool, filename_second_pool, filename_comparison_pool):
    """
    Method to read solutions from a csv file and check if it is feasible and which constraints are not satisfied
    :param filename_first_pool: name of the file from which first solutions pool is read
    :param filename_second_pool: name of the file from which second solutions pool is read
    :return:
    """

    comparison_pool = np.zeros(shape=(100, 1000))

    with open(filename_comparison_pool, "r") as file:
        csv_reader = csv.reader(file)

        idx = 0

        for line in csv_reader:
            assert len(line) == 1000
            one_hot_sol = [int(c) for c in line]
            comparison_pool[idx] = np.asarray(one_hot_sol)
            idx += 1
            if idx == 100:
                break
        assert np.sum(np.sum(comparison_pool, axis=1) == 100) == 100

    first_pool = np.zeros(shape=(1000, 1000))

    with open(filename_first_pool, "r") as file:
        csv_reader = csv.reader(file)

        idx = 0

        for line in csv_reader:
            assert len(line) == 1000, line
            one_hot_sol = [int(c) for c in line]
            first_pool[idx] = np.asarray(one_hot_sol)
            idx += 1

    #assert np.sum(np.sum(first_pool, axis=1) == 100) == 100, np.sum(np.sum(first_pool, axis=1) == 100)

    second_pool = np.zeros(shape=(1000, 1000))

    with open(filename_second_pool, "r") as file:
        csv_reader = csv.reader(file)
        idx = 0

        for line in csv_reader:
            assert len(line) == 1000
            one_hot_sol = [int(c) for c in line]
            second_pool[idx] = np.asarray(one_hot_sol)
            idx += 1

    #assert np.sum(np.sum(second_pool, axis=1) == 100) == 100

    similarity_check = np.zeros(shape=(100,))
    count = 0

    for p in comparison_pool:
        # tmp = np.sum(np.abs(p2 - comparison_pool), axis=1)
        tmp = 100 - np.sum(p * comparison_pool, axis=1)
        assert tmp.shape == (100,)
        similarity_check[count] = np.min(tmp)
        count += 1

    assert similarity_check.shape == (100,)
    assert np.sum(similarity_check) == 0

    similarity_first = np.zeros(shape=(100, ))
    similarity_second = np.zeros(shape=(100,))
    count = 0

    for p in comparison_pool:
        #tmp = np.sum(np.abs(p1 - comparison_pool), axis=1)
        tmp = 100 - np.sum(p * first_pool, axis=1)
        assert tmp.shape == (1000, )
        similarity_first[count] = np.min(tmp)

        tmp = 100 - np.sum(p * second_pool, axis=1)
        assert tmp.shape == (1000,)
        similarity_second[count] = np.min(tmp)

        count += 1

    assert similarity_first.shape == (100, )
    assert similarity_second.shape == (100, )

    print("{}: {}".format(filename_first_pool, np.sum(similarity_first)))

    print("{}: {}".format(filename_second_pool, np.sum(similarity_second)))

########################################################################################################################


def compute_feasibility_from_predictions(X, preds, dim):
    """
    Given partial assignments, compute feasibility of network predictions.
    :param X: partial assignment; as numpy array
    :param preds: network predictions; as numpy array
    :param dim: PLS dimension; as integer
    :return:
    """

    feas_count = 0

    for x, pred in zip(X, preds):
        # Create a problem instance with current training example for net prediction
        square = np.reshape(x, (dim, dim, dim))
        pls = PLSInstance(n=dim)
        pls.square = square.copy()
        # assert pls.__check_constraints__(), "Constraints should be verified before assignment"

        # Make the prediction assignment
        assignment = np.argmax(pred)
        assignment = np.unravel_index(assignment, shape=(dim, dim, dim))

        # Local consistency
        local_feas = pls.assign(assignment[0], assignment[1], assignment[2])

        ''' vals_square = np.argmax(square, axis=2) + np.sum(square, axis=2)
        solver = utility.PLSSolver(DIM, square=np.reshape(vals_square, -1))
        res = solver.solve()
        assert res, "Constraint solver is wrong because the input comes from a real solution"'''

        # Global consistency
        if local_feas:
            vals_square = np.argmax(pls.square.copy(), axis=2) + np.sum(pls.square.copy(), axis=2)
            solver = PLSSolver(dim, square=np.reshape(vals_square, -1), specialized=False,
                                       size=0)
            feas = solver.solve()
        else:
            feas = local_feas

        if feas:
            feas_count += 1

    return feas_count / X.shape[0]

########################################################################################################################


def from_penalties_to_confidences(partial_solutions, penalties, labels, confidences):
    """
    Transform penalties to confidence scores.
    :param partial_solutions: an array of shape (size, dim**3) representing the one-hot encoding
    :param penalties: an array of shape (size, dim**3) of 0 and 1, where 1 means provably infeasible value domain;
                        as numpy array.
    :param labels: an array of shape (batch_size, dim**3) with all zeros and a 1, which correspnd to a global feasible
                    assignment; as numpy array
    :param confidences: an array of shape dim**2 where each element represents the feasibility ratio of partial
                        solutions with a number of assigned variables corresponding to the position in the array.
    :return: two numpy arrays, one with confidences scores of shape (size, dim**3) and another one with
                    weights of shape (size, dim**3)
    """

    confidence_scores = np.zeros_like(penalties, dtype=np.float16)
    weights = np.ones_like(confidence_scores, dtype=np.float16)
    count = 0

    for partial_sol, penalty, label in zip(partial_solutions, penalties, labels):
        num_assigned_vars = np.sum(partial_sol)
        assert (0 <= num_assigned_vars <= 99), "Unexpected error: the number of assigned variables must be in the " \
                                               "range [0, 99]"

        m = np.sum(1 - penalty) - 1
        if m == 0:
            m = 1
        n = 1
        confidence_scores[count] = (1 - penalty) * confidences[num_assigned_vars]
        weights[count] = (n + m) / m
        indexes = np.argwhere(penalty == 1)
        weights[count, indexes] = 1

        feas_assign = np.argmax(label)
        confidence_scores[count, feas_assign] = 1
        weights[count, feas_assign] = (n + m) / n

        '''print('-------------------- Partial solution -------------------------')
        visualize(partial_sol.reshape(10, 10, 10))
        print()
        print('-------------------- Label -------------------------')
        visualize(label.reshape(10, 10, 10))
        print()
        print('-------------------- Confidences -------------------------')
        for i in range(10):
            for j in range(10):
                print(confidence_scores[count].reshape(10, 10, 10)[i, j])
            print()
        print('------------------------ Weights -----------------------------------')
        for i in range(10):
            for j in range(10):
                print(weights[count].reshape(10, 10, 10)[i, j])
            print()
        print('------------------------------------------------------------------')'''

        count += 1

    return confidence_scores, weights

########################################################################################################################


def make_subplots(nested_path, n_subplots, labels, titles, pls_sizes=[7, 10, 12]):
    sns.set_style('darkgrid')
    linestyles = ['solid', 'solid', 'dotted', 'dashed', 'dashdot', (0, (3, 1, 1, 1, 1, 1)), (0, (5, 10))]
    assert len(nested_path) == n_subplots
    plt.rcParams["figure.figsize"] = (20, 15)
    fig, axis = plt.subplots(1, n_subplots, sharey=True)
    fig.text(0.5, 0.04, '# of filled cells', ha='center', fontsize=16, fontweight='bold')
    fig.text(0.07, 0.5, 'Feasibility ratio', va='center', rotation='vertical', fontsize=16, fontweight='bold')
    subplots = [*axis]
    for subp_idx, (paths, subp) in enumerate(zip(nested_path, subplots)):
        ax = subplots[subp_idx]
        ax.set_xlim(0, pls_sizes[subp_idx]**2)
        ax.set_ylim(0, 1.1)
        ticks = np.arange(0, pls_sizes[subp_idx]**2, pls_sizes[subp_idx]*2)
        assert len(paths) <= len(linestyles), 'Max {} curves can be plotted in the same subplot'.format(len(linestyles))
        ax.set_xticks(ticks)
        ax.tick_params(labelsize=14)
        for path_idx, path in enumerate(paths):
            feasibilities = np.genfromtxt(path, delimiter=',')
            ax.plot(np.arange(len(feasibilities)), feasibilities, linestyle=linestyles[path_idx])
        if subp_idx == 0:
            ax.legend(labels, fontsize=16, loc='lower left')

        ax.set_title(titles[subp_idx], fontweight='bold', fontsize='18')
    plt.show()

########################################################################################################################


if __name__ == '__main__':
    read_solutions_from_csv(filename='solutions/pls12/model_agnostic_100k-sols_no_prop.csv', dim=12, max_size=100000)
    print()
    read_solutions_from_csv(filename='solutions/pls12/sbr_full_all_ts_no_prop.csv', dim=12, max_size=100000)
    print()
    read_solutions_from_csv(filename='solutions/pls12/sbr_full_100k-sols_no_prop.csv', dim=12, max_size=100000)
    exit()

    nested_path = [['plots/test-pls-7-tf-keras/random/rows-prop/random_feasibility.csv',
                    'plots/test-pls-7-tf-keras/random/rows-and-columns-prop/random_feasibility.csv',
                    'plots/test-pls-7-tf-keras/model-agnostic/100-sols/run-1/feasibility_test.csv',
                    'plots/test-pls-7-tf-keras/sbr-inspired-loss/100-sols/rows/run-1/feasibility_test.csv',
                    'plots/test-pls-7-tf-keras/sbr-inspired-loss/100-sols/full/run-1/feasibility_test.csv'
                    ],
                   ['plots/test-pls-10-tf-keras/random/rows-prop/random_feasibility.csv',
                    'plots/test-pls-10-tf-keras/random/rows-and-columns-prop/random_feasibility.csv',
                    'plots/test-pls-10-tf-keras/model-agnostic/100-sols/run-1/feasibility_test.csv',
                    'plots/test-pls-10-tf-keras/sbr-inspired-loss/100-sols/rows/run-1/feasibility_test.csv',
                    'plots/test-pls-10-tf-keras/sbr-inspired-loss/100-sols/full/run-1/feasibility_test.csv'
                    ],
                   ['plots/test-pls-12-tf-keras/random/rows-prop/random_feasibility.csv',
                    'plots/test-pls-12-tf-keras/random/rows-and-columns-prop/random_feasibility.csv',
                    'plots/test-pls-12-tf-keras/model-agnostic/100-sols/run-1/feasibility_test.csv',
                    'plots/test-pls-12-tf-keras/sbr-inspired-loss/100-sols/rows/run-1/feasibility_test.csv',
                    'plots/test-pls-12-tf-keras/sbr-inspired-loss/100-sols/full/run-1/feasibility_test.csv'
                    ]]

    labels = ['rnd-rows', 'rnd-full', 'agn', 'mse-rows', 'mse-full']
    titles = ['PLS-7', 'PLS-10', 'PLS-12']

    make_subplots(nested_path, n_subplots=3, labels=labels, titles=titles, pls_sizes=[7, 10, 12])

