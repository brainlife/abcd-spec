#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
import nibabel as nib
import os.path as op

ANAT_T1W = "58c33bcee13a50849b25879a"
ANAT_T2W = "594c0325fa1d2e5a1f0beda5"
DWI = "58c33c5fe13a50849b25879b"
FUNC_TASK = "59b685a08e5d38b0b331ddc5"
FUNC_REGRESSORS = "5c4f6a8af9109beac4b3dae0"
FMAP = "5c390505f9109beac42b00df"
MEG_CTF = "6000714baacf9e22a6a691c8"
MEG_FIF = "6000737faacf9ee51fa691cb"
EEG_EEGLAB = "60007410aacf9e4edda691d4"
EEG_EDF = "600074f6aacf9e7acda691d7"
EEG_BRAINVISION = "6000753eaacf9e6591a691d9"
EEG_BDF = "60007567aacf9e1615a691dd"

#derivatives datatype > directory mapping
DERIVATIVES_DIRNAMES = { "58cb22c8e13a50849b25882e": "freesurfer" }

def getModality(input):
    if input["datatype"] == ANAT_T1W:
        return "anat"
    if input["datatype"] == ANAT_T2W:
        return "anat"
    if input["datatype"] == DWI:
        return "dwi"
    if input["datatype"] == FUNC_TASK:
        return "func"
    if input["datatype"] == FUNC_REGRESSORS:
        return "func"
    if input["datatype"] == FMAP:
        return "fmap"
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

def correctPE(input, nii_img, nii_key=None):

    #if nii_key in input["meta"]:
    #    pe_direction = input["meta"][nii_key]["PhaseEncodingDirection"]
    #elif "PhaseEncodingDirection" in input["meta"]:
    #    pe_direction = input["meta"]["PhaseEncodingDirection"]
    #else:
    #    print("Cannot read PhaseEncodingDirection.")

    json_sidecar=nii_img[:-6]+"json"
    if os.path.exists(json_sidecar):
        with open(json_sidecar) as f:
            json_sidecar = json.load(f)
        pe_direction=json_sidecar["PhaseEncodingDirection"]
    elif nii_key in input["meta"]:
        pe_direction = input["meta"][nii_key]["PhaseEncodingDirection"]
    elif "PhaseEncodingDirection" in input["meta"]:
        pe_direction = input["meta"]["PhaseEncodingDirection"]
    else:
        print("Cannot read PhaseEncodingDirection.")

    print(f"Phase Encoding Direction: {pe_direction}")
    axes = (("R", "L"), ("A", "P"), ("S", "I"))
    proper_ax_idcs = {"i": 0, "j": 1, "k": 2}

    # pe_direction is ijk (no correction necessary)
    if any(x in pe_direction for x in ['i','i-','j','j-','k','k']):
        print("Phase Encoding Direction conversion not needed.")
        proper_pe_direction = pe_direction

    # pe_direction xyz (correction required)
    else:
        img = nib.load(nii_img)
        ornt = nib.aff2axcodes(img.affine)
        improper_ax_idcs = {"x": 0, "y": 1, "z": 2}
        axcode = ornt[improper_ax_idcs[pe_direction[0]]]
        axcode_index = improper_ax_idcs[pe_direction[0]]
        inv = pe_direction[1:] == "-"

        if pe_direction[0] == 'x':
            if 'L' in axcode:
                inv = not inv
        elif pe_direction[0] == 'y':
            if 'P' in axcode:
                inv = not inv
        elif pe_direction[0] == 'z':
            if 'I' in axcode:
                inv = not inv
        else:
            ValueError('pe_direction does not contain letter i, j, k, x, y, or z')

        if inv:
            polarity = '-'
        else:
            polarity = ''

        proper_pe_direction = [key for key, value in proper_ax_idcs.items() if value == axcode_index][0] + polarity

        print(f"Orientation: {ornt}")
        print(f"Phase Encoding Direction updated: {proper_pe_direction}")

    return proper_pe_direction

def determineDir(input, nii_img, nii_key=None):
    '''
    Takes pe_direction and image orientation to determine direction
    required by BIDS "_dir-" label

    Based on https://github.com/nipreps/fmriprep/issues/2341 and original code
    comes from Chris Markiewicz and Mathias Goncalves
    '''
    #if nii_key in input["meta"]:
    #    pe_direction = input["meta"][nii_key]["PhaseEncodingDirection"]
    #elif "PhaseEncodingDirection" in input["meta"]:
    #    pe_direction = input["meta"]["PhaseEncodingDirection"]
    #else:
    #    print("Cannot read PhaseEncodingDirection.")

    json_sidecar=nii_img[:-6]+"json"
    if os.path.exists(json_sidecar):
        with open(json_sidecar) as f:
            json_sidecar = json.load(f)
        pe_direction=json_sidecar["PhaseEncodingDirection"]
    elif nii_key in input["meta"]:
        pe_direction = input["meta"][nii_key]["PhaseEncodingDirection"]
    elif "PhaseEncodingDirection" in input["meta"]:
        pe_direction = input["meta"]["PhaseEncodingDirection"]
    else:
        print("Cannot read PhaseEncodingDirection.")

    img = nib.load(nii_img)
    ornt = nib.aff2axcodes(img.affine)

    axes = (("R", "L"), ("A", "P"), ("S", "I"))
    ax_idcs = {"i": 0, "j": 1, "k": 2}
    axcode = ornt[ax_idcs[pe_direction[0]]]
    inv = pe_direction[1:] == "-"

    if pe_direction[0] == 'i':
        if 'L' in axcode:
            inv = not inv
    elif pe_direction[0] == 'j':
        if 'P' in axcode:
            inv = not inv
    elif pe_direction[0] == 'k':
        if 'I' in axcode:
            inv = not inv

    for ax in axes:
        for flip in (ax, ax[::-1]):
            if flip[not inv].startswith(axcode):
                direction = "".join(flip)

    print(f"Direction: {direction}")

    return direction

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

        #https://github.com/nipreps/fmriprep/issues/2341
        if input["datatype"] in [ANAT_T1W, ANAT_T2W, DWI, FUNC_TASK, FUNC_REGRESSORS] and "PhaseEncodingDirection" in input["meta"]:
            for key in input["_key2path"]:
                path = input["_key2path"][key]
                if path.endswith(".nii.gz"):
                    print("correcting PE for", path)
                    updated_pe = correctPE(input, path)
                    input["meta"]["PhaseEncodingDirection"] = updated_pe

        #adjust subject field in sidecar (one dataset has a redundant prefix sub-)
        #subject = input["meta"]["subject"]
        #input["meta"]["subject"] = re.sub('sub-', '', subject)
        
        #clean subject field in sidecar
        subject = input["meta"]["subject"]
        input["meta"]["subject"] = clean(subject)

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
        else:
            print(src, "not found")
    except FileExistsError:
        print(dest,"already exist")

def link(src, dest):
    try:
        if os.path.exists(src):
            if os.path.isdir(src):

                recover = ""
                depth = len(dest.split("/"))
                for i in range(1, depth):
                    recover += "../"

                print("it's directory.. sym-linking (existing)", recover+src, "to (new symlink)", dest)
                os.symlink(recover+src, dest, True)
            else:
                print("hard-linking (existing)", src, "to (new link)", dest)
                os.link(src, dest)
        else:
            print(src, "not found")
    except FileExistsError:
        print(dest, "already exists (or failed to link)")

def clean(v):
    return re.sub(r'[^a-zA-Z0-9]+', '', v)

def copytree(src, dest):
    #link(src, dest)
    os.makedirs(dest)
    recover = "../"
    depth = len(dest.split("/"))
    for i in range(1, depth):
        recover += "../"
    for fname in os.listdir(src):
        os.symlink(os.path.join(recover+src, fname), os.path.join(dest, fname))

def copyfile_ctf(src, dest):
    """Copy and rename CTF files to a new location.
    Parameters
    ----------
    src : str | pathlib.Path
        Path to the source raw .ds folder.
    dest : str | pathlib.Path
        Path to the destination of the new bids folder.
    See Also
    --------
    copyfile_brainvision
    copyfile_bti
    copyfile_edf
    copyfile_eeglab
    copyfile_kit
    """
    copytree(src, dest)
    # list of file types to rename
    file_types = ('.acq', '.eeg', '.hc', '.hist', '.infods', '.bak',
                  '.meg4', '.newds', '.res4')
    # Rename files in dest with the name of the dest directory
    fnames = [f for f in os.listdir(dest) if f.endswith(file_types)]
    bids_folder_name = op.splitext(op.split(dest)[-1])[0]
    for fname in fnames:
        ext = op.splitext(fname)[-1]
        os.rename(op.join(dest, fname),
                  op.join(dest, bids_folder_name + ext))
