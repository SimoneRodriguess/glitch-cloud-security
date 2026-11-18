import pandas as pd

def read_file(path, n):
    rows = []
    with open(path) as f:
        for line in f:
            rows.append(line.strip().split(',', n))
    return rows

dataset = pd.DataFrame(read_file('dump.csv', 3), columns=['PATH', 'LINE', 'ERROR', 'CODE'])
dataset["PATH"] = dataset["PATH"].apply(lambda p: p.split("/")[-1])
dataset.drop("LINE", axis=1, inplace=True)

errors = {
    'sec_hard_secr': 'hardcoded-secret',
    'sec_empty_pass': 'empty-password',
    'sec_https': 'use of http',
    'sec_invalid_bind': 'improper ip address binding',
    'sec_no_int_check': 'no-integrity-check',
    'sec_susp_comm': 'suspicious comment',
    'sec_hard_user': 'hardcoded-username',
    'sec_hard_pass': 'hardcoded-password',
    'sec_def_admin': 'admin-by-default'
}
dataset["ERROR"] = dataset["ERROR"].apply(lambda e: errors[e])
dataset.to_csv("dump.csv", index=False, header=False)
