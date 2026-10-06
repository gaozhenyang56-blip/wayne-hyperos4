#!/usr/bin/env python3
import sys
from inspect_ota import RemoteFile
r=RemoteFile('https://drive.usercontent.google.com/download?id=1_Tu-HcN1PIz4PItm5vvCuh5FrjJpfDTX&export=download&confirm=t')
if r.size!=2683141762 or r.range(0,4)!=b'PK\x03\x04':
    raise ValueError('Unexpected original source size or ZIP header')
print('Original ZIP range preflight passed',r.size)
