"""Apache Beam Pipeline to get estimated capacity using solar_data_tools
"""
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import logging
from typing import Any, Dict, List
from .transformers.solar_data_tools_ptransforms import (
    GetAllResults,
    ReadFromS3,
    CreateHandler,
    RunSolarDataToolsPipeline,
    GetEstimatedCapacity,
    WrteToFile,
)


def run(
    input_file: list,
    process_column: str,
    solver: str,
    output_file: str,
    aws_access_key,
    aws_secret_access_key,
    aws_region,
    data_bucket,
) -> None:
    """Build and run the apache beam pipeline."""

    print(f"input file: {input_file}")
    with beam.Pipeline() as pipeline:
        capacity_estimates = (
            pipeline
            | "Set up file name" >> beam.Create(input_file)
            | "Convert csv to dataframe"
            >> beam.ParDo(
                ReadFromS3(),
                data_bucket=data_bucket,
                curr_process_column=process_column,
                aws_access_key=aws_access_key,
                aws_secret_access_key=aws_secret_access_key,
                aws_region=aws_region,
            )
            | "Create solar data tools handler" >> beam.ParDo(CreateHandler())
            | "Run solar data tools  pipeline"
            >> beam.ParDo(
                RunSolarDataToolsPipeline(), power_col=process_column, solver=solver
            )
            | "Get estimated capacity"
            >> beam.ParDo(
                GetAllResults(),
                data_bucket=data_bucket,
                curr_process_column=process_column,
                solver=solver,
            )
            | "Write to txt" >> beam.ParDo(WrteToFile(), outputfile=output_file)
            # | "print" >> beam.Map(print)
        )
        print("Complete")
