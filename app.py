import streamlit as st
from analisador.processamento import processar_csv
from analisador.graficos import gerar_grafico

st.title("Analisador SIPp")

arquivo_csv = st.file_uploader("Selecione o CSV de estatísticas (stats_*.csv)", type=["csv"])

if arquivo_csv is not None:
    df = processar_csv(arquivo_csv)
    fig, stats = gerar_grafico(df)

    st.pyplot(fig)

    st.subheader("Estatísticas do teste")
    st.write(f"📌 Pico de chamadas simultâneas: **{stats['pico']}**")
    st.write(f"📊 Média de chamadas simultâneas: **{stats['media']:.1f}**")
    st.write(f"🚀 Máxima taxa de chamadas (CallRate): **{stats['callrate_max']:.1f}**")
    st.write(f"📈 Taxa média de chamadas: **{stats['callrate_media']:.1f}**")
    st.write(f"❌ Falhas acumuladas: **{stats['total_falhas']}**")

    if stats["queda_idx"] is not None:
        st.error(f"⚠️ Queda detectada após o pico — posição: {stats['queda_idx']}")
    else:
        st.success("Nenhuma queda detectada após o pico.")

    if stats["falha_idx"] is not None:
        st.warning(f"⚠️ Primeira falha detectada em: {stats['falha_idx']}")
