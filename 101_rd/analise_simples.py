import pandas as pd
import matplotlib.pyplot as plt

# CSV do SIPp
arquivo = "estatisticas.csv"

# Lendo CSV com separador ;
df = pd.read_csv(arquivo, sep=';', engine='python')
df.columns = [c.strip() for c in df.columns]  # remove espaços extras

# Colunas de interesse
concurrent = pd.to_numeric(df['CurrentCall'], errors='coerce').fillna(0)
callrate = pd.to_numeric(df['CallRate(C)'], errors='coerce').fillna(0)
failed = pd.to_numeric(df['FailedCall(C)'], errors='coerce').fillna(0)

# Eixo X: número da linha / leitura
t = range(len(df))

# --- DETECÇÃO AUTOMÁTICA DE QUEDA / LIMITE ---

# Critério 1: quando CurrentCall atinge pico e começa a estabilizar ou cair
pico_idx = concurrent.idxmax()
pico_val = concurrent.max()

# Procurar o primeiro ponto após o pico onde concurrent < 99.5% do pico
threshold = pico_val * 0.995
declinio_idx = None
for idx in range(pico_idx+1, len(concurrent)):
    if concurrent[idx] < threshold:
        declinio_idx = idx
        break

# Critério 2: quando FailedCall(C) começa a aumentar
falhas_idx = None
for idx in range(1, len(failed)):
    if failed[idx] > failed[idx-1]:
        falhas_idx = idx
        break

# --- PRINT RESUMO ---
print("=== RESUMO DA ANÁLISE ===")
print(f"Pico de chamadas simultâneas: {pico_val:.0f} no índice {pico_idx}")
if declinio_idx:
    print(f"Queda/estabilização detectada no índice {declinio_idx} (CurrentCall={concurrent[declinio_idx]:.0f})")
else:
    print("Nenhuma queda clara detectada após o pico")

if falhas_idx:
    print(f"Primeira falha detectada no índice {falhas_idx} (FailedCall(C)={failed[falhas_idx]:.0f})")
else:
    print("Nenhuma falha detectada")

# --- PLOT ---
plt.figure(figsize=(12,6))
plt.plot(t, concurrent, label='Chamadas Ativas (CurrentCall)', linewidth=2)
plt.plot(t, callrate, label='CallRate(C)', alpha=0.8)
plt.plot(t, failed, label='Chamadas Falhadas (FailedCall(C))', alpha=0.8, linestyle='--')

# Marcar pontos de interesse
plt.axvline(x=pico_idx, color='green', linestyle='--', label='Pico de chamadas')
if declinio_idx:
    plt.axvline(x=declinio_idx, color='red', linestyle='--', label='Queda/estabilização')
if falhas_idx:
    plt.axvline(x=falhas_idx, color='orange', linestyle='--', label='Primeira falha')

plt.xlabel('Leitura #')
plt.ylabel('Quantidade')
plt.title('Evolução das Chamadas SIPp')
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('grafico_sipp_analise.png', dpi=150)
plt.show()
