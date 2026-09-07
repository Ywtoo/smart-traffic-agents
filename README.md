# smart-traffic-agents

Simulação microscópica de tráfego realista da **Av. Presidente Tancredo Neves (Aracaju/SE)** utilizando a suíte **SUMO** (*Simulation of Urban MObility*), calibrada com contagens volumétricas reais (TCC Macêdo, UFS 2016 e dados SMTT).

---

## 🛠️ 1. Onde Baixar e Instalação

* **No Windows:**
  * Baixe o instalador oficial `.msi` em [eclipse.dev/sumo](https://eclipse.dev/sumo/).
  * Caminho padrão de instalação: `C:\Program Files (x86)\Eclipse\Sumo\bin`
  * Certifique-se de que a variável de ambiente `SUMO_HOME` esteja configurada.
* **No Linux (Ubuntu/Debian):**
  ```bash
  sudo apt update && sudo apt install sumo sumo-tools sumo-doc
  ```
  * Caminho padrão: `/usr/share/sumo`

---

## 📁 2. Estrutura Centralizada do Projeto

```text
smart-traffic-agents/
├── README.md
├── mapa/
│   ├── map.osm.gz                     ← Malha viária bruta exportada do OpenStreetMap
│   ├── INFO.md                        ← Dados técnicos de tráfego, contagens e normas
│   └── backup/
│       ├── mapa.net.xml               ← Rede viária compilada pelo netconvert
│       ├── bairros.add.xml            ← Polígonos visuais dos bairros (POI/Shapes)
│       ├── bairros.taz.xml            ← Zonas de Tráfego (TAZ) geradas a partir dos polígonos
│       └── semaforos_adaptativos.add.xml ← Semáforos atuados inteligentes (Onda Verde SMTT)
├── scripts/
│   ├── gerar_fluxos.py                ← Gera os arquivos .rou.xml com físicas calibradas e clima
│   ├── executar_todos.py              ← Roda 10 rodadas (Monte Carlo) em lote via CLI
│   └── comparar_cenarios.py           ← Extrai a média dos KPIs científicos das 10 rodadas
└── simulacoes/
    ├── configs/                       ← Starters das simulações (.sumocfg)
    │   ├── viewsettings.xml           ← Configuração visual única compartilhada
│   ├── normal_radar_novo.sumocfg
│   ├── pico.sumocfg
│   ├── pico_radar_novo.sumocfg
│   ├── pico_chuva.sumocfg
│   ├── pico_chuva_radar_novo.sumocfg
│   ├── superpico.sumocfg
│   └── superpico_radar_novo.sumocfg
    ├── rotas/                         ← Arquivos de rotas e fluxos gerados
    │   ├── normal.rou.xml
    │   ├── pico.rou.xml
    │   ├── pico_chuva.rou.xml
    │   ├── superpico.rou.xml
    │   └── superpico_chuva.rou.xml
    └── outputs/                       ← Resultados cuspidos por cenário
        ├── normal/                    ← rodada_01.xml ... rodada_10.xml
        ├── normal_radar_novo/
        ├── pico/
        ├── pico_radar_novo/
        ├── pico_chuva/
        ├── pico_chuva_radar_novo/
        ├── superpico/
        ├── superpico_radar_novo/
        ├── superpico_chuva/
        ├── superpico_chuva_radar_novo/
        ├── superpico_chuva_teste/
        ├── superpico_radar_novo/
        ├── pico_chuva_teste/
        ├── pico_novo/
        ├── pico_teste/
        ├── normal_teste/
        ├── pico_radar_novo_teste/
        └── superpico_radar_novo_teste/
```

---

## 💻 3. Como Construir e Rodar a Rede (Passo a Passo)

Abra o terminal na **raiz do projeto** (`smart-traffic-agents/`).

---

### Passo 1: Compilar o mapa base do OpenStreetMap (`map.osm.gz`)

Lê o arquivo bruto do OpenStreetMap e gera a rede viária tratada:

* **No Windows (PowerShell):**
  ```powershell
  netconvert --osm-files mapa/map.osm.gz -o mapa/backup/mapa.net.xml `
    --type-files "$env:SUMO_HOME\data\typemap\osmNetconvert.typ.xml" `
    --geometry.remove --ramps.guess true --junctions.join true `
    --tls.guess-signals true --tls.join true --roundabouts.guess true
  ```

* **No Linux (Bash):**
  ```bash
  netconvert --osm-files mapa/map.osm.gz -o mapa/backup/mapa.net.xml \
    --type-files "$SUMO_HOME/data/typemap/osmNetconvert.typ.xml" \
    --geometry.remove --ramps.guess true --junctions.join true \
    --tls.guess-signals true --tls.join true --roundabouts.guess true
  ```

---

### Passo 2: Mapear os Bairros (Polígonos) e Converter em Zonas de Tráfego (TAZ)

1. **Abrir a rede no netedit:**
   * **No Windows (PowerShell):**
     ```powershell
     netedit mapa/backup/mapa.net.xml
     ```
   * **No Linux (Bash):**
     ```bash
     netedit mapa/backup/mapa.net.xml
     ```

2. **Desenhar os Polígonos dos Bairros:**
   * Pressione a tecla **`P`** para ativar o modo **Shapes / POI / Polígonos**.
   * Desenhe o contorno de cada bairro ao longo da Tancredo Neves (`po_1`, `po_2`, ..., `po_10`).
   * No menu superior, clique em: **File → Shapes and POIs → Save Shapes as...** e salve como `mapa/backup/bairros.add.xml`.

3. **Converter os Polígonos para Zonas de Tráfego (TAZ):**
   * **No Windows (PowerShell):**
     ```powershell
     python "$env:SUMO_HOME\tools\edgesInDistricts.py" -n mapa/backup/mapa.net.xml -t mapa/backup/bairros.add.xml -o mapa/backup/bairros.taz.xml
     ```
   * **No Linux (Bash):**
     ```bash
     python3 "$SUMO_HOME/tools/edgesInDistricts.py" -n mapa/backup/mapa.net.xml -t mapa/backup/bairros.add.xml -o mapa/backup/bairros.taz.xml
     ```

---

### Passo 3: Gerar os Arquivos de Rotas e Físicas Veiculares

Gera os arquivos `.rou.xml` na pasta `simulacoes/rotas/` com todas as físicas (chuva, troca de faixas, apressados e tipos de veículos):

* **No Windows (PowerShell):**
  ```powershell
  python scripts/gerar_fluxos.py
  ```

* **No Linux (Bash):**
  ```bash
  python3 scripts/gerar_fluxos.py
  ```

---

### Passo 4: Executar as Simulações

#### Opção A: Visualizar no SUMO-GUI
Abra qualquer cenário da pasta `simulacoes/configs/` diretamente no SUMO-GUI:

* **No Windows (PowerShell):**
  ```powershell
  # Exemplo 1: Pico Convencional
  sumo-gui simulacoes/configs/pico.sumocfg

  # Exemplo 2: Pico com Semáforo Inteligente (Radar Novo)
  sumo-gui simulacoes/configs/pico_radar_novo.sumocfg

  # Exemplo 3: Pico com Chuva
  sumo-gui simulacoes/configs/pico_chuva.sumocfg
  ```

* **No Linux (Bash):**
  ```bash
  # Exemplo 1: Pico Convencional
  sumo-gui simulacoes/configs/pico.sumocfg

  # Exemplo 2: Pico com Semáforo Inteligente (Radar Novo)
  sumo-gui simulacoes/configs/pico_radar_novo.sumocfg

  # Exemplo 3: Pico com Chuva
  sumo-gui simulacoes/configs/pico_chuva.sumocfg
  ```

#### Opção B: Executar 10 Rodadas em Lote (Modo Headless / Monte Carlo)
Roda 10 repetições de cada cenário gerando `rodada_01.xml` a `rodada_10.xml` dentro de `simulacoes/outputs/<cenario>/`:

* **No Windows (PowerShell):**
  ```powershell
  python scripts/executar_todos.py 10
  ```

* **No Linux (Bash):**
  ```bash
  python3 scripts/executar_todos.py 10
  ```

---

### Passo 5: Gerar a Tabela Científica Consolidada

Calcula a média de todas as rodadas executadas para cada cenário:

* **No Windows (PowerShell):**
  ```powershell
  python scripts/comparar_cenarios.py
  ```

* **No Linux (Bash):**
  ```bash
  python3 scripts/comparar_cenarios.py
  ```
