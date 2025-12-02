import streamlit as st
import json
import glob
import os
import difflib
import pandas as pd
from typing import Optional, Tuple, List

# Importação dos módulos internos (assumindo que existam)
from analisador.processamento import processar_csv
from analisador.graficos import gerar_grafico

# 1. Configuração da página deve ser SEMPRE a primeira linha
st.set_page_config(
    page_title="Analisador SIPp",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Analisador SIPp — Auto-detect ambiente")

# --- CONSTANTES E SETUP ---
AMBIENTES_DIR = "ambientes"

# 2. Caching para evitar recarregar a lista de arquivos toda hora
@st.cache_data
def listar_ambientes() -> List[Tuple[str, str]]:
    """Lista os arquivos JSON disponíveis no diretório de ambientes."""
    pattern = os.path.join(AMBIENTES_DIR, "*.json")
    paths = sorted(glob.glob(pattern))
    envs = []
    for p in paths:
        # Extrai apenas o nome do arquivo sem extensão para exibição
        base = os.path.splitext(os.path.basename(p))[0]
        envs.append((base, p))
    return envs

# 3. Caching pesado no processamento do CSV
# Isso faz com que, se o usuário mudar de aba ou configuração,
# o pandas não precise ler o CSV gigante novamente.
@st.cache_data(show_spinner="Processando CSV...")
def carregar_dados_processados(file, config_dict):
    """Wrapper para cachear o resultado do processamento."""
    # Como o file é um buffer, precisamos garantir que está no início
    file.seek(0) 
    return processar_csv(file, config_dict)

def detectar_ambiente_por_nome(filename: str, ambientes_list: list) -> Optional[str]:
    """Tenta adivinhar o ambiente baseado no nome do arquivo."""
    if not filename:
        return None
    
    filename_clean = filename.lower()
    
    # 1. Tentativa exata (substring)
    for nome, path in ambientes_list:
        if nome.lower() in filename_clean:
            return path
            
    # 2. Tentativa difusa (fuzzy match)
    candidatos = [nome for nome, _ in ambientes_list]
    # cutoff=0.6 requer 60% de similaridade
    matches = difflib.get_close_matches(
        os.path.splitext(os.path.basename(filename))[0], 
        candidatos, 
        n=1, 
        cutoff=0.6
    )
    
    if matches:
        match_name = matches[0]
        for nome, path in ambientes_list:
            if nome == match_name:
                return path
                
    return None

# --- INÍCIO DA LÓGICA DE UI ---

ambientes = listar_ambientes()

if not ambientes:
    st.error(f"❌ Nenhum JSON encontrado em '{AMBIENTES_DIR}'.")
    st.stop()

# Sidebar para inputs (deixa o gráfico com mais espaço)
with st.sidebar:
    st.header("📂 Entrada de Dados")
    arquivo_csv = st.file_uploader("Arquivo de Logs (stats_*.csv)", type=["csv", "txt"])

if arquivo_csv:
    # Lógica de detecção do ambiente
    config_path_detectado = detectar_ambiente_por_nome(arquivo_csv.name, ambientes)
    
    # Define o índice padrão para o selectbox
    index_padrao = 0
    msg_detect = None
    
    if config_path_detectado:
        # Encontra o índice do path detectado na lista de tuplas
        for i, (_, path) in enumerate(ambientes):
            if path == config_path_detectado:
                index_padrao = i
                msg_detect = f"✅ Detectado: **{ambientes[i][0]}**"
                break
    
    # Selectbox inteligente: já vem selecionado se detectou, mas permite troca
    with st.sidebar:
        st.write("---")
        st.subheader("⚙️ Configuração")
        
        if msg_detect:
            st.markdown(msg_detect)
        else:
            st.warning("⚠️ Ambiente não detectado automaticamente.")
            
        escolha_nome, escolha_path = st.selectbox(
            "Ambiente Selecionado:", 
            ambientes, 
            index=index_padrao,
            format_func=lambda x: x[0] # Mostra só o nome, mas retorna a tupla
        )

    # Carregamento do JSON (Unificado)
    try:
        with open(escolha_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        st.error(f"Erro ao ler JSON de configuração: {e}")
        st.stop()

    # --- PROCESSAMENTO E EXIBIÇÃO ---
    
    try:
        # Chama a função cacheada
        df = carregar_dados_processados(arquivo_csv, config)
    except Exception as e:
        st.error("Erro ao processar CSV.")
        st.exception(e)
        st.stop()

    # Dashboard de Métricas (Visualização em Colunas)
    try:
        fig, stats = gerar_grafico(df, config)
        
        st.markdown("### 📊 Dashboard de Performance")
        
        # Linha 1 de métricas
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Pico de Chamadas", stats['pico'])
        col2.metric("Média (Estável)", f"{stats['media']:.1f}")
        col3.metric("Max CallRate", f"{stats['callrate_max']:.1f}")
        col4.metric("Falhas Totais", stats['total_falhas'], delta_color="inverse")

        # Linha 2 de alertas (usando container para destaque)
        with st.container():
            c_alerta1, c_alerta2 = st.columns(2)
            
            if stats["queda_idx"] is not None:
                c_alerta1.error(f"⚠️ Queda Brusca detectada na linha {stats['queda_idx']}")
            else:
                c_alerta1.success("✅ Estabilidade mantida após pico")
                
            # Correção: Verifica se há QUALQUER falha, independente de ter índice ou não
            if stats['total_falhas'] > 0:
                msg_falha = f"⚠️ {stats['total_falhas']} falha(s) registrada(s)."
                if stats.get("falha_idx") is not None:
                    msg_falha += f" Primeira ocorrência na linha {stats['falha_idx']}."
                c_alerta2.warning(msg_falha)
            else:
                c_alerta2.success("✅ Sem falhas registradas")

        st.divider()
        
        # Exibição do Gráfico
        st.pyplot(fig) # Remove dpi=120 se o matplotlib já estiver configurado, ou mantém se ficar pequeno.

    except Exception as e:
        st.error("Erro na geração de gráficos/métricas.")
        st.exception(e)

else:
    # State zero (quando não tem arquivo)
    st.info("👆 Faça o upload de um arquivo CSV na barra lateral para começar.")
    
    # Mostra um exemplo do que esperar
    st.markdown("""
    ### Formato esperado:
    O sistema espera arquivos padrão do **SIPp** contendo colunas como:
    - `CurrentTime`
    - `CurrentCall`
    - `CallRate(P)`
    - `FailedCall(C)`
    """)