import click 

@click.group()
def cli():
    """Contains methods for interaction counting, storing, bedgraph generation, comparisons and plotting.
    """


@cli.command()
@click.argument('union_bedgraph')
@click.option('-n', '--capture_name', help='Name of capture probe, must be present in viewpoint file.', required=True)
@click.option('-c', '--capture_viewpoints', help='Path to capture viewpoints bed file', required=True)
@click.option('-o', '--output_prefix', help='Output prefix for pairwise statistical comparisons', default='out')
@click.option('--design_matrix', help='Path tsv file containing sample annotations (N_SAMPLES * N_INFO_COLUMNS)', default=None)
@click.option('--grouping_col', help='Column to use for grouping replicates', default='condition')
@click.option('--threshold_count', help='Minimum count required to be considered for analysis', default=20, type=click.FLOAT)
@click.option('--threshold_q', help='Upper threshold of q-value required for output.', default=0.05, type=click.FLOAT)
@click.option('--threshold_mean', help='Minimum mean count required for output.', default=0, type=click.FLOAT)
def differential(*args, **kwargs):
    """
    Identifies differential interactions between conditions.

    Parses a union bedgraph containg reporter counts from at least two conditions with
    two or more replicates for a single capture probe and outputs differential interaction
    results. Following filtering to ensure that the number of interactions is above the required 
    threshold (--threshold_count), diffxpy is used to run a wald test after 
    fitting a negative binomial model to the interaction counts.The options to filter
    results can be filtered by a minimum mean value (threshold_mean) and/or 
    maximum q-value (threshold-q) are also provided.

    Notes:
        
     Currently both the capture viewpoints and the name of the probe being analysed must 
     be provided in order to correctly extract cis interactions.
 
     If a N_SAMPLE * METADATA design matrix has not been supplied, the script 
     assumes that the standard replicate naming structure has been followed 
     i.e. SAMPLE_CONDITION_REPLICATE_(1|2).fastq.gz.    
    """

    from capcruncher.cli.reporters_differential import differential
    differential(*args, **kwargs) 




@cli.command()
@click.argument("cooler_fn")
@click.option(
    "-n",
    "--capture_names",
    help="Capture to extract and convert to bedgraph, if not provided will transform all.",
    multiple=True,
)
@click.option("-o", "--output_prefix", help="Output prefix for bedgraphs")
@click.option(
    "--normalise",
    help="Normalised bedgraph (Correct for number of cis reads)",
    default=False,
    is_flag=True,
)
@click.option(
    "--binsize",
    help="Binsize to use for converting bedgraph to evenly sized genomic bins",
    default=0,
)
@click.option("--gzip", help="Compress output using gzip", default=False, is_flag=True)
@click.option(
    "--scale_factor",
    help="Scale factor to use for bedgraph normalisation",
    default=1e6,
    type=click.INT,
)
@click.option(
    "--sparse/--dense",
    help="Produce bedgraph containing just positive bins (sparse) or all bins (dense)",
    default=True,
)
def pileup(*args, **kwargs):
    """
    Extracts reporters from a capture experiment and generates a bedgraph file.

    Identifies reporters for a single probe (if a probe name is supplied) or all capture 
    probes present in a capture experiment HDF5 file. 
    
    The bedgraph generated can be normalised by the number of cis interactions for
    inter experiment comparisons and/or binned into even genomic windows.
    """

    from capcruncher.cli.reporters_pileup import bedgraph
    bedgraph(*args, **kwargs)


@cli.command()
@click.argument("reporters")
@click.option("-o", "--output", help="Name of output file", default="counts.tsv.gz")
@click.option(
    "--remove_exclusions",
    default=False,
    help="Prevents analysis of fragments marked as proximity exclusions",
    is_flag=True,
)
@click.option(
    "--remove_capture",
    default=False,
    help="Prevents analysis of capture fragment interactions",
    is_flag=True,
)
@click.option(
    "--subsample",
    default=0,
    help="Subsamples reporters before analysis of interactions",
)
def count(*args, **kwargs):
    """
    Determines the number of captured restriction fragment interactions genome wide.

    Parses a reporter slices tsv and counts the number of unique restriction fragment 
    interaction combinations that occur within each fragment.
    
    Options to ignore unwanted counts e.g. excluded regions or capture fragments are provided. 
    In addition the number of reporter fragments can be subsampled if required.
    """
    from capcruncher.cli.reporters_count import count
    count(*args, **kwargs)

@cli.command()
@click.argument("cooler_fn", required=True)
@click.option(
    "-c",
    "--coordinates",
    help="Coordinates in the format chr1:1000-2000 or a path to a .bed file with coordinates",
)
@click.option(
    "-r",
    "--resolution",
    help="Resolution at which to plot. Must be present within the cooler file.",
    required=True,
    multiple=True,
)
@click.option(
    "-n",
    "--capture_names",
    multiple=True,
    help="Capture names to plot. If not supplied will plot all",
)
@click.option(
    "--normalisation",
    help="Normalisation method for heatmap",
    default="n_interactions",
    type=click.Choice(["n_interactions", "n_rf_n_interactions", "ice"]),
)
@click.option("--cmap", help="Colour map to use for plotting", default="jet")
@click.option("--vmax", help="Vmax for plotting", default=0, type=click.FLOAT)
@click.option("--vmin", help="Vmin for plotting", default=0, type=click.FLOAT)
@click.option("-o", "--output_prefix", help="Output prefix for plot", default="")
@click.option("--remove_capture", help='Removes the capture probe bins from the matrix', is_flag=True, default=False)
def plot(*args, **kwargs):
    """
    Plots a heatmap of reporter interactions.

    Parses a HDF5 file containg the result of a capture experiment (binned into even genomic windows)
    and plots a heatmap of interactions over a specified genomic range. If a capture probe name 
    is not supplied the script will plot all probes present in the file.

    Heatmaps can also be normalised (--normalise) using either:

     - n_interactions: The number of cis interactions.
     - n_rf_n_interactions: Normalised to the number of restriction fragments making up both genomic bins
                           and by the number of cis interactions.
     - ice: `ICE normalisation <https://www.nature.com/articles/nmeth.2148>`_ followed by number of cis interactions
             correction.  
    """
    from capcruncher.cli.reporters_heatmap import plot
    plot(*args, **kwargs)

@cli.group()
def store():
    """
    Store reporter counts.

    These commands store and manipulate reporter restriction fragment interaction 
    counts as cooler formated groups in HDF5 files.

    See subcommands for details. 

    """

@store.command(name='fragments')
@click.argument("counts", required=True)
@click.option(
    "-f",
    "--fragment_map",
    help="Path to digested genome bed file",
    required=True,
)
@click.option(
    "-c",
    "--capture_viewpoints",
    "capture_viewpoints",
    help="Path to capture viewpoints file",
    required=True,
)
@click.option(
    "-n",
    "--capture_name",
    "capture_name",
    help="Name of capture viewpoint to store",
    required=True,
)
@click.option(
    "-g",
    "--genome",
    help="Name of genome",
)
@click.option(
    "--suffix",
    help="Suffix to append after the capture name for the output file",
)
@click.option(
    "-o",
    "--output",
    help="Name of output file. (Cooler formatted hdf5 file)",
    default="out.hdf5",
)
def store_fragments(*args, **kwargs):
    """
    Stores restriction fragment interaction combinations at the restriction fragment level.

    Parses reporter restriction fragment interaction counts produced by 
    "capcruncher reporters count" and gerates a cooler formatted group in an HDF5 File. 
    See `https://cooler.readthedocs.io/en/latest/` for further details.
    """
    from capcruncher.cli.reporters_store import fragments
    fragments(*args, **kwargs)

@store.command(name='bins')
@click.argument("cooler_fn", required=True)
@click.option(
    "-b",
    "--binsizes",
    help="Binsizes to use for windowing",
    default=(5000,),
    multiple=True,
    type=click.INT,
)
@click.option(
    "--normalise",
    is_flag=True,
    help="Enables normalisation of interaction counts during windowing",
)
@click.option(
    "--overlap_fraction",
    help="Minimum overlap between genomic bins and restriction fragments for overlap",
    default=0.5,
)
@click.option(
    "-p",
    "--n_cores",
    help="Number of cores used for binning",
    default=4,
    type=click.INT,
)
@click.option(
    "--scale_factor",
    help="Scaling factor used for normalisation",
    default=1e6,
    type=click.INT,
)
@click.option(
    "--conversion_tables",
    help="Pickle file containing pre-computed fragment -> bin conversions.",
    default=None,
)
@click.option(
    "-o",
    "--output",
    help="Name of output file. (Cooler formatted hdf5 file)",
    default="out.hdf5",
)
def store_bins(*args, **kwargs):
    """
    Convert a cooler group containing restriction fragments to constant genomic windows

    Parses a cooler group and aggregates restriction fragment interaction counts into 
    genomic bins of a specified size. If the normalise option is selected,  
    columns containing normalised counts are added to the pixels table of the output
    """
    from capcruncher.cli.reporters_store import bins
    bins(*args, **kwargs)

@store.command(name='merge')
@click.argument("coolers", required=True, nargs=-1)
@click.option("-o", "--output", help="Output file name")
def store_merge(*args, **kwargs):
    """
    Merges capcruncher cooler files together.
    
    Produces a unified cooler with both restriction fragment and genomic bins whilst
    reducing the storage space required by hard linking the "bins" tables to prevent duplication.
    """
    from capcruncher.cli.reporters_store import merge
    merge(*args, **kwargs)
