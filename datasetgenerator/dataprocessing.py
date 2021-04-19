# -*- coding: utf-8 -*-
"""
Created on Fri Dec 09 19:17:01 2016

@author: Andrea Galassi
"""

import numpy
import csv
import random
import sys
import argparse


# carica il dataset da un file
def load_dataset(filename):
    
    # carico il dataset
    dataset_file = open(filename, 'r')
    dataset_list = dataset_file.read().splitlines()

    states = []
    moves = []
    
    init_len = len (dataset_list)
    
    size3 = (len(dataset_list[0])-1)/2
    size1 = int(round(numpy.cbrt(size3)))
    size2 = size1 * size1

    perc = 100

    # ogni linea del file è una coppia stato-mossa
    while len(dataset_list)>0:
        
        act_len = len(dataset_list)
        
        act_perc = act_len*100/init_len
        if (act_perc<perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))
        
        line = dataset_list.pop()
        state, move = process_dataset_line(line, size1)

        states.append(state)
        moves.append(move)

    dataset_file.close()

    return states, moves


def process_dataset_line(line, num):
    numcubo = num * num * num
    input_state = ['0'] * (numcubo)
    output_state = ['0'] * (numcubo)
    
    for j in range(0, numcubo):
        input_state[j] = line[j]
        output_state[j] = line[j+numcubo+1]

    return input_state, output_state


def load_test_dataset(filename, num):
    
    # carico il dataset
    dataset_file = open(filename, 'r')
    dataset_list = dataset_file.read().splitlines()

    states = []
    
    size3 = (len(dataset_list[0])-1)/2
    size1 = int(round(numpy.cbrt(size3)))
    size2 = size1 * size1

    # ogni linea del file è una coppia stato-mossa
    for line in dataset_list:
        state = process_test_dataset_line(line, size1)

        states.append(state)

    dataset_file.close()

    return states


def process_test_dataset_line(line, num):
    
    statedim = num * num * num
    
    """
    input_state = ['0'] * (statedim)

    for j in range(0, statedim):
        input_state[j] = line[j]
    """
    input_state = ""

    for j in range(0, statedim):
        input_state += line[j]

    return input_state


def process_state_binary(states):
    
    perc = 100
    length = len(states)
    statedim = len (states[0])

    ps = numpy.zeros((length, statedim), dtype="uint8")
    
    i = 0
    while len(states)>0:
        
        act_len = len(states)
        
        act_perc = act_len*100/length
        if (act_perc<perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))
        
        state = states.pop()
    
        for j in range(0, statedim):
            if(state[j] == '1' or state[j] == 1):
                ps[i][j] = 1
            else:
                ps[i][j] = 0            
        i += 1
        
    return ps


def process_state_and_filter_binary(states, size):
    perc = 100
    length = len(states)
    statedim = len(states[0])

    ps = numpy.zeros((length, statedim), dtype="uint8")
    filters = numpy.ones((length, statedim), dtype="uint8")

    i = 0
    while len(states) > 0:

        act_len = len(states)

        act_perc = act_len * 100 / length
        if (act_perc < perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))

        state = states.pop()

        assigned = False
        for j in range(0, statedim):
            if (state[j] == '1' or state[j] == 1):
                ps[i][j] = 1
                assigned = True
            else:
                ps[i][j] = 0

            # end of last variable bits
            if (j + 1) % size == 0:
                if assigned:
                    filters[i][j - size + 1:j + 1] = 0

                assigned = False
        i += 1

    return ps


def process_state_binary_without_pop(states):
    
    perc = 100
    length = len(states)
    statedim = len (states[0])

    ps = numpy.zeros((length, statedim), dtype="uint8")
    
    i = 0
    for state in states:
        
        act_len = len(states)
        
        act_perc = act_len*100/length
        if (act_perc<perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))
    
        for j in range(0, statedim):
            if(state[j] == '1' or state[j] == 1):
                ps[i][j] = 1
            else:
                ps[i][j] = 0            
        i += 1
        
    return ps


def process_state_and_filter_binary_without_pop(states, size):
    perc = 100
    length = len(states)
    statedim = len(states[0])

    ps = numpy.zeros((length, statedim), dtype="uint8")
    filters = numpy.ones((length, statedim), dtype="uint8")

    i = 0
    for state in states:

        act_len = len(states)

        act_perc = act_len * 100 / length
        if (act_perc < perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))

        assigned = False
        for j in range(0, statedim):

            if (state[j] == '1' or state[j] == 1):
                ps[i][j] = 1
                assigned = True
            else:
                ps[i][j] = 0

            # end of last variable bits
            if (j+1) % size == 0:
                if assigned:
                    filters[i][j-size+1:j+1] = 0

                assigned = False

        i += 1

    return ps, filters


def process_target_binary(targets):
    length = len(targets)
    ps = numpy.zeros((length), dtype="uint8")
    
    i = 0
    perc = 100
    
    while len(targets)>0:
        
        act_len = len(targets)
        act_perc = act_len*100/length
        if (act_perc<perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))
        
        target = targets.pop()
        
        j = 0
        while(target[j]=='0' or target[j] == 0):
            j += 1
        ps[i] = j
        i += 1

    return ps


def process_target_collapsed_prob(targets):
    perc = 100 
    length = len(targets)
    
    # if there are no data
    length2 = 0
    
    if length > 0:
        length2 = len(targets[0])
        
    ps = numpy.zeros((length, length2), dtype="float32")
    
    i = 0
    while len(targets)>0:
        
        act_len = len(targets)
        act_perc = act_len*100/length
        if (act_perc<perc):
            perc = act_perc
            print("\tStill remaining: " + str(act_perc) + "%: " + str(act_len))
            
            
        target = targets.pop()
        
        j = 0
        for element in target:
            if element == '1' or element == 1:
                j += 1
        num = 1.0/(j*1.0)
        
        j = 0
        for element in target:
            if element == '1' or element == 1:
                ps[i][j] = num
            j += 1
        i += 1

    return ps


def state_to_matrix(state, num):
    
    matrix = numpy.zeros((num, num, num), dtype="uint8")
    
    for i in range(num*num):
        if state[i] == '1':
            row = i / (num * num)
            column = i / num % num
            color = i % (num * num)
            matrix[row][column] = color
            
    return matrix


def state_to_matrix_set(state, num):
    
    matrix = [[set() for x in range(num)] for x in range(num)]
    
    for i in range(num):
        for j in range(num):
            for k in range(num):
                if state[i*num*num+j*num+k] == '1':
                    matrix[i][j].add(k)
            
    return matrix

def matrix_set_to_string(matrix, num):
    stringa = ""
    for i in range(num):
        for j in range(num):
            values = matrix[i][j]
            for value in values:
                stringa += str(value) + ","
            stringa += "\t"
        stringa += "\n"
    return stringa

# matrix utils
def printmatrix(matrix, num=8):
    stringa = ""
    for i in range (num):
        for j in range (num):
            stringa+=str(matrix[i][j])+" "
        stringa+="\n"
    print (stringa)


def state_to_string(state):
    stringa = ""
    for el in state:
        stringa+=str(el)
    return stringa


def string_to_state(string):
    state = []
    for car in string:
        if car == '0':
            state.append(0)
        else:
            state.append(1)
    return state


def make_move(state, choice):
    size = len(state)
    line = ""
    for i in range (size):
        if i == choice:
            line+="1"
        else:
            line+=str(state[i])
    return line


def create_dataset_A(filename, ratio, solution_num):
    sol_file = open(filename + ".csv", 'r')
    reader = csv.reader(sol_file)

    test_sol_file = open("DS.PLS.A.SOL.B." + str(ratio) +
                         "." + filename + ".txt", 'w')
    train_sol_file = open("DS.PLS.A.SOL.L." + str(ratio) +
                     "." + filename + ".txt", 'w')
    
    stat_file = open("DS.PLS.A.STAT." + str(ratio) +
                     "." + filename + ".txt", 'w')

    solutions = set()

    count_sol = 0
    
    # read all the solutions    
    for row in reader:
        solutions.add(state_to_string(row))
        count_sol += 1
        if count_sol >= solution_num:
            break
    
    # find the sizes of the problem
    row = solutions.pop()
    solutions.add(row)
    size3 = len(row)
    size1 = int(round(numpy.cbrt(size3)))
    size2 = size1 * size1
    
    # split between test and train solutions
    train_solutions = set()
    test_solutions = set()
    
    for solution in solutions:
        if ratio > 1:
            num = random.randint(1,ratio)
        elif ratio == 1:
            num = 1
        else:
            num = 0
        
        if num == 1:
            train_solutions.add(solution)
            train_sol_file.write(solution + "\n")
        else:
            test_solutions.add(solution)
            test_sol_file.write(solution + "\n")

    te_len = len (test_solutions)
    tr_len = len (train_solutions)
    tot_len = len (solutions)
    stringa = ("TOT: " + str(tot_len) +
               "; TEST: " + str(te_len) +
               ";TRAIN: " + str(tr_len))
    solutions.clear()
    
    print(stringa)
    stat_file.write(stringa + "\n")
    
    test_sol_file.close()
    train_sol_file.close()

    # compute subsolutions
    if te_len>0:
        print("Computing test subsolutions")
        sub, sub_coll = create_subsolutions(test_solutions, size1, collapsed=False)
        
        print("Test subsolutions created")
        
        # write the files
        m_file = open("DS.PLS.A.MULTIPLE.B." + str(ratio) +
                      "." + filename + ".txt", 'w')
        '''c_file = open("DS.PLS.A.COLLAPSED.B." + str(ratio) +
                              "." + filename + ".txt", 'w')'''
        '''u_file = open("DS.PLS.A.UNIQUES.B." + str(ratio) +
                            "." + filename + ".txt", 'w')'''

        '''multi_label_file = open("DS.PLS.A.MULTILABEL.B." + str(ratio) +
                      "." + filename + ".txt", 'w')'''

        
        sum_te = 0
        min_te = 1000
        max_te = -100
        te_sub_tot = 0

        count = 1
        
        for subsolution in sub.keys():

            # multi_labels_target = numpy.zeros(shape=(1000,), dtype=int)

            for target in sub[subsolution]:
                m_file.write(subsolution + "-" + state_to_string(target)
                + "\n")
                te_sub_tot += 1

                # target_as_np_array = numpy.asarray(list(target), dtype=int)
                # multi_labels_target += target_as_np_array

            # multi_labels_target = numpy.clip(multi_labels_target, 0, 1)
            # how_many = numpy.sum(multi_labels_target)

            ''' multi_label_file.write(subsolution + "-" + state_to_string(multi_labels_target)
                + "\n") '''
                
            num_targets = len(sub[subsolution])
            num = random.randint(0,num_targets-1)
            targets = list(sub[subsolution])
            target = targets[num]
            '''u_file.write(subsolution + "-" + state_to_string(target)
                + "\n")'''
            
            sum_te += num_targets
            if num_targets < min_te:
                min_te = num_targets
            
            if num_targets > max_te:
                max_te = num_targets

            if count % 1000 == 0:
                print("Examined subsolutions: {}/{}".format(count, len(sub.keys())))
            count += 1
        
        '''for subsolution in sub_coll.keys():
            c_file.write(subsolution + "-" +
                         state_to_string(sub_coll[subsolution]) + "\n")'''

        # u_file.close()
        #c_file.close()
        m_file.close()
    
        te_sub_len = len(sub.keys())
        avg_te = sum_te*1.0/te_sub_len
        stringa = ("TEST:" +
                   "\tSub_tot:\t" + str(te_sub_tot) +
                   "\tSub:\t" + str(te_sub_len) +
                   "\tAvg_t:\t" + str(round(avg_te,2)) +
                   "\tMin_t:\t" + str(min_te) +
                   "\tMax_t:\t" + str(max_te))
        print(stringa)
        stat_file.write(stringa + "\n")

    test_solutions.clear()
    sub.clear()

    if tr_len>0:
        print("Computing train subsolutions")
        sub, sub_coll = create_subsolutions(train_solutions, size1, collapsed=False)
        
        print("Train subsolutions created")
        
        # write the files
        '''c_file = open("DS.PLS.A.COLLAPSED.L." + str(ratio) +
                             "." + filename + ".txt", 'w')'''
        '''u_file = open("DS.PLS.A.UNIQUES.L." + str(ratio) +
                             "." + filename + ".txt", 'w')'''
        m_file = open("DS.PLS.A.MULTIPLE.L." + str(ratio) +
                             "." + filename + ".txt", 'w')
        
        sum_tr = 0
        min_tr = 1000
        max_tr = -100
        tr_sub_tot = 0

        if count % 1000 == 0:
            print("Examined subsolutions: {}/{}".format(count, len(subsolution)))
        count += 1

        for subsolution in sub.keys():
            for target in sub[subsolution]:
                m_file.write(subsolution + "-" + state_to_string(target)
                + "\n")
                tr_sub_tot += 1
                
            num_targets = len(sub[subsolution])
            num = random.randint(0,num_targets-1)
            targets = list(sub[subsolution])
            target = targets[num]
            '''u_file.write(subsolution + "-" + state_to_string(target)
                + "\n")'''
            
            sum_tr += num_targets
            if num_targets < min_tr:
                min_tr = num_targets
            
            if num_targets > max_tr:
                max_tr = num_targets
        
        for subsolution in sub_coll.keys():
            '''c_file.write(subsolution + "-" +
                         state_to_string(sub_coll[subsolution]) + "\n")'''
    
        #u_file.close()
        #c_file.close()
        m_file.close()
    
        tr_sub_len = len(sub.keys())
    
        avg_tr = sum_tr*1.0/tr_sub_len
        stringa = ("TRAIN:" +
                   "\tSub_tot:\t" + str(tr_sub_tot) +
                   "\tSub:\t" + str(tr_sub_len) +
                   "\tAvg_t:\t" + str(round(avg_tr,2)) +
                   "\tMin_t:\t" + str(min_tr) +
                   "\tMax_t:\t" + str(max_tr))
        print(stringa)
        stat_file.write(stringa + "\n")

    stat_file.write("\n_______________\n\n")
    stat_file.close()



def create_dataset_C(filename, ratio):
    sol_file = open(filename + ".csv", 'r')
    reader = csv.reader(sol_file)
    
    stat_file = open("DS.PLS.C.STAT." + str(ratio) +
                     "." + filename + ".txt", 'w')

    solutions = set()

    
    # read all the solutions    
    for row in reader:
        solutions.add(state_to_string(row))
    
    # find the sizes of the problem
    row = solutions.pop()
    solutions.add(row)
    size3 = len(row)
    size1 = int(round(numpy.cbrt(size3)))
    size2 = size1 * size1
    
    num = len(solutions)
    
    stringa = ("SOLUTIONS: " + str(num))

    print(stringa)
    stat_file.write(stringa + "\n")
    
    # write the files
    c_file_te = open("DS.PLS.C.COLLAPSED.B." + str(ratio) +
                         "." + filename + ".txt", 'w')
    u_file_te = open("DS.PLS.C.UNIQUES.B." + str(ratio) +
                         "." + filename + ".txt", 'w')
    m_file_te = open("DS.PLS.C.MULTIPLE.B." + str(ratio) +
                             "." + filename + ".txt", 'w')
    
    # write the files
    c_file_tr = open("DS.PLS.C.COLLAPSED.L." + str(ratio) +
                         "." + filename + ".txt", 'w')
    u_file_tr = open("DS.PLS.C.UNIQUES.L." + str(ratio) +
                         "." + filename + ".txt", 'w')
    m_file_tr = open("DS.PLS.C.MULTIPLE.L." + str(ratio) +
                             "." + filename + ".txt", 'w')
        
    sum_te = 0
    min_te = 1000
    max_te = -100
    te_sub_tot = 0
    te_sub_len = 0
    
    sum_tr = 0
    min_tr = 1000
    max_tr = -100
    tr_sub_tot = 0
    tr_sub_len = 0
    
    # elaborate subsolutions
    print("Computing subsolutions")
    sub, sub_coll = create_subsolutions(solutions, size1, False)
        
    print("Subsolutions created. Processing and dividing...")
    
    i = 0
    perc = 0
    lensol = len(sub.keys())
    
    for subsolution in sub.keys():
        
        
        i += 1
        if (i*100/lensol>perc):
            perc=i*100/lensol
            print("\t" + str(i) + "/" + str(lensol) + ":" + str(perc) + "%")
        
        
        train_temp = []
        test_temp = []
        
        # each subsolution has to go in training or in test
        for target in sub[subsolution]:
            if ratio > 1:
                num = random.randint(1,ratio)
            elif ratio == 1:
                num = 1
            else:
                num = 0
            # training
            if num == 1:
                m_file_tr.write(subsolution + "-" + state_to_string(target) 
                + "\n")
                tr_sub_tot += 1
                train_temp.append(state_to_string(target))
            # test
            else:
                m_file_te.write(subsolution + "-" + state_to_string(target) 
                + "\n")
                te_sub_tot += 1
                test_temp.append(state_to_string(target))
        
        
        num_targets_te = len(test_temp)
        num_targets_tr = len(train_temp)
        
        # compute statistics
        if num_targets_te > 0:
            num = random.randint(0,num_targets_te-1)
            target = test_temp[num]
            u_file_te.write(subsolution + "-" + state_to_string(target) 
                    + "\n")
            
            sum_te += num_targets_te
            if num_targets_te < min_te:
                min_te = num_targets_te
            
            if num_targets_te > max_te:
                max_te = num_targets_te
            
            te_sub_len += 1
            
            # create collapsed
            collapsed = ['0'] * size3
            for target in test_temp:
                index = target.index('1')
                collapsed[index] = '1'
            c_file_te.write(subsolution + "-" + state_to_string(collapsed) 
                    + "\n")
        
        
        
        # compute statistics
        if num_targets_tr > 0:
            num = random.randint(0,num_targets_tr-1)
            target = train_temp[num]
            u_file_tr.write(subsolution + "-" + state_to_string(target) 
                    + "\n")
            
            sum_tr += num_targets_tr
            if num_targets_tr < min_tr:
                min_tr = num_targets_tr
            
            if num_targets_tr > max_tr:
                max_tr = num_targets_tr
            
            tr_sub_len += 1
            
            # create collapsed
            collapsed = ['0'] * size3
            for target in train_temp:
                index = target.index('1')
                collapsed[index] = '1'
            c_file_tr.write(subsolution + "-" + state_to_string(collapsed)
                    + "\n")
    
    if te_sub_len > 0:
        avg_te = sum_te*1.0/te_sub_len
        stringa = ("TEST:" +
                   "\tSub_tot:\t" + str(te_sub_tot) +
                   "\tSub:\t" + str(te_sub_len) +
                   "\tAvg_t:\t" + str(round(avg_te,2)) +
                   "\tMin_t:\t" + str(min_te) +
                   "\tMax_t:\t" + str(max_te))
        print(stringa)
        stat_file.write(stringa + "\n")
    
    if tr_sub_len > 0:
        avg_tr = sum_tr*1.0/tr_sub_len
        stringa = ("TRAIN:" +
                   "\tSub_tot:\t" + str(tr_sub_tot) +
                   "\tSub:\t" + str(tr_sub_len) +
                   "\tAvg_t:\t" + str(round(avg_tr,2)) +
                   "\tMin_t:\t" + str(min_tr) +
                   "\tMax_t:\t" + str(max_tr))
        print(stringa)
        stat_file.write(stringa + "\n")

    u_file_te.close()
    c_file_te.close()
    m_file_te.close()
    u_file_tr.close()
    c_file_tr.close()
    m_file_tr.close()

    stat_file.write("\n_______________\n\n")
    stat_file.close()


def create_subsolutions(solutions, size1, collapsed=False):
    
    subsolutions = dict()
    subsolutions_coll = dict()

    size2 = size1 * size1
    size3 = size1 * size2
    
    i = 0
    perc = 0
    
    lensol = len(solutions)

    for i in range(100):
    
        for solution in solutions:

            i += 1
            if (i*100/lensol>perc):
                perc=i*100/lensol
                print("\t" + str(i) + "/" + str(lensol) + ":" + str(perc) + "%")

            subsol = string_to_state(solution)

            for step in range(size2, 0, -1):

                num = random.randint(0,step-1)
                count = 0
                index = 0
                for position in subsol:
                    if position == 1:
                        count += 1
                    if count <= num:
                        index += 1
                subsol[index] = 0

                stateline =""
                targetline = ""

                for index_2 in range(len(subsol)):
                    if index_2 == index:
                        targetline += "1"
                    else:
                        targetline += "0"
                    stateline += str(subsol[index_2])

                if not stateline in subsolutions.keys():
                    subsolutions[stateline] = set()
                    if collapsed:
                        subsolutions_coll[stateline] = ['0'] * size3
                subsolutions[stateline].add(targetline)
                if collapsed:
                    subsolutions_coll[stateline][index] = '1'

    return subsolutions, subsolutions_coll

    
def create_mask(data, size=10):
    """
    data: the input array
    size: the size of the problem, which is the number of possible varible values
    """
    size3 = len(data)
    mask = [1] * size3
    
    assigned = False
    for j in range(0, size3):
        if line[j] == '1' or line[j] == 1:
            assigned = True

        # when the size1 cell is reached (every possible variable values)
        # if it has been assigned, the mask is set
        # in any case, the assignment flag is set back to false
        # for the new variable
        if (j + 1) % size1 == 0:
            if assigned :
                for k in range(j-size1+1, j+1):
                    mask[k] = 0
            assigned = False
            
    return mask


def create_masks(data, size=10):
    """
    data: the input array
    size: the size of the problem, which is the number of possible varible values
    """
    batch_size = len(data)
    size3 = len(data[0])
    masks = [[1] * size3] * batch_size
    
    for i in range(0, batch_size):
        line = data[i]
        assigned = False
        for j in range(0, size3):
            if line[j] == '1' or line[j] == 1:
                assigned = True

            # when the size1 cell is reached (every possible variable values)
            # if it has been assigned, the mask is set
            # in any case, the assignment flag is set back to false
            # for the new variable
            if (j + 1) % size == 0:
                if assigned :
                    for k in range(j-size+1, j+1):
                        masks[i][k] = 0
                assigned = False
            
    return masks
    

"""
num = 8;
matrix = [[0 for x in range(num)] for y in range(num)] 

col = 2
row = 4

diff = col - row

for i in range(num):
  
  if (i+diff) >= 0 and (i+diff) < num :
    matrix[i][i+diff]=3
  
  if (num-i+diff) >= 0 and (num-i+diff) < num:
    matrix[i][num-i+diff]=2

matrix[row][col]=1
printmatrix(matrix)
"""

########################################################################################################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Random deconstruction')
    parser.add_argument('-n', '--name', type=str, required=True,
                        help='Deconstructed solutions file name')
    parser.add_argument('-r', '--ratio', type=int, default=4,
                        help='Split ratio between training and test set')
    parser.add_argument('--sol-num', type=int, default=10000,
                        help='Number of solution loaded from file')

    # Parse command line options
    args = parser.parse_args()
    filename = args.name
    ratio = args.ratio
    sol_num = args.sol_num

    create_dataset_A(filename, ratio, sol_num)
