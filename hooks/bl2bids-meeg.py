#!/usr/bin/env python3

import json
import pathlib
import os
import sys
import re
from utilsMEEG import getModality, outputSidecar, copyJSON, link, clean


if __name__ == '__main__':    

    #datatype IDs that we handle 
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

	    short_name=name

	    #task is mandatory
	    if "task" in input["meta"]:
                name+="_task-"+clean(input["meta"]["task"])
            else:
                print("meta.task is not set.. defaulting to id%d") %(id+1)
                name+="_task-id%d" %(id+1)

	    if "acq" in input["meta"]:
                acq = clean(input["meta"]["acq"])
		name+="_acq-"+acq
		short_name+="_acq-"+acq

	    if "space" in input["meta"]:
                space = clean(input["meta"]["space"])
		name+="_space-"+space
		short_name+="_space-"+space

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

            modality=getModality(input)
            path += "/"+modality
            pathlib.Path(path).mkdir(parents=True, exist_ok=True)

            #symlink recovery path
            recover = ""
            for i in path.split("/"):
                recover += "../"

            input_dir = os.path.join('..', input["task_id"], input["subdir"])
            dest=path+"/"+name
            short_dest=path+"/"+short_name #does not contain task and run

            if input["datatype"] == MEG_CTF:
                src=os.path.join(input_dir, 'meg.ds')
                link(src, dest+"_meg.ds")
		src=os.path.join(input_dir, 'channels.tsv')
                link(src, dest+"_channels.tsv")
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
                src=os.path.join(input_dir, 'channels.tsv')
                link(src, dest+"_channels.tsv")
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
                src=os.path.join(input_dir, 'electrodes.tsv')
                link(src, short_dest+"_electrodes.tsv")
                src=os.path.join(input_dir, 'coordsystem.json')
                link(src, short_dest+"_coordsystem.json")

		outputSidecar(dest+"_eeg.json", input)

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
