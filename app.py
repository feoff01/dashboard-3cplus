from flask import Flask, jsonify, send_file
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

TOKEN = "WxKTCV3PvjUAHLYy9sgmZ1bLsXM2qAnbL7jQYp6Qc8kmUgO9GJH0Zn7kUlDd"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
URL = "https://barsixp.3c.plus/api/v1/calls"

dados_cache = []

@app.route("/")
def index():
    caminho = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return send_file(caminho)

@app.route("/api/pegar")
def pegar_dados():
    global dados_cache
    dados = []
    page = 1
    data_hoje = datetime.now()
    data_inicio = data_hoje - timedelta(days=30)

    try:
        while True:
            params = {
                "filters[created_at][from]": data_inicio.strftime("%Y-%m-%dT00:00:00Z"),
                "filters[created_at][to]": data_hoje.strftime("%Y-%m-%dT23:59:59Z"),
                "agent_ids[]": [],
                "per_page": 500,
                "page": page
            }

            resp = requests.get(URL, headers=HEADERS, params=params, timeout=30)
            if resp.status_code != 200:
                return jsonify({"erro": f"Erro {resp.status_code} da API"}), 500

            page_data = resp.json().get("data", [])
            if not page_data:
                break

            chamadas_validas = [
                lig for lig in page_data
                if lig.get("readable_status_text") == "Finalizada"
                and lig.get("speaking_time", "00:00:00") > "00:00:00"
            ]

            dados.extend(chamadas_validas)
            page += 1

        dados_cache = dados
        return jsonify({"status": "ok", "mensagem": "Dados prontos para exibir."})

    except requests.exceptions.RequestException as e:
        return jsonify({"erro": f"Erro ao acessar a API: {e}"}), 500

@app.route("/api/resumo")
def resumo_ligacoes():
    global dados_cache
    dados = dados_cache

    def obter_inicio_e_fim_da_semana():
        hoje = datetime.today()
        inicio = hoje - timedelta(days=hoje.weekday())  # Segunda
        fim = inicio + timedelta(days=6)                # Domingo
        return inicio.date(), fim.date()

    hoje = datetime.now().date()
    inicio_semana, fim_semana = obter_inicio_e_fim_da_semana()
    inicio_mes = hoje.replace(day=1)

    contagem_total = 0
    contagem_hoje = 0
    contagem_semana = 0
    qualificacao_total = 0
    qualificacao_semana = 0
    agentes_hoje = {}
    agentes_qual_total = {}
    agentes_qual_semana = {}

    for lig in dados:
        if "call_date" not in lig:
            continue
        try:
            data_lig = datetime.strptime(lig["call_date"][:10], "%Y-%m-%d").date()
        except:
            continue

        agente = lig.get("agent") or lig.get("agente_nome") or "Desconhecido"
        qualificacao = lig.get("qualification", "")

        # ✅ Total do mês (1º dia até hoje)
        if data_lig >= inicio_mes:
            contagem_total += 1
            if qualificacao == "Venda feita por telefone":
                qualificacao_total += 1
                agentes_qual_total[agente] = agentes_qual_total.get(agente, 0) + 1

        # ✅ Semana atual (segunda a domingo)
        if inicio_semana <= data_lig <= fim_semana:
            contagem_semana += 1
            if qualificacao == "Venda feita por telefone":
                qualificacao_semana += 1
                agentes_qual_semana[agente] = agentes_qual_semana.get(agente, 0) + 1

        # ✅ Hoje
        if data_lig == hoje:
            contagem_hoje += 1
            agentes_hoje[agente] = agentes_hoje.get(agente, 0) + 1

    agente_top_hoje = max(agentes_hoje, key=agentes_hoje.get) if agentes_hoje else "Nenhum agente"
    ligacoes_top_hoje = agentes_hoje.get(agente_top_hoje, 0)

    agente_venda_semana = max(agentes_qual_semana, key=agentes_qual_semana.get) if agentes_qual_semana else "Nenhum agente"
    vendas_semana_agente = agentes_qual_semana.get(agente_venda_semana, 0)

    agente_venda_total = max(agentes_qual_total, key=agentes_qual_total.get) if agentes_qual_total else "Nenhum agente"
    vendas_total_agente = agentes_qual_total.get(agente_venda_total, 0)

    resumo = {
        "agente_top_hoje": agente_top_hoje,
        "ligacoes_top_hoje": ligacoes_top_hoje,
        "contagem_hoje": contagem_hoje,
        "contagem_semana": contagem_semana,
        "contagem_total": contagem_total,  # total no mês
        "qualificacao_total": qualificacao_total,  # total no mês2
        "qualificacao_semana": qualificacao_semana,
        "agente_venda_total": agente_venda_total,
        "vendas_total_agente": vendas_total_agente,
        "agente_venda_semana": agente_venda_semana,
        "vendas_semana_agente": vendas_semana_agente
    }

    return jsonify(resumo)

@app.route("/api/graficos")
def dados_graficos():
    global dados_cache
    dados = dados_cache

    agentes_vendas = {}
    agentes_ligacoes_semana = {}
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    inicio_mes = hoje.replace(day=1)

    for lig in dados:
        agente = lig.get("agent") or lig.get("agente_nome") or "Desconhecido"
        qualificacao = lig.get("qualification", "")
        data_lig = lig.get("call_date")

        if not data_lig:
            continue

        try:
            data_formatada = datetime.strptime(data_lig[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

        if qualificacao == "Venda feita por telefone" and data_formatada >= inicio_mes:
            agentes_vendas[agente] = agentes_vendas.get(agente, 0) + 1

        if inicio_semana <= data_formatada <= hoje:
            agentes_ligacoes_semana[agente] = agentes_ligacoes_semana.get(agente, 0) + 1

    top_vendas = sorted(agentes_vendas.items(), key=lambda x: x[1], reverse=True)[:5]
    top_ligacoes_semana = sorted(agentes_ligacoes_semana.items(), key=lambda x: x[1], reverse=True)[:5]

    return jsonify({
        "top_vendas": top_vendas,
        "top_ligacoes_semana": top_ligacoes_semana
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
