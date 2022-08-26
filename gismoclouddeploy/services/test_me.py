import datetime
import time
import json
import re
import pandas as pd
df = pd.read_csv("init_command_logs_644.csv")
print(df["file_name"])