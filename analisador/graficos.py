import numpy as np
import matplotlib.pyplot as plt

LIMIAR_QUEDA = 0.995
IGNORAR_INICIAIS = 200
IGNORAR_FINAIS = 200
LIMITE_SUPERIOR = 59820

def gerar_grafico(df):
    current = df['CurrentCall'].astype(float)
    callrate = df['CallRate(P)'].astype(float)
    failed = df['FailedCall(C)'].astype(float)
    t = np.arange(len(df))

    # Corta final quando CallRate = 0
    if (callrate > 0).any():
        ultimo_idx_ativo = int(np.max(np.where(callrate > 0)))
        df = df.iloc[:ultimo_idx_ativo + 1]
        current = current.iloc[:ultimo_idx_ativo + 1]
        callrate = callrate.iloc[:ultimo_idx_ativo + 1]
        failed = failed.iloc[:ultimo_idx_ativo + 1]
        t = np.arange(len(df))

    pico_idx = current.values.argmax()
    pico_val = current.iloc[pico_idx]
    threshold = pico_val * LIMIAR_QUEDA

    queda_idx = next((i for i in range(pico_idx + 1, len(current)) if current.iloc[i] < threshold), None)
    falha_idx = next((i for i in range(pico_idx + 1, len(failed)) if failed.iloc[i] > failed.iloc[i - 1]), None)

    # Estatísticas
    inicio_valido = IGNORAR_INICIAIS
    fim_valido = len(current) - IGNORAR_FINAIS
    media_chamadas = current.iloc[inicio_valido:fim_valido].mean() if fim_valido > inicio_valido else current.mean()

    stats = {
        "pico": int(pico_val),
        "media": float(media_chamadas),
        "callrate_max": float(callrate.max()),
        "callrate_media": float(callrate[callrate > 0].mean()),
        "total_falhas": int(failed.iloc[-1]),
        "queda_idx": queda_idx,
        "falha_idx": falha_idx,
    }

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    ax1.plot(t, current, label='CurrentCall')
    ax1.plot(t, callrate, label='CallRate(P)')
    ax2.plot(t, failed, linestyle='--', label='FailedCall(C)')

    ax1.axvline(pico_idx, color='green', linestyle='--', label='Pico')
    if queda_idx is not None:
        ax1.axvline(queda_idx, color='red', linestyle='--', label='Início da Queda')
    if falha_idx is not None:
        ax1.axvline(falha_idx, color='orange', linestyle='--', label='Primeira Falha')

    ax1.axhline(LIMITE_SUPERIOR, color='purple', linestyle=':', label=f'Limite {LIMITE_SUPERIOR}')
    ax1.set_xlabel('Amostra')
    ax1.set_ylabel('Chamadas / Taxa de Chamadas')
    ax2.set_ylabel('Falhas')

    fig.suptitle('Análise de Chamadas SIPp')
    fig.legend(loc='upper left')
    fig.tight_layout()

    return fig, stats
