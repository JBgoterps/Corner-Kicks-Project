import pandas as pd
from statsbombpy import sb

events = sb.events(match_id=18237) # random match id 

non_null_columns = []
for col in events.columns:
    if not events[col].isna().all():  # keep only columns with at least one non-null value
        non_null_columns.append(col)

print("Total non-null columns:", len(non_null_columns))
print(non_null_columns)