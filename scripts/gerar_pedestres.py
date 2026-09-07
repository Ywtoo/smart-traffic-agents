"""
================================================================================
GERADOR DE PEDESTRES - FAIXAS DE PEDESTRE DA TANCREDO NEVES (ARACAJU/SE)
================================================================================
Lê a rede (com calçadas + faixas) e gera fluxos de pedestres atravessando as
faixas do corredor, de forma periódica. A demanda varia por cenário:

  normal    -> poucos pedestres (entrepico)
  pico      -> muitos pedestres
  superpico -> máxima demanda
  *_chuva   -> chuva reduz pedestres (fator 0.25): menos gente atravessa avenida
  *_radar_novo -> reutiliza o mesmo arquivo do cenário base

Arquivos gerados em simulacoes/rotas/pedestres_<cenario>.rou.xml.
================================================================================
"""

import os
import re
import math
import xml.etree.ElementTree as ET


# ==============================================================================
# 1. CAMINHOS PADRÃO
# ==============================================================================
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET_PADRAO = os.path.join(RAIZ, "mapa", "backup", "mapa.net.xml")
DIR_ROTAS = os.path.join(RAIZ, "simulacoes", "rotas")
DIR_CFGS = os.path.join(RAIZ, "simulacoes", "configs")


# ==============================================================================
# 2. DEMANDA E FÍSICA DOS PEDESTRES (PARÂMETROS CLAROS)
# ==============================================================================
BASES = {
    "normal": "normal",
    "pico": "pico",
    "pico_chuva": "pico_chuva",
    "superpico": "superpico",
}

TAXAS_BASE = {
    "normal": 30.0,
    "pico": 120.0,
    "superpico": 240.0
}

FATOR_CHUVA = 0.25

FISICA_PEDESTRE = {
    "vClass": "pedestrian",
    "maxSpeed": 1.39,
    "speedFactor": "normc(1.0,0.15,0.7,1.3)",
    "color": "0.9,0.7,0.2",
    "guiShape": "pedestrian"
}

MARGEM_CORREDOR = 90.0

# Nome do corredor usado para filtrar faixas próximas. Se nenhuma edge tiver
# esse texto no atributo "name" (ex: rede reexportada sem name, ou nome
# diferente), caímos no fallback abaixo em vez de quebrar com ValueError.
NOME_CORREDOR = "tancredo neves"


# ==============================================================================
# 3. DETECÇÃO DAS FAIXAS DE PEDESTRE DO CORREDOR
# ==============================================================================
def dist_pt_seg(px, py, a, b):
    """Distância do ponto (px,py) até o segmento a-b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(px - a[0], py - a[1])
    t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / l2))
    return math.hypot(px - (a[0] + dx * t), py - (a[1] + dy * t))


def descobrir_faixas(net_path, margem_corredor=MARGEM_CORREDOR):
    """
    Retorna a lista de faixas utilizáveis do corredor: (junction, [(edgeA, partidaA), (edgeB, partidaB)]).

    edgeA/edgeB = calçada que toca diretamente o cruzamento (usada como "to",
    ponto onde o pedestre atravessa e some).
    partidaA/partidaB = calçada um trecho antes (usada como "from", ponto de
    nascimento do pedestre — dá espaço/tempo pra fila se formar antes do sinal
    abrir). Cai de volta na própria edgeA/edgeB quando não existe continuação.

    Uma faixa é considerada utilizável quando o cruzamento tem faixa de pedestre
    E calçadas (edges de caminhada) conectadas dos dois lados.

    Se nenhuma edge do corredor for encontrada por nome (NOME_CORREDOR), o
    filtro de distância é desativado (fallback: considera todas as faixas com
    calçada nos dois lados) em vez de quebrar com ValueError no min() vazio.
    """
    jpos = {}
    cross_by_j = {}
    walk_inc = {}
    corr = []

    # Uma única passada pelo net.xml (junctions + edges juntos)
    for _, e in ET.iterparse(net_path, events=("end",)):
        if e.tag == "junction" and e.get("x") and e.get("y"):
            jpos[e.get("id")] = (float(e.get("x")), float(e.get("y")))
        elif e.tag == "edge":
            eid = e.get("id") or ""
            fn = e.get("function", "normal")
            if eid.startswith(":") and fn == "crossing":
                m = re.match(r":(.+)_c\d+$", eid)
                if m:
                    cross_by_j.setdefault(m.group(1), []).append(eid)
            elif fn == "normal":
                typ = e.get("type") or ""
                allow = e.get("allow") or ""
                f, t = e.get("from"), e.get("to")
                if f and t:
                    is_walk = (any(w in typ for w in ("footway", "pedestrian", "sidewalk", "path", "steps"))
                               or "pedestrian" in allow)
                    if is_walk:
                        walk_inc.setdefault(f, []).append((eid, t))
                        walk_inc.setdefault(t, []).append((eid, f))
                    if NOME_CORREDOR in (e.get("name") or "").lower():
                        # guarda pra depois, resolve pos ao final (f/t já em jpos ou não)
                        corr.append((f, t))
        e.clear()

    # Resolve posições do corredor agora que jpos está completo
    corr_pts = [(jpos[f], jpos[t]) for f, t in corr if f in jpos and t in jpos]

    usar_filtro_distancia = bool(corr_pts)
    if not usar_filtro_distancia:
        print(f"[AVISO] Nenhuma edge encontrada com nome contendo '{NOME_CORREDOR}'. "
              f"Filtro de distância ao corredor DESATIVADO — considerando todas as "
              f"faixas de pedestre da rede com calçada nos dois lados.")

    faixas = []
    for j, cs in cross_by_j.items():
        if j not in jpos:
            continue
        if usar_filtro_distancia:
            d = min(dist_pt_seg(jpos[j][0], jpos[j][1], a, b) for a, b in corr_pts)
            if d > margem_corredor:
                continue
        ws = walk_inc.get(j, [])
        if len(ws) >= 2:
            (a, far_a), (b, far_b) = ws[0], ws[1]
            # Estende o ponto de partida um trecho de calçada antes da que já
            # toca no cruzamento, se existir. Sem isso, o pedestre nasce em
            # cima do sinal (a calçada que toca a crossing costuma ser um
            # stub curto) e não sobra espaço/tempo visual para "acumular"
            # gente esperando o sinal abrir — só aparece, espera pouco e
            # atravessa. Com a extensão, ele nasce um pouco mais longe, anda
            # até a faixa e, se o sinal estiver fechado, várias pessoas vão
            # se juntando ali visivelmente antes de atravessar.
            partida_a = _estender_para_fila(far_a, a, walk_inc) or a
            partida_b = _estender_para_fila(far_b, b, walk_inc) or b
            faixas.append((j, [(a, partida_a), (b, partida_b)]))
    return faixas


def _estender_para_fila(node, edge_atual, walk_inc):
    """
    A partir de 'node' (extremidade da calçada que toca o cruzamento, do lado
    de fora), procura outra calçada conectada além de 'edge_atual' para
    estender o ponto de nascimento do pedestre um trecho pra trás. Retorna o
    id da edge estendida, ou None se 'node' for uma ponta sem continuação
    (nesse caso o chamador usa a própria edge_atual, comportamento antigo).
    """
    for eid, _far in walk_inc.get(node, []):
        if eid != edge_atual:
            return eid
    return None


# ==============================================================================
# 4. GERAÇÃO DOS ARQUIVOS DE PEDESTRES
# ==============================================================================
def horario_cenario(base):
    """Lê o intervalo de simulação (begin/end) do .sumocfg do cenário base."""
    cfg = os.path.join(DIR_CFGS, base + ".sumocfg")
    txt = open(cfg, encoding="utf-8").read()
    b = re.search(r"<begin value=\"([0-9.]+)\"", txt)
    e = re.search(r"<end value=\"([0-9.]+)\"", txt)
    return float(b.group(1)), float(e.group(1))


def gerar_arquivo_pedestres(base, faixas, pph_por_faixa, destino):
    """
    Escreve o .rou.xml com os fluxos periódicos de pedestres nas faixas.

    Chegada usa period="exp(LAMBDA)" (processo de Poisson) em vez de period
    fixo: pedestre chega em intervalos aleatórios exponenciais, não cravados
    de N em N segundos — mais realista e evita padrão "robótico" no GUI.
    """
    b0, e0 = horario_cenario(base)
    linhas = []
    linhas.append('<?xml version="1.0" encoding="UTF-8"?>')
    linhas.append('<routes>')
    linhas.append('    <!-- Pedestres atravessando as faixas do corredor (gerado por gerar_pedestres.py) -->')
    linhas.append(f'    <!-- Demanda: {pph_por_faixa:.0f} pedestres/h por faixa (total dois sentidos), janela {b0:.0f}-{e0:.0f}s -->')
    linhas.append('    <!-- Chegada: processo de Poisson (period=exp(lambda)), nao intervalo fixo -->')

    linhas.append(f'    <vType id="ped" vClass="{FISICA_PEDESTRE["vClass"]}" '
                  f'maxSpeed="{FISICA_PEDESTRE["maxSpeed"]}" speedFactor="{FISICA_PEDESTRE["speedFactor"]}" '
                  f'color="{FISICA_PEDESTRE["color"]}" guiShape="{FISICA_PEDESTRE["guiShape"]}"/>')

    n = 0
    for j, ws in faixas:
        (a, partida_a), (b, partida_b) = ws[0], ws[1]
        por_direcao = max(1, round(pph_por_faixa / 2.0))
        lambda_por_seg = por_direcao / 3600.0  # taxa média de chegada (pedestres/segundo)
        # from = edge estendida (nasce mais longe, anda até a crossing e fica
        #        na fila se o sinal estiver fechado)
        # to   = edge que já toca a crossing do lado de chegada (atravessa e
        #        some ali, sem andar mais depois — comportamento mantido)
        for direcao, (de, para) in enumerate(((partida_a, b), (partida_b, a))):
            n += 1
            linhas.append(
                f'    <personFlow id="ped_{j}_{direcao}" type="ped" begin="{b0:.0f}" end="{e0:.0f}" '
                f'period="exp({lambda_por_seg:.6f})">'
            )
            linhas.append(f'        <walk from="{de}" to="{para}"/>')
            linhas.append('    </personFlow>')

    linhas.append('</routes>')
    with open(destino, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))
    return n


# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    print("\n=======================================================")
    print("REGENERANDO PEDESTRES DAS FAIXAS DO CORREDOR")
    print("=======================================================\n")

    faixas = descobrir_faixas(NET_PADRAO)
    print(f"Faixas do corredor com calçadas dos dois lados: {len(faixas)}")
    for j, ws in faixas:
        print(f"   J={j} calçadas={ws}")

    if not faixas:
        print("\n[AVISO] Nenhuma faixa encontrada — verifique NOME_CORREDOR ou a rede de entrada.\n")

    os.makedirs(DIR_ROTAS, exist_ok=True)
    for base, prefixo in BASES.items():
        base_demanda = base.replace("_chuva", "")
        pph = TAXAS_BASE[base_demanda]
        if "_chuva" in base:
            pph *= FATOR_CHUVA
        destino = os.path.join(DIR_ROTAS, f"pedestres_{prefixo}.rou.xml")
        n = gerar_arquivo_pedestres(prefixo, faixas, pph, destino)
        print(f" -> Cenário [{prefixo}]: {pph:.0f} ped/h/faixa | {n} fluxos gerados -> {os.path.relpath(destino, RAIZ)}")

    print("\n[✓] Todos os arquivos de pedestres foram atualizados com sucesso!\n")