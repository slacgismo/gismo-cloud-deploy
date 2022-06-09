# from project import db


class SolarData(object):
    def __init__(
        self,
        task_id,
        hostname,
        host_ip,
        stat_time,
        end_time,
        bucket_name,
        file_path_name,
        column_name,
        process_time,
        length,
        power_units,
        capacity_estimate,
        data_sampling,
        data_quality_score,
        data_clearness_score,
        error_message,
        time_shifts,
        capacity_changes,
        num_clip_points,
        tz_correction,
        inverter_clipping,
        normal_quality_scores,
    ):
        self.task_id = task_id
        self.hostname = hostname
        self.host_ip = host_ip
        self.stat_time = stat_time
        self.end_time = end_time
        self.bucket_name = bucket_name
        self.file_path_name = file_path_name
        self.column_name = column_name
        self.process_time = process_time
        self.power_units = power_units
        self.length = length
        self.capacity_estimate = capacity_estimate
        self.data_sampling = data_sampling
        self.data_quality_score = data_quality_score
        self.error_message = error_message
        self.capacity_changes = capacity_changes
        self.num_clip_points = num_clip_points
        self.normal_quality_scores = normal_quality_scores
        self.data_clearness_score = data_clearness_score
        self.inverter_clipping = inverter_clipping
        self.tz_correction = tz_correction
        self.time_shifts = time_shifts

    def to_json(self):

        return {
            "task_id": self.task_id,
            "hostname": self.hostname,
            "host_ip": self.host_ip,
            "stat_time": self.stat_time,
            "end_time": self.end_time,
            "bucket_name": self.bucket_name,
            "file_path_name": self.file_path_name,
            "column_name": self.column_name,
            "process_time": self.process_time,
            "power_units": self.power_units,
            "length": self.length,
            "capacity_estimate": self.capacity_estimate,
            "data_sampling": self.data_sampling,
            "data_quality_score": self.data_quality_score,
            "error_message": self.error_message,
            "capacity_changes": self.capacity_changes,
            "num_clip_points": self.num_clip_points,
            "normal_quality_scores": self.normal_quality_scores,
            "data_clearness_score": self.data_clearness_score,
            "inverter_clipping": self.inverter_clipping,
            "tz_correction": self.tz_correction,
            "time_shifts": self.time_shifts,
        }
