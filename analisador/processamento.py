import pandas as pd

def processar_csv(caminho_ou_obj, config):
    """
    Recebe: caminho de arquivo (str) ou file-like (UploadedFile).
    Usa o config (dict) apenas para parâmetros (IGNORAR_INICIAIS/FINAIS etc).
    Retorna: DataFrame já com colunas limpas e tipadas.
    """

    # pandas aceita file-like (BytesIO) ou caminho str
    # detecta separador ; ou tab via engine regex (igual ao seu antigo)
    df = pd.read_csv(caminho_ou_obj, sep=r'[;\t]', engine='python', dtype=str)
    # limpa espaços nos nomes de colunas
    df.columns = [c.strip() for c in df.columns]

    # converte colunas numéricas principais para numeric, preenchendo NaN com 0
    for col in ['CurrentCall', 'CallRate(P)', 'CallRate(C)', 'FailedCall(C)']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            # cria coluna vazia se faltar (para evitar KeyError adiante)
            df[col] = 0

    # mantém colunas de tempo textuais (ElapsedTime(C/P) e CurrentTime) como estão
    # devolve df pronto
    return df
