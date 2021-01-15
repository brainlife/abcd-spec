#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
import nibabel as nib

#datatype IDs that we handle (everything else is treated as derivatives)
ANAT_T1W = "58c33bcee13a50849b25879a"
ANAT_T2W = "594c0325fa1d2e5a1f0beda5"
DWI = "58c33c5fe13a50849b25879b"
FUNC_TASK = "59b685a08e5d38b0b331ddc5"
FUNC_REGRESSORS = "5c4f6a8af9109beac4b3dae0"
FMAP = "5c390505f9109beac42b00df"

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
    return "derivatives"

def get_nii_img(input):
    if input["id"] == 't1w': 
        nii_img = config["t1"]
    elif input["id"] == 't2w':
        nii_img = config["t2"]
    elif input["id"] == 'dwi':
        nii_img = config["dwi"]    
    elif input["id"] == 'freesurfer':
        nii_img = config["t1"] #change?!
    elif input["id"] == 'fmri':   
        nii_img = config["fmri"]
    return nii_img     

def correctPE(pe, nii_img):
    
    #if it's using ijk already don't need to do anything
    if pe[0] == 'i' or pe[0] == 'j' or pe[0] == 'k':
        print("Phase Encoding Direction conversion not needed.")
        return pe
    
    #convert xyz to ijk
    img = nib.load(nii_img)
    codes = nib.aff2axcodes(img.affine) 
    ax_idcs = {"x": 0, "y": 1, "z": 2}
    axis = ax_idcs[pe[0]]
    if codes[axis] in ('L', 'R'):
        updated_pe = 'i'
    if codes[axis] in ('P', 'A'):
        updated_pe = 'j'
    if codes[axis] in ('I', 'S'):
        updated_pe = 'k'
    
    #flip polarity if it's using L/P/I
    inv = pe[1:] == "-"
    if pe[0] == 'x':
        if codes[0] == 'L':
            inv = not inv 
    if pe[0] == 'y':
        if codes[1] == 'P':
            inv = not inv 
    if pe[0] == 'z':
        if codes[2] == 'I':
            inv = not inv 
    if inv:
        updated_pe += "-"
    print(f"Orientation: {codes}")    
    print(f"Phase Encoding Direction updated: {updated_pe}") 

    return updated_pe     

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
        if "PhaseEncodingDirection" in input["meta"]:
            nii_img = get_nii_img(input)
            pe = input["meta"]["PhaseEncodingDirection"]
            updated_pe = correctPE(pe, nii_img)
            input["meta"]["PhaseEncodingDirection"] = updated_pe    

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
            else:
                os.link(src, dest)
    except FileExistsError:
        #don't create link of src doesn't exist
        pass

def clean(v):
    return re.sub(r'[^a-zA-Z0-9]+', '', v)

with open('config.json', encoding='utf-8') as f:
    config = json.load(f)

    if not "_inputs" in config:
        print("no _inputs in config.json.. can't generate bids structure without it")
        sys.exit(1)
        
    intended_paths = []

    for input in config["_inputs"]:

        path="bids"

        subject = None
        if "subject" in input["meta"]:
            subject = clean(input["meta"]["subject"])

        session = None
        if "session" in input["meta"]:
            session = clean(input["meta"]["session"])

        run = None
        if "run" in input["meta"]:
            #TODO - run should be an integer and it should not be 0-padded according to Tal
            #but on brainlife, it could be set to any string.. so I can't just convert to int as it could
            #raise invalid literal ValueError exception
            try:
                _run = clean(input["meta"]["run"])
                run = str(int(_run))
            except ValueError:
                print("can't parse run.. ignoring", input["meta"]["run"])

        #meta contains both acq and acquisition set to different value
        #I am not sure why, but let's make acqusition take precedence
        acq = None
        if "acquisition" in input["meta"]:
            acq = clean(input["meta"]["acquisition"])
        elif "acq" in input["meta"]:
            acq = clean(input["meta"]["acq"])

        rec = None
        if "rec" in input["meta"]:
            rec = clean(input["meta"]["rec"])

        #all non raw data is stored under derivatives
        modality=getModality(input)
        if modality == "derivatives":
            path += "/derivatives"
            path += "/"+input["task_id"] #TODO we need app name for "pipeline name"

        path+="/sub-"+subject
        if session:
            path+="/ses-"+session

        name="sub-"+subject
        if session:
            name+="_ses-"+session

        if "task" in input["meta"]:
            name+="_task-"+clean(input["meta"]["task"])
        else:
            if input["datatype"] == FUNC_TASK:
                print("meta.task is not set.. defaulting to rest")
                name+="_task-rest"

        if "echo" in input["meta"]:
            name+="_echo-"+clean(input["meta"]["echo"])

        if acq:
            name+="_acq-"+acq
        if run:
            name+="_run-"+run
        if rec:
            name+="_rec-"+rec

        if modality == "derivatives":
            path += "/dt-"+input["datatype"]+".todo" #TODO - need to lookup datatype.bids.derivatives type
        else:
            path += "/"+modality
    
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)

        #symlink recovery path
        recover = ""
        for i in path.split("/"):
            recover += "../"

        if input["datatype"] == ANAT_T1W:
            #there should be 1 and only nifti
            for key in input["keys"]:
                src=config[key]
                dest=path+"/"+name
                if src.endswith("t1.nii.gz"):
                    link(src, dest+"_T1w.nii.gz")
            outputSidecar(path+"/"+name+"_T1w.json", input)

        elif input["datatype"] == ANAT_T2W:
            #there should be 1 and only nifti
            for key in input["keys"]:
                src=config[key]
                dest=path+"/"+name
                if src.endswith("t2.nii.gz"):
                    link(src, dest+"_T2w.nii.gz")
            outputSidecar(path+"/"+name+"_T2w.json", input)
             
        elif input["datatype"] == DWI:
            for key in input["keys"]:
                src=config[key]
                dest=path+"/"+name
                if src.endswith("dwi.nii.gz"):
                    link(src, dest+"_dwi.nii.gz")
                if src.endswith("dwi.bvecs"):
                    link(src, dest+"_dwi.bvec")
                if src.endswith("dwi.bvals"):
                    link(src, dest+"_dwi.bval")
            outputSidecar(path+"/"+name+"_dwi.json", input)

            dest_under_sub = "/".join(dest.split("/")[1:])
            intended_paths.append(dest_under_sub+"_dwi.nii.gz")

        elif input["datatype"] == FUNC_TASK:

            for key in input["keys"]:
                src=config[key]
                dest=path+"/"+name
                if src.endswith("bold.nii.gz"):
                    link(src, dest+"_bold.nii.gz")
                if src.endswith("events.tsv"):
                    link(src, dest+"_events.tsv")
                if src.endswith("events.json"):
                    link(src, dest+"_events.json")
                if src.endswith("sbref.nii.gz"):
                    link(src, dest+"_sbref.nii.gz")
                if src.endswith("sbref.json"):
                    link(src, dest+"_sbref.json")
                if src.endswith("physio.tsv.gz"):
                    link(src, dest+"_physio.tsv.gz")
                if src.endswith("physio.json"):
                    link(src, dest+"_physio.json")
            outputSidecar(path+"/"+name+"_bold.json", input)

            dest_under_sub = "/".join(dest.split("/")[2:])
            intended_paths.append(dest_under_sub+"_bold.nii.gz")

        elif input["datatype"] == FUNC_REGRESSORS:
            name += "_desc-confound"
            for key in input["keys"]:
                src=config[key]
                dest=path+"/"+name
                if src.endswith("regressors.tsv"):
                    link(src, dest+"_regressors.tsv")
            outputSidecar(path+"/"+name+"_regressors.json", input)

        elif input["datatype"] == FMAP:
            for key in input["keys"]:
                src=config[key]
                dest=path+"/"+name
                fmap_dest=dest

                #https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/01-magnetic-resonance-imaging-data.html

                # [CASE 1] Phase difference image and at least one magnitude image
                # phasediff.nii.gz
                # phasediff.json (should have EchoTime1 / Echotime2, IntendedFor)
                # magnitude1.nii.gz
                # magnitude2.nii.gz (optional)

                # [CASE 2] Two phase images and two magnitude images
                # phase1.nii.gz
                # phase1.json (should have EchoTime / IntendedFor set)
                # phase2.nii.gz
                # phase2.json (should have EchoTime / IntendedFor set)
                # magnitude1.nii.gz
                # magnitude2.nii.gz

                # [CASE 3] A real fieldmap image
                # magnitude.nii.gz
                # fieldmap.nii.gz
                # fieldmap.json (Units(like "rad/s") and IntendedFor should be set)
                
                # [CASE 4] Multiple phase encoded directions ("pepolar")
                # dir-<label>_epi.nii.gz
                # dir-<label>_epi.json (should have PhaseEncodingDirection / TotalReadoutTime / IntendedFor )

                if src.endswith("phasediff.nii.gz"):
                    link(src, dest+"_phasediff.nii.gz")

                if src.endswith("magnitude.nii.gz"):
                    link(src, dest+"_magnitude.nii.gz")
                if src.endswith("magnitude1.nii.gz"):
                    link(src, dest+"_magnitude1.nii.gz")
                if src.endswith("magnitude2.nii.gz"):
                    link(src, dest+"_magnitude2.nii.gz")
                if src.endswith("fieldmap.nii.gz"):
                    link(src, dest+"_fieldmap.nii.gz")

                if src.endswith("phase1.nii.gz"):
                    link(src, dest+"_phase1.nii.gz")
                if src.endswith("phase2.nii.gz"):
                    link(src, dest+"_phase2.nii.gz")

                if src.endswith("epi1.nii.gz"):
                    link(src, dest+"_epi1.nii.gz")
                if src.endswith("epi2.nii.gz"):
                    link(src, dest+"_epi2.nii.gz")

            #outputSidecar(path+"/"+name+"_bold.json", input)
        else:
            #just copy the entire file/dir name
            for key in input["keys"]:
                base = os.path.basename(config[key])
                src=config[key]
                dest=path+"/"+name
                link(src, dest+"_"+base, recover)
                #print(path, name, key, config[key])
            outputSidecar(path+"/"+name+"_"+input["id"]+".json", input)
            
    #fix IntendedFor field for fmap json files
    for input in config["_inputs"]:
        if input["datatype"] == FMAP:
            for key in input["keys"]:
                src=config[key]
                dest=fmap_dest
                if src.endswith("phasediff.json"):
                    copyJSON(src, dest+"_phasediff.json", override={"IntendedFor": intended_paths})
                if src.endswith("phase1.json"):
                    copyJSON(src, dest+"_phase1.json", override={"IntendedFor": intended_paths})
                if src.endswith("phase2.json"):
                    copyJSON(src, dest+"_phase2.json", override={"IntendedFor": intended_paths})
                if src.endswith("epi1.json"):
                    copyJSON(src, dest+"_epi1.json", override={"IntendedFor": intended_paths})
                if src.endswith("epi2.json"):
                    copyJSON(src, dest+"_epi2.json", override={"IntendedFor": intended_paths})
                #fix PhaseEncodingDirection
                if key.endswith("_json"):
                    nii_key = key[:-5] #remove suffix "_json"
                    nii_img = config[nii_key] 
                    if os.path.exists(nii_img):
                        print(nii_key)
                        pe = input["meta"][nii_key]["PhaseEncodingDirection"]
                        updated_pe = correctPE(pe, nii_img)
                        f_json = dest+"_"+nii_key+".json"
                        print(f_json)
                        copyJSON(f_json, f_json, override={"PhaseEncodingDirection": updated_pe})

#generate fake dataset_description.json
name="brainlife"
if "TASK_ID" in os.environ:
    name += " task:"+os.environ["TASK_ID"]
desc = {
  "Name": name,
  "BIDSVersion": "1.4.0",
  "Authors": [ "Brainlife <brlife@iu.edu>" ]
}
pathlib.Path("bids").mkdir(parents=True, exist_ok=True)
with open("bids/dataset_description.json", 'w') as f:
    print("writing dataset_description.json", desc)
    json.dump(desc, f)


