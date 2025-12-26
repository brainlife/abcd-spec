# Application for Big Computational Data (ABCD) Specification (v1.1)

#### MIT Copyright (c) 2020 brainlife.io The University of Texas at Austin and Indiana University

### Authors
- Soichi Hayashi (hayashis@iu.edu)

### Contributors
- Franco Pestilli (pestilli@utexas.edu)

### Funding Acknowledgement
brainlife.io is publicly funded and for the sustainability of the project it is helpful to Acknowledge the use of the platform. We kindly ask that you acknowledge the funding below in your publications and code reusing this code.

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://grantome.com/grant/NIH/R01-EB029272-01)

### Citations
We kindly ask that you cite the following articles when publishing papers and code using this code. 

1. Avesani, P., McPherson, B., Hayashi, S. et al. The open diffusion data derivatives, brain data upcycling via integrated publishing of derivatives and reproducible open cloud services. Sci Data 6, 69 (2019). [https://doi.org/10.1038/s41597-019-0073-y](https://doi.org/10.1038/s41597-019-0073-y)

## Background

Scientists routinely use applications to compute and perform analyses either using personal computers (local hardware) or remote resources (remote/distal hardware, such as high performance clusters or cloud systems). Scientists must be familiar with variety of methods and programming languages in order to use these application effectively. Scientists must be able to install these application in diverse environment, and prepare input data to meet each application requirements by organizing, or converting their input data types. Needless to say, this makes it difficult to reproduce other scientists's results, or to reuse applications developed by other collaborators.

### Application Abstraction

As a way to mitigate these problem, scientists have recently started containerising their applications using tools such as Docker. Containerization can reduce the complexity involved with installing applications and avoid dependency conflicts between different applications. This approach, however, still leaves the major task of preparing the appropriate input files for each applications and parsing of output files to the end user.

### Data Format Abstraction

Recently, there has been a proposal to create a standard data structures such as BIDS for Neuroscience (or BioXSD for Bioinformatics?). By applying these standard to the application containerization effort, it could greatly reduce the overhead of preparing the input and output files and foster truly reusable software framework within a specific domain of science.

### Execution Abstraction

These advancements greatly benefit advanced domain experts, however, we need yet another layer of abstraction to execute these application to automate the execution and monitoring of a workflow. *Workflow manager* is commonly used to orchestrate complex series of applications to deal with large amount of computational data, or to create a facade application to wrap a complicated subsystem with a simpler interface.

Indeed, many workflow management systems have been developed, but so far there has not been a widely adopted generic specification describing how to start, stop, and monitor applications so that applications can be programmatically executed across different workflow managers. This lack of standard necessitates developers to create different applications (or the application wrappers) thus making it difficult for reuse.

## Specification

This specification proposes a very simple standard to allow abstraction of application execution and monitoring in order to make it easier for workflow management systems to interface with compliant applications. This specification does not extend to how the entire workflow is constructed like [Common Workflow Language](https://github.com/common-workflow-language/common-workflow-language), nor how UI should be constructed based on ints input / output format like [GenApp](https://cwiki.apache.org/confluence/display/AIRAVATA/GenApp). A developer of the application can adopt combination of other such specifications in order to execute it on specific workflow systems that require more stringent specifications. 

The main usecase for this specification to assist the creation of REST API driven workflow manager - to be access via Web interface.

> Please note that, in this specification, *workflow management system* can be as simple as a small shell script that manages execution of a small and static set of applications, or a large software suite that can handle asynchronous executions of multi-user / multi-cluster workflows.

### package.json (optional)

ABCD compliant application can provide `package.json` under the root directory of the application (such as root folder of a git repo) This file can be created by hand, or by using [`npm init`](https://docs.npmjs.com/cli/init) command.

```json
{
  "abcd": {
    "start": "./start.sh",
    "stop": "./stop.sh",
    "status": "./status.sh"
  }
}
```

The scripts listed under `abcd` keys are the `application hooks` which are just any bash scripts that are meant to be executed by the workflow manager (but it can also be executed locally to test your application).

At minimum, most workflow management systems must be able to.

* Start your application (or run it synchronously if it's a very simple application), 
* Stop your application - based on user request or other reasons
* Monitor the status of your application, and know if it is completed / failed / running, etc..

In above example, ABCD compliant workflow management system knows that we have 3 shell scripts on a root directory of this application to `start`, `stop`, and monitor `status` of this application. Each hook can point to any script (bash, python, javascript, etc) or compiled executables. 
All hook scripts must be executable (`chmod +x start.sh`)

The `package.json` is optional for application that runs on remote resource that provides the `default hooks`. Under this scenario, application should provide `main` executable that simply runs the application (not start it). Please see "Default Hooks" section below.

### `start` Hook

`start.sh` (or any script or binary that you've mapped "start" to) must *start* the application; the script itself should return immediately after it spawns another thread that runs the actual program. 

An example start script for a vanilla VM.

```bash
#!/bin/bash
nohup time bash -c "./main; echo \$? > exit-code" > output.log 2> error.log &
echo $! > pid
```

This script runs `main` which is the actual application for this app, and *nohup*s it so that the start.sh itself can safely exit. It also stores the pid of the started process so that `status` or `stop` script can interact with the application process.

Or, for PBS cluster, you might want to do something like..

```bash
#!/bin/bash
qsub myapp.sub > jobid
exit $?
```

qsub simply submits the job to the local cluster and exits (it does not *run* your application), so you don't have to nohup / background the process.

If you have a very simple application that always finishes in a matter of seconds, you may actually run the application itself inside start.sh and block before exiting, but all start.sh is expected to complete within a few seconds. Otherwise you will risk your application to be be killed by the workflow management system - depending on its implementation.

#### Exit code

Start script should return exit code 0 for successful start or submission of your application, and non-0 for startup failure.

#### stdout/stderr

Start script can output startup log to stdout, or any error messages to stderr. Such messages should be handled by the workflow manager and relayed to the user in appropriate manner.

### `status` Hook

This script will be executed by workflow manager periodically to query status of the application. You can simply check for the PID of the application to make sure that it's running, or for a batch system, you can use commands such as `qstat` or `condor_status` to query for your application.

Please see [ABCD default hook scripts](https://github.com/brain-life/abcd-spec/tree/master/hooks) as an example.

#### Exit Code

Status script should return one of following code

* 0 - Job is still running
* 1 - Job has finished successfully
* 2 - Job has failed
* 3 - Job status is *temporarily* unknown (should be retried later)

Status script return within a few seconds, or workflow manager may assume that the job status is unknown.

#### stdout/stderr

Any detail about the current job status can be reported by outputting any messages to stdout. You script can simply check for the process/job to be running and state that it is running, or you can construct the script to analyze the log file to find out detailed status of yoru application and output a message such as "Job 25.5% complete - processing XYZ", as an example. Any string output to stdout should be treated by the workflow manager as a status message and relayed to the users in the appropriate manner. Therefore, any stdout from the status script should be small (usually a single line).

### `stop` Hook

This script will be executed when workflow manager wants to stop your job for whatever the reason (maybe user hit CTRL+C on the simple workflow manager script, or user has requested termination of workflow via the web UI of the portal, etc..)

Here is an example stop script for PBS application

```bash
#!/bin/bash
qdel `cat jobid`
```

`jobid` is created by `start.sh` in this example. 

Or, your stop script may choose to do `kill -9 $pid`, or run application specific termination command like `docker stop $dockerid`.

#### Exit Code

Stop script should return one of following code.

* 0 - Application was cleanly terminated
* 1 - Failed to terminate the application cleanly.

If your stop script returns code 1, workflow manager may report back to the user that the termination has failed (and user may repeat the request), or some workflow manager may simply retry later on automatically.
ret=$?

### Default hooks

If application does not provide `package.json`, or `abcd` key is missing inside `package.json`, following hook configurations is used as default.

```json
{
  "abcd": {
    "start": "start",
    "stop": "stop",
    "status": "status"
  }
}
```

This means that, by default, all ABCD applications are started by an executable called `start`, and stopped by an executable called `stop`, and monitored by executing `status`. These executables must be installed on the remote resource by resource administrator, and proper PATH is set to find those executable under the user account that the resource is configured for.

ABCD specification repository provides a default hooks for direct (vanilla VM), PBS, and slurm cluster and can be installed simply by cloning this repository.

```
git clone https://github.com/brain-life/abcd-spec.git ~/abcd-spec
``` 

Then, PATH must be configured to look for a particular set of abcd hooks under ~/.bashrc. For PBS,

```bash
export PATH=~/abcd-spec/pbs:$PATH
```

For slurm

```bash
export PATH=~/abcd-spec/slurm:$PATH
```

And for Vanilla VM

```bash
export PATH=~/abcd-spec/direct:$PATH
```

#### Default `start` hook

The default `start` hook will look for an executable called `main` under the current directory (application repo's root directory) and run the app using whichever the most appropriate mechanism to start a job for the resource. For PBS cluster, `~/abcd-spec/pbs/start` would use qsub, for example. 

To reiterate, if application does not provide its own `package.json`, workflow manager will look for the default `start` hook installed on the remote resource (so it must exist there, or application will fail to start). The default `start` hook will then look for `main` within the application's current directory, so the application must provide `main` if it does not provide `package.json`.

By application relying on resource's default hooks, application can be made simpler (only `main` needs to exist) and can be made to handle variety of remote resources as remote resource will be responsible to provide appropriate ABCD hooks.

### Application Dependencies

Any dependencies that application uses must be installed on all remote resources where the application is enabled to run on with correct version and correct installation method. Application should be able to reference specific version of the dependencies (like /usr/local/dipy_0.12) so that each application can reference correct versions of any dependencies. Once the dependencies are installed, it should not be modified. 

Such environment is difficult to maintain, extremely brittle, and often impossible to properly construct. For your application to be truly portable, you should publish `Dockerfile` as part of your application with instruction on how to build a docker container to run your application. You can then configure dockerhub to [auto-build](https://docs.docker.com/docker-hub/builds/) your container whenever you make changes to your github repository. Once this is done, on your `start.sh` (or `main` if you are using default hook), you can launch your container via [singularity](http://singularity.lbl.gov/docs-docker) like following.

```
#!/bin/bash
singularity exec docker://myorg/myapp
```

By dockerizing your application, your app can run on wide range of remote resources that has singularity installed.

### Environment Parameters

ABCD application should receive all standard ENV parameters set by users or the cluster administrator. ABCD workflow manager should also set various workflow manager specific ENV parameters. For example, [Amaretti](https://github.com/brain-life/amaretti) provides following set of parameters to all tasks.

```       
TASK_ID: A unique task ID.
USER_ID: For multi-user workflow manager, the ID of the user who made the request
SERVICE: Name of the service (github repo name such as "brain-life/app-life")
SERVICE_BRANCH: Name of the service branch (if specified by the user)
```

### Workflow directory

ABCD workflow manager should git clones requested service on remote resource's scratch space as a new work directory for each task and set the current directory to that directory prior to executing ABCD hooks. Application can therefore expect to find all files that are distributed via the specified github repository (with `--depth 1` to omit git history, however).

### Input Parameters (config.json)

ABCD workflow manager should pass input parameters to ABCD applications through a JSON file named `config.json` created on the work directory for each task prior to executing `start` hook. ABCD application then must parse the `config.json` to pull any input parameters.

For example, let's say user has specified `dwi` parameter to be `"/N/dc2/somewhere/test.dwi"` and `count` parameter to be `100` through some UI. Workflow manager will construct following `config.json` and stores it in a working directory (on the current directory) prior to application execution.

```json
{
 "dwi": "/N/dc2/somewhere/test.dwi",
 "count": 100
}
```

Your application can parse this directly using any JSON parsing library, or application's start hook can parse it using [jq](https://stedolan.github.io/jq)command line JSON parsing tool.

```bash
#!/bin/bash
dwi=$(jq -r .dwi config.json)
count=$(jq -r .count config.json)
nohup ./myapp --dwi $dwi --count $count &
```

### Input Files

Staging of input files are outside the scope of ABCD specification. It is a task for workflow manager to transfer / stage any necessary input files (referenced in the `config.json`) prior to executing your application.

### Output Files

Your application must produce any output files, or intermediary files (including any log files) inside the current working directory. You must not make any modification outside the working directory, although you most likely need to read input files stored outside it.

ABCD specification itself does not specify how you should format your output data. The structure of the output data are up to each application and the platform that application is developed for. For example, all Brain-Life app should output datasets in a compatible format that the application is registered to output through Brain-Life. This allows the output from your app to be used as input to another app.

## Misc.

### ABCD Badge

For all ABCD specification compliant services, you can display following badge on top of the README.md to indicate that your service can be executed on all workflow manager who supports ABCD specification.

[![Abcdspec-compliant](https://img.shields.io/badge/ABCD_Spec-v1.1-green.svg)](https://github.com/brain-life/abcd-spec)

```
[![Abcdspec-compliant](https://img.shields.io/badge/ABCD_Spec-v1.1-green.svg)](https://github.com/brain-life/abcd-spec)
```

### ABCD Reference Application Implementations

Examples of ABCD compliant services can be found under [Brain-Life Application](https://github.com/brain-life/?tab=repositories&q=app)

### ABCD Reference Workflow Manager Implementation

Currently, [Amaretti](https://github.com/brain-life/amaretti) is the the only workflow manager that uses this specification, and can be used as a reference implementation for this specification.


