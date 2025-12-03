import streamlit as st
import json
import glob
import os
import difflib
from typing import Optional, Tuple, List

# Importação dos módulos internos
from analisador.processamento import processar_csv
from analisador.graficos import gerar_grafico, plotar_comparacao

# 1. Configuração da página
st.set_page_config(
    page_title="Analisador SIPp",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Analisador SIPp — Multi-Agent Support")

# --- CONSTANTES E SETUP ---
AMBIENTES_DIR = "ambientes"

# --- FUNÇÕES AUXILIARES E CACHE ---

@st.cache_data
def listar_ambientes() -> List[Tuple[str, str]]:
    """Lista os arquivos JSON disponíveis no diretório de ambientes."""
    pattern = os.path.join(AMBIENTES_DIR, "*.json")
    paths = sorted(glob.glob(pattern))
    envs = []
    for p in paths:
        base = os.path.splitext(os.path.basename(p))[0]
        envs.append((base, p))
    return envs

@st.cache_data(show_spinner="Processando CSV...")
def carregar_dados_processados(file):
    """
    Wrapper para cachear o processamento do CSV.
    REMOVIDO: Dependência de 'config_dict', pois a limpeza bruta independe do ambiente.
    """
    if file is None: return None
    # Garante que o ponteiro do arquivo esteja no início antes de ler
    file.seek(0) 
    # Passamos dict vazio {} pois processar_csv exige o argumento mas não usa para limpeza bruta
    return processar_csv(file, {})

def detectar_ambiente_por_nome(filename: str, ambientes_list: list) -> Optional[str]:
    """Tenta adivinhar o ambiente baseado no nome do arquivo."""
    if not filename: return None
    clean_name = filename.lower()
    
    # 1. Match exato
    for nome, path in ambientes_list:
        if nome.lower() in clean_name: return path
            
    # 2. Match aproximado
    candidatos = [nome for nome, _ in ambientes_list]
    matches = difflib.get_close_matches(
        os.path.splitext(os.path.basename(filename))[0], 
        candidatos, n=1, cutoff=0.6
    )
    if matches:
        match_name = matches[0]
        for nome, path in ambientes_list:
            if nome == match_name: return path
    return None

def obter_indice_ambiente(path_detectado, lista_ambientes):
    """Retorna o índice do ambiente na lista para setar o valor default do selectbox."""
    if path_detectado:
        for i, (_, path) in enumerate(lista_ambientes):
            if path == path_detectado:
                return i
    return 0

# --- INÍCIO DA INTERFACE ---

ambientes = listar_ambientes()
if not ambientes:
    st.error(f"❌ Nenhum JSON encontrado em '{AMBIENTES_DIR}'.")
    st.stop()

# --- SIDEBAR: CONTROLE ---
with st.sidebar:
    st.header("🎛️ Painel de Controle")
    modo_operacao = st.radio("Modo de Análise", ["Individual", "Comparação (A/B)"])
    st.divider()

# ==========================================
# MODO INDIVIDUAL
# ==========================================
if modo_operacao == "Individual":
    with st.sidebar:
        st.subheader("📂 Arquivo Único")
        arquivo_csv = st.file_uploader("Upload CSV", type=["csv", "txt"], key="single")

    if arquivo_csv:
        # Detecção de Ambiente
        config_path = detectar_ambiente_por_nome(arquivo_csv.name, ambientes)
        idx_padrao = obter_indice_ambiente(config_path, ambientes)
        
        msg_status = "⚠️ Ambiente não detectado."
        if config_path:
             msg_status = f"✅ Sugerido: **{ambientes[idx_padrao][0]}**"
        
        with st.sidebar:
            st.markdown(msg_status)
            escolha_nome, escolha_path = st.selectbox(
                "Confirmar Ambiente:", ambientes, index=idx_padrao, format_func=lambda x: x[0]
            )

        # Carregar Config
        try:
            with open(escolha_path, "r", encoding="utf-8") as f: 
                config = json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar configuração: {e}")
            st.stop()
        
        try:
            # Processa o CSV (sem depender da config)
            df = carregar_dados_processados(arquivo_csv)
            # Gera gráficos (aplicando a config apenas aqui)
            fig, stats = gerar_grafico(df, config)
            
            # Exibição
            st.markdown(f"### 📊 Análise: {arquivo_csv.name}")
            
            # Métricas em Cards
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Pico de Chamadas", stats['pico'])
            c2.metric("Média Estável", f"{stats['media']:.1f}")
            c3.metric("Max CallRate", f"{stats['callrate_max']:.1f}")
            c4.metric("Falhas Totais", stats['total_falhas'], delta_color="inverse")
            
            # Alertas
            if stats['total_falhas'] > 0:
                st.warning(f"⚠️ Atenção: {stats['total_falhas']} falhas detectadas.")
            
            st.pyplot(fig)
            
        except Exception as e:
            st.error(f"Erro ao processar: {e}")
    else:
        st.info("👆 Faça o upload de um arquivo para iniciar.")

# ==========================================
# MODO COMPARAÇÃO (NOVO)
# ==========================================
else:
    st.header("⚔️ Comparação Temporal (Alinhamento por Relógio)")
    
    with st.sidebar:
        st.subheader("📂 Arquivos para Comparar")
        f_a = st.file_uploader("Lado A", type=["csv", "txt"], key="fa")
        f_b = st.file_uploader("Lado B", type=["csv", "txt"], key="fb")
        
        st.divider()
        st.subheader("⚙️ Configurações (Apenas Informativo)")

    if f_a and f_b:
        # Detecção Automática para A
        path_a_detect = detectar_ambiente_por_nome(f_a.name, ambientes)
        idx_a = obter_indice_ambiente(path_a_detect, ambientes)
        
        # Detecção Automática para B
        path_b_detect = detectar_ambiente_por_nome(f_b.name, ambientes)
        idx_b = obter_indice_ambiente(path_b_detect, ambientes)

        with st.sidebar:
            # Seletor A
            st.markdown(f"**Ambiente A** ({f_a.name})")
            nome_a, path_a = st.selectbox(
                "Config A:", ambientes, index=idx_a, format_func=lambda x: x[0], key="sel_a"
            )
            
            # Seletor B
            st.markdown(f"**Ambiente B** ({f_b.name})")
            nome_b, path_b = st.selectbox(
                "Config B:", ambientes, index=idx_b, format_func=lambda x: x[0], key="sel_b"
            )

        try:
            # Carregamos apenas para exibir o nome, já que o gráfico comparativo é Raw Data
            # Isso evita que um JSON corrompido quebre o carregamento do CSV
            pass 
        except Exception as e:
            st.error(f"Erro: {e}")
            
        try:
            # Processa cada um de forma INDEPENDENTE da configuração
            df_a = carregar_dados_processados(f_a)
            df_b = carregar_dados_processados(f_b)
            
            # Chama a função plotar_comparacao
            fig_comp = plotar_comparacao(df_a, f_a.name, df_b, f_b.name)
            
            st.pyplot(fig_comp)
            
            # Resumo rápido em colunas
            st.divider()
            col_a, col_b = st.columns(2)
            
            with col_a:
                pico_a = df_a['CurrentCall'].max() if not df_a.empty else 0
                st.info(f"📁 **{f_a.name}**")
                st.caption(f"Ambiente detectado: {nome_a}")
                st.metric("Pico A", int(pico_a))

            with col_b:
                pico_b = df_b['CurrentCall'].max() if not df_b.empty else 0
                st.info(f"📁 **{f_b.name}**")
                st.caption(f"Ambiente detectado: {nome_b}")
                st.metric("Pico B", int(pico_b))
            
        except Exception as e:
            st.error(f"Erro na comparação: {e}")
            st.warning("Verifique se as colunas 'CurrentTime' existem e estão no formato correto.")
    else:
        st.info("Necessário fazer upload de ambos os arquivos (A e B).")