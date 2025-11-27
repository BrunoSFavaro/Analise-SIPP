import numpy as np
import matplotlib.pyplot as plt

def gerar_grafico(df, config=None):
    """
    Gera figura matplotlib e um dict com estatísticas.
    Config é um dict que pode conter:
      - IGNORAR_INICIAIS
      - IGNORAR_FINAIS
      - LIMITE_SUPERIOR
      - LIMIAR_QUEDA (opcional)
    """

    LIMIAR_QUEDA = config.get("LIMIAR_QUEDA", 0.995) if config else 0.995
    IGNORAR_INICIAIS = int(config.get("IGNORAR_INICIAIS", 200)) if config else 200
    IGNORAR_FINAIS = int(config.get("IGNORAR_FINAIS", 200)) if config else 200
    LIMITE_SUPERIOR = int(config.get("LIMITE_SUPERIOR", 59820)) if config else 59820

    # pega colunas principais assumindo que já foram convertidas em processar_csv
    current = df['CurrentCall'].astype(float)
    # tenta usar CallRate(P) quando disponível senão CallRate(C)
    callrate_col = 'CallRate(P)' if 'CallRate(P)' in df.columns else ('CallRate(C)' if 'CallRate(C)' in df.columns else None)
    callrate = df[callrate_col].astype(float) if callrate_col else np.zeros(len(df))
    failed = df['FailedCall(C)'].astype(float)

    t = np.arange(len(df))

    # Corta final quando CallRate = 0 (mesmo comportamento que você tinha)
    if (callrate > 0).any():
        ultimo_idx_ativo = int(np.max(np.where(callrate > 0)))
        corte_realizado = ultimo_idx_ativo < len(df) - 1
        if corte_realizado:
            df = df.iloc[:ultimo_idx_ativo + 1]
            current = current.iloc[:ultimo_idx_ativo + 1]
            callrate = callrate.iloc[:ultimo_idx_ativo + 1]
            failed = failed.iloc[:ultimo_idx_ativo + 1]
            t = np.arange(len(df))
    else:
        corte_realizado = False

    pico_idx = int(current.values.argmax())
    pico_val = float(current.iloc[pico_idx])
    threshold = pico_val * LIMIAR_QUEDA

    queda_idx = next((i for i in range(pico_idx + 1, len(current)) if current.iloc[i] < threshold), None)
    falha_idx = next((i for i in range(pico_idx + 1, len(failed)) if failed.iloc[i] > failed.iloc[i - 1]), None)

    inicio_valido = IGNORAR_INICIAIS
    fim_valido = len(current) - IGNORAR_FINAIS
    media_chamadas = current.iloc[inicio_valido:fim_valido].mean() if fim_valido > inicio_valido else current.mean()

    stats = {
        "pico": int(pico_val),
        "media": float(media_chamadas),
        "callrate_max": float(callrate.max()),
        "callrate_media": float(callrate[callrate > 0].mean()) if (callrate > 0).any() else 0.0,
        "total_falhas": int(failed.iloc[-1]) if len(failed) > 0 else 0,
        "queda_idx": queda_idx,
        "falha_idx": falha_idx,
        "corte_realizado": corte_realizado,
        "limite_superior": LIMITE_SUPERIOR,
    }

    # figura
    fig, ax1 = plt.subplots(figsize=(13, 7))
    ax2 = ax1.twinx()

    ax1.plot(t, current, label='Chamadas Ativas (CurrentCall)', linewidth=2)
    ax1.plot(t, callrate, label='Taxa de Chamadas (CallRate)', alpha=0.7)
    ax2.plot(t, failed, label='Falhas (FailedCall(C))', linestyle='--', alpha=0.8)

    ax1.axvline(pico_idx, color='green', linestyle='--', label='Pico')
    if queda_idx is not None:
        ax1.axvline(queda_idx, color='red', linestyle='--', label='Início da Queda')
    if falha_idx is not None:
        ax1.axvline(falha_idx, color='orange', linestyle='--', label='Primeira Falha')

    ax1.axhline(LIMITE_SUPERIOR, color='purple', linestyle=':', label=f'Limite {LIMITE_SUPERIOR}')
    ax1.set_xlabel('Amostra (tempo relativo)')
    ax1.set_ylabel('Chamadas / Taxa de Chamadas')
    ax2.set_ylabel('Falhas')

    fig.suptitle('Análise de Chamadas SIPp')
    fig.legend(loc='upper left')
    fig.tight_layout()

    return fig, stats
