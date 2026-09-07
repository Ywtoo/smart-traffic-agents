# smart-traffic-agents

Simulação microscópica de tráfego realista da **Av. Presidente Tancredo Neves (Aracaju/SE)** utilizando a suíte **SUMO** (*Simulation of Urban MObility*), calibrada com contagens volumétricas reais (TCC Macêdo, UFS 2016 e dados SMTT).

---

## 🛠️ 1. Onde Baixar e Instalação

* **No Windows:**
  * Baixe o instalador oficial `.msi` em [eclipse.dev/sumo](https://eclipse.dev/sumo/).
  * Caminho padrão de instalação: `C:\\Program Files (x86)\\Eclipse\\Sumo\\bin`
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
│       ├── semaforos_adaptativos.add.xml ← Semáforos atuados inteligentes (Onda Verde SMTT)
│       └── pontos_onibus.add.xml      ← Pontos de parada do transporte coletivo
├── scripts/
│   ├── gerar_fluxos.py                ← Gera os trips e os roteadores (rotear.sh/.bat/.ps1)
│   └── gerar_pedestres.py             ← Gera as rotas de pedestres por faixa do corredor
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
    │   ├── pedestres_normal.rou.xml
    │   ├── pedestres_pico.rou.xml
    │   ├── pedestres_pico_chuva.rou.xml
    │   └── pedestres_superpico.rou.xml
    └── outputs/                       ← Resultados cuspidos por cenário
        ├── normal_radar_novo/
        ├── pico/
        ├── pico_radar_novo/
        ├── pico_chuva/
        ├── pico_chuva_radar_novo/
        ├── superpico/
        └── superpico_radar_novo/
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
   * Desenhe o contorno de cada bairro ao longo da Tancredo Neves (`po_0`, `po_1`, ..., `po_9`).
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

### Passo 3: Gerar os Arquivos de Rotas, Fluxos e Pedestres

Gera os arquivos de trips e os roteadores na pasta `simulacoes/rotas/`, e também as rotas de pedestres:

* **Todos:**
  ```
  python scripts/gerar_fluxos.py
  python scripts/gerar_pedestres.py
  ```


Depois disso, rode o roteador do seu SO para converter os `.trips.xml` em `.rou.xml` roteados:

* **Linux / Git-Bash / WSL:**
  ```bash
  bash simulacoes/rotas/rotear.sh
  ```
* **Windows (cmd):**
  ```cmd
  simulacoes\rotas\rotear.bat
  ```
* **Windows (PowerShell):**
  ```powershell
  .\simulacoes\rotas\rotear.ps1
  ```

Isso requer `duarouter` no PATH (vem na pasta `bin/` da instalação do SUMO).

---

### Passo 4: Cenários Implementados

No momento, os cenários executáveis são:

* **Entrepico com semáforo inteligente:** `normal_radar_novo.sumocfg`
* **Pico convencional:** `pico.sumocfg`
* **Pico com semáforo inteligente:** `pico_radar_novo.sumocfg`
* **Pico com chuva convencional:** `pico_chuva.sumocfg`
* **Pico com chuva e semáforo inteligente:** `pico_chuva_radar_novo.sumocfg`
* **Super pico convencional:** `superpico.sumocfg`
* **Super pico com semáforo inteligente:** `superpico_radar_novo.sumocfg`

Os cenários com `..._radar_novo` usam `semaforos_adaptativos.add.xml` nos `additional-files`. Os demais usam apenas `bairros.taz.xml`, `bairros.add.xml` e `pontos_onibus.add.xml`.

---

## 🔗 4. Referências do Corredor

Os parâmetros de calibração estão detalhados em `mapa/INFO.md`.
