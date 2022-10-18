"""
PTransforms for solar data tools operations
"""
from ast import Str
import apache_beam as beam
import pandas as pd
from solardatatools import DataHandler
from .read_csv_from_s3 import read_csv_from_s3
from typing import Tuple, Iterable, TypeVar, Dict, Union
from apache_beam.io import filesystems
import json


T = TypeVar("T")


class WrteToFile(beam.DoFn):
    """
    Run the solar data tool pipeline on a PCollection of DataHandler objects
    ...

    Methods
    -------
    process(element):
        Run the process.
    """

    def process(self, element, outputfile):
        dict_ = element
        encode = json.dumps(dict_).encode("utf-8")
        writer = filesystems.FileSystems.create(outputfile)
        # writer.write(bytes(encode, 'utf-8'))
        writer.write(encode)
        writer.close()


class ReadFromS3(beam.DoFn):
    def process(
        self,
        element,
        curr_process_column,
        aws_access_key,
        aws_secret_access_key,
        aws_region,
        data_bucket,
    ):

        file = element
        print("Read from S3")
        df = read_csv_from_s3(
            bucket_name=data_bucket,
            file_path_name=file,
            column_name=curr_process_column,
            aws_access_key=aws_access_key,
            aws_secret_access_key=aws_secret_access_key,
            aws_region=aws_region,
        )
        yield file, df


class ConverCSVToDataFrame(beam.DoFn):
    def process(self, element, column):

        file = element
        df = pd.read_csv(
            file,
            index_col=0,
            parse_dates=[0],
            usecols=["Time", column],
        )

        yield file, df


@beam.typehints.with_input_types(Tuple[T, Iterable[Dict]])
@beam.typehints.with_output_types(Tuple[T, DataHandler])
class CreateHandler(beam.DoFn):
    def process(self, element):

        (file, df) = element
        dh = DataHandler(df)
        yield file, dh


@beam.typehints.with_input_types(Tuple[T, DataHandler], str, str)
@beam.typehints.with_output_types(Tuple[T, DataHandler])
class RunSolarDataToolsPipeline(beam.DoFn):
    def process(self, element, power_col, solver):

        (file, data_handler) = element
        data_handler.run_pipeline(
            power_col=power_col,
            min_val=-5,
            max_val=None,
            zero_night=True,
            interp_day=True,
            fix_shifts=True,
            density_lower_threshold=0.6,
            density_upper_threshold=1.05,
            linearity_threshold=0.1,
            clear_day_smoothness_param=0.9,
            clear_day_energy_param=0.8,
            verbose=False,
            start_day_ix=None,
            end_day_ix=None,
            c1=None,
            c2=500.0,
            solar_noon_estimator="com",
            correct_tz=True,
            extra_cols=None,
            daytime_threshold=0.1,
            units="W",
            solver=solver,
        )
        yield file, data_handler


@beam.typehints.with_input_types(Tuple[T, DataHandler])
@beam.typehints.with_output_types(Dict)
class GetEstimatedCapacity(beam.DoFn):
    """
    Run the solar data tool pipeline on a PCollection of DataHandler objects
    ...

    Methods
    -------
    process(element):
        Run the process.
    """

    def process(self, element):
        (file, data_handler) = element
        yield {"file": file, "capacity_estimate": data_handler.capacity_estimate}


@beam.typehints.with_input_types(Tuple[T, DataHandler], str, str, str)
@beam.typehints.with_output_types(Dict)
class GetAllResults(beam.DoFn):
    """
    Run the solar data tool pipeline on a PCollection of DataHandler objects
    ...

    Methods
    -------
    process(element):
        Run the process.
    """

    def process(self, element, data_bucket, curr_process_column, solver):
        (file, dh) = element
        length = float("{:.2f}".format(dh.num_days))
        if dh.num_days >= 365:
            length = float("{:.2f}".format(dh.num_days / 365))

        capacity_estimate = float("{:.2f}".format(dh.capacity_estimate))

        power_units = str(dh.power_units)
        if power_units == "W":
            capacity_estimate = float("{:.2f}".format(dh.capacity_estimate / 1000))
        data_sampling = int(dh.data_sampling)

        if dh.raw_data_matrix.shape[0] > 1440:
            data_sampling = int(dh.data_sampling * 60)

        data_quality_score = float("{:.1f}".format(dh.data_quality_score * 100))
        data_clearness_score = float("{:.1f}".format(dh.data_clearness_score * 100))
        time_shifts = bool(dh.time_shifts)
        num_clip_points = int(dh.num_clip_points)
        tz_correction = int(dh.tz_correction)
        inverter_clipping = bool(dh.inverter_clipping)
        normal_quality_scores = bool(dh.normal_quality_scores)
        capacity_changes = bool(dh.capacity_changes)

        save_data = {
            "bucket": data_bucket,
            "file": file,
            "column": curr_process_column,
            "solver": solver,
            "length": length,
            "capacity_estimate": capacity_estimate,
            "power_units": power_units,
            "data_sampling": data_sampling,
            "data_quality_score": data_quality_score,
            "data_clearness_score": data_clearness_score,
            "time_shifts": time_shifts,
            "num_clip_points": num_clip_points,
            "tz_correction": tz_correction,
            "inverter_clipping": inverter_clipping,
            "normal_quality_scores": normal_quality_scores,
            "capacity_changes": capacity_changes,
        }
        yield save_data
