import pandas as pd
import os
import numpy as np


class SliceFilter:

    """
    Perform slice filtering (inplace) and reporter identification.

    The SliceFilter classes e.g. CCSliceFilter, TriCSliceFilter, TiledCSliceFilter perform all of the filtering (inplace)
    and reporter identification whilst also provide statistics of the numbers of slices/reads removed at each stage.
    
    Attributes:
     slices (pd.DataFrame): Annotated slices dataframe.
     fragments (pd.DataFrame): Slices dataframe aggregated by parental read.
     reporters (pd.DataFrame): Slices identified as reporters.
     filter_stages (dict): Dictionary containg stages and a list of class methods (str) required to get to this stage.
     slice_stats (pd.DataFrame): Provides slice level statistics.
     read_stats (pd.DataFrame): Provides statistics of slice filtering at the parental read level.
     filter_stats (pd.DataFrame): Provides statistics of read filtering.

    """

    def __init__(
        self,
        slices: pd.DataFrame,
        filter_stages: dict = None,
        sample_name: str = "",
        read_type: str = "",
    ):
        """Base for all slice filter objects.

            Slices DataFrame must have the following columns:

            - slice_name: Unique aligned read identifier (e.g. XZKG:889:11|flashed|1)
            - parent_read: Identifier shared by slices from same fragment (e.g.XZKG:889:11)
            - pe: Read combined by FLASh or not (i.e. "flashed" or "pe")
            - mapped: Alignment is mapped (e.g. 0/1)
            - multimapped: Alignment is mapped (e.g. 0/1)
            - slice: Slice number (e.g. 0)
            - chrom: Chromosome e.g. chr1
            - start: Start coord
            - end: End coord
            - capture: Capture site intersecting slice (e.g. Slc25A37)
            - capture_count: Number of capture probes overlapping slice (e.g. 1)
            - exclusion: Read present in excluded region (e.g. Slc25A37)
            - exclusion_count: Number of excluded regions overlapping slice (e.g. 1)
            - blacklist: Read present in excluded region (e.g. 0)
            - coordinates: Genome coordinates (e.g. chr1:1000-2000)

        Args:
            slices (pd.DataFrame): DatFrame containing annotated slices
            filter_stages (dict, optional): Dictionary defining order of slice filtering. Defaults to None.
            sample_name (str, optional): Name of sample being processed e.g. DOX-treated_1. Defaults to "".
            read_type (str, optional): Combined (flashed) or not-combined (pe). Defaults to "".

        Raises:
            ValueError: Filter stages must be provided. This is done automatically by all subclasses
        """

        self._check_required_columns_present(slices)
        self.slices = slices.sort_values(["parent_read", "slice"])

        if filter_stages:
            self.filter_stages = filter_stages
        else:
            raise ValueError("Filter stages not provided")

        self.filtered = False
        self._filter_stats = pd.DataFrame()
        self.sample_name = sample_name
        self.read_type = read_type

    def _check_required_columns_present(self, df):

        columns_required = [
            "slice_name",
            "parent_read",
            "pe",
            "mapped",
            "multimapped",
            "slice",
            "chrom",
            "start",
            "end",
            "capture",
            "capture_count",
            "exclusion",
            "blacklist",
            "coordinates",
        ]

        for col in columns_required:
            if not col in df.columns:
                raise KeyError(f'Required column "{col}" not in slices dataframe')

    @property
    def slice_stats(self) -> pd.DataFrame:
        """Gets statisics at a slice level.

        Calculates stats at slice level.

        Returns:
         DataFrame containing slice statistics
        """
        raise NotImplementedError("Override this method")

    @property
    def filter_stats(self):
        """Gets statisics for each filter stage.

        Calculates stats per filter stage.

        Returns:
         pd.Dataframe: Contains slice statistics
        """
        return (
            self._filter_stats.transpose()
            .reset_index()
            .rename(columns={"index": "stage"})
            .assign(sample=self.sample_name, read_type=self.read_type)
        )

    @property
    def read_stats(self):
        """Gets statisics at a read level.

        Aggregates slices by parental read id and calculates stats.

        Returns:
         pd.Dataframe: Contains slice statistics
        """
        return self.filter_stats.rename(
            columns={
                "stage": "stat_type",
                "unique_fragments": "stat",
            }
        )[["stat_type", "stat"]].assign(
            stage="ccanalysis",
            read_type=self.read_type,
            sample=self.sample_name,
            read_number=0,
        )

    @property
    def fragments(self):
        """Summarises slices at the fragment level.

         Uses pandas groupby to aggregate slices by their parental read name
         (shared by all slices from the same fragment). Also determines the
         number of reporter slices for each fragment.

        Returns:
          Dataframe of slices aggregated by fragment

        """
        raise NotImplementedError("Override this property")

    @property
    def reporters(self):
        """
        Extracts reporter slices from slices dataframe i.e. non-capture slices

        Returns:
         pd.Dataframe containg all non-capture slices

        """
        raise NotImplementedError("Override this property")

    def filter_slices(self, output_slices=False, output_location="."):
        """Performs slice filtering by calling the class methods from the filter_stages dictionary

        Args:
            output_slices (bool, optional): Determines if slices are to be output to a specified location after each filtering step.
                                            Useful for debugging. Defaults to False.
            output_location (str, optional): Location to output slices at each stage. Defaults to ".".
        """

        for stage, filters in self.filter_stages.items():
            for filt in filters:
                # Call all of the filters in the filter_stages dict in order
                print(f"Filtering: {filt}")
                getattr(self, filt)()  # Gets and calls the selected method
                print(f"Number of slices: {self.slices.shape[0]}")
                print(f'Number of reads: {self.slices["parent_read"].nunique()}')

                if output_slices == "filter":
                    self.slices.to_csv(os.path.join(output_location, f"{filt}.tsv.gz"))

            if output_slices == "stage":
                self.slices.to_csv(os.path.join(output_location, f"{stage}.tsv.gz"))

            self._filter_stats[stage] = self.slice_stats

    def get_raw_slices(self):
        self.slices = self.slices

    def remove_unmapped_slices(self):
        """
        Removes slices marked as unmapped (Uncommon)
        """
        self.slices = self.slices.query("mapped == 1")

    def remove_orphan_slices(self):
        """Remove fragments with only one aligned slice (Common)"""

        fragments = self.fragments
        fragments_multislice = fragments.query("unique_slices > 1")
        self.slices = self.slices[
            self.slices["parent_read"].isin(fragments_multislice["parent_read"])
        ]

    def remove_duplicate_re_frags(self):
        """
        Prevent the same restriction fragment being counted more than once (Uncommon).
        
        e.g. --RE_FRAG1--\----Capture----\---RE_FRAG1----

        """
        self.slices = self.slices.drop_duplicates(subset=["parent_read", "restriction_fragment"])

    def remove_slices_without_re_frag_assigned(self):
        """Removes slices if restriction_fragment column is N/A"""
        self.slices = self.slices.query('restriction_fragment != "."')

    def remove_duplicate_slices(self):
        """Remove all slices if the slice coordinates and slice order are shared
        with another fragment i.e. are PCR duplicates (Common).

        e.g
                          coordinates
        | Frag 1:  chr1:1000-1250 chr1:1500-1750
        | Frag 2:  chr1:1000-1250 chr1:1500-1750
        | Frag 3:  chr1:1050-1275 chr1:1600-1755
        | Frag 4:  chr1:1500-1750 chr1:1000-1250

        Frag 2 removed. Frag 1,3,4 retained


        """

        frags_deduplicated = self.fragments.sample(frac=1).drop_duplicates(
            subset="coordinates", keep="first"
        )

        self.slices = self.slices[
            self.slices["parent_read"].isin(frags_deduplicated["parent_read"])
        ]

    def remove_duplicate_slices_pe(self):
        """Removes PCR duplicates from non-flashed (PE) fragments (Common).
        Sequence quality is often lower at the 3' end of reads leading to variance in mapping coordinates.
        PCR duplicates are removed by checking that the fragment start and end are not duplicated in the dataframe.


        """
        if (
            self.slices["pe"].str.contains("unflashed").sum() > 1
        ):  # at least one un-flashed
            fragments = self.fragments.assign(
                read_start=lambda df: df["coordinates"]
                .str.split("|")
                .str[0]
                .str.split(r":|-")
                .str[1],
                read_end=lambda df: df["coordinates"]
                .str.split("|")
                .str[-1]
                .str.split(r":|-")
                .str[-1],
            )

            fragments_pe = fragments.query('pe == "unflashed"')
            fragments_pe_duplicated = fragments_pe[
                fragments_pe.duplicated(subset=["read_start", "read_end"])
            ]

            self.slices = self.slices[
                ~(
                    self.slices["parent_read"].isin(
                        fragments_pe_duplicated["parent_read"]
                    )
                )
            ]  # Slices not in duplicated

    def remove_excluded_slices(self):
        """Removes any slices in the exclusion region (default 1kb) (V. Common)"""
        self.slices = self.slices.query("exclusion_count < 1")

    def remove_blacklisted_slices(self):
        """Removes slices marked as being within blacklisted regions"""
        self.slices = self.slices.query("blacklist < 1")


class CCSliceFilter(SliceFilter):
    def __init__(self, slices, filter_stages=None, **sample_kwargs):
        if not filter_stages:
            filter_stages = {
                "pre-filtering": [
                    "get_raw_slices",
                ],
                "mapped": [
                    "remove_unmapped_slices",
                ],
                "contains_single_capture": [
                    "remove_orphan_slices",
                    "remove_multi_capture_fragments",
                ],
                "contains_capture_and_reporter": [
                    "remove_excluded_slices",
                    "remove_blacklisted_slices",
                    "remove_non_reporter_fragments",
                    "remove_multicapture_reporters",
                ],
                "duplicate_filtered": [
                    "remove_slices_without_re_frag_assigned",
                    "remove_duplicate_re_frags",
                    "remove_duplicate_slices",
                    "remove_duplicate_slices_pe",
                    "remove_non_reporter_fragments",
                ],
            }

        super(CCSliceFilter, self).__init__(slices, filter_stages, **sample_kwargs)

    @property
    def fragments(self):
        df = (
            self.slices.sort_values(["parent_read", "chrom", "start"])
            .groupby("parent_read", as_index=False, sort=False)
            .agg(
                {
                    "slice": "nunique",
                    "pe": "first",
                    "mapped": "sum",
                    "multimapped": "sum",
                    "capture": "nunique",
                    "capture_count": "sum",
                    "exclusion": "nunique",
                    "exclusion_count": "sum",
                    "restriction_fragment": "nunique",
                    "blacklist": "sum",
                    "coordinates": "|".join,
                }
            )
        )
        df["capture"] = df["capture"] - 1  # nunique identifies '.' as a capture site
        df["exclusion"] = df["exclusion"] - 1  # as above

        # Add the number of reporters to the dataframe.
        # Only consider a reporter if at least one capture slice is present
        # in the fragment.
        df["reporter_count"] = np.where(
            df["capture_count"] > 0,
            df["mapped"]
            - (df["exclusion_count"] + df["capture_count"] + df["blacklist"]),
            0,
        )

        # Rename for clarity
        df = df.rename(
            columns={
                "capture": "unique_capture_sites",
                "exclusion": "unique_exclusion_sites",
                "restriction_fragment": "unique_restriction_fragments",
                "slice": "unique_slices",
                "blacklist": "blacklisted_slices",
            }
        )
        return df

    @property
    def slice_stats(self):

        slices = self.slices.copy()
        if slices.empty:  # Deal with empty dataframe i.e. no valid slices
            for col in slices:
                slices[col] = np.zeros((10,))

        stats_df = slices.agg(
            {
                "slice_name": "nunique",
                "parent_read": "nunique",
                "mapped": "sum",
                "multimapped": "sum",
                "capture": "nunique",
                "capture_count": lambda col: (col > 0).sum(),
                "exclusion_count": lambda col: (col > 0).sum(),
                "blacklist": "sum",
            }
        )

        stats_df = stats_df.rename(
            {
                "slice_name": "unique_slices",
                "parent_read": "unique_fragments",
                "multimapped": "multimapping_slices",
                "capture": "unique_capture_sites",
                "capture_count": "number_of_capture_slices",
                "exclusion_count": "number_of_slices_in_exclusion_region",
                "blacklist": "number_of_slices_in_blacklisted_region",
            }
        )

        return stats_df

    @property
    def frag_stats(self):
        return self.fragments.agg(
            {
                "parent_read": "nunique",
                "mapped": lambda col: (col > 1).sum(),
                "multimapped": lambda col: (col > 0).sum(),
                "capture_count": lambda col: (col > 0).sum(),
                "exclusion_count": lambda col: (col > 0).sum(),
                "blacklisted_slices": lambda col: (col > 0).sum(),
                "reporter_count": lambda col: (col > 0).sum(),
            }
        ).rename(
            {
                "parent_read": "unique_fragments",
                "multimapped": "fragments_with_multimapping_slices",
                "capture_count": "fragments_with_capture_sites",
                "exclusion_count": "fragments_with_excluded_regions",
                "blacklisted_slices": "fragments_with_blacklisted_regions",
                "reporter_count": "fragments_with_reporter_slices",
            }
        )

    @property
    def reporters(self) -> pd.DataFrame:
        return self.slices.query('capture == "."')

    @property
    def captures(self) -> pd.DataFrame:
        """Extracts capture slices from slices dataframe

        i.e. slices that do not have a null capture name

        Returns:
         pd.DataFrame containg all capture slices"""
        return self.slices.query('~(capture == ".")')

    @property
    def capture_site_stats(self) -> pd.Series:
        """Extracts the number of unique capture sites."""
        return self.captures["capture"].value_counts()

    @property
    def merged_captures_and_reporters(self) -> pd.DataFrame:
        """Merges captures and reporters sharing the same parental id.

        Returns:
         pd.DataFrame containing merged capture and reporter slices
        """

        captures = (
            self.captures.set_index("parent_read")
            .add_prefix("capture_")
            .rename(columns={"capture_capture": "capture"})
        )

        reporters = self.reporters.set_index("parent_read").add_prefix("reporter_")

        # Join reporters to captures using the parent read name
        captures_and_reporters = (
            captures.join(reporters).dropna(axis=0, how="any").reset_index()
        )

        return captures_and_reporters

    @property
    def cis_or_trans_stats(self) -> pd.DataFrame:
        """Extracts reporter cis/trans statistics from slices.

        Returns:
         DataFrame containing reporter cis/trans statistics
        """
        cap_and_rep = self.merged_captures_and_reporters.copy()

        cap_and_rep["cis/trans"] = np.where(
            cap_and_rep["capture_chrom"] == cap_and_rep["reporter_chrom"],
            "cis",
            "trans",
        )

        try:
            # Aggregate by capture site for reporting
            interactions_by_capture = pd.DataFrame(
                cap_and_rep.groupby("capture")["cis/trans"]
                .value_counts()
                .to_frame()
                .rename(columns={"cis/trans": "count"})
                .reset_index()
                .assign(sample=self.sample_name, read_type=self.read_type)
            )
        except Exception as e:
            print(e)
            interactions_by_capture = pd.DataFrame()

        return interactions_by_capture

    def remove_non_reporter_fragments(self):
        """Removes all slices (i.e. the entire fragment) if it has no reporter slices present (Common)"""
        frags_reporter = self.fragments.query("reporter_count > 0")
        self.slices = self.slices[
            self.slices["parent_read"].isin(frags_reporter["parent_read"])
        ]

    def remove_multi_capture_fragments(self):
        """
        Removes double capture fragments.
        
        All slices (i.e. the entire fragment) are removed if more than
        one capture probe is present i.e. double captures (V. Common)
        
        """
        frags_capture = self.fragments.query("0 < unique_capture_sites < 2")
        self.slices = self.slices[
            self.slices["parent_read"].isin(frags_capture["parent_read"])
        ]

    def remove_multicapture_reporters(self, n_adjacent: int = 1):
        """
        Deals with an odd situation in which a reporter spanning two adjacent capture sites is not removed.

        |e.g.
        |------Capture 1----/------Capture 2------
        |                     -----REP--------

        In this case the "reporter" slice is not considered either a capture or exclusion.

        These cases are dealt with by explicitly removing reporters on restriction fragments
        adjacent to capture sites.

        The number of adjacent RE fragments can be adjusted with n_adjacent.

        Args:
         n_adjacent: Number of adjacent restriction fragments to remove

        """

        captures = self.captures
        re_frags = captures["restriction_fragment"].unique()

        # Generates a list of restriction fragments to be excluded from further analysis
        excluded_fragments = [
            frag + modifier
            for frag in re_frags
            for modifier in range(-n_adjacent, n_adjacent + 1)
        ]

        # Remove non-capture slices (reporters) in excluded regions
        self.slices = self.slices[
            (self.slices["capture_count"] > 0)
            | (~self.slices["restriction_fragment"].isin(excluded_fragments))
        ]


class TriCSliceFilter(CCSliceFilter):
    def __init__(self, slices, filter_stages=None, **sample_kwargs):

        if filter_stages:
            self.filter_stages = filter_stages
        else:
            filter_stages = {
                "pre-filtering": [
                    "get_raw_slices",
                ],
                "mapped": [
                    "remove_unmapped_slices",
                    "remove_slices_without_re_frag_assigned",
                ],
                "contains_single_capture": [
                    "remove_orphan_slices",
                    "remove_multi_capture_fragments",
                ],
                "contains_capture_and_reporter": [
                    "remove_blacklisted_slices",
                    "remove_non_reporter_fragments",
                ],
                "duplicate_filtered": [
                    "remove_duplicate_re_frags",
                    "remove_duplicate_slices",
                    "remove_duplicate_slices_pe",
                    "remove_non_reporter_fragments",
                ],
                "tric_reporter": ["remove_slices_with_one_reporter"],
            }

        super(TriCSliceFilter, self).__init__(slices, filter_stages, **sample_kwargs)

    def remove_slices_with_one_reporter(self):
        """Removes fragments if they do not contain at least two reporters."""
        fragments_triplets = self.fragments.query("reporter_count > 1")
        self.slices = self.slices.loc[
            lambda df: df["parent_read"].isin(fragments_triplets["parent_read"])
        ]


class TiledCSliceFilter(SliceFilter):
    def __init__(self, slices, filter_stages=None, **sample_kwargs):

        if not filter_stages:
            filter_stages = {
                "pre-filtering": [
                    "get_raw_slices",
                ],
                "mapped": ["remove_unmapped_slices", "remove_orphan_slices"],
                "not_blacklisted": ["remove_blacklisted_slices"],
                "contains_capture": [
                    "remove_non_capture_fragments",
                    "remove_dual_capture_fragments",
                ],
                "duplicate_filtered": [
                    "remove_slices_without_re_frag_assigned",
                    "remove_duplicate_re_frags",
                    "remove_duplicate_slices",
                    "remove_duplicate_slices_pe",
                ],
                "has_reporter": ["remove_orphan_slices"],
            }

        super(TiledCSliceFilter, self).__init__(slices, filter_stages, **sample_kwargs)

    @property
    def fragments(self) -> pd.DataFrame:
        df = (
            self.slices.sort_values(["parent_read", "chrom", "start"])
            .groupby("parent_read", as_index=False, sort=False)
            .agg(
                {
                    "slice": "nunique",
                    "pe": "first",
                    "mapped": "sum",
                    "multimapped": "sum",
                    "capture_count": "sum",
                    "restriction_fragment": "nunique",
                    "blacklist": "sum",
                    "coordinates": "|".join,
                }
            )
        )

        # Rename for clarity
        df = df.rename(
            columns={
                "restriction_fragment": "unique_restriction_fragments",
                "slice": "unique_slices",
                "blacklist": "blacklisted_slices",
            }
        )
        return df

    @property
    def slice_stats(self):
        stats_df = self.slices.agg(
            {
                "slice_name": "nunique",
                "parent_read": "nunique",
                "mapped": "sum",
                "multimapped": "sum",
                "capture_count": lambda col: (col > 0).sum(),
                "blacklist": "sum",
            }
        )

        stats_df = stats_df.rename(
            {
                "slice_name": "unique_slices",
                "parent_read": "unique_fragments",
                "multimapped": "multimapping_slices",
                "capture_count": "number_of_capture_slices",
                "blacklist": "number_of_slices_in_blacklisted_region",
            }
        )

        return stats_df

    @property
    def cis_or_trans_stats(self):
        interactions_by_capture = dict()

        for capture_site, df_cap in self.slices.query('capture != "."').groupby(
            "capture"
        ):

            capture_chrom = df_cap.iloc[0]["chrom"]
            df_primary_capture = df_cap.groupby(
                "parent_read"
            ).first()  # Artifact required as need to call one slice the "capture"
            df_not_primary_capture = df_cap.loc[
                ~(df_cap["slice_name"].isin(df_primary_capture["slice_name"]))
            ]
            df_outside_capture = self.slices.query('capture == "."').loc[
                lambda df_rep: df_rep["parent_read"].isin(df_cap["parent_read"])
            ]

            df_pseudo_reporters = pd.concat(
                [df_not_primary_capture, df_outside_capture]
            )
            n_cis_interactions = df_pseudo_reporters.query(
                f'chrom == "{capture_chrom}"'
            ).shape[0]
            n_trans_interactions = df_pseudo_reporters.shape[0] - n_cis_interactions

            interactions_by_capture[capture_site] = {
                "cis": n_cis_interactions,
                "trans": n_trans_interactions,
            }

        return (
            pd.DataFrame(interactions_by_capture)
            .transpose()
            .reset_index()
            .rename(columns={"index": "capture"})
            .melt(id_vars="capture", var_name="cis/trans", value_name="count")
            .sort_values("capture")
            .assign(sample=self.sample_name, read_type=self.read_type)
        )

    def remove_slices_outside_capture(self):
        """Removes slices outside of capture region(s)"""
        self.slices = self.slices.query('capture != "."')

    def remove_non_capture_fragments(self):
        """Removes fragments without a capture assigned"""
        fragments_with_capture = self.fragments.query("capture_count > 0")
        self.slices = self.slices[
            self.slices["parent_read"].isin(fragments_with_capture["parent_read"])
        ]

    def remove_dual_capture_fragments(self):
        """Removes a fragment with multiple different capture sites.

        Modified for TiledC filtering as the fragment dataframe is generated
        slightly differently
        """
        multicapture_fragments = (
            self.slices.query('capture != "."')
            .groupby("parent_read")["capture"]
            .nunique()
            > 1
        )
        self.slices = (
            self.slices.set_index("parent_read")
            .loc[~multicapture_fragments]
            .reset_index()
        )