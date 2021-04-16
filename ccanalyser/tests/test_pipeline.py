import os
import sys
import subprocess
import shutil
import glob
import pytest



# Pre-run setup
dir_test = os.path.realpath(os.path.dirname(__file__))
dir_test_run = os.path.join(dir_test, 'pipeline_test_run')
dir_package = os.path.dirname(dir_test)
dir_repo = os.path.dirname(dir_package)
dir_pipeline = os.path.join(dir_package, 'pipeline')
dir_data = os.path.join(dir_package, "data")

# data paths
data_path_fq1 = os.path.join(dir_data, 'test', 'Slc25A37-test_1_1.fastq.gz')
data_path_fq2 = os.path.join(dir_data, 'test', 'Slc25A37-test_1_2.fastq.gz')
data_path_oligos = os.path.join(dir_data, 'test', 'mm9_capture_oligos_Slc25A37.bed')
data_path_genome = os.path.join(dir_data, 'test', 'data_for_pipeline_run', 'chr14.fa.gz')
data_path_chromsizes = os.path.join(dir_data, 'test', 'data_for_pipeline_run', 'chr14.fa.fai')
data_path_bowtie2_indicies = os.path.join(dir_data, 'test', 'data_for_pipeline_run', 'chr14_bowtie2_indicies')
data_path_config = os.path.join(dir_repo, 'config.yml')


@pytest.fixture(scope="module", autouse=True)
def setup():
    ## Set-up run.
    dir_root = os.getcwd()
    os.mkdir(dir_test_run) 
    os.chdir(dir_test_run)
    cwd = os.getcwd()

    ## Copy fastq file
    shutil.copy(data_path_fq1, cwd)
    shutil.copy(data_path_fq2, cwd)    

    ## Read config and replace with correct paths
    replacements = {'PATH_TO_VIEWPOINTS': data_path_oligos,
                    'PATH_TO_GENOME_FASTA': data_path_genome,
                    'PATH_TO_ALIGNER_INDICIES': data_path_bowtie2_indicies,
                    'PATH_TO_CHROMOSOME_SIZES': data_path_chromsizes,
                    'HUB_DIR': dir_test_run}
            
    with open(data_path_config, 'r') as config:
        with open('config.yml', 'w') as writer:
            for line in config:
                for key in replacements:
                    if key in line:
                        line = line.replace(key, replacements[key])

                writer.write(line)
    
    yield

    os.chdir(dir_root)
    shutil.rmtree(dir_test_run) 

def test_pipeline_fastq_preprocessing():

    cmd = f'python {dir_pipeline}/pipeline.py make fastq_preprocessing --local -p 4'
    completed = subprocess.run(cmd.split())
    assert completed.returncode == 0
    assert os.path.exists('ccanalyser_preprocessing/digested/Slc25A37-test_1_part0.flashed.fastq.gz')

def test_pipeline_pre_annotation():

    cmd = f'python {dir_pipeline}/pipeline.py make pre_annotation --local -p 4'
    completed = subprocess.run(cmd.split())
    assert completed.returncode == 0

def test_pipeline_post_annotation():

    cmd = f'python {dir_pipeline}/pipeline.py make post_annotation --local -p 4'
    completed = subprocess.run(cmd.split())
    assert completed.returncode == 0

def test_pipeline_post_ccanalyser_analysis():

    cmd = f'python {dir_pipeline}/pipeline.py make post_ccanalyser_analysis --local -p 4'
    completed = subprocess.run(cmd.split())
    assert completed.returncode == 0

def test_pipeline_all():

    cmd = f'python {dir_pipeline}/pipeline.py make --local -p 4'
    completed = subprocess.run(cmd.split())

    assert completed.returncode == 0
    assert os.path.exists('statistics/visualise_statistics.html')
    assert os.path.exists('pipeline_complete.txt')
    assert os.path.exists('ccanalyser_analysis/bigwigs/Slc25A37-test_1.raw.Slc25A37.bigWig')
    assert os.path.exists('capturec_test.hub.txt')




