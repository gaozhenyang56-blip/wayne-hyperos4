#!/usr/bin/env python3
from download_verified import bounded
from inspect_ota import RemoteFile
r=bounded(lambda:RemoteFile('https://drive.usercontent.google.com/download?id=1_Tu-HcN1PIz4PItm5vvCuh5FrjJpfDTX&export=download&confirm=t'),'initial range probe')
if r.size!=2683141762 or bounded(lambda:r.range(0,4),'ZIP header')!=b'PK\x03\x04':
    raise ValueError('Unexpected original source size or ZIP header')
print('Original ZIP range preflight passed',r.size)
