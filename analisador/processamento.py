import pandas as pd
import streamlit as st

def processar_csv(caminho_ou_obj, config):
    """
    Recebe: caminho de arquivo (str) ou file-like (UploadedFile).
    Usa o config (dict) apenas para parâmetros (IGNORAR_INICIAIS/FINAIS etc).
    Retorna: DataFrame já com colunas limpas e tipadas.
    """
    
    try:
        df = pd.read_csv(caminho_ou_obj, sep=r'[;\t]', engine='python', dtype=str)
    except Exception as e:
        raise ValueError(f"Erro ao ler CSV: {e}")

    df.columns = [c.strip() for c in df.columns]

    # --- TRATAMENTO HÍBRIDO DE TEMPO (COM CORREÇÃO GMT-3) ---
    if 'CurrentTime' in df.columns:
        def extrair_data_hibrida(val):
            if not isinstance(val, str): return val
            partes = val.split()
            
            # 1. Tenta Epoch (último elemento) - Prioridade Ouro
            if len(partes) >= 1:
                try:
                    epoch = float(partes[-1])
                    if epoch > 946684800:
                        # Converte UTC e subtrai 3 horas para Brasil (GMT-3)
                        return pd.to_datetime(epoch, unit='s') - pd.Timedelta(hours=3)
                except ValueError:
                    pass

            # 2. Fallback para Texto (Data + Hora originais do log)
            # Se o Epoch falhar, usamos o texto que já deve estar no horário local
            if len(partes) >= 2:
                return f"{partes[0]} {partes[1]}"
            return val

        df['CurrentTime'] = df['CurrentTime'].apply(extrair_data_hibrida)
        df['CurrentTime'] = pd.to_datetime(df['CurrentTime'], errors='coerce')

    # Conversão de numéricos
    cols_numericas = ['CurrentCall', 'CallRate(P)', 'CallRate(C)', 'FailedCall(C)']
    for col in cols_numericas:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0.0

    return df