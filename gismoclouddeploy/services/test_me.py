import datetime
import time
import json
import re
origin_Str = "datetime.datetime(2022, 8, 23, 0, 47, 16, tzinfo=tzutc())"
res = re.search('\(([^)]+)', origin_Str).group(1)
year, month, day, hours, minutes, sec, tz = res.split(', ')
dattime_string = f"{year}/{month}/{day} {hours}:{minutes}:{sec}"
print(dattime_string)
timestamp = time.mktime(datetime.datetime.strptime(dattime_string, "%Y/%m/%d %H:%M:%S").timetuple())
print(timestamp)
# year, month, day, hours, minutes, sec = re.search('\(([^)]+)', date_time_str).group(1)
# print(year, month, day, hours, minutes, sec)
# start_at_time = f"{datime_list[0]}/{datime_list[1]}/{datime_list[2]}"
# print(start_at_time)