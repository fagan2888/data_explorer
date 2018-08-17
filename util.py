import pandas as pd
from scipy.stats import entropy


def entropy_series(s: pd.Series):
    p = s.value_counts(dropna=True) / len(s.dropna())
    return entropy(p, base=s.nunique(dropna=True))

def div_style(split=50, position='left'):
    if position == 'left':
        return { 'width': '{}%'.format(split - 1), 'display': 'inline-block' }
    if position == 'right':
        return {'width': '{}%'.format(100 - split - 1), 'display': 'inline-block', 'float': 'right' }