import pandas as pd
import sys

def read_file(path, n):
    rows = []
    with open(path) as f:
        for line in f:
            rows.append(line.strip().split(',', n))
    return rows

errors = {
    "Use of HTTP without SSL/TLS": 'use of http',
    "Admin by default": 'admin-by-default',
    "Suspicious comment": 'suspicious comment',
    "Empty password": 'empty-password',
    "Hard-coded secret": 'hardcoded-secret',
    "Unrestricted IP Address": 'improper ip address binding',
    "No integrity check": 'no-integrity-check',
    "none": 'none'
}

oracle = pd.read_csv("oracle_dataset.csv")
print(oracle.groupby(['CATEGORY']).count())
oracle['CATEGORY'] = oracle['CATEGORY'].apply(lambda e: errors[e])
all_files = set(oracle['PATH'].to_list())

results_oracle = pd.DataFrame(read_file(sys.argv[1], 2), columns=['PATH', 'ERROR', 'CODE'])
false_positives = {
    'none': 0
}
false_positives_nones = []

for file in all_files:
    if (len(results_oracle[results_oracle.PATH == file].index) == 0) and \
            oracle[oracle.PATH == file].iloc[0]["CATEGORY"] != "none":
        false_positives['none'] += 1
        false_positives_nones.append((file, "", "none"))

true_positives = {
    'use of http': 0,
    'admin-by-default': 0,
    'suspicious comment': 0,
    'empty-password': 0,
    'hardcoded-secret': 0,
    'hardcoded-password': 0, # IGNORE
    'hardcoded-username': 0, # IGNORE
    'improper ip address binding': 0,
    'no-integrity-check': 0,
    'none': 0
}
false_negatives = []

for _, row in oracle.iterrows():
    with open("../oracle-dataset/" + row["PATH"], "r") as f:
        if (row["CATEGORY"] == "none"):
            if len(results_oracle[results_oracle.PATH == row["PATH"]].index) == 0:
                true_positives["none"] += 1
            else:
                false_negatives.append((row["PATH"], row["LINE"], row["CATEGORY"]))
        else:
            line = f.readlines()[row["LINE"] - 1]
            true_positive = False

            for slac_index, slac_row in results_oracle.iterrows():
                if slac_row["ERROR"] == row["CATEGORY"] and \
                        slac_row["PATH"] == row["PATH"]:
                    if row["CATEGORY"] == "suspicious comment" and \
                            line.strip() == slac_row["CODE"].strip():
                        true_positives[row["CATEGORY"]] += 1
                        true_positive = True
                        results_oracle.drop(slac_index, inplace=True) 
                        break
                    else:
                        key, value = slac_row["CODE"].split(':', 1)
                        key, value = key.strip('\"\''), value.strip('\"\'')
                        if key in line and value in line:
                            true_positives[row["CATEGORY"]] += 1
                            true_positive = True
                            results_oracle.drop(slac_index, inplace=True) 
                            break

            if not true_positive:
                false_negatives.append((row["PATH"], row["LINE"], row["CATEGORY"]))

#print("True positives: ", true_positives)
precision = {}
recall = {}
false_positives.update(results_oracle.groupby("ERROR").count().to_dict()['PATH'])

print("\n\nPRECISION")
for k, v in true_positives.items():
    if (k in ['hardcoded-password', 'hardcoded-username']):
        continue
    if k in false_positives:
        precision[k] = v / (v + false_positives[k])
    elif v == 0:
        precision[k] = "N/D"
    else:
        precision[k] = 1

for k, v in precision.items():
    print(k, v)

print("\n\nRECALL")
for k, v in true_positives.items():
    if (k in ['hardcoded-password', 'hardcoded-username']):
        continue
    fn = 0
    for false_negative in false_negatives:
        if false_negative[2] == k:
            fn += 1
    if (fn + v != 0):
        recall[k] = v / (fn + v)
    else:
        recall[k] = "N/D"

for k, v in recall.items():
    print(k, v)

#print("\n\nFALSE NEGATIVES")
#for false_negative in false_negatives:
#    if (false_negative[2] != 'hardcoded-password' and false_negative[2] != 'hardcoded-username'):
#        print(false_negative)

#results_oracle.sort_values(by=['PATH'], inplace=True)
#print("\n\nFALSE POSITIVES")
#for _, row in results_oracle.iterrows():
#    if (row["ERROR"] != 'hardcoded-password' and row["ERROR"] != 'hardcoded-username'):
#        print((row["PATH"], row["CODE"], row["ERROR"]))
#for false_positive_none in false_positives_nones:
#    print(false_positive_none)
