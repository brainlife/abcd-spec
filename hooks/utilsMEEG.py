#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
import shutil

#datatype IDs that we handle
MEG_CTF = "6000714baacf9e22a6a691c8"
MEG_FIF = "6000737faacf9ee51fa691cb"
EEG_EEGLAB = "60007410aacf9e4edda691d4"
EEG_EDF = "600074f6aacf9e7acda691d7"
EEG_BRAINVISION = "6000753eaacf9e6591a691d9"
EEG_BDF = "60007567aacf9e1615a691dd"

def getModality(input):
    if input["datatype"] == MEG_CTF:
        return "meg"
    if input["datatype"] == MEG_FIF:
        return "meg"
    if input["datatype"] == EEG_EEGLAB:
        return "eeg"
    if input["datatype"] == EEG_EDF:
        return "eeg"
    if input["datatype"] == EEG_BRAINVISION:
        return "eeg"
    if input["datatype"] == EEG_BDF:
        return "eeg"
    return "derivatives"

def outputSidecar(path, input):
    with open(path, 'w') as outfile:

        #remove some meta fields that conflicts
        #ValueError: Conflicting values found for entity 'datatype' in filename /export/prod/5f1b9122a5b643aa7fa03b8c/5f1b912ca5b6434713a03b8f/bids/sub-10/anat/sub-10_T1w.nii.gz (value='anat') versus its JSON sidecar (value='16'). Please reconcile this discrepancy.
        if "datatype" in input["meta"]:
            print("removing datatype key from meta", path)
            del input["meta"]["datatype"]

        #https://github.com/bids-standard/pybids/issues/687
        if "run" in input["meta"]:
            print("removing run from meta", path)
            del input["meta"]["run"]  

        json.dump(input["meta"], outfile)  
        
def copyJSON(src, dest, override=None):
    try:
        if os.path.exists(src):        
            with open(src) as infile:
                config = json.load(infile)
                if override is not None:
                    for key in override.keys():
                        #print("fixing field", key)
                        config[key] = override[key]
            with open(dest, 'w') as outfile:
                print("copying", src, "to", dest, override)
                json.dump(config, outfile)  
    except FileExistsError:
        #don't create copy if src doesn't exist
        pass

def link(src, dest, recover=None):
    try:
        if os.path.exists(src):
            print("linking", src, "to", dest)
            if os.path.isdir(src):
                os.symlink(recover+src, dest, True)
                #os.link(src, dest, True)
            else:
                os.link(src, dest)
        else:
            print(src, "not found")
    except FileExistsError:
        #don't create link if src doesn't exist
        pass

def copy_folder(src, dest):
    try:
        shutil.copytree(src, dest)
    except shutil.Error:
        pass

def clean(v):
    return re.sub(r'[^a-zA-Z0-9]+', '', v)
