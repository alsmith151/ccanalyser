# CCanalyser

## Analysis software for Capture-C, Tri-C and Tiled-C data.

CCanalyser is a tool designed to automate the processing of Capture-C, Tri-C and Tiled-C data from fastq files. The package is effectively a re-implementation of [CCseqBasicS](https://github.com/Hughes-Genome-Group/CCseqBasicS) that combines [CaptureCompare](https://github.com/djdownes/CaptureCompare). 

The package is entirely written in python and  consists of a highly configurable data processing pipline and supporting command line interface to enable finer grained control.

## Installation

As the pipeline relies on conda enviroments to run, it is highly recomended that a conda enviroment is first generated using the provided yaml file.

If conda is already installed then clone the repository:

```
git clone https://github.com/sims-lab/capture-c.git
conda env create -f ccanalyser_conda_env.yml
conda activate cc
```

### Installing the package

#### Github

```
git clone https://github.com/sims-lab/capture-c.git
pip install .
```

#### PIP 

The package should shortly be on pip (if I can figure out how)

```
pip install ccanalyser
```

Please see the documentation for further details.

## Running the pipeline

* Create a working directory with the fastq files required for the analysis.
* Copy [config.yml](https://github.com/sims-lab/capture-c/blob/master/config.yml) to the working directory
* Edit config.yml to suit your experiment and set-up.

Run the pipeline:

```
# Activate the conda enviroment if it has not already been activated.
conda activate cc

# Runs the pipeline untill all tasks are completed
ccanalyser pipeline make
```

If a cluster is not being used, or there is an issue with the DRMAA interface. The pipeline can be run locally with the number of parallel jobs set by the -p flag:

```
ccanalyser pipeline make --local -p 4
```

