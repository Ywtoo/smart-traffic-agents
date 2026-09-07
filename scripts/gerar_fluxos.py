"""
================================================================================
GERADOR DE FLUXOS DE TRÁFEGO - AV. TANCREDO NEVES (ARACAJU/SE)
================================================================================
Regras de Demanda:
  - Polo Norte: po_0 e po_1 (grandes geradores/atratores no extremo Norte)
  - Polo Sul:   po_9 e po_8 (grandes geradores/atratores no extremo Sul)
  - Eixo Central de Alta Demanda: po_7 (conector central / HUSE / corredores)

  Pares Proibidos (viagens internas/adjacentes que não usam a rodovia):
    * Norte interno: po_0 <-> po_1
    * Adjacências:   po_1 <-> po_2, po_2 <-> po_3, po_3 <-> po_7
    * Zona 5 bloqueada: po_5 <-> po_4 e po_5 <-> po_6

  Toda viagem é SEMPRE entre dois TAZ diferentes (o == d nunca gera viagem).

Depois de gerar o .trips.xml, o próprio script chama o duarouter diretamente
(via subprocess) para produzir o .rou.xml final, sem precisar de scripts
externos (.sh/.bat/.ps1). Requer 'duarouter' no PATH (pasta bin/ da instalação
do SUMO). Ao final de cada cenário com sucesso, os arquivos intermediários
(.trips.xml e .alt.xml) são apagados automaticamente — só o .rou.xml fica.
================================================================================
"""

import os
import random
import shutil
import subprocess

try:
    import sumolib
except ImportError:
    sumolib = None
    print("[AVISO] sumolib não encontrado. Rode `pip install sumolib` ou "
          "garanta que $SUMO_HOME/tools esteja no PYTHONPATH. "
          "A validação leve de TAZ vazias será pulada.")

# ==============================================================================
# 1. CAMINHOS
# ==============================================================================
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAMINHO_TAZ = os.path.join(RAIZ, "mapa", "backup", "bairros.taz.xml")
CAMINHO_NET = os.path.join(RAIZ, "mapa", "backup", "mapa.net.xml")
PASTA_ROTAS = os.path.join(RAIZ, "simulacoes", "rotas")

TODAS_ZONAS = [f"po_{i}" for i in range(10)]  # po_0 até po_9


def validar_tazs_com_sumolib(caminho_taz=CAMINHO_TAZ):
    """
    Checagem leve (não faz roteamento): garante que cada TAZ do bairros.taz.xml
    tem pelo menos uma edge referenciada. Só um sanity-check pra avisar cedo
    se algum bairro ficou "vazio" no TAZ, antes de gastar tempo com duarouter.
    """
    import re
    txt = open(caminho_taz, encoding="utf-8").read()
    tazs_vazias = []
    for tid, es in re.findall(r'<taz id="([^"]+)"[^>]*edges="([^"]*)"', txt):
        if not es.strip():
            tazs_vazias.append(tid)
    if tazs_vazias:
        print(f"[AVISO] TAZ sem nenhuma edge listada: {tazs_vazias}")
    return tazs_vazias


validar_tazs_com_sumolib()

# ==============================================================================
# 2. PARES ESTRITAMENTE PROIBIDOS (Bidirecionais)
# ==============================================================================
PARES_PROIBIDOS = {
    ("po_0", "po_1"), ("po_1", "po_0"),
    ("po_1", "po_2"), ("po_2", "po_1"),
    ("po_2", "po_3"), ("po_3", "po_2"),
    ("po_3", "po_7"), ("po_7", "po_3"),
    ("po_5", "po_4"), ("po_4", "po_5"),
    ("po_5", "po_6"), ("po_6", "po_5"),
}

POLOS_ALTOS = {"po_0", "po_1", "po_7", "po_8", "po_9"}


def calcular_matriz_fluxos():
    """Gera a matriz O-D completa (origem, destino, veiculos_por_hora).

    o == d NUNCA aparece aqui: viagem dentro do mesmo TAZ não é gerada.
    """
    fluxos = []
    for o in TODAS_ZONAS:
        for d in TODAS_ZONAS:
            if o == d:
                continue  # nunca viagem dentro do mesmo bairro
            if (o, d) in PARES_PROIBIDOS:
                continue  # pares proibidos (internos/adjacentes)

            e_alto_o = o in POLOS_ALTOS
            e_alto_d = d in POLOS_ALTOS

            if e_alto_o and e_alto_d:
                if (o in {"po_0", "po_1"} and d in {"po_8", "po_9"}) or \
                   (o in {"po_8", "po_9"} and d in {"po_0", "po_1"}):
                    vph = 200
                elif o == "po_7" or d == "po_7":
                    vph = 140
                else:
                    vph = 110
            elif e_alto_o or e_alto_d:
                vph = 28
            else:
                vph = 15

            fluxos.append((o, d, vph))
    return fluxos


VIAGENS_CALIBRADAS = calcular_matriz_fluxos()


# ==============================================================================
# 3. FÍSICA DOS VEÍCULOS
# ==============================================================================
CONFIGURACOES_CLIMATICAS = {
    "PISTA_SECA": {
        "carro_comum": {
            "porcentagem": 0.630, "comprimento_metros": 4.5, "velocidade_maxima_ms": 16.7,
            "aceleracao": 2.6, "desaceleracao": 4.5, "distancia_parado_fila_metros": 2.0,
            "hesitacao_humana": 0.2, "variacao_velocidade": "normc(1.0,0.1,0.8,1.2)",
            "vontade_trocar_faixa_para_ultrapassar": 1.5, "preferencia_faixa_direita": 0.3,
            "cor": "0.8,0.8,0.8"
        },
        "carro_apressado_doido": {
            "porcentagem": 0.100, "comprimento_metros": 4.5, "velocidade_maxima_ms": 22.2,
            "aceleracao": 3.2, "desaceleracao": 5.0, "distancia_parado_fila_metros": 1.2,
            "hesitacao_humana": 0.1, "variacao_velocidade": "normc(1.2,0.15,1.0,1.4)",
            "vontade_trocar_faixa_para_ultrapassar": 3.0, "preferencia_faixa_direita": 0.1,
            "cor": "0.9,0.2,0.2"
        },
        "moto": {
            "porcentagem": 0.185, "comprimento_metros": 2.2, "velocidade_maxima_ms": 20.0,
            "aceleracao": 3.8, "desaceleracao": 5.5, "distancia_parado_fila_metros": 0.8,
            "hesitacao_humana": 0.3, "variacao_velocidade": "normc(1.1,0.15,0.9,1.35)",
            "vontade_trocar_faixa_para_ultrapassar": 3.0, "preferencia_faixa_direita": 0.1,
            "cor": "1.0,0.5,0.0"
        },
        "onibus": {
            "porcentagem": 0.035, "comprimento_metros": 12.0, "velocidade_maxima_ms": 12.5,
            "aceleracao": 1.2, "desaceleracao": 3.5, "distancia_parado_fila_metros": 2.5,
            "hesitacao_humana": 0.1, "variacao_velocidade": "0.9",
            "vontade_trocar_faixa_para_ultrapassar": 0.5, "preferencia_faixa_direita": 0.8,
            "cor": "0.0,0.5,1.0"
        },
        "caminhao": {
            "porcentagem": 0.026, "comprimento_metros": 8.5, "velocidade_maxima_ms": 11.1,
            "aceleracao": 1.0, "desaceleracao": 3.5, "distancia_parado_fila_metros": 2.5,
            "hesitacao_humana": 0.1, "variacao_velocidade": "0.85",
            "vontade_trocar_faixa_para_ultrapassar": 0.3, "preferencia_faixa_direita": 1.0,
            "cor": "0.5,0.3,0.0"
        },
        "bicicleta": {
            "porcentagem": 0.020, "comprimento_metros": 1.6, "largura_metros": 0.8,
            "velocidade_maxima_ms": 5.5, "aceleracao": 1.2, "desaceleracao": 3.0,
            "distancia_parado_fila_metros": 1.0, "hesitacao_humana": 0.2,
            "cor": "0.2,0.8,0.2"
        },
        "ambulancia_policia": {
            "porcentagem": 0.004, "comprimento_metros": 6.0, "velocidade_maxima_ms": 25.0,
            "aceleracao": 3.5, "desaceleracao": 5.5, "distancia_parado_fila_metros": 1.5,
            "hesitacao_humana": 0.0, "variacao_velocidade": "1.3",
            "vontade_trocar_faixa_para_ultrapassar": 3.0, "cor": "1.0,0.0,0.0"
        }
    },
    "PISTA_MOLHADA_CHUVA": {
        "carro_comum": {
            "porcentagem": 0.680, "comprimento_metros": 4.5, "velocidade_maxima_ms": 12.5,
            "aceleracao": 1.8, "desaceleracao": 3.2, "distancia_parado_fila_metros": 3.5,
            "hesitacao_humana": 0.4, "variacao_velocidade": "normc(0.85,0.08,0.7,1.0)",
            "vontade_trocar_faixa_para_ultrapassar": 1.0, "preferencia_faixa_direita": 0.5,
            "cor": "0.6,0.6,0.6"
        },
        "carro_apressado_doido": {
            "porcentagem": 0.060, "comprimento_metros": 4.5, "velocidade_maxima_ms": 15.5,
            "aceleracao": 2.2, "desaceleracao": 3.8, "distancia_parado_fila_metros": 2.2,
            "hesitacao_humana": 0.3, "variacao_velocidade": "normc(1.05,0.1,0.9,1.2)",
            "vontade_trocar_faixa_para_ultrapassar": 2.0, "preferencia_faixa_direita": 0.1,
            "cor": "0.8,0.2,0.2"
        },
        "moto": {
            "porcentagem": 0.150, "comprimento_metros": 2.2, "velocidade_maxima_ms": 13.9,
            "aceleracao": 2.2, "desaceleracao": 3.5, "distancia_parado_fila_metros": 2.0,
            "hesitacao_humana": 0.5, "variacao_velocidade": "normc(0.9,0.1,0.75,1.1)",
            "vontade_trocar_faixa_para_ultrapassar": 1.5, "preferencia_faixa_direita": 0.2,
            "cor": "0.9,0.4,0.0"
        },
        "onibus": {
            "porcentagem": 0.045, "comprimento_metros": 12.0, "velocidade_maxima_ms": 10.0,
            "aceleracao": 0.9, "desaceleracao": 2.5, "distancia_parado_fila_metros": 4.0,
            "hesitacao_humana": 0.2, "variacao_velocidade": "0.8",
            "vontade_trocar_faixa_para_ultrapassar": 0.3, "preferencia_faixa_direita": 1.0,
            "cor": "0.0,0.5,1.0"
        },
        "caminhao": {
            "porcentagem": 0.030, "comprimento_metros": 8.5, "velocidade_maxima_ms": 9.5,
            "aceleracao": 0.8, "desaceleracao": 2.5, "distancia_parado_fila_metros": 4.0,
            "hesitacao_humana": 0.2, "variacao_velocidade": "0.75",
            "vontade_trocar_faixa_para_ultrapassar": 0.2, "preferencia_faixa_direita": 1.0,
            "cor": "0.5,0.3,0.0"
        },
        "bicicleta": {
            "porcentagem": 0.015, "comprimento_metros": 1.6, "largura_metros": 0.8,
            "velocidade_maxima_ms": 4.2, "aceleracao": 0.8, "desaceleracao": 2.0,
            "distancia_parado_fila_metros": 1.8, "hesitacao_humana": 0.3,
            "cor": "0.2,0.8,0.2"
        },
        "ambulancia_policia": {
            "porcentagem": 0.020, "comprimento_metros": 6.0, "velocidade_maxima_ms": 20.0,
            "aceleracao": 2.8, "desaceleracao": 4.5, "distancia_parado_fila_metros": 2.0,
            "hesitacao_humana": 0.1, "variacao_velocidade": "1.15",
            "vontade_trocar_faixa_para_ultrapassar": 2.5, "cor": "1.0,0.0,0.0"
        }
    }
}


def construir_bloco_veiculos(clima_chuva=False):
    tipo = "PISTA_MOLHADA_CHUVA" if clima_chuva else "PISTA_SECA"
    cfg = CONFIGURACOES_CLIMATICAS[tipo]
    linhas = ['    <vTypeDistribution id="mix">']

    c = cfg["carro_comum"]
    linhas.append(f'        <!-- 1. Carro Comum ({int(c["porcentagem"]*100)}% da frota) -->')
    linhas.append(f'        <vType id="car_padrao" probability="{c["porcentagem"]}" vClass="passenger" '
                   f'length="{c["comprimento_metros"]}" maxSpeed="{c["velocidade_maxima_ms"]}" accel="{c["aceleracao"]}" '
                   f'decel="{c["desaceleracao"]}" sigma="{c["hesitacao_humana"]}" minGap="{c["distancia_parado_fila_metros"]}" '
                   f'speedFactor="{c["variacao_velocidade"]}" lcStrategic="1.5" lcCooperative="1.0" '
                   f'lcSpeedGain="{c["vontade_trocar_faixa_para_ultrapassar"]}" lcKeepRight="{c["preferencia_faixa_direita"]}" color="{c["cor"]}"/>')

    a = cfg["carro_apressado_doido"]
    linhas.append(f'        <!-- 2. Carro Apressado / Corre acima do radar ({int(a["porcentagem"]*100)}% da frota) -->')
    linhas.append(f'        <vType id="car_agressivo" probability="{a["porcentagem"]}" vClass="passenger" '
                   f'length="{a["comprimento_metros"]}" maxSpeed="{a["velocidade_maxima_ms"]}" accel="{a["aceleracao"]}" '
                   f'decel="{a["desaceleracao"]}" sigma="{a["hesitacao_humana"]}" minGap="{a["distancia_parado_fila_metros"]}" '
                   f'speedFactor="{a["variacao_velocidade"]}" lcStrategic="2.5" lcCooperative="0.3" '
                   f'lcSpeedGain="{a["vontade_trocar_faixa_para_ultrapassar"]}" lcKeepRight="{a["preferencia_faixa_direita"]}" color="{a["cor"]}"/>')

    m = cfg["moto"]
    linhas.append(f'        <!-- 3. Motocicleta ({int(m["porcentagem"]*100)}% da frota) -->')
    linhas.append(f'        <vType id="moto" probability="{m["porcentagem"]}" vClass="motorcycle" '
                   f'length="{m["comprimento_metros"]}" maxSpeed="{m["velocidade_maxima_ms"]}" accel="{m["aceleracao"]}" '
                   f'decel="{m["desaceleracao"]}" sigma="{m["hesitacao_humana"]}" minGap="{m["distancia_parado_fila_metros"]}" '
                   f'speedFactor="{m["variacao_velocidade"]}" lcStrategic="2.0" lcSpeedGain="{m["vontade_trocar_faixa_para_ultrapassar"]}" '
                   f'lcKeepRight="{m["preferencia_faixa_direita"]}" color="{m["cor"]}"/>')

    o = cfg["onibus"]
    linhas.append(f'        <!-- 4. Ônibus ({int(o["porcentagem"]*100)}% da frota) -->')
    linhas.append(f'        <vType id="bus" probability="{o["porcentagem"]}" vClass="bus" '
                   f'length="{o["comprimento_metros"]}" maxSpeed="{o["velocidade_maxima_ms"]}" accel="{o["aceleracao"]}" '
                   f'decel="{o["desaceleracao"]}" sigma="{o["hesitacao_humana"]}" minGap="{o["distancia_parado_fila_metros"]}" '
                   f'speedFactor="{o["variacao_velocidade"]}" lcKeepRight="{o["preferencia_faixa_direita"]}" color="{o["cor"]}"/>')

    k = cfg["caminhao"]
    linhas.append(f'        <!-- 5. Caminhão ({int(k["porcentagem"]*100)}% da frota) -->')
    linhas.append(f'        <vType id="truck" probability="{k["porcentagem"]}" vClass="truck" '
                   f'length="{k["comprimento_metros"]}" maxSpeed="{k["velocidade_maxima_ms"]}" accel="{k["aceleracao"]}" '
                   f'decel="{k["desaceleracao"]}" sigma="{k["hesitacao_humana"]}" minGap="{k["distancia_parado_fila_metros"]}" '
                   f'speedFactor="{k["variacao_velocidade"]}" lcKeepRight="{k["preferencia_faixa_direita"]}" color="{k["cor"]}"/>')

    b = cfg["bicicleta"]
    linhas.append(f'        <!-- 6. Bicicleta ({int(b["porcentagem"]*100)}% da frota) -->')
    linhas.append(f'        <vType id="bike" probability="{b["porcentagem"]}" vClass="bicycle" '
                   f'length="{b["comprimento_metros"]}" width="{b["largura_metros"]}" maxSpeed="{b["velocidade_maxima_ms"]}" '
                   f'accel="{b["aceleracao"]}" decel="{b["desaceleracao"]}" sigma="{b["hesitacao_humana"]}" '
                   f'minGap="{b["distancia_parado_fila_metros"]}" color="{b["cor"]}"/>')

    e = cfg["ambulancia_policia"]
    linhas.append(f'        <!-- 7. Emergência SAMU / Polícia ({e["porcentagem"]*100:.1f}%) -->')
    linhas.append(f'        <vType id="emergency" probability="{e["porcentagem"]}" vClass="emergency" '
                   f'length="{e["comprimento_metros"]}" maxSpeed="{e["velocidade_maxima_ms"]}" accel="{e["aceleracao"]}" '
                   f'decel="{e["desaceleracao"]}" sigma="{e["hesitacao_humana"]}" minGap="{e["distancia_parado_fila_metros"]}" '
                   f'speedFactor="{e["variacao_velocidade"]}" guiShape="emergency" lcStrategic="3.0" '
                   f'lcSpeedGain="{e["vontade_trocar_faixa_para_ultrapassar"]}" color="{e["cor"]}"/>')

    linhas.append('    </vTypeDistribution>')
    return "\n".join(linhas)


# ==============================================================================
# 4. GERAÇÃO DE TRIPS
# ==============================================================================
def salvar_arquivo_trips(caminho_arquivo, multiplicador_volume=1.0, clima_chuva=False,
                          segundo_inicio=25200, segundo_fim=28800):
    """
    Gera um .trips.xml com fromTaz/toTaz. Este arquivo NÃO é a rota final:
    precisa passar pelo duarouter (--with-taz) pra virar .rou.xml roteado.
    Toda viagem é entre dois TAZ diferentes — nunca o == d.
    """
    os.makedirs(os.path.dirname(os.path.abspath(caminho_arquivo)), exist_ok=True)
    bloco_veiculos = construir_bloco_veiculos(clima_chuva=clima_chuva)

    janela_horas = (segundo_fim - segundo_inicio) / 3600.0
    total_trips = 0
    trips_todos = []  # (depart, linha_xml)

    for origem, destino, volume_base in VIAGENS_CALIBRADAS:
        assert origem != destino, "regra violada: viagem dentro do mesmo TAZ"
        volume_ajustado = max(1, int(round(volume_base * multiplicador_volume)))
        qtd_veiculos = max(1, int(round(volume_ajustado * janela_horas)))

        for i in range(qtd_veiculos):
            depart = segundo_inicio + random.random() * (segundo_fim - segundo_inicio)
            total_trips += 1
            trips_todos.append((
                depart,
                f'    <trip id="v_{origem}_{destino}_{i}" type="mix" '
                f'fromTaz="{origem}" toTaz="{destino}" depart="{depart:.2f}"/>'
            ))

    trips_todos.sort(key=lambda x: x[0])  # SUMO exige ordem por depart

    linhas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<routes>',
        '',
        bloco_veiculos,
        '',
        '    <!-- ============ TRIPS POR TAZ (roteados depois via duarouter, opcao with-taz) ============ -->',
    ]
    linhas.extend(linha for _, linha in trips_todos)
    linhas.append('')
    linhas.append('</routes>')

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")

    nome_pasta = os.path.basename(os.path.dirname(caminho_arquivo))
    clima_texto = "🌧️ Chuva" if clima_chuva else "☀️ Seco"
    print(f" -> Cenário [{nome_pasta}]: {clima_texto} | Fator: {multiplicador_volume}x | "
          f"{total_trips} trips (fromTaz/toTaz) gerados em {os.path.basename(caminho_arquivo)}")


def _rel(caminho, base_dir):
    """Caminho relativo a base_dir, com barras normais."""
    return os.path.relpath(caminho, base_dir).replace(os.sep, "/")


def rodar_duarouter(pasta_rotas, nome_trip, manter_intermediarios=False):
    """
    Chama o duarouter diretamente via subprocess (sem gerar .sh/.bat/.ps1).
    Precisa do executável 'duarouter' no PATH (pasta bin/ da instalação do SUMO).

    Em caso de sucesso, apaga os arquivos intermediários (o .trips.xml de
    entrada e qualquer .alt.xml de rotas alternativas que o duarouter gere
    junto), deixando só o .rou.xml final na pasta. Passe
    manter_intermediarios=True para preservá-los (ex: debug).

    Retorna True em sucesso, False em falha (loga o motivo e segue adiante
    sem interromper os outros cenários).
    """
    if shutil.which("duarouter") is None:
        print("[ERRO] 'duarouter' não encontrado no PATH. "
              "Adicione a pasta bin/ da instalação do SUMO ao PATH do sistema "
              "(ex: C:\\Program Files (x86)\\Eclipse\\Sumo\\bin no Windows).")
        return False

    base = nome_trip.replace(".trips.xml", "")
    caminho_trip = os.path.join(pasta_rotas, nome_trip)
    caminho_rou = os.path.join(pasta_rotas, base + ".rou.xml")
    net_rel = _rel(CAMINHO_NET, pasta_rotas)
    taz_rel = _rel(CAMINHO_TAZ, pasta_rotas)

    comando = [
        "duarouter",
        "--net-file", net_rel,
        "--route-files", nome_trip,
        "--taz-files", taz_rel,
        "--with-taz", "--repair", "--ignore-errors", "--randomize-flows",
        "-o", base + ".rou.xml",
    ]

    resultado = subprocess.run(comando, cwd=pasta_rotas, capture_output=True, text=True)

    if resultado.returncode != 0:
        print(f" [ERRO] duarouter falhou para {nome_trip}:")
        print(resultado.stderr.strip() or resultado.stdout.strip())
        return False

    if not os.path.isfile(caminho_rou):
        print(f" [ERRO] duarouter terminou sem erro, mas {base}.rou.xml não foi criado.")
        return False

    print(f" -> Roteado: {nome_trip} -> {base}.rou.xml")

    if not manter_intermediarios:
        # remove o .trips.xml de entrada
        try:
            os.remove(caminho_trip)
        except OSError:
            pass
        # remove qualquer .alt.xml (rotas alternativas) que o duarouter gere
        # para este cenário, ex: normal.rou.alt.xml
        for nome in os.listdir(pasta_rotas):
            if nome.startswith(base) and nome.endswith(".alt.xml"):
                try:
                    os.remove(os.path.join(pasta_rotas, nome))
                except OSError:
                    pass

    return True


# ==============================================================================
# 5. EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    random.seed(42)  # reprodutibilidade

    print("\n=======================================================")
    print("REGENERANDO FLUXOS (fromTaz/toTaz, sempre entre TAZ diferentes)")
    print("=======================================================\n")

    CENARIOS = [
        ("normal.trips.xml",          0.30, False),
        ("pico.trips.xml",            1.00, False),
        ("pico_chuva.trips.xml",      1.00, True),
        ("superpico.trips.xml",       2.00, False),
    ]

    for nome_arq, fator, chovendo in CENARIOS:
        caminho_saida = os.path.join(PASTA_ROTAS, nome_arq)
        salvar_arquivo_trips(caminho_saida, multiplicador_volume=fator, clima_chuva=chovendo)

    print("\n=======================================================")
    print("ROTEANDO COM DUAROUTER (fromTaz/toTaz -> caminho real)")
    print("=======================================================\n")

    ok, falhas = 0, []
    for nome_arq, _, _ in CENARIOS:
        if rodar_duarouter(PASTA_ROTAS, nome_arq):
            ok += 1
        else:
            falhas.append(nome_arq)

    print(f"\n[✓] {ok}/{len(CENARIOS)} cenários roteados com sucesso.")
    if falhas:
        print(f"[AVISO] Falharam: {', '.join(falhas)} — .trips.xml mantido para esses (não apagado).")
    else:
        print("[✓] .trips.xml e .alt.xml intermediários removidos. Só os .rou.xml finais permanecem.\n")