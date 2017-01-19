# BDA (Big Data Application) Specification (v1.0)
(temporary name.. "BDAS".. sounds bad for one thing)

## Background

Scientists have been writing programs and scripts to do computations on their local computers or remote resources submitted through interfaces such as Matlab GUI or *bash terminals*. Each application will have its unique dependencies and input file must be organized in specific ways to run it. In order to reuse the application written by someone else, or simply to reproduce the results, each user must carefully install required software and prepare input files in a way that application author has intended.

### Application Abstraction

To mitigate this problem, developers has started to containerised their application (such as a Docker container) to reduce the complexity involved with installing the application and avoid dependency conflicts between different applications. However, this approach still leaves the task of preparing the input files for each application to the end user.

### Data Format Abstraction

Recently, there has been a proposal to create a standard data structures (such as BIDS for Neuroscience) and create containers (such as BIDS Apps) that are designed to receive input files in this common data structure and output another BIDS formatted data structure. Such approach can establish truly reusable software framework - at least within a specific domain of science. 

### Execution Abstraction

These advancements greatly benefits advanced domain experts, however, we need yet another layer of abstraction; commonly refer to as *workflow manager*, which is necessary to orchestrate the processing of large amounts of data, or make the applications accessible to novice users through an interface such as web portals. 

Indeed, many workflow management systems have been developed but so far there has not been a widely adopted ways to descrbie how to execute, and monitor our applications so that it can be used by various workflow managers.

## GOAL

This specification proposes a simple standard to allow abstraction of application execution that can be used by workflow management systems that can automate data staging, execution, monitoring of each applications. 

Please note that, "workflow management system" can be as simple as a small shell script that manages execution of a small and static set of applications, or a large software suite that can handle asynchronous executions and smart monitoring system with multi-user / multi-cluster capabilities.

## package.json

All BDA application must have `package.json` under on a root directory of the application (such as root folder of a git repo) This file can be created by hand, or by using [`npm init`](https://docs.npmjs.com/cli/init) command (npm is a commonly used package manager for nodejs - but the application itself does not have to be a node app).

```bash
$ npm init
```

[package.json]
```json
{
  "name": "bda-hello",
  "version": "1.0.0",
  "description": "sample BDA app",
  "main": "index.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "author": "Soichi Hayashi <hayashis@iu.edu>",
  "license": "MIT"
}
```

`package.json` describes basic information about your application (name, description, license, dependencies, etc..). "scripts" section will list BDA hooks that your application supports (see below)

## Application Hooks

At minimum, most workflow management systems must be able to.. 

* start your application (or run it synchronously if it's a very simple application), 
* stop your application - based on user request or other reasons
* monitor the status of your application, and know if it is completed / failed / running, etc..

BDA based workflow management system (such as SCA-workflow service) must publish list of these hooks inside `package.json` as following

```json
  "scripts": {
    "start": "start.sh",
    "stop": "stop.sh",
    "status": "status.sh"
  },
 ```

In this example, this application tells BDA enabled workflow management system that we have 3 shell scripts on a root directory of this application to start, stop, and monitor status of this application. Each hook can point to any script, or binaries. For example, "start", could be mapped to "start.py" if you prefer to use Python, or any binary executable, or even a command line such as "qsub start.sub".

All hook scripts must be executable (`chmod +x start.sh`)

### Start hook

Start.sh (or any script or binary that you've mapped "start" to) must *start* the application - but not actually *run* it. Meaning, you must nohup and spawn a new process (using & at the end of the command line) that actually do the processing. For example...

[start.sh]
```bash
#!/bin/bash
nohup matlab -r $SCA_SERVICE_DIR/main &
echo $? > run.pid
exit $?
```

If you are spawning your program, you should store the PID of your application so that later you can use to monitor the process or stop it (explained later).

Or, for PBS cluster, you can simply do

```bash
#!/bin/bash
qsub myapp.sub > jobid
exit $?
```

qsub simply submits the job to the local cluster and exits (it does not *run* your application), so you don't have to nohup / background the process.

Handling of input / output files will be described later.

If you have a very simple application that always exits in a matter of seconds, you may actually run the application itself inside start.sh and wait for it to exit, but all start.sh is expected to complete within a few seconds or otherwise risk being killed by the workflow management system - depending on its implementation.

#### Exit code
Start script should return exit code 0 for successful start or submission of your application, and non-0 for startup failure.

#### stdout/stderr
start.sh can output startup log to stdout, or any error message to stderr for such messages to be handled by the workflow manager.

### Status hook

This script can be executed by workflow manager periodically to gather status about the application. If can simply check for the PID of the application to make sure that it's running, or for a batch system, you can run qstat / condor_status type command to query for your application. 

Here is an example of job status checker for PBS jobs

[https://github.com/soichih/sca-service-dtiinit/blob/master/status.sh]

#### Exit Code

Status script should return one of following code

* 0 - Job is still running
* 1 - Job has finished successfully
* 2 - Job has failed
* 3 - Job status is *temporarily* unknown (should be retried later)

Status script return within a few seconds, or workflow manager may assume that the job status is unknown.

#### stdout/stderr

Any detail about the current job status can be reported by outputting any message to stdout, but it is optional. If your status script is smart enough to know the execution stage of your application, you could output a string such as "Job 25% complete - processing XYZ", for example. Message should be small, and usually be limited to a single string. Workflow manager may use it as a label for your workflow to be displayed on some UI.

### Stop Hook

This script will be executed when workflow manager wants to stop your job for whatever the reason (maybe user hit CTRL+C on the manager script, or user has requested termination of workflow via the web UI, etc..)

Here is an example stop script for PBS application

```bash
#!/bin/bash
qdel `cat jobid`
```

Your stop script may choose to do `kill -9 $pid`, or run application specific termination command like `docker stop $dockerid`.

#### Exit Code

* 0 - Application was cleanly terminated
* 1 - Failed to terminate the application cleanly.

If your stop script returns code 1, workflow manager may report back to the user that the termination has failed (and user may repeat the request), or some workflow manager may simply retry later on automatically.

## Environment Parameters

BDA application will receive all standard ENV parameters set by users or the cluster administrator. BDA workflow manager should also set following ENV parameters.

`$SCA_TASK_ID` Unique ID for this application instance.

`$SCA_TASK_DIR` Initial working directory for your application instance (not the application)

`$SCA_WORKFLOW_DIR` Directory where $SCA_TASK_DIR is stored (should be a parent of $SCA_TASK_DIR)

`$SCA_SERVICE` Name of the application executed. Often a github repo ID (like "soichih/sca-service-dtiinit")

`$SCA_SERVICE_DIR` Where the application is installed.

* "SCA" maybe renamed to "BDA" in the near future..

## Application Installation Directory

BDA is designed for Big Data and parallel processing. One common aspect of highly parallel environment is that, workflow manager often stage your application in a common shared filesystem, and share the same installation across all instances of your application. The working directory will be creased for each instance to stage your input and output data. 

BDA application will be executed with current directory set to this workfing directory, not the directory where the application is installed. This means that, in order to reference other files in your application, you will need to prefix them by `$SCA_SERVICE_DIR`.

For example, let's say you have following files in your application.

```
./package.json
./start.sh
./main.m
```

In your start.sh, even though it's main.m is located next to start.sh, however, your current working directory may not be set to another location. Therefore, you will need to prefix main.m with `$SCA_SERVICE_DIR`, like..

```bash
#!/bin/bash
nohup matlab -r $SCA_SERVICE_DIR/main &
echo $? > run.pid
exit $?
```

In order to help debugging your application during development, you'd like to have following at the top of your `start.sh`

```
if [ -z $SCA_SERVICE_DIR ]; then export SCA_SERVICE_DIR=`pwd`; fi
```

This will allow your application to be executed on the same directory where your current directory is.

Obviously, if you have no files other than the actual hook scripts themselves (maybe you are just running a docker container), you don't need to worry about this. Please see [https://github.com/soichih/sca-service-dtiinit/blob/master/start.sh] for more concrete example.


## Input Parameters (config.json)

For command line applications, input parameters can be passed via command line parameters. In order to allow workflow manager to execute BDA application, all input parameters must be passed via config.json. When users specify input parameters through various UI, workflow manager will pass that information by generating config.json containing all parameters used to execute the application. 

BDA application must parse config.json within the application, or your start.sh can do the parsing and pass parameters to your application via command line variables. 

For example, let's say user has specify "input_dwi" to be "/N/dc2/somewhere/test.dwi" and "paramA" to be 1234 on some UI. Workflow manager will construct following config.json and stores it in a working directory (which is set to current directory for your application).

```json
{
 "Input_dwi": "/N/dc2/somewhere/test.dwi",
 "paramA": 1234
}
```

Your application can then parse this directly, or in your start.sh you can do something like following to *pass* input arguments to your application.

```bash
#!/bin/bash
docker run -ti --rm \
-v `jq '.input_dwi[] config.json'`:/input/input.dwi \
someapp paramA=`jq '.paramA[]' config.json` \
> dockerid
```

`jq` is a popular JSON parsing tool for command line.

## Input Files

Handling of input files are outside the scope of BDA specification. It is a task for workflow manager to transfer / stage necessary input files (referenced in the config.json) prior to executing your application.

## Output Files

Your application can output any output data, or log files in the current working directory.  The structure of the output files is up to each application

It is customary, but not required, to generate a file named `products.json` in the working directory with a list of all output files generated in order for workflow manager to generate catalog of the output files generated by your application. `products.json` maybe useful, for example, if your application can generate N number of images or CSV files that can be used to draw graphs / images as part of workflow post-submission GUI.

## BDA Reference Implementation

Currently, the sca-wf is the only workflow manager that uses this specification, and can be used as a reference implementation.
[https://github.com/soichih/sca-wf]


