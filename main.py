# Author: Mattia Silvestri

"""
Main program.
"""

import os

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from utility import PLSInstance, PLSSolver, random_assigner
from models import MyModel, PLSCNNModel
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
import csv
import argparse
import time
import pandas as pd

########################################################################################################################

# Set seed in order to reproduce results
tf.random.set_seed(0)

# Tensorflow 2 GPU setup
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    # Restrict TensorFlow to only use the first GPU
    try:
        tf.config.experimental.set_visible_devices(gpus[0], 'GPU')
        tf.config.experimental.set_virtual_device_configuration(
            gpus[0],
            [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=8192)])
        logical_gpus = tf.config.experimental.list_logical_devices('GPU')
        print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPU")
    except RuntimeError as e:
        # Visible devices must be set before GPUs have been initialized
        print(e)

########################################################################################################################

parser = argparse.ArgumentParser()
parser.add_argument("--dim", type=int, default=10, help="Problem dimension")
parser.add_argument("--train", action="store_true",
                    help="Train the model; if not set the default is test mode.", default=False)
parser.add_argument("--test-num", default=None,
                    help="Test identifier.")
parser.add_argument("--num-epochs", default=300, type=int,
                    help="Number of training epochs.")
parser.add_argument("--max-size", default=1000000, type=int,
                    help="Maximum number of training/test instances to be loaded.")
parser.add_argument("--load-mode", default="onehot", choices=["onehot", "string"],
                    help="Dataset loading mode.")
parser.add_argument("--batch-size", default=1024, type=int,
                    help="Mini-batch size.")
parser.add_argument("--leave-columns-domains", action="store_true", default=False,
                    help="True if you don't want to prune columns domains values with forward checking.")
parser.add_argument("--num-sol", type=str, default="10k",
                    help="Number of solutions from which the training set has been generated; thousands are expressed "
                         + "with k (for example 10000=10k).")
parser.add_argument("--model", default="cnn", choices=["fnn", "cnn"],
                    help="Choose the model architecture.")  # TODO: change default
parser.add_argument("--model-type", default="agnostic", choices=["agnostic", "sbrinspiredloss", "negative", "binary"],
                    help="Choose the model type. 'agnostic' is the model-agnostic baseline. 'sbrinspiredloss', "
                         + "'negative' and 'binary' are relatively the mse, negative and binary-cross entropy versions"
                         + " of the SBR inspiredloss.")
parser.add_argument("--validation-size", type=int, default=0,
                    help="Validation set dimension. If zero no validation set is used.")
parser.add_argument("--use-prop", action="store_true", default=False,
                    help="True if you want to assist the estimators with constraints propagation at evaluation time.")
parser.add_argument("--rnd-feas", action="store_true", default=False,
                    help="True if you want to compute feasibility ratio also for random estimator.")
parser.add_argument("--lmbd", default=1.0, type=float, help="Lambda for SBR-inspired term.")
parser.add_argument("--patience", default=10, type=int,
                    help="Specify the number of 10 epochs intervals without improvement in "
                         "feasibility after which training is stopped.")

args = parser.parse_args()

# Problem dimension.
DIM = int(args.dim)

COLUMN_TYPES = [int() for _ in range(DIM ** 3)]

# Set training or test mode.
TRAIN = args.train
if TRAIN:
    print("Training mode")
    mode = "train"
else:
    print("Test mode")
    mode = "test"

# Test number identifier
TEST_NUM = args.test_num

# Number of training epochs
EPOCHS = int(args.num_epochs)

# Maximum number of data set examples to load
MAX_SIZE = int(args.max_size)

# Available loading mode are string and one-hot
LOAD_MODE = args.load_mode

# Mini-batch size
BATCH_SIZE = int(args.batch_size)

# True if you want to adopt SRB-inspired loss function
MODEL_TYPE = args.model_type

if mode == "test":
    mode_char = "L"
else:
    mode_char = "B"

if not TRAIN:
    file_name = "pls{}_10k".format(DIM)
else:
    file_name = "pls{}_{}".format(DIM, args.num_sol)

VAL_SIZE = args.validation_size

NUM_SOL = args.num_sol

# Model name for both training and test
model_name = "test-{}/".format(TEST_NUM)

# Where to save plots
SAVE_PATH = "plots/test-{}/".format(TEST_NUM)
try:
    os.makedirs(SAVE_PATH)
except:
    print("Directory already exists")

# Model name for both training and test
model_name = "test-{}/".format(TEST_NUM)

# Where to save plots
SAVE_PATH = "plots/test-{}/".format(TEST_NUM)
try:
    os.makedirs(SAVE_PATH)
except:
    print("Directory already exists")

########################################################################################################################

# Create a validation set if required
val_indexes = None

if VAL_SIZE > 0:
    print("Loading validation set...")
    start = time.time()
    X_val = pd.read_csv("datasets/pls{}/partial_solutions_{}_train.csv".format(DIM, NUM_SOL),
                        sep=',',
                        header=None,
                        nrows=MAX_SIZE,
                        dtype=np.int8).values

    # Create penalties for the examples
    if MODEL_TYPE != 'agnostic':
        P_val = pd.read_csv("datasets/pls{}/domains_train_{}.csv".format(DIM, NUM_SOL),
                            sep=',',
                            header=None,
                            nrows=MAX_SIZE,
                            dtype=np.int8).values
    else:
        P_val = np.zeros_like(X_val, dtype=np.int8)

    end = time.time()
    print("Elapsed {} seconds".format((end - start)))

    val_indexes = np.random.choice(np.arange(0, X_val.shape[0]), size=VAL_SIZE, replace=False)
    X_val = X_val[val_indexes]
    P_val = P_val[val_indexes]
    validation_set = (X_val, P_val)

# Load training examples
features_filepath = "datasets/pls{}/partial_solutions_{}_{}.csv".format(DIM, NUM_SOL, mode)
print("Loading features from {}...".format(features_filepath))
start = time.time()
X = pd.read_csv(features_filepath, sep=',', header=None, nrows=MAX_SIZE, dtype=np.int8).values
end = time.time()
print("Elapsed {} seconds, {} GB required".format((end - start), X.nbytes / 10 ** 9))
print("Number of rows: {}".format(X.shape[0]))

labels_filepath = "datasets/pls{}/assignments_{}_{}.csv".format(DIM, NUM_SOL, mode)
print("Loading labels from {}...".format(labels_filepath))
start = time.time()
Y = pd.read_csv(labels_filepath, sep=',', header=None, nrows=MAX_SIZE, dtype=np.int32).values
end = time.time()
print("Elapsed {} seconds, {} GB required".format((end - start), Y.nbytes / 10 ** 9))

# Create penalties for the examples
if MODEL_TYPE == 'agnostic' and not args.use_prop:
    P = np.zeros_like(X, dtype=np.int8)
else:
    if not args.leave_columns_domains:
        penalties_filepath = "datasets/pls{}/domains_{}_{}.csv".format(DIM, mode, NUM_SOL)
    else:
        penalties_filepath = "datasets/pls{}/rows_propagation_domains_{}_{}.csv".format(DIM, mode, NUM_SOL)

    print("Loading penalties from {}...".format(penalties_filepath))
    start = time.time()
    P = pd.read_csv(penalties_filepath, sep=',', header=None, nrows=MAX_SIZE, dtype=np.int8).values
end = time.time()
print("Elapsed {} seconds, {} GB required".format((end - start), P.nbytes / 10 ** 9))

# Remove validation samples from the training set
if val_indexes is not None:
    X = np.delete(X, val_indexes, axis=0)
    Y = np.delete(Y, val_indexes, axis=0)
    P = np.delete(P, val_indexes, axis=0)

# Create TF datasets
dataset = tf.data.Dataset.from_tensor_slices((X, Y, P)).shuffle(10000).batch(BATCH_SIZE)

# Create the model
if args.model == "cnn":
    model = PLSCNNModel(num_layers=2,
                        num_hidden=[512, 512],
                        input_shape=X.shape[1:],
                        output_dim=DIM ** 3,
                        method=MODEL_TYPE,
                        lmbd=args.lmbd)
else:
    model = MyModel(num_layers=2,
                    num_hidden=[512, 512],
                    input_shape=X.shape[1:],
                    output_dim=DIM ** 3,
                    method=MODEL_TYPE,
                    lmbd=args.lmbd)

# Train model
if TRAIN:
    history = model.train(EPOCHS,
                          dataset,
                          "models/{}".format(model_name),
                          DIM,
                          validation_set,
                          args.use_prop,
                          args.patience)

    for name in history.keys():
        values = history[name]

        plt.plot(np.arange(0, len(values)), values,
                 label=name)
        plt.ylim(bottom=0)
        plt.legend()
        plt.savefig("{}/{}.png".format(SAVE_PATH, name))
        plt.close()

        with open("{}/{}.csv".format(SAVE_PATH, name), "w") as file:
            wr = csv.writer(file)
            wr.writerow(values)
            file.close()
    exit(0)

else:
    model.model = tf.saved_model.load("models/{}".format(model_name))

################################################################################

# Test the model

# Make predictions
tensor_X = X.astype(np.float32)
predict_val = model.predict_from_saved_model(tensor_X).numpy()

# Prune values according to constraints propagator if required
if args.use_prop:
    predict_val *= (1 - P)

# Count of correct predictions grouped by number of assigned variables
pred_by_num_assigned = np.zeros(shape=(DIM ** 2))
# Count of feasible solutions grouped by number of assigned variables
feas_by_num_assigned = np.zeros(shape=(DIM ** 2))
# Count of total examples grouped by number of assigned variables
tot_by_num_assigned = np.zeros(shape=(DIM ** 2))
# Count of random correct predictions grouped by number of assigned variables
rand_pred_by_num_assigned = np.zeros(shape=(DIM ** 2))
# Count of random feasible solutions grouped by number of assigned variables
rand_feas_by_num_assigned = np.zeros(shape=(DIM ** 2))

# Compute overall accuracy on training set
acc = 0
count = 0
acc_rand = 0

# Compute accuracy grouped by number of assigned variables
preds = []
for x, pred, y, d in zip(X, predict_val, Y, P):

    if count % 1000 == 0:
        print("Examined {} instances".format(count))

    num_assigned_vars = np.sum(x.astype(np.int8))
    pred_label = np.argmax(pred.reshape(-1))
    correct_label = np.argmax(y.reshape(-1))

    if pred_label == correct_label:
        acc += 1
        pred_by_num_assigned[num_assigned_vars] += 1

    # Create a problem instance with current examples for net prediction
    square = np.reshape(x, (DIM, DIM, DIM))
    pls = PLSInstance(n=DIM)
    pls.square = square.copy()
    # assert pls.__check_constraints__(), "Constraints should be verified before assignment"

    # Make the prediction assignment
    assignment = np.argmax(pred)
    assignment = np.unravel_index(assignment, shape=(DIM, DIM, DIM))

    # Local consistency
    local_feas = pls.assign(assignment[0], assignment[1], assignment[2])

    '''vals_square = np.argmax(square, axis=2) + np.sum(square, axis=2)
    solver = utility.PLSSolver(DIM, square=np.reshape(vals_square, -1))
    res = solver.solve()
    assert res, "Constraint solver is wrong because the input comes from a real solution"'''

    # Global consistency
    if local_feas:
        vals_square = np.argmax(pls.square.copy(), axis=2) + np.sum(pls.square.copy(), axis=2)
        solver = PLSSolver(DIM, square=np.reshape(vals_square, -1))
        feas = solver.solve()
    else:
        feas = local_feas

    if feas:
        feas_by_num_assigned[num_assigned_vars] += 1

    # Check random assignment performance if required
    if args.rnd_feas:
        if not args.use_prop:
            d = None
        rand_assignment = random_assigner(DIM ** 3, d)
        if rand_assignment == correct_label:
            acc_rand += 1
            rand_pred_by_num_assigned[num_assigned_vars] += 1

        # Create a problem instance with current training example for random prediction
        square = np.reshape(x, (DIM, DIM, DIM))
        pls = PLSInstance(n=DIM)
        pls.square = square.copy()
        # assert pls.__check_constraints__(), "Constraints should be verified before assignment"

        # Make the random assignment
        rand_assignment = np.unravel_index(rand_assignment, shape=(DIM, DIM, DIM))

        local_feas = pls.assign(rand_assignment[0], rand_assignment[1], rand_assignment[2])

        # Check global consistency
        if local_feas:
            vals_square = np.argmax(pls.square.copy(), axis=2) + np.sum(pls.square.copy(), axis=2)
            solver = PLSSolver(DIM, square=np.reshape(vals_square, -1))
            feas = solver.solve()
        else:
            feas = local_feas

        if feas:
            rand_feas_by_num_assigned[num_assigned_vars] += 1

    # Increase count of solutions with this number of assignments
    tot_by_num_assigned[num_assigned_vars] += 1
    count += 1

    # Save results checkpoint
    if count % 1000 == 0:

        feasibility = list((feas_by_num_assigned / (tot_by_num_assigned + 1e-8))[1:])

        if not args.use_prop:
            filename = "{}/feasibility_{}.csv".format(SAVE_PATH, mode)
        else:
            if args.leave_columns_domains:
                filename = "{}/feasibility_{}_with_row_prop.csv".format(SAVE_PATH, mode)
            else:
                filename = "{}/feasibility_{}_with_full_prop.csv".format(SAVE_PATH, mode)

        with open(filename, "w") as epoch_file:
            wr = csv.writer(epoch_file)
            wr.writerow(feasibility)

# Check accuracy is correctly computed
assert np.sum(pred_by_num_assigned) == acc and np.sum(tot_by_num_assigned) == count, \
    "acc: {} | acc_vectorized: {} | count: {} | count_vectorized: {}".format(acc, np.sum(pred_by_num_assigned),
                                                                             count, np.sum(tot_by_num_assigned))

# Make plots

accuracy = list((pred_by_num_assigned / (tot_by_num_assigned + 1e-8))[1:])
feasibility = list((feas_by_num_assigned / (tot_by_num_assigned + 1e-8))[1:])
if args.rnd_feas:
    random_feasibility = list((rand_feas_by_num_assigned / (tot_by_num_assigned + 1e-8))[1:])

# Save random assigner results
if args.rnd_feas:
    RANDOM_SAVE_PATH = "plots/test-pls-{}-tf-keras/random/".format(DIM)

    if args.use_prop:
        if not args.leave_columns_domains:
            RANDOM_SAVE_PATH += "rows-and-columns-prop"
        else:
            RANDOM_SAVE_PATH += "rows-prop"
    else:
        RANDOM_SAVE_PATH += "no-prop"

    try:
        os.makedirs(RANDOM_SAVE_PATH)
    except:
        print("Directory {} already exists".format(RANDOM_SAVE_PATH))

    with open("{}/random_feasibility.csv".format(RANDOM_SAVE_PATH, mode), "w") as epoch_file:
        wr = csv.writer(epoch_file)
        wr.writerow(random_feasibility)
