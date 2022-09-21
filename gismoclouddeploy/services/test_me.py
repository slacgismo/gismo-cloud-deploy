import datetime
import time
import json
import re
import pandas as pd
# df = pd.read_csv("init_command_logs_644.csv")
# print(df["file_name"])

import fnmatch
files =['this.csv','LICENSE.txt', 'lines.txt', 'listwidget.ui', 'lo1.ui', 'lo2.ui', 'lo3.ui', 'logo.png', 'logo.svg', 'lw.ui']
matching = fnmatch.fnmatch('htis.csv', '*.csv')
print(matching)