# 🔥 Analisador de Testes de Estresse SIP (SIPP)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red)

Aplicação em **Streamlit** para análise automática de logs gerados em testes de estresse com **SIPP**, convertendo arquivos CSV em gráficos interativos e métricas detalhadas.

> **Objetivo:** Eliminar o processamento manual, padronizar análises e acelerar a interpretação dos resultados de testes de carga em VoIP.

---

## Como funciona

1. O usuário seleciona o **ambiente de teste**.
2. A aplicação carrega automaticamente o arquivo de configuração JSON correspondente.
3. O usuário faz o upload do **CSV gerado pelo SIPP**.
4. O sistema plota o gráfico de evolução e gera um relatório automático de métricas.

---

## 📂 Estrutura do Projeto

```text
📦 raiz/
├── app.py                  # Ponto de entrada do Streamlit
├── analisador/             # Módulos principais
│   ├── processamento.py    # Tratamento de dados (Pandas)
│   ├── graficos.py         # Geração de plots (Plotly/Matplotlib)
│   └── relatorio.py        # Cálculo de métricas
│
├── ambientes/              # Configurações JSON por ambiente
│   ├── ambiente_A.json
│   ├── ambiente_B.json
│   └── ambiente_C.json
│
├── ambiente_A/stats                  # Diretórios de saída de cada ambiente
│   ├── ambiente_A_stats_321312/
│   ├── ambiente_A_stats_313213/
│   └── ambiente_A_stats_312443/
│
└── ambiente_B/stats
    ├── ambiente_B_stats_321312/
    ├── ambiente_B_stats_313213/
    └── ambiente_B_stats_312443/
```

---

## Configuração (JSON)

Cada ambiente possui um arquivo `.json` que dita as regras de análise:

```json
{
  "IGNORAR_INICIAIS": 200,
  "IGNORAR_FINAIS": 200,
  "LIMITE_SUPERIOR": 59820,
  "LIMIAR_QUEDA": 0.995
}
```

**Entenda os parâmetros:**

* `IGNORAR_INICIAIS` / `FINAIS`: Intervalo de tempo (ou amostras) ignorado no início (ramp-up) e no fim (ramp-down) do teste.
* `LIMITE_SUPERIOR`: O teto esperado de chamadas simultâneas.
* `LIMIAR_QUEDA`: Sensibilidade para detecção automática de queda de performance.

---

## Métricas Calculadas

A ferramenta processa o CSV e exibe as seguintes informações no relatório:

| Métrica | Descrição |
| :--- | :--- |
| 🔹 **Pico de Chamadas** | Valor máximo de chamadas simultâneas sustentado. |
| 🔹 **Média de Chamadas** | Média calculada desconsiderando *ramp-up* e *ramp-down*. |
| 🔹 **CallRate Máxima** | Maior taxa de chamadas (CPS) registrada. |
| 🔹 **CallRate Média** | Ritmo médio de chamadas ao longo do teste. |
| 🔹 **Falhas Acumuladas** | Total de chamadas falhadas detectadas na execução. |

Além disso, é gerado um gráfico de evolução comparando:
* `CurrentCall`
* `CallRate(P)`
* `FailedCall(C)`

---

## ▶️ Como Executar

1. **Clone o repositório** 
```bash
git clone https://github.com/BrunoSFavaro/Analise-SIPP.git
```

2. **Acesse o diretório do projeto**
```bash
cd Analise-SIPP
```

3. **Crie um ambiente virtual**

```bash
python -m venv .venv
```

4. **Ative o ambiente virtual**
```bash
.venv\Scripts\activate.bat
```

5. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

6. **Execute a aplicação:**

```bash
python -m streamlit run app.py
```

---

## 🛣️ Evoluções Planejadas (Roadmap)

- [ ] Upload de múltiplos CSVs com alinhamento automático por `CurrentTime`.
- [ ] Exportação de relatório em **PDF / Excel** (contendo gráficos e métricas).
- [ ] Comparação visual entre execuções distintas (ex: Baseline vs. Teste Atual).
- [ ] Histórico de execuções salvo localmente.
- [ ] Aba dedicada para análise detalhada de erros (drill-down de falhas).