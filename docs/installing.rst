Installing
##########

Pre-Installation recommendations
********************************

1. Install conda if it has not been already using the `conda install instructions <https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html#install-linux-silent>`_.

2. If capcruncher is **not** being installed through conda, first generate a new conda
   environment using the yaml file in the `GitHub repository <https://github.com/sims-lab/CapCruncher/blob/master/environment.yml>`_:

::
    
    wget https://raw.githubusercontent.com/sims-lab/CapCruncher/master/environment.yml
    conda env create -f environment.yml
    conda activate cc

1. If you intend to use a cluster e.g. SunGrid engine/SLURM add the path to the DRMAA interface to your .bashrc:

:: 

    # Access to the DRMAA library: https://en.wikipedia.org/wiki/DRMAA
    echo "export DRMAA_LIBRARY_PATH=/<full-path>/libdrmaa.so" >> ~/.bashrc

    # You can get this value from your configured environment:
    env | grep DRMAA_LIBRARY_PATH

    # or just look for the library:
    find / -name "*libdrmaa.so"


Installation
************

The package can be installed in several ways:

.. note::

    Currently only github installation is supported


1. Install from conda:
:: 

    conda install capcruncher # do not use: not available yet

2. Install from pypi:
:: 

    pip install capcruncher # do not use: not available yet

3. Install from GitHub:

:: 

    git clone https://github.com/sims-lab/capture-c.git
    cd capture-c
    pip install .
