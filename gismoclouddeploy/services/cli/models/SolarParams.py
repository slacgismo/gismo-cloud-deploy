from utils.read_wirte_io import read_yaml

import logging

logger = logging.getLogger()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s: %(levelname)s: %(message)s"
)


class SolarParams(object):
    def __init__(
        self,
        power_col=None,
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
        solver="MOSEK",
    ):
        self.power_col = power_col
        self.min_val = min_val
        self.max_val = max_val
        self.zero_night = zero_night
        self.interp_day = interp_day
        self.fix_shifts = fix_shifts
        self.density_lower_threshold = density_lower_threshold
        self.density_upper_threshold = density_upper_threshold
        self.linearity_threshold = linearity_threshold
        self.clear_day_smoothness_param = clear_day_smoothness_param
        self.clear_day_energy_param = clear_day_energy_param
        self.verbose = verbose
        self.start_day_ix = start_day_ix
        self.end_day_ix = end_day_ix
        self.c1 = c1
        self.c2 = c2
        self.solar_noon_estimator = solar_noon_estimator
        self.correct_tz = correct_tz
        self.extra_cols = extra_cols
        self.daytime_threshold = daytime_threshold
        self.units = units
        self.solver = solver

    def import_solar_params_from_yaml(file: str):
        try:
            sdt_params = read_yaml(filename=file)
        except Exception as e:
            logger.error(f"{file} file didn't exist: {e}")
            raise e
        try:
            solardata = SolarParams(
                power_col=sdt_params["solardata"]["power_col"],
                min_val=sdt_params["solardata"]["min_val"],
                max_val=sdt_params["solardata"]["max_val"],
                zero_night=sdt_params["solardata"]["zero_night"],
                interp_day=sdt_params["solardata"]["interp_day"],
                fix_shifts=sdt_params["solardata"]["fix_shifts"],
                density_lower_threshold=sdt_params["solardata"][
                    "density_lower_threshold"
                ],
                density_upper_threshold=sdt_params["solardata"][
                    "density_upper_threshold"
                ],
                linearity_threshold=sdt_params["solardata"]["linearity_threshold"],
                clear_day_smoothness_param=sdt_params["solardata"][
                    "clear_day_smoothness_param"
                ],
                clear_day_energy_param=sdt_params["solardata"][
                    "clear_day_energy_param"
                ],
                verbose=sdt_params["solardata"]["verbose"],
                start_day_ix=sdt_params["solardata"]["start_day_ix"],
                end_day_ix=sdt_params["solardata"]["end_day_ix"],
                c1=sdt_params["solardata"]["c1"],
                c2=sdt_params["solardata"]["c2"],
                solar_noon_estimator=sdt_params["solardata"]["solar_noon_estimator"],
                correct_tz=sdt_params["solardata"]["correct_tz"],
                extra_cols=sdt_params["solardata"]["extra_cols"],
                daytime_threshold=sdt_params["solardata"]["daytime_threshold"],
                units=sdt_params["solardata"]["units"],
                solver=sdt_params["solardata"]["solver"],
            )
            return solardata
        except Exception as e:
            logger.error(
                f"solardata parameters format in {file} file is incorrect: {e}"
            )
            raise e

    def parse_solardata_params_to_json_str(self):
        str = "{"
        str += f' "power_col":"{self.power_col}",'
        str += f' "min_val":"{self.min_val}",'
        str += f' "max_val":"{self.max_val}",'
        str += f' "zero_night":"{self.zero_night}",'
        str += f' "interp_day":"{self.interp_day}",'
        str += f' "fix_shifts":"{self.fix_shifts}",'
        str += f' "density_lower_threshold":"{self.density_lower_threshold}",'
        str += f' "density_upper_threshold":"{self.density_upper_threshold}",'
        str += f' "linearity_threshold":"{self.linearity_threshold}",'
        str += f' "clear_day_smoothness_param":"{self.clear_day_smoothness_param}",'
        str += f' "clear_day_energy_param":"{self.clear_day_energy_param}",'
        str += f' "verbose":"{self.verbose}",'
        str += f' "start_day_ix":"{self.start_day_ix}",'
        str += f' "end_day_ix":"{self.end_day_ix}",'
        str += f' "c1":"{self.c1}",'
        str += f' "c2":"{self.c2}",'
        str += f' "solar_noon_estimator":"{self.solar_noon_estimator}",'
        str += f' "correct_tz":"{self.correct_tz}",'
        str += f' "extra_cols":"{self.extra_cols}",'
        str += f' "daytime_threshold":"{self.daytime_threshold}",'
        str += f' "units":"{self.units}",'
        str += f' "solver":"{self.solver}"'
        str += "}"
        return str
