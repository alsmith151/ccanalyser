import os
import pandas as pd
import diffxpy.api as de
import click
import itertools

from ccanalyser.cli import cli 

def get_chromosome_from_name(df: pd.DataFrame, name: str):
    chrom = (df.query(f'name == "{name}"')
               ['chrom']
               .iloc[0])
    return chrom
    

@cli.command()
#@click.command()
@click.argument('union_bedgraph')
@click.option('-n', '--capture_name', help='Name of capture probe, must be present in oligo file.', required=True)
@click.option('-c', '--capture_oligos', help='Path to capture oligos bed file', required=True)
@click.option('-o', '--output_prefix', help='Output prefix for pairwise statistical comparisons', default='out')
@click.option('--design_matrix', help='Path tsv file containing sample annotations (N_SAMPLES * N_INFO_COLUMNS)', default=None)
@click.option('--grouping_col', help='Column to use for grouping replicates', default='condition')
@click.option('--threshold_count', help='Minimum count required to be considered for analysis', default=20, type=click.FLOAT)
@click.option('--threshold_q', help='Upper threshold of q-value required for output.', default=0.05, type=click.FLOAT)
@click.option('--threshold_mean', help='Minimum mean count required for output.', default=0, type=click.FLOAT)
def interactions_differential(union_bedgraph: os.PathLike,
                              capture_name: str,
                              capture_oligos: os.PathLike,
                              output_prefix: os.PathLike = 'differential',
                              design_matrix: os.PathLike = None,
                              grouping_col: str = 'condition',
                              threshold_count: float = 20,
                              threshold_q: float = 0.05,
                              threshold_mean: float = 0):
    
    '''Identifies differential interactions between conditions'''
    
    df_bdg = pd.read_csv(union_bedgraph, sep='\t')
    df_oligos = pd.read_csv(capture_oligos, sep='\t', names=['chrom', 'start', 'end', 'name'])

    #  If design matrix present then use it. Else will assume that the standard format has been followed:
    #  i.e. NAME_TREATMENT_REPLICATE
    if design_matrix:
        df_design = pd.read_csv(design_matrix, sep='\t')
    else:
        col_dict = {col: '_'.join(col.split('_')[:-1]) for col in df_bdg.columns[3:]}
        df_design = pd.Series(col_dict).to_frame(grouping_col)
    

    # Only cis interactions
    capture_chrom = get_chromosome_from_name(df_oligos, name=capture_name)
    df_bdg_counts = df_bdg.query(f'chrom == "{capture_chrom}"')

    # Only counts
    df_bdg_counts = df_bdg_counts.iloc[:, 3:]

    # Only with number of interactions > threshold per group in at least 2 replicates
    df_bdg_counts = (df_bdg_counts.groupby(df_design[grouping_col], axis=1)
                                  .apply(lambda df: df[(df >= threshold_count).sum(axis=1) >= 2])
                                  .fillna(0))
    
    # Run differential testing
    count_data = df_bdg_counts.transpose().values
    fragment_names = df_bdg_counts.index.values

    tests = de.test.pairwise(count_data, 
                             grouping=grouping_col, 
                             sample_description=df_design,
                             gene_names=fragment_names,
                             test='wald',
                             lazy=False)
       
    # Go through all of the pairwise tests
    for g1, g2 in itertools.combinations(tests.groups, 2):
        df_comparison = tests.summary_pairs(groups0=[g1,], 
                                            groups1=[g2,],
                                            qval_thres=threshold_q, 
                                            mean_thres=threshold_mean)

        # Extract the fragment coords
        df_coords = df_bdg.loc[df_comparison['gene'], ['chrom', 'start', 'end']]
        # Merge with test results
        df_comparison = df_comparison.merge(df_coords, left_on='gene', right_index=True)
        # Output to tsv
        (df_comparison.drop(columns='gene')
                      [['chrom', 'start', 'end', 'mean', 'log2fc', 'pval', 'qval']]
                      .to_csv(f'{output_prefix}_{g1}_vs_{g2}.tsv', sep='\t', index=False))



# if __name__ == '__main__':
#     interactions_differential()
        




    
