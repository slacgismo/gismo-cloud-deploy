from project import db


class SolarData(db.Model):

    __tablename__ = "solardata"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(128), unique=True, nullable=False)
    bucket_name = db.Column(db.String(128), nullable=False)
    file_path = db.Column(db.String(128),  nullable=False)
    file_name = db.Column(db.String(128),  nullable=False)
    column_name = db.Column(db.String(128), nullable=False)
    process_time = db.Column(db.Float(), nullable=False)
    length = db.Column(db.Float(),  nullable=False)
    capacity_estimate = db.Column(db.Float(),  nullable=False)
    data_sampling = db.Column(db.Float(),  nullable=False)
    capacity_changes =  db.Column(db.Float(),  nullable=False)
    num_clip_points = db.Column(db.Float(),  nullable=False)
    normal_quality_scores = db.Column(db.Float(),  nullable=False)
    error_message = db.Column(db.String(256), nullable=True)
    power_units = db.Column(db.String(128),  nullable=False)
    time_shifts = db.Column(db.Float(),  nullable=False)
    def __init__( self, 
                    task_id, 
                    bucket_name, 
                    file_path,
                    file_name,
                    column_name,
                    process_time,
                    length,
                    power_units,
                    capacity_estimate,
                    data_sampling,
                    error_message,
                    time_shifts,
                    capacity_changes,
                    num_clip_points,
                    normal_quality_scores,
                    *args, **kwargs):

        self.task_id = task_id
        self.bucket_name = bucket_name
        self.file_path = file_path
        self.file_name = file_name
        self.column_name = column_name
        self.process_time = process_time

        self.power_units = power_units
        self.length = length
        self.capacity_estimate = capacity_estimate
        self.data_sampling = data_sampling
        self.error_message = error_message
        self.capacity_changes = capacity_changes
        self.num_clip_points = num_clip_points
        self.normal_quality_scores = normal_quality_scores
        self.time_shifts = time_shifts