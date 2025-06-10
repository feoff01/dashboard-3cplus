from flask import Flask, jsonify, send_file
from flask_cors import CORS
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)  # Ativa CORS

TOKEN = "WxKTCV3PvjUAHLYy9sgmZ1bLsXM2qAnbL7jQYp6Qc8kmUgO9GJH0Zn7kUlDd"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
URL = "https://barsixp.3c.plus/api/v1/calls"

def buscar_ligacoes_da_api():
    dados = []
    page = 1
    max_paginas = 50

    data_inicio = datetime(datetime.now().year, 1, 1)
    data_hoje = datetime.utcnow()

    try:
        while page <= max_paginas:
            params = {
                "filters[created_at][from]": data_inicio.strftime("%Y-%m-%dT00:00:00Z"),
                "filters[created_at][to]": data_hoje.strftime("%Y-%m-%dT23:59:59Z"),
                "agent_ids[]": [],
                "per_page": 500,
                "page": page
            }

            resp = requests.get(URL, headers=HEADERS, params=params, timeout=30)

            if resp.status_code != 200:
                print(f"❌ Erro: {resp.text}", flush=True)
                return []

            page_data = resp.json().get("data", [])
            if not page_data:
                break

            dados.extend(page_data)
            page += 1

        return dados

    except requests.exceptions.RequestException as e:
        print(f"❌ Erro de conexão com API: {e}", flush=True)
        return []

@app.route("/")
def index():
    caminho = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return send_file(caminho)

@app.route("/api/ligacoes")
def obter_ligacoes():
    dados = buscar_ligacoes_da_api()
    return jsonify(dados)

@app.route("/api/resumo")
def resumo_ligacoes():
    dados = buscar_ligacoes_da_api()

    hoje = datetime.utcnow().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())

    contagem_total = 0
    contagem_hoje = 0
    contagem_semana = 0
    qualificacao_total = 0
    qualificacao_semana = 0
    agentes_hoje = {}
    agentes_qual_total = {}
    agentes_qual_semana = {}

    for lig in dados:
        call_date_str = lig.get("call_date", "")
        try:
            data_lig = datetime.strptime(call_date_str[:10], "%Y-%m-%d").date()
        except Exception:
            continue

        agente_info = lig.get("agent")
        agente = "Desconhecido"

        if isinstance(agente_info, dict):
            agente = agente_info.get("name", "Desconhecido")
        elif isinstance(agente_info, str):
            agente = agente_info.strip() or "Desconhecido"
        elif lig.get("agente_nome"):
            agente = lig.get("agente_nome")

        qualificacao = lig.get("qualification", "")

        contagem_total += 1
        if inicio_semana <= data_lig <= hoje:
            contagem_semana += 1
            if qualificacao == "Venda feita por telefone":
                qualificacao_semana += 1
                agentes_qual_semana[agente] = agentes_qual_semana.get(agente, 0) + 1

        if data_lig == hoje:
            contagem_hoje += 1
            agentes_hoje[agente] = agentes_hoje.get(agente, 0) + 1

        if qualificacao == "Venda feita por telefone":
            qualificacao_total += 1
            agentes_qual_total[agente] = agentes_qual_total.get(agente, 0) + 1

    agente_top_hoje = max(agentes_hoje, key=agentes_hoje.get, default="Nenhum agente")
    agente_venda_semana = max(agentes_qual_semana, key=agentes_qual_semana.get, default="Nenhum agente")
    agente_venda_total = max(agentes_qual_total, key=agentes_qual_total.get, default="Nenhum agente")

    resumo = {
        "agente_top_hoje": agente_top_hoje,
        "ligacoes_top_hoje": agentes_hoje.get(agente_top_hoje, 0),
        "contagem_hoje": contagem_hoje,
        "contagem_semana": contagem_semana,
        "contagem_total": contagem_total,
        "qualificacao_total": qualificacao_total,
        "qualificacao_semana": qualificacao_semana,
        "agente_venda_total": agente_venda_total,
        "vendas_total_agente": agentes_qual_total.get(agente_venda_total, 0),
        "agente_venda_semana": agente_venda_semana,
        "vendas_semana_agente": agentes_qual_semana.get(agente_venda_semana, 0)
    }

    return jsonify(resumo)

@app.route("/api/debug")
def debug_api():
    return jsonify({"mensagem": "API está ativa!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
