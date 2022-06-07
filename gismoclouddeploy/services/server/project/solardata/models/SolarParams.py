import json


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


def make_solardata_params_from_str(command_str: str) -> SolarParams:
    solar_params_json = json.loads(command_str)
    power_col = str(solar_params_json["power_col"])
    min_val = solar_params_json["min_val"]
    if min_val == "None":
        min_val = None
    else:
        min_val = int(solar_params_json["min_val"])

    max_val = solar_params_json["max_val"]
    if max_val == "None":
        max_val = None
    else:
        max_val = int(solar_params_json["max_val"])

    zero_night = eval(solar_params_json["zero_night"])
    interp_day = eval(solar_params_json["interp_day"])
    fix_shifts = eval(solar_params_json["fix_shifts"])
    density_lower_threshold = float(solar_params_json["density_lower_threshold"])
    density_upper_threshold = float(solar_params_json["density_upper_threshold"])
    linearity_threshold = float(solar_params_json["linearity_threshold"])
    clear_day_smoothness_param = float(solar_params_json["clear_day_smoothness_param"])
    clear_day_energy_param = float(solar_params_json["clear_day_energy_param"])
    verbose = eval(solar_params_json["verbose"])

    start_day_ix = solar_params_json["start_day_ix"]
    if start_day_ix == "None":
        start_day_ix = None
    else:
        start_day_ix = int(solar_params_json["start_day_ix"])

    end_day_ix = solar_params_json["end_day_ix"]
    if end_day_ix == "None":
        end_day_ix = None
    else:
        end_day_ix = int(solar_params_json["end_day_ix"])

    c1 = solar_params_json["c1"]
    if c1 == "None":
        c1 = None
    else:
        c1 = float(solar_params_json["c1"])

    c2 = solar_params_json["c2"]
    if c2 == "None":
        c2 = None
    else:
        c2 = float(solar_params_json["c2"])

    solar_noon_estimator = str(solar_params_json["solar_noon_estimator"])
    correct_tz = eval(solar_params_json["correct_tz"])
    extra_cols = str(solar_params_json["extra_cols"])

    extra_cols = solar_params_json["extra_cols"]
    if extra_cols == "None":
        extra_cols = None
    else:
        extra_cols = str(solar_params_json["extra_cols"])

    daytime_threshold = float(solar_params_json["daytime_threshold"])
    units = str(solar_params_json["units"])

    solver = solar_params_json["solver"]
    if solver == "None":
        solver = None
    else:
        solver = str(solar_params_json["solver"])

    solarparams = SolarParams(
        power_col,
        min_val,
        max_val,
        zero_night,
        interp_day,
        fix_shifts,
        density_lower_threshold,
        density_upper_threshold,
        linearity_threshold,
        clear_day_smoothness_param,
        clear_day_energy_param,
        verbose,
        start_day_ix,
        end_day_ix,
        c1,
        c2,
        solar_noon_estimator,
        correct_tz,
        extra_cols,
        daytime_threshold,
        units,
        solver,
    )

    return solarparams
