#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
import nibabel as nib

import utils

with open('config.json') as f:
    config = json.load(f)

if not "_inputs" in config:
    print("no _inputs in config.json.. can't generate bids structure without it")
    sys.exit(1)
    
intended_paths = []

#map the path specified by keys for each input
multi_counts = {} #to handle mulltiple inputs
for id, input in enumerate(config["_inputs"]):
    input["_key2path"] = {}
    for key in input["keys"]:
        if isinstance(config[key], list):
            input["_multi"] = True
            if key not in multi_counts:
                multi_counts[key] = 0
            input["_key2path"][key] = config[key][multi_counts[key]]
            multi_counts[key] += 1
        else:
            input["_multi"] = False
            input["_key2path"][key] = config[key]
    
#now construct bids structure!
for id, input in enumerate(config["_inputs"]):
    path="bids"

    #all non raw data is stored under derivatives
    modality=utils.getModality(input)
    print("--> Modality: %s" %modality)

    if modality == "derivatives":
        if input["datatype"] in utils.DERIVATIVES_DIRNAMES:
            dirname = utils.DERIVATIVES_DIRNAMES[input["datatype"]]
        else:
            print("unknown derivative datatype - using input id")
            dirname = input["id"]+"."+input["datatype"]
        path+="/derivatives/" + dirname
        if input["_multi"]:
            path+=".%d" %(id+1)           

    subject = None
    if "subject" in input["meta"]:
        subject = utils.clean(input["meta"]["subject"])
        if modality != "derivatives":
            path+="/sub-"+subject
        name="sub-"+subject

    session = None
    if "session" in input["meta"]:
        session = utils.clean(input["meta"]["session"])
        if modality != "derivatives":
            path+="/ses-"+session
        name+="_ses-"+session

    if modality != "derivatives":
        path+="/"+modality

    short_name=name

    if "task" in input["meta"]:
        name+="_task-"+utils.clean(input["meta"]["task"])
    elif "TaskName" in input["meta"]:
        name+="_task-"+utils.clean(input["meta"]["TaskName"])
    else:
        if input["datatype"] == utils.FUNC_TASK:
            print("meta.task is not set.. defaulting to rest")
            name+="_task-rest"
        if modality == "meg" or modality == "eeg":
            print("meta.task is not set.. defaulting to id%d" %(id+1))
            name+="_task-id%d" %(id+1)

    #meta contains both acq and acquisition set to different value
    #I am not sure why, but let's make acqusition take precedence
    acq = None
    if "acquisition" in input["meta"]:
        acq = utils.clean(input["meta"]["acquisition"])
    elif "acq" in input["meta"]:
        acq = utils.clean(input["meta"]["acq"])
        name+="_acq-"+acq
        short_name+="_acq-"+acq

    if "space" in input["meta"]:
        space = utils.clean(input["meta"]["space"])
        name+="_space-"+space
        short_name+="_space-"+space

    run = None
    if "run" in input["meta"]:
        #TODO - run should be an integer and it should not be 0-padded according to Tal
        #but on brainlife, it could be set to any string.. so I can't just convert to int as it could
        #raise invalid literal ValueError exception
        try:
            _run = utils.clean(input["meta"]["run"])
            run = str(int(_run))
            name+="_run-"+run
        except ValueError:
            print("can't parse run.. ignoring", input["meta"]["run"])

    if "proc" in input["meta"]:
        proc = utils.clean(input["meta"]["proc"])
        name+="_proc-"+proc

    if "rec" in input["meta"]:
        rec = utils.clean(input["meta"]["rec"])
        name+="_rec-"+rec

    if "echo" in input["meta"]:
        echo = utils.clean(input["meta"]["echo"])
        name+="_echo-"+echo

    #make path directories
    print("creating directory", path)
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    #just grab the first item in keys to lookup dirname..
    first_key = input["keys"][0]
    input_dir = os.path.dirname(input["_key2path"][first_key])

    dest=path+"/"+name 
    short_dest=path+"/"+short_name #does not contain task and run 

    #handle multiple input by adding acq
    if input["_multi"] and run == None:
        if acq == None: 
            acq="id%d" %(id+1)
        dest+="_acq-"+acq     

    ##################################################
    ##
    ## now handle each datatype
    ##

    if input["datatype"] == utils.ANAT_T1W:
        src=os.path.join(input_dir, 't1.nii.gz')
        utils.link(src, dest+"_T1w.nii.gz")
        utils.outputSidecar(dest+"_T1w.json", input)

    elif input["datatype"] == utils.ANAT_T2W:
        src=os.path.join(input_dir, 't2.nii.gz')
        utils.link(src, dest+"_T2w.nii.gz")
        utils.outputSidecar(dest+"_T2w.json", input)
         
    elif input["datatype"] == utils.DWI:
        src=os.path.join(input_dir, 'dwi.nii.gz')
        utils.link(src, dest+"_dwi.nii.gz")
        src=os.path.join(input_dir, 'dwi.bvals')
        utils.link(src, dest+"_dwi.bval")
        src=os.path.join(input_dir, 'dwi.bvecs')
        utils.link(src, dest+"_dwi.bvec")
        src=os.path.join(input_dir, 'sbref.nii.gz')
        utils.link(src, dest+"_sbref.nii.gz")
        src=os.path.join(input_dir, 'sbref.json')
        utils.link(src, dest+"_sbref.json")

        utils.outputSidecar(dest+"_dwi.json", input)

        dest_under_sub = "/".join(dest.split("/")[2:])
        intended_paths.append(dest_under_sub+"_dwi.nii.gz")

    elif input["datatype"] == utils.FUNC_TASK:

        for key in input["keys"]:
            src=config[key]
            if src.endswith("bold.nii.gz"):
                utils.link(src, dest+"_bold.nii.gz")
            if src.endswith("events.tsv"):
                utils.link(src, dest+"_events.tsv")
            if src.endswith("events.json"):
                utils.link(src, dest+"_events.json")
            if src.endswith("sbref.nii.gz"):
                utils.link(src, dest+"_sbref.nii.gz")
            if src.endswith("sbref.json"):
                utils.link(src, dest+"_sbref.json")
            if src.endswith("physio.tsv.gz"):
                utils.link(src, dest+"_physio.tsv.gz")
            if src.endswith("physio.json"):
                utils.link(src, dest+"_physio.json")

        utils.outputSidecar(dest+"_bold.json", input)

        dest_under_sub = "/".join(dest.split("/")[2:])
        intended_paths.append(dest_under_sub+"_bold.nii.gz")

    elif input["datatype"] == utils.FUNC_REGRESSORS:
        src=os.path.join(input_dir, 'regressors.tsv')

        #desc- is only for derivatives..
        #https://github.com/bids-standard/bids-validator/issues/984
        #can't use input id to make it unique.. it looks like
        #https://fmriprep.org/en/stable/outputs.html#confound-regressors-description
        #dest+="_desc-confounds%d"%(id+1) #is this bids-compliant?

        #it looks like BIDS requires that regressors having "confounds" for desc?
        dest+="_desc-confounds"

        utils.link(src, dest+"_regressors.tsv")
        utils.outputSidecar(dest+"_regressors.json", input)

    elif input["datatype"] == utils.FMAP:

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
                utils.link(src, dest+"_"+nii_key+".nii.gz")

    elif input["datatype"] == utils.MEG_CTF:
        src=os.path.join(input_dir, 'meg.ds')
        #utils.copy_folder(src, dest+"_meg.ds") #just copy the content for now
        utils.link(src, dest+"_meg.ds") #just copy the content for now
        src=os.path.join(input_dir, 'channels.tsv')
        utils.link(src, dest+"_channels.tsv")
        src=os.path.join(input_dir, 'events.tsv')
        utils.link(src, dest+"_events.tsv")
        src=os.path.join(input_dir, 'events.json')
        utils.link(src, dest+"_events.json")              
        src=os.path.join(input_dir, 'headshape.pos')
        utils.link(src, short_dest+"_headshape.pos")
        src=os.path.join(input_dir, 'coordsystem.json')
        utils.link(src, short_dest+"_coordsystem.json")

        utils.outputSidecar(dest+"_meg.json", input)

    elif input["datatype"] == utils.MEG_FIF:
        src=os.path.join(input_dir, 'meg.fif')
        utils.link(src, dest+"_meg.fif")
        src=os.path.join(input_dir, 'channels.tsv')
        utils.link(src, dest+"_channels.tsv")
        src=os.path.join(input_dir, 'events.tsv')
        utils.link(src, dest+"_events.tsv")
        src=os.path.join(input_dir, 'events.json')
        utils.link(src, dest+"_events.json")
        src=os.path.join(input_dir, 'headshape.pos')
        utils.link(src, short_dest+"_headshape.pos")
        src=os.path.join(input_dir, 'coordsystem.json')
        utils.link(src, short_dest+"_coordsystem.json")
        src=os.path.join(input_dir, 'calibration_meg.dat')
        utils.link(src, short_dest+"_acq-calibration_meg.dat")
        src=os.path.join(input_dir, 'crosstalk_meg.fif')
        utils.link(src, short_dest+"_acq-crosstalk_meg.fif")
        src=os.path.join(input_dir, 'destination.fif')
        utils.link(src, short_dest+"_destination.fif")

        utils.outputSidecar(dest+"_meg.json", input)

    elif input["datatype"] == utils.EEG_EEGLAB:
        src=os.path.join(input_dir, 'eeg.fdt')
        utils.link(src, dest+"_eeg.fdt")
        src=os.path.join(input_dir, 'eeg.set')
        utils.link(src, dest+"_eeg.set")
        src=os.path.join(input_dir, 'channels.tsv')
        utils.link(src, dest+"_channels.tsv")
        src=os.path.join(input_dir, 'events.tsv')
        utils.link(src, dest+"_events.tsv")
        src=os.path.join(input_dir, 'events.json')
        utils.link(src, dest+"_events.json")
        src=os.path.join(input_dir, 'electrodes.tsv')
        utils.link(src, short_dest+"_electrodes.tsv")
        src=os.path.join(input_dir, 'coordsystem.json')
        utils.link(src, short_dest+"_coordsystem.json")

        utils.outputSidecar(dest+"_eeg.json", input)

    elif input["datatype"] == utils.EEG_EDF:
        src=os.path.join(input_dir, 'eeg.edf')
        utils.link(src, dest+"_eeg.edf")
        src=os.path.join(input_dir, 'channels.tsv')
        utils.link(src, dest+"_channels.tsv")
        src=os.path.join(input_dir, 'events.tsv')
        utils.link(src, dest+"_events.tsv")
        src=os.path.join(input_dir, 'events.json')
        utils.link(src, dest+"_events.json")
        src=os.path.join(input_dir, 'electrodes.tsv')
        utils.link(src, short_dest+"_electrodes.tsv")
        src=os.path.join(input_dir, 'coordsystem.json')
        utils.link(src, short_dest+"_coordsystem.json")

        utils.outputSidecar(dest+"_eeg.json", input)

    elif input["datatype"] == utils.EEG_BRAINVISION:
        src=os.path.join(input_dir, 'eeg.eeg')
        utils.link(src, dest+"_eeg.eeg")
        src=os.path.join(input_dir, 'eeg.vhdr')
        utils.link(src, dest+"_eeg.vhdr")
        src=os.path.join(input_dir, 'eeg.vmrk')
        utils.link(src, dest+"_eeg.vmrk")
        rc=os.path.join(input_dir, 'channels.tsv')
        utils.link(src, dest+"_channels.tsv")
        src=os.path.join(input_dir, 'events.tsv')
        utils.link(src, dest+"_events.tsv")
        src=os.path.join(input_dir, 'events.json')
        utils.link(src, dest+"_events.json")
        src=os.path.join(input_dir, 'electrodes.tsv')
        utils.link(src, short_dest+"_electrodes.tsv")
        src=os.path.join(input_dir, 'coordsystem.json')
        utils.link(src, short_dest+"_coordsystem.json")

        utils.outputSidecar(dest+"_eeg.json", input)

    elif input["datatype"] == utils.EEG_BDF:
        src=os.path.join(input_dir, 'eeg.bdf')
        utils.link(src, dest+"_eeg.bdf")
        src=os.path.join(input_dir, 'channels.tsv')
        utils.link(src, dest+"_channels.tsv")
        src=os.path.join(input_dir, 'events.tsv')
        utils.link(src, dest+"_events.tsv")
        src=os.path.join(input_dir, 'events.json')
        utils.link(src, dest+"_events.json")
        src=os.path.join(input_dir, 'electrodes.tsv')
        utils.link(src, short_dest+"_electrodes.tsv")
        src=os.path.join(input_dir, 'coordsystem.json')
        utils.link(src, short_dest+"_coordsystem.json")

        utils.outputSidecar(dest+"_eeg.json", input)

    else:
        #others are considered delivatives and the entire files/dirs will be copied over
        for key in input["keys"]:
            print("..", key)
            base = os.path.basename(config[key])
            src=config[key] #does not work with multi input!
            utils.link(src, dest)
        utils.outputSidecar(path+".json", input)
        
#fix IntendedFor field and PhaseEncodingDirection for fmap json files
for input in config["_inputs"]:
    if input["datatype"] == utils.FMAP:
        #set "correct" IntendedFor
        dest=fmap_dest #does not work with multi input!
        input_dir=fmap_dir #does not work with multi input!

        for key in input["keys"]:   
            if key.endswith("_json"):
                nii_key = key[:-5] #remove suffix "_json"
                src=os.path.join(input_dir, nii_key+".json")
                f_json = dest+"_"+nii_key+".json"
                utils.copyJSON(src, f_json, override={"IntendedFor": intended_paths})
                #fix PhaseEncodingDirection 
                nii_img=os.path.join(input_dir, nii_key+".nii.gz")
                if os.path.exists(nii_img):
                    print(nii_key)
                    updated_pe = utils.correctPE(input, nii_img, nii_key)
                    utils.copyJSON(f_json, f_json, override={"PhaseEncodingDirection": updated_pe})

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
