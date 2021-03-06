#!/usr/bin/env python

import sys
d={}

for line in open(sys.argv[1], "r"):
    for i in range(0,28):
        d[i] = d.get(i, {})
        e=line[i];d[i][e.upper()] = d[i].get(e,0) + 1

s="{:<8} {:<8} {:<8} {:<8} {:<8}"
print(s.format("Position","A","T","C","G"))
for k, v in d.items():
    print(s.format(k+1, v.get("A", 0),v.get("T", 0),v.get("C", 0),v.get("G", 0)))