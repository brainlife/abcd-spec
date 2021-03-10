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
MEG_CTF = "6000714baacf9e22a6a691c8"
MEG_FIF = "6000737faacf9ee51fa691cb"
EEG_EEGLAB = "60007410aacf9e4edda691d4"
EEG_EDF = "600074f6aacf9e7acda691d7"
EEG_BRAINVISION = "6000753eaacf9e6591a691d9"
EEG_BDF = "60007567aacf9e1615a691dd"

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

def get_nii_img(input):

    #TODO1 - input id is set by each App, so we can't just assume it to be certain nanme like input["t1w"]
    #we need to use the input["datatype"] to determine which datatype is it.
    #TODO2 - once we find the datatype, we can't rely on certain key under config like config["t1"]
    #as developer can map to any name they want. we need to look for input["id"] == "t1" to find 
    #the right object, then lookup its "keys" (it could be multiple!) and finally lookup the path pointed
    #by the key
    #DONE!

    input_dir = os.path.join('..', input["task_id"], input["subdir"])

    if input["datatype"] == ANAT_T1W:
        nii_img = os.path.join(input_dir, 't1.nii.gz')
    elif input["datatype"] == ANAT_T2W:
        nii_img = os.path.join(input_dir, 't2.nii.gz')
    elif input["datatype"] == DWI:
        nii_img = os.path.join(input_dir, 'dwi.nii.gz') 
    elif input["datatype"] == FUNC_TASK:   
        nii_img = config["fmri"] #doesn't work with multi input!
    elif input["datatype"] == FUNC_REGRESSORS:
        nii_img = config["fmri"] #doesn't work with multi input!
    else:
        #datatype not supported
        return None
    return nii_img     

def correctPE(input, nii_img, nii_key=None):
    
    if nii_key in input["meta"]:
        pe = input["meta"][nii_key]["PhaseEncodingDirection"]
    elif "PhaseEncodingDirection" in input["meta"]:
        pe = input["meta"]["PhaseEncodingDirection"]
    else:
        print("Cannot read PhaseEncodingDirection.")

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
            if nii_img:
                updated_pe = correctPE(input, nii_img)
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
        else:
            print(src, "not found")
    except FileExistsError:
        #don't create link if src doesn't exist
        pass

def clean(v):
    return re.sub(r'[^a-zA-Z0-9]+', '', v)

with open('config.json') as f:
    config = json.load(f)

    if not "_inputs" in config:
        print("no _inputs in config.json.. can't generate bids structure without it")
        sys.exit(1)
        
    intended_paths = []

    for id, input in enumerate(config["_inputs"]):
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
        if modality == "meg" or modality == "eeg":
            break
        elif modality == "derivatives":
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

        input_dir = os.path.join('..', input["task_id"], input["subdir"])
        dest=path+"/"+name

        if input["datatype"] == ANAT_T1W:
            src=os.path.join(input_dir, 't1.nii.gz')
            link(src, dest+"_T1w.nii.gz")

            outputSidecar(dest+"_T1w.json", input)

        elif input["datatype"] == ANAT_T2W:
            src=os.path.join(input_dir, 't2.nii.gz')
            print("linking t2", src, dest+"_T2w.nii.gz")
            link(src, dest+"_T2w.nii.gz")
            
            outputSidecar(dest+"_T2w.json", input)
             
        elif input["datatype"] == DWI:
            if isinstance(config["dwi"], list) and len(config["dwi"])>1:
                print("Multiple dwi input detected.")
                if run == None:
                    if acq == None: 
                        acq="id%d" %(id+1)
                    else:
                        acq+="id%d" %(id+1)
                    dest+="_acq-"+acq        
            src=os.path.join(input_dir, 'dwi.nii.gz')
            link(src, dest+"_dwi.nii.gz")
            src=os.path.join(input_dir, 'dwi.bvals')
            link(src, dest+"_dwi.bval")
            src=os.path.join(input_dir, 'dwi.bvecs')
            link(src, dest+"_dwi.bvec")
            src=os.path.join(input_dir, 'sbref.nii.gz')
            link(src, dest+"_sbref.nii.gz")
            src=os.path.join(input_dir, 'sbref.json')
            link(src, dest+"_sbref.json")

            outputSidecar(dest+"_dwi.json", input)

            dest_under_sub = "/".join(dest.split("/")[2:])
            intended_paths.append(dest_under_sub+"_dwi.nii.gz")

        elif input["datatype"] == FUNC_TASK:

            for key in input["keys"]:
                src=config[key]
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

            outputSidecar(dest+"_bold.json", input)

            dest_under_sub = "/".join(dest.split("/")[2:])
            intended_paths.append(dest_under_sub+"_bold.nii.gz")

        elif input["datatype"] == FUNC_REGRESSORS:
            src=os.path.join(input_dir, 'regressors.tsv')

            if isinstance(config["confounds"], list) and len(config["confounds"])>1:
                print("Multiple confounds input detected.")
                if run == None:
                    if acq == None: 
                        acq="id%d" %(id+1)
                    else:
                        acq+="id%d" %(id+1)
                    dest+="_acq-"+acq
            #desc- is only for derivatives..
            #https://github.com/bids-standard/bids-validator/issues/984
            #can't use input id to make it unique.. it looks like
            #https://fmriprep.org/en/stable/outputs.html#confound-regressors-description
            #dest+="_desc-confounds%d"%(id+1) #is this bids-compliant?

            #it looks like BIDS requires that regressors having "confounds" for desc?
            dest+="_desc-confounds"

            link(src, dest+"_regressors.tsv")
            outputSidecar(dest+"_regressors.json", input)

        elif input["datatype"] == FMAP:

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

            fmap_dest=dest #used later to reset IntendedFor
            fmap_dir=input_dir #used later to reset IntendedFor

            for key in input["keys"]:   
                if not key.endswith("_json"):
                    nii_key = key
                    src=os.path.join(input_dir, nii_key+".nii.gz")
                    link(src, dest+"_"+nii_key+".nii.gz")
            
        else:
            #other datatypes...
            #just copy the entire file/dir name
            for key in input["keys"]:
                base = os.path.basename(config[key])
                src=config[key] #does not work with multi input!
                dest=path+"/"+name
                link(src, dest+"_"+base, recover)
            outputSidecar(path+"/"+name+"_"+input["id"]+".json", input)
            
    #fix IntendedFor field and PhaseEncodingDirection for fmap json files
    for input in config["_inputs"]:
        if input["datatype"] == FMAP:
            #set "correct" IntendedFor
            dest=fmap_dest #does not work with multi input!
            input_dir=fmap_dir #does not work with multi input!

            for key in input["keys"]:   
                if key.endswith("_json"):
                    nii_key = key[:-5] #remove suffix "_json"
                    src=os.path.join(input_dir, nii_key+".json")
                    f_json = dest+"_"+nii_key+".json"
                    copyJSON(src, f_json, override={"IntendedFor": intended_paths})
                    #fix PhaseEncodingDirection 
                    nii_img=os.path.join(input_dir, nii_key+".nii.gz")
                    if os.path.exists(nii_img):
                        print(nii_key)
                        updated_pe = correctPE(input, nii_img, nii_key)
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
