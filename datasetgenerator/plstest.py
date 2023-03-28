#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
An efficient code to:

- Check the feasibility of a Partial Latin Square instances
- Test the effectiveness of the NN as a search heuristic

The code is based on a classical PLS model.

Dependencies:

- The code is written for python 2
- The code requires the or-tools, solver, which can be installed with:
    pip2 install ortools
'''

from ortools.constraint_solver import pywrapcp as pycp
import argparse
import math
import gzip
import numpy as np
import tensorflow as tf
import os

cwd = os.getcwd()
import sys
# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, '{}/../'.format(cwd))
from models import MyModel
from datasetgenerator import common, search
from utility import from_one_hot_to_2d

########################################################################################################################


class PLSFormatter:
    def __init__(self, n, frm):
        self.frm = frm
        self.n = n

    def format(self, X):
        return common.format_pls(X, self.n, self.frm)


def read_pls(s, frm):
    # Split the input string and determine the order
    res = {}
    if frm == 'csv': # NOTE not an alternative "if"!
        vals  = s.split(',')
        # Detect the PLS order
        order = math.sqrt(len(vals))
        if order != int(order):
            raise ValueError('Invalid problem order')
        else:
            order = int(order)
        for pos, val in enumerate(vals):
            if int(val) > 0:
                i, j = pos // order, pos % order
                res[i, j] = int(val)
    elif frm in ('bin', 'bits'):
        if frm == 'bin':
            vals = [int(v) for v in s.split(',')]
        else:
            vals = [int(v) for v in s]
        # Detect the PLS order
        order = len(vals)**(1./3)
        if abs(order**3 - len(vals)) >= 1:
            raise ValueError('Invalid problem order')
        else:
            order = int(round(order))
        # Extract the information about the pre-filled cells
        # NOTE tensor dot will use a dot product on the last axis of "tensor"
        tensor = np.asarray(vals, dtype=np.int64)
        tensor = tensor.reshape((order, order, order))
        pls = np.tensordot(tensor, np.arange(1, order+1), axes=1)
        f_i, f_j = np.nonzero(pls) # Indices of nonzero elements
        for i, j, v in zip(f_i, f_j, pls[f_i, f_j]):
            res[i,j] = v
    return order, res


class DNNDecisionBuilder(pycp.PyDecisionBuilder):
    def __init__(self, X, dnn, model_type):
        pycp.PyDecisionBuilder.__init__(self)
        self.X = X
        self.dnn = dnn
        self.n = int(round(math.sqrt(len(X))))
        self.model_type = model_type

    def Next(self, slv):
        # If all variables are bound, the search is over
        if all(x.Bound() for x in self.X):
            return None
        # Obtain a binary representation of the current solution
        n, sol = self.n, []
        for x in self.X:
            val = [0] * n
            if x.Bound():
                val[x.Value()-1] = 1
            sol.extend(val)

        # Query the DNN to obtain var-value pair rankings
        if self.model_type == 'cnn':
            tensor_sol = np.asarray(sol, dtype=np.float32).reshape(-1, n ** 3)
            tensor_sol = from_one_hot_to_2d(tensor_sol)
        elif self.model_type == 'fnn':
            tensor_sol = np.asarray(sol, dtype=np.float32).reshape(1, n ** 3)

        scores = tf.nn.softmax(self.dnn(tensor_sol)).numpy()[0]
        assert scores.shape == (n ** 3,), "Shape is {}".format(scores.shape)

        maxscore = None
        var, val = None, None
        for i, x in enumerate(self.X):

            if not x.Bound():

                vals = []
                probs = []

                # Choose value to be assigned among the feasible ones according to net output probability
                for v in x.DomainIterator():
                    vals.append(v)
                    probs.append(scores[i * n + v - 1])

                # Normalize probabilities
                probs = np.asarray(probs)
                probs /= probs.sum()

                var = x
                val = int(np.random.choice(vals, p=probs))

        # Open a choice point
        return slv.AssignVariableValue(var, val)


class MSDNNDecisionBuilder(pycp.PyDecisionBuilder):
    def __init__(self, X, dnn):
        pycp.PyDecisionBuilder.__init__(self)
        self.X = X
        self.dnn = dnn
        self.n = int(round(math.sqrt(len(X))))

    def Next(self, slv):
        # If all variables are bound, the search is over
        if all(x.Bound() for x in self.X):
            return None
        # Obtain a binary representation of the current solution
        n, sol = self.n, []
        for x in self.X:
            val = [0] * n
            if x.Bound():
                val[x.Value()-1] = 1
            sol.extend(val)

        # Query the DNN to obtain var-value pair rankings
        scores = self.dnn.predict_from_saved_model(np.asarray(sol).reshape(1, 1000), apply_softmax=True)[0]
        assert scores.shape == (1000,), "Shape is {}".format(scores.shape)

        # Choose a variable with the minimum size domain
        best, var, varidx = None, None, None
        for i, x in enumerate(self.X):
            if not x.Bound():
                if best is None or best > x.Size():
                    var, varidx = x, i
                    best = x.Size()

        # Choose value to be assigned among the feasible ones according to net output probability
        var = x

        # Choose the best value predicted by the network
        best, val = None, None
        for v in var.DomainIterator():
            score = scores[varidx * n + v - 1]
            if best is None or score > best:
                best = score
                val = v
        # Open a choice point
        return slv.AssignVariableValue(var, val)

########################################################################################################################


if __name__ == '__main__':
    # Build a command line parser
    desc = 'A testing solver for the PLS problem.'
    parser = argparse.ArgumentParser(description=desc)
    # Configure the parser
    parser.add_argument('infile', nargs='?', default=None,
            help='The name of the file with the instances. If missing, the solver will read from the standard input')
    parser.add_argument('-s', '--seed', type=int, default=100,
            help='Seed for the Random Number Generator')
    parser.add_argument('--input-format',
            choices=['csv', 'bin', 'bits'], default='csv',
            help='Format for the input instances; "csv" will use a comma-separted list of values for PLS rows' +
            ' (a 0 means empty); "bin" will do the same, except that a one-hot encoding of the numbers will be used; ' +
                 'in this case, all zeros will mean an empty cell' + '; "bits" will use a string of 0-1 values to ' +
            'represent the PLS instance')
    parser.add_argument('--output-format',
            choices=['friendly', 'csv', 'bin'], default='friendly',
            help='Format for the output instances; "friendly" will use a matrix of numbers (the Latin Square); "csv" ' +
                 'will use a comma-separted list PLS rows (a 0 means empty); "bin" will do the same, except that a ' +
                 'one-hot encoding of the numbers will be used; in this case, all zeros will mean an empty cell')
    parser.add_argument('--search-strategy',
            choices=['ms', 'rnd', 'snail-lex', 'snail-ms', 'snail-dnn', 'snail-msdnn'],
            default='ms',
            help='Search strategy to be used: "ms" will use a default min size domain heuristic (and lexicographic '
                 'value selection); "snail-lex" will use python-built lexicographic search; "snail-ms" will use a '
                 'python-built min size domain heuristic; "snail-dnn" will use a pyhon-built, DNN driven search')
    parser.add_argument('--dnn-fstem',
            default=None,
            help='File stem for the DNN. This argument is required if the "snail-dnn" search is used')
    parser.add_argument('--print-inst', action='store_true',
            help='Print the instance in csv format (useful for debugging)')
    parser.add_argument('--no-print-sol', action='store_true',
            help='Do not print the solution')
    parser.add_argument('--timeout', type=int, default=0,
            help='Timeout for solving an instance')
    parser.add_argument('--failcap', type=int, default=0,
            help='Fail cap for solving an instance')
    parser.add_argument('--constraint',
                        choices=['none', 'checker', 'checker-v2'], default='none',
                        help='Generate solutions considering the additional constraint')
    parser.add_argument('--size',
                        default=0,
                        help='How many constraint rule indexes to consider')
    parser.add_argument('--rm-rows-constraints', action='store_true',
                        help='Remove rows constraints to the solver')
    parser.add_argument('--rm-columns-constraints', action='store_true',
                        help='Remove columns constraints to the solver')
    parser.add_argument('--max-size', type=int, default=10000,
            help='Maximum number of input solutions to be loaded')
    parser.add_argument('--model', required=True, choices=['fnn', 'cnn'])

    # Parse command line options
    args = parser.parse_args()

    # Define a function to read instance data
    def read(data, frm):
        orders, bmark = [], []
        count = 0
        for rcd in data:
            count += 1
            # print(count)
            # Parse the input instances
            n, prb = read_pls(rcd, frm)
            orders.append(n)
            bmark.append(prb)

            if count == args.max_size:
                break

        return orders, bmark

    # Open the input file and read the input instances
    if args.infile is not None:
        if args.infile.endswith('.gz'):
            with gzip.open(args.infile) as fp:
                orders, bmark = read(fp, args.input_format)
        elif args.infile.endswith('.npz'):
            with np.load(args.infile) as fp:
                data = np.unpackbits(fp['confs'], axis=1)
                orders, bmark = read(data, 'bits')
        else:
            with open(args.infile) as fp:
                orders, bmark = read(fp, args.input_format)
    else:
        orders, bmark = read(sys.stdin, args.input_format)

    # Check that all instances have the same order
    if not all(o == orders[0] for o in orders):
        raise ValueError('Inconsistent order of the n-queen instances')
    n = orders[0]

    # Build a solver
    slv = pycp.Solver('PLS problem tester')

    # Build the variables
    X = {(i,j):slv.IntVar(1, n, 'x_{%d,%d}' % (i,j))
            for i in range(n) for j in range(n)}
    # Build a variable to identify the subproblem number
    K = slv.IntVar(0, len(bmark)-1, 'K')

    add_rows_constraints = not args.rm_rows_constraints
    add_columns_constraints = not args.rm_columns_constraints

    # Post the constraitns
    if add_rows_constraints or add_columns_constraints:
        for i in range(n):
            if add_rows_constraints:
                slv.Add(slv.AllDifferent([X[i,j] for j in range(n)]))
            if add_columns_constraints:
                slv.Add(slv.AllDifferent([X[j,i] for j in range(n)]))

    # Load a DNN, in case the "snail-dnn" search has been requested
    if args.search_strategy in ('snail-dnn', 'snail-msdnn'):
        if args.dnn_fstem is None:
            raise ValueError('Missing file stem for the DNN')

        model = tf.keras.models.load_model(args.dnn_fstem)
        dnn = model

    # Prepare a data structure to store global information abut search
    stats = {}
    # Configure search
    flatX = [X[i,j] for i in range(n) for j in range(n)]

    if args.search_strategy == 'ms':
        db = slv.Phase(flatX, slv.CHOOSE_MIN_SIZE, slv.ASSIGN_MIN_VALUE)
    elif args.search_strategy == 'rnd':
        db = slv.Phase(flatX, slv.CHOOSE_RANDOM, slv.ASSIGN_RANDOM_VALUE)
    elif args.search_strategy == 'snail-lex':
        db = search.SnailLexDecisionBuilder(flatX)
    elif args.search_strategy == 'snail-ms':
        db = search.SnailMinSizeDecisionBuilder(flatX)
    elif args.search_strategy == 'snail-dnn':
        db = DNNDecisionBuilder(flatX, dnn, model_type=args.model)
    elif args.search_strategy == 'snail-msdnn':
        db = MSDNNDecisionBuilder(flatX, dnn)
    # Build a custom decision builder to store a solution and trigger a fail
    frmO = PLSFormatter(n, args.output_format)
    storedb = search.StoreDecisionBuilder(X, frmO, stats,
                                          not args.no_print_sol)
    # Build a DB to control the sequence of subproblems
    seqdb = slv.Phase([K], slv.CHOOSE_FIRST_UNBOUND, slv.ASSIGN_MIN_VALUE)
    # Buid a DB to enforce the pre-assignments of a subproblem
    frmI = None
    if args.print_inst:
        frmI = PLSFormatter(n, 'csv')
    subpdb = search.SubPDecisionBuilder(X, K, bmark, stats, frmI, args.failcap)
    # Build the overall search strategy
    inner_monitors = []
    if args.timeout > 0:
        inner_monitors.append(slv.TimeLimit(1000 * args.timeout))
    if args.failcap > 0:
        inner_monitors.append(slv.FailuresLimit(args.failcap))
    dball = slv.Compose([seqdb,
        slv.SolveOnce(slv.Compose([subpdb, db, storedb]), inner_monitors)])
    # Fake optimization (just to increase K whever a solutio is found)
    monitors = [slv.Maximize(K, 1)]

    # Generate the instances
    slv.ReSeed(args.seed)
    slv.Solve(dball, monitors)