import pandas as pd

dataset = pd.read_csv('dump.csv', names=["PATH", "ERROR", "CODE"])
dataset["PATH"] = dataset["PATH"].apply(lambda p: p.split("/")[-1])
dataset.to_csv("dump.csv", index=False, header=False)
