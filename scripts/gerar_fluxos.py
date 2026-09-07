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

================================================================================
COMO FUNCIONA (mudança em relação à versão anterior)
================================================================================
Este script agora só gera TRIPS com fromTaz/toTaz (sem sortear aresta manual
dentro do TAZ). Quem escolhe a aresta de entrada/saída dentro de cada zona e
calcula a rota de verdade é o duarouter, usando o próprio bairros.taz.xml.

Isso elimina:
  - parsing manual de allow/disallow de lane (sumolib faz isso melhor)
  - parsing manual de <connection> via regex
  - sorteio de aresta "boa" sem garantia de rota completa até o destino

E resolve a causa mais comum de teleporte: trip nascendo numa aresta sem
caminho real até o destino. O duarouter reporta/descrada esses casos com
--repair e --ignore-errors ao invés de deixar a simulação teleportar.

Depois de gerar o .trips.xml, rode (ou use o helper `rotear.sh` gerado):

    duarouter --net-file mapa/backup/mapa.net.xml \\
              --route-files <arquivo>.trips.xml \\
              --taz-files mapa/backup/bairros.taz.xml \\
              --with-taz \\
              --repair \\
              --ignore-errors \\
              --randomize-flows \\
              -o <arquivo>.rou.xml

Isso substitui as antigas ARESTAS_TRAGEGAVEIS / ARESTAS_BOAS por completo.
================================================================================
"""

import os
import random

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
                continue

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
# 3. FÍSICA DOS VEÍCULOS (inalterado — mesma lógica de antes)
# ==============================================================================
CONFIGURACOES_CLIMATICAS = {
    "PISTA_SECA": {
        "carro_comum": {
            "porcentagem": 0.630, "comprimento_metros": 4.5, "velocidade_maxima_ms": 16.7,
            "aceleracao": 2.6, "desaceleracao": 4.5, "distancia_parado_fila_metros": 2.0,
            "hesitacao_humana": 0.2, "variacao_velocidade": "normc(1.0,0.1,0.8,1.2)",
            "vontade_trocar_faixa_para_ultrapassar": 1.5, "preferencia_faixa_direita": 0.8,
            "cor": "0.8,0.8,0.8"
        },
        "carro_apressado_doido": {
            "porcentagem": 0.100, "comprimento_metros": 4.5, "velocidade_maxima_ms": 22.2,
            "aceleracao": 3.2, "desaceleracao": 5.0, "distancia_parado_fila_metros": 1.2,
            "hesitacao_humana": 0.1, "variacao_velocidade": "normc(1.2,0.15,1.0,1.4)",
            "vontade_trocar_faixa_para_ultrapassar": 3.0, "preferencia_faixa_direita": 0.2,
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
            "vontade_trocar_faixa_para_ultrapassar": 0.5, "preferencia_faixa_direita": 1.5,
            "cor": "0.0,0.5,1.0"
        },
        "caminhao": {
            "porcentagem": 0.026, "comprimento_metros": 8.5, "velocidade_maxima_ms": 11.1,
            "aceleracao": 1.0, "desaceleracao": 3.5, "distancia_parado_fila_metros": 2.5,
            "hesitacao_humana": 0.1, "variacao_velocidade": "0.85",
            "vontade_trocar_faixa_para_ultrapassar": 0.3, "preferencia_faixa_direita": 2.0,
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
            "vontade_trocar_faixa_para_ultrapassar": 1.0, "preferencia_faixa_direita": 1.0,
            "cor": "0.6,0.6,0.6"
        },
        "carro_apressado_doido": {
            "porcentagem": 0.060, "comprimento_metros": 4.5, "velocidade_maxima_ms": 15.5,
            "aceleracao": 2.2, "desaceleracao": 3.8, "distancia_parado_fila_metros": 2.2,
            "hesitacao_humana": 0.3, "variacao_velocidade": "normc(1.05,0.1,0.9,1.2)",
            "vontade_trocar_faixa_para_ultrapassar": 2.0, "preferencia_faixa_direita": 0.4,
            "cor": "0.8,0.2,0.2"
        },
        "moto": {
            "porcentagem": 0.150, "comprimento_metros": 2.2, "velocidade_maxima_ms": 13.9,
            "aceleracao": 2.2, "desaceleracao": 3.5, "distancia_parado_fila_metros": 2.0,
            "hesitacao_humana": 0.5, "variacao_velocidade": "normc(0.9,0.1,0.75,1.1)",
            "vontade_trocar_faixa_para_ultrapassar": 1.5, "preferencia_faixa_direita": 0.5,
            "cor": "0.9,0.4,0.0"
        },
        "onibus": {
            "porcentagem": 0.045, "comprimento_metros": 12.0, "velocidade_maxima_ms": 10.0,
            "aceleracao": 0.9, "desaceleracao": 2.5, "distancia_parado_fila_metros": 4.0,
            "hesitacao_humana": 0.2, "variacao_velocidade": "0.8",
            "vontade_trocar_faixa_para_ultrapassar": 0.3, "preferencia_faixa_direita": 1.8,
            "cor": "0.0,0.5,1.0"
        },
        "caminhao": {
            "porcentagem": 0.030, "comprimento_metros": 8.5, "velocidade_maxima_ms": 9.5,
            "aceleracao": 0.8, "desaceleracao": 2.5, "distancia_parado_fila_metros": 4.0,
            "hesitacao_humana": 0.2, "variacao_velocidade": "0.75",
            "vontade_trocar_faixa_para_ultrapassar": 0.2, "preferencia_faixa_direita": 2.0,
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
# 4. GERAÇÃO DE TRIPS (fromTaz/toTaz — sem sortear aresta manualmente)
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


def _comando_duarouter(pasta_rotas, nome_trip):
    """Monta o comando duarouter (mesma lógica pros 3 formatos de script)."""
    base = nome_trip.replace(".trips.xml", "")
    return (
        f'duarouter --net-file "{CAMINHO_NET}" '
        f'--route-files "{os.path.join(pasta_rotas, nome_trip)}" '
        f'--taz-files "{CAMINHO_TAZ}" '
        f'--with-taz --repair --ignore-errors --randomize-flows '
        f'-o "{os.path.join(pasta_rotas, base + ".rou.xml")}"'
    )


def gerar_script_roteamento(pasta_rotas, nomes_arquivos):
    """
    Gera os scripts de roteamento em 3 formatos, pra rodar em qualquer SO:
      - rotear.sh   -> Linux/Mac/Git-Bash/WSL
      - rotear.bat  -> Windows (cmd.exe)
      - rotear.ps1  -> Windows (PowerShell)
    Todos fazem a mesma coisa: chamar duarouter --with-taz para cada cenário.
    """
    # --- .sh (bash) ---
    caminho_sh = os.path.join(pasta_rotas, "rotear.sh")
    linhas_sh = ["#!/usr/bin/env bash", "set -e", ""]
    for nome in nomes_arquivos:
        linhas_sh.append(_comando_duarouter(pasta_rotas, nome))
    with open(caminho_sh, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas_sh) + "\n")
    try:
        os.chmod(caminho_sh, 0o755)
    except OSError:
        pass  # chmod pode falhar/ser irrelevante no Windows, sem problema

    # --- .bat (cmd.exe do Windows) ---
    caminho_bat = os.path.join(pasta_rotas, "rotear.bat")
    linhas_bat = ["@echo off", "setlocal", ""]
    for nome in nomes_arquivos:
        cmd = _comando_duarouter(pasta_rotas, nome)
        linhas_bat.append(cmd)
        linhas_bat.append("if errorlevel 1 goto :erro")
        linhas_bat.append("")
    linhas_bat.append("echo.")
    linhas_bat.append("echo [OK] Todas as rotas foram geradas.")
    linhas_bat.append("goto :fim")
    linhas_bat.append(":erro")
    linhas_bat.append("echo [ERRO] duarouter falhou. Verifique se ele esta no PATH (pasta bin do SUMO).")
    linhas_bat.append("exit /b 1")
    linhas_bat.append(":fim")
    with open(caminho_bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(linhas_bat) + "\n")

    # --- .ps1 (PowerShell do Windows) ---
    caminho_ps1 = os.path.join(pasta_rotas, "rotear.ps1")
    linhas_ps1 = ["$ErrorActionPreference = 'Stop'", ""]
    for nome in nomes_arquivos:
        linhas_ps1.append(_comando_duarouter(pasta_rotas, nome))
    linhas_ps1.append("")
    linhas_ps1.append("Write-Host '[OK] Todas as rotas foram geradas.'")
    with open(caminho_ps1, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(linhas_ps1) + "\n")

    print(f"\n[✓] Scripts de roteamento gerados em: {pasta_rotas}")
    print(f"    - Linux/Mac/Git-Bash/WSL : rotear.sh")
    print(f"    - Windows (cmd)          : rotear.bat")
    print(f"    - Windows (PowerShell)   : rotear.ps1")
    print("    Rode o do seu SO depois deste script, para converter .trips.xml em .rou.xml roteados.")
    print("    Requer 'duarouter' no PATH (vem na pasta bin/ da instalação do SUMO).")


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
        ("superpico_chuva.trips.xml", 2.00, True),
    ]

    for nome_arq, fator, chovendo in CENARIOS:
        caminho_saida = os.path.join(PASTA_ROTAS, nome_arq)
        salvar_arquivo_trips(caminho_saida, multiplicador_volume=fator, clima_chuva=chovendo)

    gerar_script_roteamento(PASTA_ROTAS, [n for n, _, _ in CENARIOS])

    print("\n[✓] Trips gerados. Rode simulacoes/rotas/rotear.sh para produzir os .rou.xml finais.\n")