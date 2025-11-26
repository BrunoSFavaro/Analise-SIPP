import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import glob
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm

# === BUSCA AUTOMÁTICA DO ÚLTIMO CSV EM /stats ===
pasta_stats = "stats"
arquivos = glob.glob(os.path.join(pasta_stats, "stats_*.csv"))

if not arquivos:
    raise FileNotFoundError("Nenhum arquivo 'stats_*.csv' encontrado na pasta /stats.")

ARQUIVO = max(arquivos, key=os.path.getctime)
base_nome = os.path.splitext(os.path.basename(ARQUIVO))[0]
PDF_SAIDA = os.path.join(pasta_stats, f"{base_nome}_relatorio.pdf")
IMG_SAIDA = os.path.join(pasta_stats, f"{base_nome}_grafico.png")

print(f"📊 Analisando arquivo: {ARQUIVO}")

# === CONFIGURAÇÕES ===
LIMIAR_QUEDA = 0.995  # 0,5% abaixo do pico = início de queda
IGNORAR_INICIAIS = 30
IGNORAR_FINAIS = 30
LIMITE_SUPERIOR = 4180  # valor de interesse

# === LEITURA DO CSV ===
df = pd.read_csv(ARQUIVO, sep=r'[;\t]', engine='python')
df.columns = [c.strip() for c in df.columns]

# === EXTRAÇÃO DE DADOS ===
current = pd.to_numeric(df['CurrentCall'], errors='coerce').fillna(0)
callrate = pd.to_numeric(df['CallRate(P)'], errors='coerce').fillna(0)
failed = pd.to_numeric(df['FailedCall(C)'], errors='coerce').fillna(0)
t = np.arange(len(df))

# === CORTA O FINAL QUANDO CALLRATE ZERA ===
if np.any(callrate > 0):
    ultimo_idx_ativo = int(np.max(np.where(callrate > 0)))
    corte_realizado = ultimo_idx_ativo < len(df) - 1
else:
    ultimo_idx_ativo = len(df) - 1
    corte_realizado = False

if corte_realizado:
    print(f"✂️  Cortando {len(df) - ultimo_idx_ativo - 1} linhas finais sem geração (CallRate=0).")
    df = df.iloc[:ultimo_idx_ativo + 1]
    current = current.iloc[:ultimo_idx_ativo + 1]
    callrate = callrate.iloc[:ultimo_idx_ativo + 1]
    failed = failed.iloc[:ultimo_idx_ativo + 1]
    t = np.arange(len(df))

# === DETECÇÃO DE PICO E QUEDA ===
pico_idx = current.to_numpy().argmax()
pico_val = current.iloc[pico_idx]
threshold = pico_val * LIMIAR_QUEDA

queda_idx = next(
    (i for i in range(pico_idx + 1, len(current)) if current.iloc[i] < threshold),
    None
)

falha_idx = next(
    (i for i in range(pico_idx + 1, len(failed)) if failed.iloc[i] > failed.iloc[i - 1]),
    None
)

# === CÁLCULOS ESTATÍSTICOS ===
max_chamadas = pico_val

inicio_valido = IGNORAR_INICIAIS
fim_valido = len(current) - IGNORAR_FINAIS
if fim_valido > inicio_valido:
    media_chamadas = current.iloc[inicio_valido:fim_valido].mean()
else:
    media_chamadas = current.mean()

total_falhas = failed.iloc[-1]
duracao_amostras = len(df)
taxa_media_callrate = callrate[callrate > 0].mean()
callrate_max = callrate.max()

# === DURAÇÃO EM SEGUNDOS ===
if 'ElapsedTime(C)' in df.columns:
    duracao_segundos = pd.to_numeric(df['ElapsedTime(C)'], errors='coerce').fillna(0).iloc[-1]
else:
    duracao_segundos = duracao_amostras

# === TIMESTAMP DO PICO ===
momento_pico = None
for coluna in ['ElapsedTime(C)', 'ElapsedTime(P)', 'CurrentTime']:
    if coluna in df.columns:
        momento_pico = str(df.iloc[pico_idx][coluna])
        break
if not momento_pico:
    momento_pico = f"t={pico_idx}"

# === TAXA DE FALHAS ===
taxa_falhas = (total_falhas / max_chamadas * 100) if max_chamadas > 0 else 0

# === DETECÇÃO DE ULTRAPASSAGENS DE 64.000 ===
def tempo_para_segundos(valor):
    """Converte formato HH:MM:SS ou HH:MM:SS:ffffff para segundos"""
    try:
        partes = str(valor).split(':')
        if len(partes) == 4:
            h, m, s, _ = partes
        elif len(partes) == 3:
            h, m, s = partes
        else:
            return 0
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return 0

ultrapassagens = df[df['CurrentCall'] > LIMITE_SUPERIOR]
momentos_ultrapassagem = []

if not ultrapassagens.empty:
    if 'ElapsedTime(C)' in df.columns:
        momentos_ultrapassagem = [tempo_para_segundos(v) for v in ultrapassagens['ElapsedTime(C)']]
    elif 'ElapsedTime(P)' in df.columns:
        momentos_ultrapassagem = [tempo_para_segundos(v) for v in ultrapassagens['ElapsedTime(P)']]
    else:
        momentos_ultrapassagem = ultrapassagens.index.tolist()

qtd_ultrapassagens = len(momentos_ultrapassagem)

# === DIAGNÓSTICO ===
diagnostico = []
if queda_idx:
    diagnostico.append(f"🔻 Queda detectada após o pico, em t={queda_idx}.")
else:
    diagnostico.append("✅ Nenhuma queda detectada após o pico — sistema estável.")

if falha_idx:
    diagnostico.append(f"⚠️ Falhas começaram em t={falha_idx}.")
if total_falhas > 0:
    diagnostico.append(f"❌ Total de falhas acumuladas: {int(total_falhas)}.")
if corte_realizado:
    diagnostico.append(f"✂️ Linhas finais removidas: {len(df) - ultimo_idx_ativo - 1} (CallRate=0).")
if qtd_ultrapassagens > 0:
    diagnostico.append(f"🚀 O CurrentCall ultrapassou {LIMITE_SUPERIOR} {qtd_ultrapassagens} vez(es).")

# === INTERPRETAÇÃO ===
if queda_idx and falha_idx and falha_idx <= queda_idx:
    interpretacao = "As falhas começaram antes ou durante o declínio — provável saturação do sistema."
elif queda_idx and not falha_idx:
    interpretacao = "Houve redução de chamadas sem falhas visíveis — possível ajuste de carga."
elif not queda_idx and falha_idx:
    interpretacao = "O sistema manteve estabilidade, mas apresentou falhas pontuais."
else:
    interpretacao = "Teste estável dentro dos limites de carga."

# === GRÁFICO ===
fig, ax1 = plt.subplots(figsize=(13, 7))
ax2 = ax1.twinx()

ax1.plot(t, current, label='Chamadas Ativas (CurrentCall)', linewidth=2, color='tab:blue')
ax1.plot(t, callrate, label='Taxa de Chamadas (CallRate(P))', alpha=0.7, color='tab:orange')
ax2.plot(t, failed, label='Falhas (FailedCall(C))', linestyle='--', color='tab:red', alpha=0.8)

ax1.axvline(pico_idx, color='green', linestyle='--', label='Pico')
if queda_idx:
    ax1.axvline(queda_idx, color='red', linestyle='--', label='Início da Queda')
if falha_idx:
    ax1.axvline(falha_idx, color='orange', linestyle='--', label='Primeira Falha')

ax1.axhline(LIMITE_SUPERIOR, color='purple', linestyle=':', label=f'Limite {LIMITE_SUPERIOR}')
ax1.set_xlabel('Amostra (tempo relativo)')
ax1.set_ylabel('Chamadas / Taxa de Chamadas')
ax2.set_ylabel('Falhas Acumuladas')

fig.suptitle('Análise de Chamadas SIPp (sem suavização)', fontsize=14)
fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.93), fontsize=9)
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(IMG_SAIDA, dpi=150)
plt.close()

# === GERAÇÃO DO PDF ===
styles = getSampleStyleSheet()
story = []

story.append(Paragraph("<b>Relatório de Análise SIPp</b>", styles['Title']))
story.append(Spacer(1, 0.5*cm))
story.append(Paragraph("<b>Resumo Técnico</b>", styles['Heading2']))

story.append(Paragraph(f"Pico de chamadas simultâneas: <b>{int(max_chamadas)}</b> (atingido em {momento_pico})", styles['Normal']))
story.append(Paragraph(f"Média de chamadas simultâneas (ignorando ramp-up e ramp-down): <b>{media_chamadas:.1f}</b>", styles['Normal']))
story.append(Paragraph(f"Maior taxa de chamadas (CallRate(P)): <b>{callrate_max:.1f}</b>", styles['Normal']))
story.append(Paragraph(f"Taxa média de chamadas (CallRate(P)): <b>{taxa_media_callrate:.1f}</b>", styles['Normal']))
story.append(Paragraph(f"Duração total do teste: <b>{duracao_segundos:.1f} s</b>", styles['Normal']))
story.append(Paragraph(f"Falhas totais registradas: <b>{int(total_falhas)}</b>", styles['Normal']))
story.append(Paragraph(f"Taxa de falhas em relação ao pico: <b>{taxa_falhas:.2f}%</b>", styles['Normal']))

if qtd_ultrapassagens > 0:
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"O CurrentCall ultrapassou {LIMITE_SUPERIOR} {qtd_ultrapassagens} vez(es).", styles['Normal']))
    momentos_str = ", ".join(f"{s}s" for s in momentos_ultrapassagem)
    story.append(Paragraph(f"Momentos aproximados (ElapsedTime): {momentos_str}", styles['Normal']))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("<b>Diagnóstico Automático</b>", styles['Heading2']))
for linha in diagnostico:
    story.append(Paragraph(linha, styles['Normal']))

story.append(Spacer(1, 0.4*cm))
story.append(Paragraph("<b>Interpretação</b>", styles['Heading2']))
story.append(Paragraph(interpretacao, styles['Normal']))

story.append(Spacer(1, 0.7*cm))
story.append(Paragraph("<b>Gráfico de Evolução das Chamadas</b>", styles['Heading2']))
story.append(Spacer(1, 0.3*cm))
story.append(Image(IMG_SAIDA, width=17*cm, height=9*cm))

doc = SimpleDocTemplate(PDF_SAIDA, pagesize=A4)
doc.build(story)

print("\n✅ Relatório PDF gerado com sucesso!")
print(f"📄 PDF: {PDF_SAIDA}")
print(f"🖼️ Gráfico: {IMG_SAIDA}")
