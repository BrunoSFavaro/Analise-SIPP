import pandas as pd

def processar_csv(caminho_csv):
    df = pd.read_csv(caminho_csv, sep=r'[;\t]', engine='python', encoding='utf-8-sig')
    df.columns = [c.strip() for c in df.columns]
    return df
