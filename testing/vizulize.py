#!/usr/bin/env python3

from matplotlib import pyplot as plt
import json
import numpy as np




'''
Plotting the sensitivity testing
'''

def plot_sensitivity(data_sg, data_design):
    x_titles     = [line['description'].split(', ')[-1].split('=')[1] for line in data_design if 'Sensitivity Testing, designed, ' in line['description']]
    x_titles     = list(map(lambda x: int(float(x)*100), x_titles))

    my_goodputs  = [line['results']['goodputs']  for line in data_design if 'Sensitivity Testing, designed, ' in line['description']]
    my_overheads = [line['results']['overheads'] for line in data_design if 'Sensitivity Testing, designed, ' in line['description']]
    my_gp_means  = [np.mean(gp) / 1000 for gp in my_goodputs]
    my_gp_stds   = [np.std(gp)  / 1000 for gp in my_goodputs]
    my_oh_means  = [np.mean(oh) * 100 for oh in my_overheads]
    my_oh_stds   = [np.std(oh)  * 100 for oh in my_overheads]

    sg_goodputs  = [line['results']['goodputs']  for line in data_sg if 'Sensitivity Testing, stop and go, ' in line['description']]
    sg_overheads = [line['results']['overheads'] for line in data_sg if 'Sensitivity Testing, stop and go, ' in line['description']]
    sg_gp_means  = [np.mean(gp) / 1000 for gp in sg_goodputs]
    sg_gp_stds   = [np.std(gp)  / 1000 for gp in sg_goodputs]
    sg_oh_means  = [np.mean(oh) * 100 for oh in sg_overheads]
    sg_oh_stds   = [np.std(oh)  * 100 for oh in sg_overheads]

    fig, (ax0, ax1) = plt.subplots(1,2)
    fig.suptitle(f'Protocol Sensitivity (n={len(my_goodputs[0])})')

    x_vals = np.arange(len(x_titles))
    width  = 0.4
    ax0.bar(x_vals+(width/2), my_gp_means, width=width, yerr=my_gp_stds, capsize=6, label='Designed')
    ax0.bar(x_vals-(width/2), sg_gp_means, width=width, yerr=sg_gp_stds, capsize=6, label='Stop and Go')
    ax0.set_title('Goodput')
    ax0.set_xlabel(f'Loss & Reorder Probability (%)')
    ax0.set_ylabel(f'Sample Mean (Kb/s)')
    ax0.set_xticks(x_vals, x_titles)
    ax0.legend()

    ax1.bar(x_vals+(width/2), my_oh_means, width=width, yerr=my_oh_stds, capsize=6, label='Designed')
    ax1.bar(x_vals-(width/2), sg_oh_means, width=width, yerr=sg_oh_stds, capsize=6, label='Stop and Go')
    ax1.set_title('Overhead')
    ax1.set_xlabel(f'Loss & Reorder Probability (%)')
    ax1.set_ylabel(f'Sample Mean (%)')
    ax1.set_xticks(x_vals, x_titles)
    ax1.legend()

    plt.tight_layout()
    plt.savefig(f'sensitivity.png')

def plot_var(data_design):
    my_goodputs  = np.ravel([line['results']['goodputs']  for line in data_design if 'Var, designed' in line['description']])
    my_overheads = np.ravel([line['results']['overheads'] for line in data_design if 'Var, designed' in line['description']])
    sg_goodputs  = np.ravel([line['results']['goodputs']  for line in data_design if 'Var, stop and go' in line['description']])
    sg_overheads = np.ravel([line['results']['overheads'] for line in data_design if 'Var, stop and go' in line['description']])
    my_gp_means  = np.mean(my_goodputs) / 1000
    my_gp_stds   = np.std(my_goodputs)  / 1000
    my_oh_means  = np.mean(my_overheads) * 100
    my_oh_stds   = np.std(my_overheads) * 100
    sg_gp_means  = np.mean(sg_goodputs) / 1000 
    sg_gp_stds   = np.std(sg_goodputs)  / 1000 
    sg_oh_means  = np.mean(sg_overheads) * 100 
    sg_oh_stds   = np.std(sg_overheads)  * 100 

    fig, (ax0, ax1) = plt.subplots(1,2)
    fig.suptitle(f'Designed Protocol Variance (n={len(my_goodputs)})')
    ax0.hist([g/1000 for g in my_goodputs])
    ax0.set_title('Goodput')
    ax0.set_ylabel(f'frequency')
    ax0.set_xlabel(f'Goodput (Kb/s)')
    ax1.hist([o*100 for o in my_overheads])
    ax1.set_title('Overhead')
    ax1.set_ylabel(f'Frequency')
    ax1.set_xlabel(f'Overhead (%)')
    plt.tight_layout()
    plt.savefig(f'variance_des.png')


    fig, (ax0, ax1) = plt.subplots(1,2)
    fig.suptitle(f'Stop and Go Variance (n={len(sg_goodputs)})')
    ax0.hist([g/1000 for g in sg_goodputs])
    ax0.set_title('Goodput')
    ax0.set_ylabel(f'frequency')
    ax0.set_xlabel(f'Goodput (Kb/s)')
    ax1.hist([o*100 for o in sg_overheads])
    ax1.set_title('Overhead')
    ax1.set_ylabel(f'Frequency')
    ax1.set_xlabel(f'Overhead (%)')
    plt.tight_layout()
    plt.savefig(f'variance_sg.png')



    fig, (ax0, ax1) = plt.subplots(1,2)
    fig.suptitle(f'Protocol Sensitivity (n={len(my_goodputs)})')
    x_vals = np.arange(1)
    width  = 0.4
    ax0.bar(x_vals+(width/2), my_gp_means, width=width, yerr=my_gp_stds, capsize=6, label='Designed')
    ax0.bar(x_vals-(width/2), sg_gp_means, width=width, yerr=sg_gp_stds, capsize=6, label='Stop and Go')
    ax0.set_title('Goodput')
    ax0.set_xlabel(f'Loss & Reorder Probability (%)')
    ax0.set_ylabel(f'Sample Mean (Kb/s)')
    ax0.legend()

    ax1.bar(x_vals+(width/2), my_oh_means, width=width, yerr=my_oh_stds, capsize=6, label='Designed')
    ax1.bar(x_vals-(width/2), sg_oh_means, width=width, yerr=sg_oh_stds, capsize=6, label='Stop and Go')
    ax1.set_title('Overhead')
    ax1.set_xlabel(f'Loss & Reorder Probability (%)')
    ax1.set_ylabel(f'Sample Mean (%)')
    ax1.legend()

    plt.tight_layout()
    plt.savefig(f'variance.png')


if __name__ == '__main__':
    data_sg     = [json.loads(l) for l in open('test_results_cp1.log', 'r')]
    data_design = [json.loads(l) for l in open('test_results.log', 'r')]
    
    
    plot_sensitivity(data_sg, data_design)

    plot_var(data_design)