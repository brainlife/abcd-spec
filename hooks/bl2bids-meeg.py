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

            proc = None
            if "proc" in input["meta"]:
                proc = clean(input["meta"]["proc"])
            
            path+="/sub-"+subject
            if session:
                path+="/ses-"+session

            name="sub-"+subject
            if session:
                name+="_ses-"+session

            short_name=name

            if "task" in input["meta"]:
                name+="_task-"+clean(input["meta"]["task"])
            else:
                print("meta.task is not set.. defaulting to id%d") %(id+1)
                name+="_task-id%d" %(id+1)

            if run:
                name+="_run-"+run
            if proc:
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
            short_dest=path+"/"+short_name

            if input["datatype"] == MEG_CTF:
                src=os.path.join(input_dir, 'meg.ds')
                link(src, dest+"_meg.ds")
                src=os.path.join(input_dir, 'headshape.pos')
                link(src, short_dest+"_headshape.pos")
                src=os.path.join(input_dir, 'channels.tsv')
                link(src, dest+"_channels.tsv")
                src=os.path.join(input_dir, 'coordsystem.json')
                link(src, short_dest+"_coordsystem.json")

                outputSidecar(dest+"_meg.json", input)

            elif input["datatype"] == MEG_FIF:
                src=os.path.join(input_dir, 'meg.fif')
                link(src, dest+"_meg.fif")
                src=os.path.join(input_dir, 'headshape.pos')
                link(src, short_dest+"_headshape.pos")
                src=os.path.join(input_dir, 'channels.tsv')
                link(src, dest+"_channels.tsv")
                src=os.path.join(input_dir, 'coordsystem.json')
                link(src, short_dest+"_coordsystem.json")
                src=os.path.join(input_dir, 'calibration_meg.dat')
                link(src, short_dest+"_calibration_meg.dat")
                src=os.path.join(input_dir, 'crosstalk_meg.fif')
                link(src, short_dest+"_crosstalk_meg.fif")
                src=os.path.join(input_dir, 'destination.fif')
                link(src, short_dest+"_destination.fif")       

                outputSidecar(dest+"_meg.json", input)
                

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
