from flask import Flask, jsonify, send_file, request
import requests, os
from datetime import datetime, timedelta

app = Flask(__name__)

TOKEN   = "WxKTCV3PvjUAHLYy9sgmZ1bLsXM2qAnbL7jQYp6Qc8kmUgO9GJH0Zn7kUlDd"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}
URL     = "https://barsixp.3c.plus/api/v1/calls"

# --------------------------------------------------------------------------- #
#  Cache de dados brutos (últimos 30 dias)                                    #
# --------------------------------------------------------------------------- #
dados_cache = []

# --------------------------------------------------------------------------- #
#  Cache DIÁRIO para o PERÍODO ANTERIOR (resumo + gráficos)                   #
#  Expira automaticamente no próximo dia                                      #
# --------------------------------------------------------------------------- #
prev_cache = {
    "date": None,        # string 'YYYY-MM-DD'
    "resumo": None,      # dicionário pronto para /api/resumo?prev
    "graficos": None     # dicionário pronto para /api/graficos?prev
}


# --------------------------------------------------------------------------- #
#  Conversões de tempo                                                        #
# --------------------------------------------------------------------------- #
def tempo_para_segundos(hms: str) -> int:
    try:
        h, m, s = map(int, hms.split(":"))
        return h * 3600 + m * 60 + s
    except Exception:
        return 0


def segundos_para_hms(seg: int) -> str:
    return str(timedelta(seconds=seg))


# --------------------------------------------------------------------------- #
#  Períodos “ontem / semana passada / mês passado”                            #
# --------------------------------------------------------------------------- #
def intervalos_anteriores():
    hoje = datetime.now().date()

    ontem  = hoje - timedelta(days=1)

    primeiro_deste_mes   = hoje.replace(day=1)
    ultimo_mes_passado   = primeiro_deste_mes - timedelta(days=1)
    primeiro_mes_passado = ultimo_mes_passado.replace(day=1)

    inicio_semana_atual  = hoje - timedelta(days=hoje.weekday())
    fim_semana_passada   = inicio_semana_atual - timedelta(days=1)
    inicio_semana_passada = fim_semana_passada - timedelta(days=6)

    return {
        "ontem":            (ontem, ontem),
        "semana_passada":   (inicio_semana_passada, fim_semana_passada),
        "mes_passado":      (primeiro_mes_passado, ultimo_mes_passado)
    }


# --------------------------------------------------------------------------- #
#  Rotas Flask                                                                
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "dashboard.html"))


@app.route("/previous")
def previous():
    return send_file(os.path.join(os.path.dirname(__file__), "dashboard_prev.html"))


@app.route("/api/pegar")
def pegar_dados():
    """Busca as ligações dos últimos 30 dias na API e guarda em cache."""
    global dados_cache
    dados, page = [], 1
    hoje = datetime.now()
    inicio = hoje - timedelta(days=30)

    try:
        while True:
            params = {
                "filters[created_at][from]": inicio.strftime("%Y-%m-%dT00:00:00Z"),
                "filters[created_at][to]":   hoje.strftime("%Y-%m-%dT23:59:59Z"),
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

            dados.extend([
                lig for lig in page_data
                if lig.get("readable_status_text") == "Finalizada"
                and lig.get("speaking_time", "00:00:00") > "00:00:00"
            ])
            page += 1

        dados_cache = dados
        return jsonify({"status": "ok", "mensagem": "Dados prontos."})

    except requests.exceptions.RequestException as e:
        return jsonify({"erro": f"Erro ao acessar a API: {e}"}), 500


# --------------------------------------------------------------------------- #
#  Resumo (atual ou períodos anteriores)                                      #
# --------------------------------------------------------------------------- #
@app.route("/api/resumo")
def resumo_ligacoes():
    global dados_cache, prev_cache
    dados = dados_cache
    anterior = request.args.get("prev") is not None
    hoje = datetime.now().date()
    hoje_str = hoje.strftime("%Y-%m-%d")

    # ---------- se for período anterior, tenta devolver o cache ----------
    if anterior and prev_cache["date"] == hoje_str and prev_cache["resumo"]:
        return jsonify(prev_cache["resumo"])

    # ---------- define intervalos ----------
    if anterior:
        intvs                 = intervalos_anteriores()
        ontem_i, _            = intvs["ontem"]
        sem_ini, sem_fim      = intvs["semana_passada"]
        mes_ini, mes_fim      = intvs["mes_passado"]
        dia_base              = ontem_i
    else:
        sem_ini               = hoje - timedelta(days=hoje.weekday())
        sem_fim               = sem_ini + timedelta(days=6)
        mes_ini               = hoje.replace(day=1)
        mes_fim               = hoje
        dia_base              = hoje

    # ---------- acumuladores ----------
    contagem_mes = contagem_semana = contagem_dia = 0
    vendas_mes = vendas_semana = 0

    tempo_ag_dia, tempo_ag_sem, tempo_ag_mes = {}, {}, {}
    vendas_ag_sem, vendas_ag_mes = {}, {}

    # ---------- processamento principal ----------
    for lig in dados:
        data_raw = lig.get("call_date")
        if not data_raw:
            continue
        try:
            data_lig = datetime.strptime(data_raw[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

        agente       = lig.get("agent") or lig.get("agente_nome") or "Desconhecido"
        qualificacao = lig.get("qualification", "")
        speaking     = tempo_para_segundos(lig.get("speaking_time", "00:00:00"))

        if mes_ini <= data_lig <= mes_fim:
            contagem_mes += 1
            tempo_ag_mes[agente] = tempo_ag_mes.get(agente, 0) + speaking
            if qualificacao == "Venda feita por telefone":
                vendas_mes += 1
                vendas_ag_mes[agente] = vendas_ag_mes.get(agente, 0) + 1

        if sem_ini <= data_lig <= sem_fim:
            contagem_semana += 1
            tempo_ag_sem[agente] = tempo_ag_sem.get(agente, 0) + speaking
            if qualificacao == "Venda feita por telefone":
                vendas_semana += 1
                vendas_ag_sem[agente] = vendas_ag_sem.get(agente, 0) + 1

        if data_lig == dia_base:
            contagem_dia += 1
            tempo_ag_dia[agente] = tempo_ag_dia.get(agente, 0) + speaking

    # ---------- recordistas ----------
    ag_top_dia   = max(tempo_ag_dia,  key=tempo_ag_dia.get,  default="Nenhum agente")
    tempo_top_dia= segundos_para_hms(tempo_ag_dia.get(ag_top_dia, 0))

    ag_v_sem     = max(vendas_ag_sem,key=vendas_ag_sem.get, default="Nenhum agente")
    v_sem        = vendas_ag_sem.get(ag_v_sem, 0)

    ag_v_mes     = max(vendas_ag_mes,key=vendas_ag_mes.get, default="Nenhum agente")
    v_mes        = vendas_ag_mes.get(ag_v_mes, 0)

    ag_t_sem     = max(tempo_ag_sem, key=tempo_ag_sem.get, default="Nenhum agente")
    t_sem        = segundos_para_hms(tempo_ag_sem.get(ag_t_sem, 0))

    ag_t_mes     = max(tempo_ag_mes, key=tempo_ag_mes.get, default="Nenhum agente")
    t_mes        = segundos_para_hms(tempo_ag_mes.get(ag_t_mes, 0))

    resposta = {
        "contagem_hoje":        contagem_dia,
        "contagem_semana":      contagem_semana,
        "contagem_total":       contagem_mes,

        "agente_top_hoje":      ag_top_dia,
        "ligacoes_top_hoje":    tempo_top_dia,

        "qualificacao_semana":  vendas_semana,
        "qualificacao_total":   vendas_mes,

        "agente_venda_semana":  ag_v_sem,
        "vendas_semana_agente": v_sem,

        "agente_venda_total":   ag_v_mes,
        "vendas_total_agente":  v_mes,

        "agente_tempo_semana":  ag_t_sem,
        "tempo_ttl_semana":     t_sem,

        "agente_tempo_mes":     ag_t_mes,
        "tempo_ttl_mes":        t_mes,
    }

    # ---------- salva no cache se for período anterior ----------
    if anterior:
        prev_cache["date"]   = hoje_str
        prev_cache["resumo"] = resposta

    return jsonify(resposta)


# --------------------------------------------------------------------------- #
#  Dados para gráficos (atuais ou anteriores)                                 #
# --------------------------------------------------------------------------- #
@app.route("/api/graficos")
def dados_graficos():
    global dados_cache, prev_cache
    dados = dados_cache
    anterior = request.args.get("prev") is not None
    hoje = datetime.now().date()
    hoje_str = hoje.strftime("%Y-%m-%d")

    # ---------- devolve cache se existir ----------
    if anterior and prev_cache["date"] == hoje_str and prev_cache["graficos"]:
        return jsonify(prev_cache["graficos"])

    if anterior:
        sem_ini, sem_fim   = intervalos_anteriores()["semana_passada"]
        mes_ini, mes_fim   = intervalos_anteriores()["mes_passado"]
    else:
        sem_ini            = hoje - timedelta(days=hoje.weekday())
        sem_fim            = hoje
        mes_ini, mes_fim   = hoje.replace(day=1), hoje

    vendas_ag, lig_sem_ag = {}, {}

    for lig in dados:
        data_raw = lig.get("call_date")
        if not data_raw:
            continue
        try:
            data_lig = datetime.strptime(data_raw[:10], "%Y-%m-%d").date()
        except ValueError:
            continue

        agente       = lig.get("agent") or lig.get("agente_nome") or "Desconhecido"
        qualificacao = lig.get("qualification", "")

        if mes_ini <= data_lig <= mes_fim and qualificacao == "Venda feita por telefone":
            vendas_ag[agente] = vendas_ag.get(agente, 0) + 1

        if sem_ini <= data_lig <= sem_fim:
            lig_sem_ag[agente] = lig_sem_ag.get(agente, 0) + 1

    top_vendas     = sorted(vendas_ag.items(),   key=lambda x: x[1], reverse=True)[:5]
    top_lig_sem    = sorted(lig_sem_ag.items(), key=lambda x: x[1], reverse=True)[:5]

    resposta = {
        "top_vendas":          top_vendas,
        "top_ligacoes_semana": top_lig_sem
    }

    if anterior:
        prev_cache["date"]     = hoje_str
        prev_cache["graficos"] = resposta

    return jsonify(resposta)


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
