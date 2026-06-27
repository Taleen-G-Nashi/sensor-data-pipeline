import pandas as pd
import os

#---Load-------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
df = pd.read_csv(os.path.join(DATA_DIR, 'airtravel.csv'))

print(f'Shape: {df.shape}')
print(f'Columns: {df.columns.tolist()}')
print(('\nFirst 5 rows:'))
print(df.head())

#---Inspect----------------------
print('\nBasic statistics: ')
print(df.describe())

#---Compute a derived column-----
numeric_cols = df.select_dtypes(include='number').columns.tolist()
df['row_total'] = df[numeric_cols].sum(axis = 1)
df['row_mean'] = df[numeric_cols].mean(axis = 1).round(1)

#---Filter: only rows above te annual mean----
annual_mean = df['row_total'].mean()
high = df[df['row_total'] > annual_mean].copy()
print(f'\nRows above annual mean ({annual_mean:.0f}): {len(high)}')


#---Save------------------------
out_path = os.path.join(DATA_DIR, 'high_travel.csv')
high.to_csv(out_path, index=False)
print(f'Saved filtered data to {out_path}')
