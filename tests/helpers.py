import numpy as np

def set_sweeps_args(sequence) -> list:
    set_sweeps_args = [
        {
            sequence.dummy_parent_sub.sub_seq1.par1: np.zeros((5), dtype= int),
            sequence.dummy_parent_sub.sub_seq2.par4: np.ones((5)),
        },
        {
            sequence.dummy_parent_sub.sub_seq1.vHome_J1: np.zeros((7), dtype= int)
        },
    ]
    return set_sweeps_args

def qua_program_trim_gen_time(qp) -> list:
    qpn = qp.split('\n')
    n=0
    for l in qpn:
        if 'Single QUA script generated at' in l:
            break
        else:
            n+=1
    qpr = qpn[n+1:]
    return qpr

def compare_qua_programs(qp1, qp2) -> list:

    n1 = len(qp1)
    n2 = len(qp2)
    lines=[]
    for n in range(0, n1):
        if qp1[n]!=qp2[n]:
            print(f'differencs on line n={n}')
            print(qp1[n])
            print(qp2[n])
            lines.append(n)
    if len(lines):
        print('\n\n differences on lines :')
        print(lines)
    else:
        print('identical programs')
    return lines
