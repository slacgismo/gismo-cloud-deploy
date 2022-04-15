from project.solardata.models import SolarData

def get_all_data_from_solardata():
    """ Find all solar data results """
    return SolarData.query.all()