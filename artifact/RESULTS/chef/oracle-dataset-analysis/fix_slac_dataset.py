import pandas as pd
errors = {
    'SECURITY:::HARD_CODED_SECRET_': 'hardcoded-secret',
    'SECURITY:::EXPOSING_SECRET_LOCATION_': 'hardcoded-secret',
    'SECURITY:::EMPTY_PASSWORD:::': 'empty-password',
    'SECURITY:::HTTP:::': 'use of http',
    'SECURITY:::BINDING_TO_ALL:::': 'improper ip address binding',
    'SECURITY:::SOURCE_INTEGRITY:::': 'no-integrity-check',
    'SECURITY:::SUSPICOUS_COMMENTS:::': 'suspicious comment',
    'SECURITY:::HARD_CODED_SECRET_USER_NAME:::': 'hardcoded-username',
    'SECURITY:::HARD_CODED_SECRET_PASSWORD:::': 'hardcoded-password',
    'SECURITY:::ADMIN_BY_DEFAULT:::': 'admin-by-default',
    'SECURITY:::MISSING_DEFAULT:::': 'missing default case statement',
    'SECURITY:::MD5:::': 'weak cryptography algorithms'
}

dataset = pd.read_csv('dump.csv', names=["PATH", "ERROR", "LINE"])
dataset["PATH"] = dataset["PATH"].apply(lambda p: p.split("/")[-1])
dataset["ERROR"] = dataset["ERROR"].apply(lambda e: errors[e])
dataset = pd.concat([
    dataset[dataset['LINE'] == -1],
    dataset[dataset['LINE'] != -1].drop_duplicates(subset=['PATH', 'ERROR', 'LINE'])
])
dataset.to_csv("dump.csv", index=False)
