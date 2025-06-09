from flask import Flask, jsonify, send_file
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

TOKEN = "WxKTCV3PvjUAHLYy9sgmZ1bLsXM2qAnbL7jQYp6Qc8kmUgO9GJH0Zn7kUlDd"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
URL = "https://barsixp.3c.plus/api/v1/calls"

@app.route("/")
def index():
    caminho = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return send_file(caminho)

@app.route("/api/ligacoes")
def obter_ligacoes():
    print("🚀 [Railway] Rota /api/ligacoes foi acessada!",flush=True)
    dados = []
    page = 1

    data_hoje = datetime.now()
    data_inicio = data_hoje - timedelta(days=7)

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
                print(f"❌ Erro ao acessar API: {resp.status_code}")
                print(f"Resposta da API: {resp.text}")
                return jsonify({"erro": f"Erro {resp.status_code} da API"}), 500

            page_data = resp.json().get("data", [])
            if not page_data:
                break

            dados.extend(page_data)
            page += 1

        # 🔽 ADICIONANDO OS LOGS AQUI:
        print(f"🔍 Total de registros recebidos da API: {len(dados)}")
        if dados:
            print(f"📦 Exemplo de dado recebido: {dados[0]}",flush=True)
        else:
            print("⚠️ Nenhum dado foi retornado pela API 3C Plus.")

        return jsonify(dados)

    except requests.exceptions.RequestException as e:
        print("❌ Erro na requisição:", e)
        return jsonify({"erro": "Erro na conexão com a API 3C Plus."}), 500


@app.route("/api/resumo")
def resumo_ligacoes():
    response = obter_ligacoes()
    if isinstance(response, tuple):
        return response

    dados = response.get_json()
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=7)
    
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
        data_lig = datetime.strptime(lig["call_date"][:10], "%Y-%m-%d").date()
        agente = lig.get("agent") or lig.get("agente_nome") or "Desconhecido"
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

    return jsonify(resumo)

@app.route("/api/debug")
def debug_api():
    print("✅ Rota /api/debug acessada com sucesso.")
    return jsonify({"mensagem": "API está ativa!"})
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

