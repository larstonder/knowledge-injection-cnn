# @Author: Mattia Silvestri

"""
    Utility script to visualize multiple histograms in the same plot.
"""

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

########################################################################################################################


def autolabel(rects, ax):
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        '''ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')'''
########################################################################################################################à

def make_bars(ax, title, rnd, agn, sbr):
    labels = ['Rows', 'Columns']
    x = np.arange(len(labels))  # the label locations
    width = 0.1  # the width of the bars

    rects1 = ax.bar(x - width, rnd, width, label='rnd')
    rects2 = ax.bar(x, agn, width, label='agn')
    rects3 = ax.bar(x + width, sbr, width, label='sbr')
    autolabel(rects1, ax)
    autolabel(rects2, ax)
    autolabel(rects3, ax)
    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_title(title, fontweight='bold', fontsize='18')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.tick_params(labelsize=14)
    ax.legend(loc='lower center', fontsize=16)

########################################################################################################################


sns.set_style('dark')
plt.rcParams["figure.figsize"] = (15, 7)
fig, (ax1, ax2, ax3) = plt.subplots(1, 3)
pls7 = np.asarray([[0, 0], [10002, 10378], [2056, 2030]])
pls10 = np.asarray([[0, 0], [26035, 26.987], [3948, 3852]])
pls12 = np.asarray([[0, 0], [35089, 38.109], [8545, 10047]])
make_bars(ax1, title='PLS-7', rnd=pls7[0], agn=pls7[1], sbr=pls7[2])
make_bars(ax2, title='PLS-10', rnd=pls10[0], agn=pls10[1], sbr=pls10[2])
make_bars(ax3, title='PLS-12', rnd=pls12[0], agn=pls12[1], sbr=pls12[2])
fig.tight_layout()
plt.subplots_adjust(wspace=0.1, hspace=0)
plt.show()