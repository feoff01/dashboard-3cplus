from flask import Flask, jsonify, send_file
import os
from datetime import datetime

app = Flask(__name__)

@app.route("/")
def index():
    caminho = os.path.join(os.path.dirname(__file__), "dashboard.html")
    return send_file(caminho)

@app.route("/api/ligacoes")
def obter_ligacoes():
    # Retorna uma lista vazia (simulando ausência de dados)
    return jsonify([])

@app.route("/api/resumo")
def resumo_ligacoes():
    hoje = datetime.now().date().isoformat()
    resumo = {
        "agente_top_hoje": "Felipe",
        "ligacoes_top_hoje": 0,
        "contagem_hoje": 0,
        "contagem_semana": 0,
        "contagem_total": 0,
        "qualificacao_total": 0,
        "qualificacao_semana": 0,
        "agente_venda_total": "—",
        "vendas_total_agente": 0,
        "agente_venda_semana": "—",
        "vendas_semana_agente": 0
    }
    return jsonify(resumo)

if __name__ == "__main__":
    app.run(debug=True)
