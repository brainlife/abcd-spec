#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
import nibabel as nib
from utils import getModality, correctPE, outputSidecar, copyJSON, link, copy_folder, clean

if __name__ == '__main__':

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

		    subject = None
		    if "subject" in input["meta"]:
		        subject = clean(input["meta"]["subject"])
		        path+="/sub-"+subject
		        name="sub-"+subject

		    session = None
		    if "session" in input["meta"]:
		        session = clean(input["meta"]["session"])
		        path+="/ses-"+session
		        name+="_ses-"+session

		    #all non raw data is stored under derivatives
		    modality=getModality(input)
		    print("--> Modality: %s" %modality)
		    if modality == "derivatives":
		        path += "/derivatives"
		        path += "/dt-"+input["datatype"]+".todo" #TODO - need to lookup datatype.bids.derivatives type
		    else:
		        path += "/"+modality

		    short_name=name

		    if "task" in input["meta"]:
		        name+="_task-"+clean(input["meta"]["task"])
		    elif "TaskName" in input["meta"]:
		        name+="_task-"+clean(input["meta"]["TaskName"])
		    else:
		        if input["datatype"] == FUNC_TASK:
		            print("meta.task is not set.. defaulting to rest")
		            name+="_task-rest"
		        if modality == "meg" or modality == "eeg":
		            print("meta.task is not set.. defaulting to id%d" %(id+1))
		            name+="_task-id%d" %(id+1)

		    #meta contains both acq and acquisition set to different value
		    #I am not sure why, but let's make acqusition take precedence
		    acq = None
		    if "acquisition" in input["meta"]:
		        acq = clean(input["meta"]["acquisition"])
		    elif "acq" in input["meta"]:
		        acq = clean(input["meta"]["acq"])
		        name+="_acq-"+acq
		        short_name+="_acq-"+acq

		    if "space" in input["meta"]:
		        space = clean(input["meta"]["space"])
		        name+="_space-"+space
		        short_name+="_space-"+space

		    run = None
		    if "run" in input["meta"]:
		        #TODO - run should be an integer and it should not be 0-padded according to Tal
		        #but on brainlife, it could be set to any string.. so I can't just convert to int as it could
		        #raise invalid literal ValueError exception
		        try:
		            _run = clean(input["meta"]["run"])
		            run = str(int(_run))
		            name+="_run-"+run
		        except ValueError:
		            print("can't parse run.. ignoring", input["meta"]["run"])

		    if "proc" in input["meta"]:
		        proc = clean(input["meta"]["proc"])
		        name+="_proc-"+proc

		    if "rec" in input["meta"]:
		        rec = clean(input["meta"]["rec"])
		        name+="_rec-"+rec

		    if "echo" in input["meta"]:
		        echo = clean(input["meta"]["echo"])
		        name+="_echo-"+echo

		    #make path directories
		    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

		    recover = ""
		    for i in path.split("/"):
		        recover += "../"

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

		    if input["datatype"] == ANAT_T1W:
		        src=os.path.join(input_dir, 't1.nii.gz')
		        link(src, dest+"_T1w.nii.gz")
		        outputSidecar(dest+"_T1w.json", input)

		    elif input["datatype"] == ANAT_T2W:
		        src=os.path.join(input_dir, 't2.nii.gz')
		        link(src, dest+"_T2w.nii.gz")
		        outputSidecar(dest+"_T2w.json", input)
		         
		    elif input["datatype"] == DWI:
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

		    elif input["datatype"] == MEG_CTF:
		        src=os.path.join(input_dir, 'meg.ds')
		        #link(src, dest+"_meg.ds", recover="")
		        copy_folder(src, dest+"_meg.ds") #just copy the content for now
		        src=os.path.join(input_dir, 'channels.tsv')
		        link(src, dest+"_channels.tsv")
		        src=os.path.join(input_dir, 'events.tsv')
		        link(src, dest+"_events.tsv")
		        src=os.path.join(input_dir, 'events.json')
		        link(src, dest+"_events.json")				
		        src=os.path.join(input_dir, 'headshape.pos')
		        link(src, short_dest+"_headshape.pos")
		        src=os.path.join(input_dir, 'coordsystem.json')
		        link(src, short_dest+"_coordsystem.json")

		        outputSidecar(dest+"_meg.json", input)

		    elif input["datatype"] == MEG_FIF:
		        src=os.path.join(input_dir, 'meg.fif')
		        link(src, dest+"_meg.fif")
		        src=os.path.join(input_dir, 'channels.tsv')
		        link(src, dest+"_channels.tsv")
		        src=os.path.join(input_dir, 'events.tsv')
		        link(src, dest+"_events.tsv")
		        src=os.path.join(input_dir, 'events.json')
		        link(src, dest+"_events.json")
		        src=os.path.join(input_dir, 'headshape.pos')
		        link(src, short_dest+"_headshape.pos")
		        src=os.path.join(input_dir, 'coordsystem.json')
		        link(src, short_dest+"_coordsystem.json")
		        src=os.path.join(input_dir, 'calibration_meg.dat')
		        link(src, short_dest+"_acq-calibration_meg.dat")
		        src=os.path.join(input_dir, 'crosstalk_meg.fif')
		        link(src, short_dest+"_acq-crosstalk_meg.fif")
		        src=os.path.join(input_dir, 'destination.fif')
		        link(src, short_dest+"_destination.fif")

		        outputSidecar(dest+"_meg.json", input)

		    elif input["datatype"] == EEG_EEGLAB:
		        src=os.path.join(input_dir, 'eeg.fdt')
		        link(src, dest+"_eeg.fdt")
		        src=os.path.join(input_dir, 'eeg.set')
		        link(src, dest+"_eeg.set")
		        src=os.path.join(input_dir, 'channels.tsv')
		        link(src, dest+"_channels.tsv")
		        src=os.path.join(input_dir, 'events.tsv')
		        link(src, dest+"_events.tsv")
		        src=os.path.join(input_dir, 'events.json')
		        link(src, dest+"_events.json")
		        src=os.path.join(input_dir, 'electrodes.tsv')
		        link(src, short_dest+"_electrodes.tsv")
		        src=os.path.join(input_dir, 'coordsystem.json')
		        link(src, short_dest+"_coordsystem.json")

		        outputSidecar(dest+"_eeg.json", input)

		    elif input["datatype"] == EEG_EDF:
		        src=os.path.join(input_dir, 'eeg.edf')
		        link(src, dest+"_eeg.edf")
		        src=os.path.join(input_dir, 'channels.tsv')
		        link(src, dest+"_channels.tsv")
		        src=os.path.join(input_dir, 'events.tsv')
		        link(src, dest+"_events.tsv")
		        src=os.path.join(input_dir, 'events.json')
		        link(src, dest+"_events.json")
		        src=os.path.join(input_dir, 'electrodes.tsv')
		        link(src, short_dest+"_electrodes.tsv")
		        src=os.path.join(input_dir, 'coordsystem.json')
		        link(src, short_dest+"_coordsystem.json")

		        outputSidecar(dest+"_eeg.json", input)

		    elif input["datatype"] == EEG_BRAINVISION:
		        src=os.path.join(input_dir, 'eeg.eeg')
		        link(src, dest+"_eeg.eeg")
		        src=os.path.join(input_dir, 'eeg.vhdr')
		        link(src, dest+"_eeg.vhdr")
		        src=os.path.join(input_dir, 'eeg.vmrk')
		        link(src, dest+"_eeg.vmrk")
		        rc=os.path.join(input_dir, 'channels.tsv')
		        link(src, dest+"_channels.tsv")
		        src=os.path.join(input_dir, 'events.tsv')
		        link(src, dest+"_events.tsv")
		        src=os.path.join(input_dir, 'events.json')
		        link(src, dest+"_events.json")
		        src=os.path.join(input_dir, 'electrodes.tsv')
		        link(src, short_dest+"_electrodes.tsv")
		        src=os.path.join(input_dir, 'coordsystem.json')
		        link(src, short_dest+"_coordsystem.json")

		        outputSidecar(dest+"_eeg.json", input)

		    elif input["datatype"] == EEG_BDF:
		        src=os.path.join(input_dir, 'eeg.bdf')
		        link(src, dest+"_eeg.bdf")
		        src=os.path.join(input_dir, 'channels.tsv')
		        link(src, dest+"_channels.tsv")
		        src=os.path.join(input_dir, 'events.tsv')
		        link(src, dest+"_events.tsv")
		        src=os.path.join(input_dir, 'events.json')
		        link(src, dest+"_events.json")
		        src=os.path.join(input_dir, 'electrodes.tsv')
		        link(src, short_dest+"_electrodes.tsv")
		        src=os.path.join(input_dir, 'coordsystem.json')
		        link(src, short_dest+"_coordsystem.json")

		        outputSidecar(dest+"_eeg.json", input)
        
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
