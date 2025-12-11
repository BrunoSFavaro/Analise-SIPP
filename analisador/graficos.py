import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def gerar_grafico(df, config=None):
    """
    Gera gráfico interativo Plotly e um dict com estatísticas (Modo Individual).
    """
    # --- 1. PREPARAÇÃO DOS DADOS ---
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

    # --- 2. PLOTAGEM INTERATIVA COM PLOTLY ---
    
    # Cria figura com eixo Y secundário (para Falhas)
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Linha Principal: Chamadas Ativas (Azul)
    fig.add_trace(
        go.Scatter(
            x=t, y=current, name="Chamadas Ativas", 
            line=dict(color='#1f77b4', width=2),
            hovertemplate="%{y} chamadas<extra></extra>"
        ),
        secondary_y=False
    )

    # Linha: CallRate (Verde)
    fig.add_trace(
        go.Scatter(
            x=t, y=callrate, name="CallRate", 
            line=dict(color='#2ca02c', width=1), opacity=0.6,
            hovertemplate="%{y} cps<extra></extra>"
        ),
        secondary_y=False
    )

    # Linha: Falhas (Vermelho) - Eixo Secundário
    fig.add_trace(
        go.Scatter(
            x=t, y=failed, name="Falhas", 
            line=dict(color='#d62728', width=2, dash='dash'),
            hovertemplate="%{y} falhas<extra></extra>"
        ),
        secondary_y=True
    )

    # Marcadores Verticais
    fig.add_vline(x=pico_idx, line_width=1, line_dash="dash", line_color="green", annotation_text="Pico", annotation_position="top left")
    
    if queda_idx:
        fig.add_vline(x=queda_idx, line_width=1, line_dash="dash", line_color="red", annotation_text="Queda", annotation_position="bottom right")

    fig.add_hline(y=LIMITE_SUPERIOR, line_width=1, line_dash="dot", line_color="purple", annotation_text=f"Limite {LIMITE_SUPERIOR}")

    # Layout
    fig.update_layout(
        title="Análise SIPp Interativa",
        xaxis_title="Tempo (segundos)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig.update_xaxes(hoverformat=".1f") 
    fig.update_yaxes(title_text="Volume (Chamadas/Taxa)", secondary_y=False)
    fig.update_yaxes(title_text="Total Falhas", secondary_y=True)

    return fig, stats

def plotar_comparacao(df1, name1, df2, name2):
    """
    Gera gráfico comparativo INTERATIVO (Plotly) alinhado pelo RELÓGIO (GMT-3).
    """
    
    # --- 1. LIMPEZA DE TEMPO ---
    def preparar_df_tempo(df_in):
        if df_in is None or df_in.empty or 'CurrentTime' not in df_in.columns:
            return pd.DataFrame()
        df_out = df_in.copy()
        
        # Parser robusto para lixo no log (Data Hora Epoch)
        if pd.api.types.is_object_dtype(df_out['CurrentTime']):
            def parser_robusto(val):
                if not isinstance(val, str): return val
                parts = val.split()
                if len(parts) >= 3:
                    try:
                        epoch = float(parts[-1])
                        if epoch > 946684800: 
                            # Correção GMT-3 aqui também
                            return pd.to_datetime(epoch, unit='s') - pd.Timedelta(hours=3)
                    except: pass
                    return f"{parts[0]} {parts[1]}"
                return val
            df_out['CurrentTime'] = df_out['CurrentTime'].apply(parser_robusto)

        df_out['CurrentTime'] = pd.to_datetime(df_out['CurrentTime'], errors='coerce')
        return df_out.dropna(subset=['CurrentTime'])

    d1 = preparar_df_tempo(df1)
    d2 = preparar_df_tempo(df2)

    if d1.empty or d2.empty:
        raise ValueError("Dados de tempo inválidos em um dos arquivos.")
        
    min_global = min(d1['CurrentTime'].min(), d2['CurrentTime'].min())

    d1['RelativeSeconds'] = (d1['CurrentTime'] - min_global).dt.total_seconds()
    d2['RelativeSeconds'] = (d2['CurrentTime'] - min_global).dt.total_seconds()
    
    d1 = d1.sort_values('RelativeSeconds')
    d2 = d2.sort_values('RelativeSeconds')

    # --- 2. PLOTAGEM INTERATIVA ---
    fig = go.Figure()

    # Carga Combinada (Soma) - Área Sombreada ao Fundo
    try:
        ts1 = d1.set_index('CurrentTime')['CurrentCall'].resample('1s').mean()
        ts2 = d2.set_index('CurrentTime')['CurrentCall'].resample('1s').mean()
        
        # FFILL para evitar quedas artificiais
        ts1 = ts1.ffill(limit=1).fillna(0)
        ts2 = ts2.ffill(limit=1).fillna(0)

        total_load = ts1.add(ts2, fill_value=0)
        total_seconds = (total_load.index - min_global).total_seconds()
        
        fig.add_trace(go.Scatter(
            x=total_seconds, 
            y=total_load.values,
            fill='tozeroy', 
            mode='lines',
            line=dict(width=0), 
            name='Carga Combinada (Soma)',
            fillcolor='rgba(128, 128, 128, 0.5)', 
            hovertemplate="<b>%{y:.0f}</b> (Soma)<extra></extra>"
        ))
    except Exception:
        pass

    # Linha Arquivo A
    fig.add_trace(go.Scatter(
        x=d1['RelativeSeconds'], y=d1['CurrentCall'],
        mode='lines', name=f"{name1}", line=dict(width=2),
        hovertemplate="<b>%{y}</b> chamadas<extra></extra>" 
    ))

    # Linha Arquivo B
    fig.add_trace(go.Scatter(
        x=d2['RelativeSeconds'], y=d2['CurrentCall'],
        mode='lines', name=f"{name2}", line=dict(width=2),
        hovertemplate="<b>%{y}</b> chamadas<extra></extra>" 
    ))

    fig.update_layout(
        title=f"Comparativo Sincronizado (Zero = {min_global.strftime('%H:%M:%S')})",
        xaxis_title="Tempo de Execução (segundos)",
        yaxis_title="Chamadas Simultâneas",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_xaxes(hoverformat=".1f") 

    return fig