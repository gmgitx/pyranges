import numpy as np
import pandas as pd

from pyranges.statistics import StatisticsMethods
from pyranges.genomicfeatures import GenomicFeaturesMethods
from pyranges.out import OutMethods
from pyranges import PyRanges


def set_dtypes(df, extended):

    if extended is None:
        extended = False if df.Start.dtype == np.int32 else True

    if not extended:
        dtypes = {
            "Start": np.int32,
            "End": np.int32,
            "Chromosome": "category",
            "Strand": "category"
        }
    else:
        dtypes = {
            "Start": np.int64,
            "End": np.int64,
            "Chromosome": "category",
            "Strand": "category"
        }

    if not "Strand" in df:
        del dtypes["Strand"]

    # on test data with a few rows, the below code does not work
    # therefore test for a good number of rows
    # categoricals = (df.nunique() / len(df) <= 0.1).replace({
    #     True: "category",
    #     False: "object"
    # }).to_dict()
    # categoricals.update(dtypes)
    # dtypes = categoricals

    for col, dtype in dtypes.items():

        if df[col].dtype.name != dtype:
            df[col] = df[col].astype(dtype)

    return df


def create_df_dict(df):

    chrs = df.Chromosome.cat.remove_unused_categories()

    # with Debug(locals()):
    #     f = df.head(1).head(1)

    df["Chromosome"] = chrs

    if "Strand" in df:
        grpby_key = "Chromosome Strand".split()
        df["Strand"] = df.Strand.cat.remove_unused_categories()
    else:
        grpby_key = "Chromosome"

    return {k: v for k, v in df.groupby(grpby_key)}


def create_pyranges_df(chromosomes, starts, ends, strands=None):

    if isinstance(chromosomes, str):
        chromosomes = pd.Series([chromosomes] * len(starts), dtype="category")

    if strands is not None:

        if isinstance(strands, str):
            strands = pd.Series([strands] * len(starts), dtype="category")

        columns = [chromosomes, starts, ends, strands]
        lengths = list(str(len(s)) for s in columns)
        assert len(
            set(lengths)
        ) == 1, "chromosomes, starts, ends and strands must be of equal length. But are {}".format(
            ", ".join(lengths))
        colnames = "Chromosome Start End Strand".split()
    else:
        columns = [chromosomes, starts, ends]
        lengths = list(str(len(s)) for s in columns)
        assert len(
            set(lengths)
        ) == 1, "chromosomes, starts and ends must be of equal length. But are {}".format(
            ", ".join(lengths))
        colnames = "Chromosome Start End".split()

    idx = range(len(starts))
    series_to_concat = []
    for s in columns:
        if isinstance(s, pd.Series):
            s = pd.Series(s.values, index=idx)
        else:
            s = pd.Series(s, index=idx)

        series_to_concat.append(s)

    df = pd.concat(series_to_concat, axis=1)
    df.columns = colnames

    return df


def _init(self,
          df=None,
          chromosomes=None,
          starts=None,
          ends=None,
          strands=None,
          copy_df=False,
          extended=None):
    # TODO: add categorize argument with dict of args to categorize?

    if isinstance(df, PyRanges):
        raise Exception("Object is already a PyRange.")

    if copy_df:
        df = df.copy()

    if df is False or df is None:
        df = create_pyranges_df(chromosomes, starts, ends, strands)

    if isinstance(df, pd.DataFrame):

        df = set_dtypes(df, extended)

    # below is not a good idea! then gr["chr1"] might change the dtypes of a gr!
    # elif isinstance(df, dict):
    #     df = {k: set_dtypes(v, extended) for k, v in df.items()}

    if isinstance(df, pd.DataFrame):
        self.__dict__["dfs"] = create_df_dict(df)
    else:
        # df is actually dict of dfs
        empty_removed = {k: v for k, v in df.items() if not v.empty}

        # empty
        if not empty_removed:
            self.__dict__["dfs"] = {}
        else:
            # if the df has has Strand added to them we must update
            # the PyRanges dict
            first_key, first_df = list(empty_removed.items())[0]
            assert all(c in first_df for c in "Chromosome Start End".split(
            )), "Columns Chromosome, Start and End must be in the dataframe!"

            if not isinstance(first_key, tuple) and "Strand" in first_df:
                new_dfs = {}
                for k, v in empty_removed.items():
                    for s, sdf in v.groupby("Strand"):
                        new_dfs[k, s] = sdf
                empty_removed = new_dfs
        self.__dict__["dfs"] = empty_removed

    self.__dict__["features"] = GenomicFeaturesMethods(self)
    self.__dict__["stats"] = StatisticsMethods(self)
    self.__dict__["out"] = OutMethods(self)
