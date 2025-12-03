import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def gerar_grafico(df, config=None):
    """
    Gera figura matplotlib e um dict com estatísticas (Modo Individual).
    """
    # Configurações com valores padrão seguros
    LIMIAR_QUEDA = config.get("LIMIAR_QUEDA", 0.995) if config else 0.995
    IGNORAR_INICIAIS = int(config.get("IGNORAR_INICIAIS", 200)) if config else 200
    IGNORAR_FINAIS = int(config.get("IGNORAR_FINAIS", 200)) if config else 200
    LIMITE_SUPERIOR = int(config.get("LIMITE_SUPERIOR", 59820)) if config else 59820

    current = df['CurrentCall'].astype(float)
    
    callrate_col = 'CallRate(P)' if 'CallRate(P)' in df.columns else ('CallRate(C)' if 'CallRate(C)' in df.columns else None)
    callrate = df[callrate_col].astype(float) if callrate_col else np.zeros(len(df))
    failed = df['FailedCall(C)'].astype(float)

    t = np.arange(len(df))

    # Crop Inteligente
    corte_realizado = False
    if (callrate > 0).any():
        ultimo_idx_ativo = int(np.max(np.where(callrate > 0)))
        if ultimo_idx_ativo < len(df) - 1:
            corte_realizado = True
            df = df.iloc[:ultimo_idx_ativo + 1]
            current = current.iloc[:ultimo_idx_ativo + 1]
            callrate = callrate.iloc[:ultimo_idx_ativo + 1]
            failed = failed.iloc[:ultimo_idx_ativo + 1]
            t = np.arange(len(df))

    # Estatísticas
    pico_idx = int(current.values.argmax())
    pico_val = float(current.iloc[pico_idx])
    threshold = pico_val * LIMIAR_QUEDA

    queda_idx = next((i for i in range(pico_idx + 1, len(current)) if current.iloc[i] < threshold), None)
    falha_idx = next((i for i in range(len(failed)) if failed.iloc[i] > 0), None)

    inicio_valido = IGNORAR_INICIAIS
    fim_valido = len(current) - IGNORAR_FINAIS
    if fim_valido > inicio_valido:
        media_chamadas = current.iloc[inicio_valido:fim_valido].mean()
    else:
        media_chamadas = current.mean()

    stats = {
        "pico": int(pico_val),
        "media": float(media_chamadas),
        "callrate_max": float(callrate.max()),
        "callrate_media": float(callrate[callrate > 0].mean()) if (callrate > 0).any() else 0.0,
        "total_falhas": int(failed.iloc[-1]) if len(failed) > 0 else int(failed.sum()),
        "queda_idx": queda_idx,
        "falha_idx": falha_idx,
        "corte_realizado": corte_realizado,
        "limite_superior": LIMITE_SUPERIOR,
    }

    fig, ax1 = plt.subplots(figsize=(13, 7))
    ax2 = ax1.twinx()

    ax1.plot(t, current, label='Chamadas Ativas', linewidth=2, color='#1f77b4')
    ax1.plot(t, callrate, label='CallRate', alpha=0.5, color='#2ca02c')
    ax2.plot(t, failed, label='Falhas', linestyle='--', alpha=0.8, color='#d62728')

    ax1.axvline(pico_idx, color='green', linestyle='--', alpha=0.5, label='Pico')
    if queda_idx: ax1.axvline(queda_idx, color='red', linestyle='--', alpha=0.5, label='Queda')
    
    ax1.axhline(LIMITE_SUPERIOR, color='purple', linestyle=':', label=f'Limite {LIMITE_SUPERIOR}')
    
    ax1.set_xlabel('Tempo (segundos)')
    ax1.set_ylabel('Volume')
    ax2.set_ylabel('Falhas')
    
    fig.suptitle('Análise SIPp (Individual)')
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))
    fig.tight_layout()

    return fig, stats

def plotar_comparacao(df1, name1, df2, name2):
    """
    Gera um gráfico comparativo alinhado pelo RELÓGIO, mas exibindo em SEGUNDOS RELATIVOS.
    """
    
    # Função interna auxiliar para garantir a limpeza do tempo
    def preparar_df_tempo(df_in):
        if df_in is None or df_in.empty or 'CurrentTime' not in df_in.columns:
            return pd.DataFrame() # Retorna vazio se inválido
            
        df_out = df_in.copy()
        
        # Se a coluna for do tipo objeto (string), forçamos o parser robusto
        if pd.api.types.is_object_dtype(df_out['CurrentTime']):
            def parser_robusto(val):
                if not isinstance(val, str): return val
                # split() sem argumentos lida com espaços E tabs (\t) automaticamente
                parts = val.split()
                
                # Caso do log sujo: "2025-11-14 15:42:22.442155 1763145742.442155" (3 partes)
                if len(parts) >= 3:
                    # TENTATIVA 1: Epoch (último elemento) - Mais seguro e preciso
                    try:
                        epoch = float(parts[-1])
                        # Validação simples: Epoch > ano 2000 (946684800)
                        if epoch > 946684800:
                            return pd.to_datetime(epoch, unit='s')
                    except: pass
                    
                    # TENTATIVA 2: Fallback para Data + Hora (dois primeiros elementos)
                    # Ex: "2025-11-14 15:42:22.442155"
                    return f"{parts[0]} {parts[1]}"
                
                return val

            # Aplica o parser em TODAS as linhas (removemos a verificação de amostra que poderia falhar)
            df_out['CurrentTime'] = df_out['CurrentTime'].apply(parser_robusto)

        # Converte para datetime. Se o parser retornou Timestamp, ele mantém. Se retornou string limpa, ele converte.
        df_out['CurrentTime'] = pd.to_datetime(df_out['CurrentTime'], errors='coerce')
            
        return df_out.dropna(subset=['CurrentTime'])

    # Aplica a preparação robusta
    d1 = preparar_df_tempo(df1)
    d2 = preparar_df_tempo(df2)

    # Encontra o "Zero Absoluto" (o momento que o PRIMEIRO dos dois testes começou)
    if d1.empty or d2.empty:
        raise ValueError("Um dos arquivos não possui dados de tempo válidos após o processamento. Verifique se o log contém Data/Hora ou Timestamp legível.")
        
    min_global = min(d1['CurrentTime'].min(), d2['CurrentTime'].min())

    # Cria coluna de segundos relativos mantendo o offset real
    # Ex: Se A começou às 10:00:00 (0s) e B às 10:00:05, B começará em 5s.
    d1['RelativeSeconds'] = (d1['CurrentTime'] - min_global).dt.total_seconds()
    d2['RelativeSeconds'] = (d2['CurrentTime'] - min_global).dt.total_seconds()

    d1 = d1.sort_values('RelativeSeconds')
    d2 = d2.sort_values('RelativeSeconds')

    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plota usando Segundos no X
    ax.plot(d1['RelativeSeconds'], d1['CurrentCall'], label=f"{name1}", alpha=0.8, linewidth=2)
    ax.plot(d2['RelativeSeconds'], d2['CurrentCall'], label=f"{name2}", alpha=0.8, linewidth=2)
    
    # Carga Combinada (Soma)
    try:
        # Resample precisa de DatetimeIndex
        ts1 = d1.set_index('CurrentTime')['CurrentCall'].resample('1S').mean().fillna(0)
        ts2 = d2.set_index('CurrentTime')['CurrentCall'].resample('1S').mean().fillna(0)
        total_load = ts1.add(ts2, fill_value=0)
        
        # Converte o índice da soma também para segundos relativos
        total_seconds = (total_load.index - min_global).total_seconds()
        
        ax.fill_between(total_seconds, total_load.values, color='gray', alpha=0.1, label="Carga Combinada")
    except Exception:
        pass

    # Ajustes finais
    ax.set_title(f"Comparativo Sincronizado (Zero em {min_global.strftime('%H:%M:%S')})")
    ax.set_ylabel("Chamadas Simultâneas")
    ax.set_xlabel("Tempo de Execução (segundos)")
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.legend()
    
    return fig