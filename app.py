import streamlit as st
import json
import glob
import os
import difflib

from analisador.processamento import processar_csv
from analisador.graficos import gerar_grafico

st.set_page_config(layout="wide")
st.title("Analisador SIPp — Auto-detect ambiente")

# lista os JSONs de configuração
AMBIENTES_DIR = "ambientes"
json_paths = sorted(glob.glob(os.path.join(AMBIENTES_DIR, "*.json")))

def listar_ambientes():
    envs = []
    for p in json_paths:
        base = os.path.splitext(os.path.basename(p))[0]
        envs.append((base, p))
    return envs

ambientes = listar_ambientes()

if not ambientes:
    st.error(f"Nenhum JSON de ambiente encontrado em '{AMBIENTES_DIR}'. Crie arquivos .json com as configurações.")
    st.stop()

# uploader
arquivo_csv = st.file_uploader("Selecione o CSV de estatísticas (stats_*.csv) ou arraste-o aqui", type=["csv", "txt"])

# função que tenta detectar ambiente a partir do nome do arquivo
def detectar_ambiente_por_nome(filename):
    if not filename:
        return None
    # tenta correspondência direta (substring)
    for nome, path in ambientes:
        if nome.lower() in filename.lower():
            return path
    # tenta correspondência por similaridade do nome
    candidatos = [nome for nome, _ in ambientes]
    best = difflib.get_close_matches(os.path.splitext(os.path.basename(filename))[0], candidatos, n=1, cutoff=0.6)
    if best:
        sel = best[0]
        for nome, path in ambientes:
            if nome == sel:
                return path
    return None

config = None
config_path = None

if arquivo_csv is not None:
    # nome do arquivo enviado
    upload_name = getattr(arquivo_csv, "name", None)
    config_path = detectar_ambiente_por_nome(upload_name)

    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        st.info(f"Ambiente detectado automaticamente: **{os.path.splitext(os.path.basename(config_path))[0]}**")
    else:
        st.warning("Não foi possível detectar automaticamente o ambiente a partir do nome do CSV.")
        escolhas = [nome for nome, _ in ambientes]
        escolha = st.selectbox("Selecione o ambiente (fallback)", escolhas)
        # encontra o path do escolhido
        for nome, path in ambientes:
            if nome == escolha:
                config_path = path
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                break

    # processa CSV e gera gráfico
    try:
        df = processar_csv(arquivo_csv, config)
    except Exception as e:
        st.exception(e)
        st.stop()

    try:
        fig, stats = gerar_grafico(df, config)
    except Exception as e:
        st.exception(e)
        st.stop()

    st.pyplot(fig, dpi=120)

    st.subheader("Estatísticas do teste")
    st.write(f"📌 Pico de chamadas simultâneas: **{stats['pico']}**")
    st.write(f"📊 Média de chamadas simultâneas (ignorando ramp-up/down): **{stats['media']:.1f}**")
    st.write(f"🚀 Máxima taxa de chamadas (CallRate): **{stats['callrate_max']:.1f}**")
    st.write(f"📈 Taxa média de chamadas: **{stats['callrate_media']:.1f}**")
    st.write(f"❌ Falhas acumuladas: **{stats['total_falhas']}**")

    if stats["queda_idx"] is not None:
        st.error(f"⚠️ Queda detectada após o pico — posição: {stats['queda_idx']}")
    else:
        st.success("Nenhuma queda detectada após o pico.")

    if stats["falha_idx"] is not None:
        st.warning(f"⚠️ Primeira falha detectada em: {stats['falha_idx']}")
