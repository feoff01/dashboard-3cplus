from flask import Flask, jsonify, send_file
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

TOKEN = "WxKTCV3PvjUAHLYy9sgmZ1bLsXM2qAnbL7jQYp6Qc8kmUgO9GJH0Zn7kUlDd"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
URL = "https://barsixp.3c.plus/api/v1/calls"

def buscar_ligacoes_da_api():
    dados = []
    page = 1
    max_paginas = 50

    # ✅ Pegando dados do ano todo para testes
    data_inicio = datetime.strptime("2025-01-01", "%Y-%m-%d")
    data_hoje = datetime.strptime("2025-12-31", "%Y-%m-%d")

    try:
        print("[Railway] Iniciando chamada para a API da 3C Plus...", flush=True)

        while page <= max_paginas:
            params = {
                "filters[created_at][from]": data_inicio.strftime("%Y-%m-%dT00:00:00Z"),
                "filters[created_at][to]": data_hoje.strftime("%Y-%m-%dT23:59:59Z"),
                "agent_ids[]": [],
                "per_page": 500,
                "page": page
            }

            resp = requests.get(URL, headers=HEADERS, params=params, timeout=30)
            print(f"🛰️ Página {page} | Status: {resp.status_code}", flush=True)

            if resp.status_code != 200:
                print(f"❌ Erro: {resp.text}", flush=True)
                return []

            page_data = resp.json().get("data", [])
            print(f"📦 Página {page}: {len(page_data)} registros", flush=True)

            for item in page_data:
                print("🔍 Item recebido:", item, flush=True)

            if not page_data:
                break

            dados.extend(page_data)
            page += 1

        print(f"✅ Total de registros: {len(dados)}", flush=True)
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
    print("🚀 [Railway] Rota /api/ligacoes foi acessada!", flush=True)
    dados = buscar_ligacoes_da_api()
    return jsonify(dados)

@app.route("/api/resumo")
def resumo_ligacoes():
    print("📊 [Railway] Rota /api/resumo foi acessada!", flush=True)
    dados = buscar_ligacoes_da_api()

    hoje = datetime.strptime("2025-12-31", "%Y-%m-%d").date()
    inicio_semana = datetime.strptime("2025-12-24", "%Y-%m-%d").date()

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
        except Exception as e:
            print(f"⚠️ Erro ao converter data: '{call_date_str}' - {e}", flush=True)
            continue

        agente_info = lig.get("agent")
        agente = "Desconhecido"

        if isinstance(agente_info, dict):
            agente = agente_info.get("name", "Desconhecido")
        elif isinstance(agente_info, str) and agente_info.strip():
            agente = agente_info.strip()
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
        "contagem_total": contagem_total,
        "qualificacao_total": qualificacao_total,
        "qualificacao_semana": qualificacao_semana,
        "agente_venda_total": agente_venda_total,
        "vendas_total_agente": vendas_total_agente,
        "agente_venda_semana": agente_venda_semana,
        "vendas_semana_agente": vendas_semana_agente
    }

    print(f"📤 Enviando resumo: {resumo}", flush=True)
    return jsonify(resumo)

@app.route("/api/debug")
def debug_api():
    print("✅ Rota /api/debug acessada com sucesso.", flush=True)
    return jsonify({"mensagem": "API está ativa!"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
