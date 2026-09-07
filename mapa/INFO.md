# Caracterização do Tráfego e Parâmetros de Calibração: Av. Presidente Tancredo Neves (Aracaju/SE)

Este documento consolida os levantamentos volumétricos, parâmetros operacionais da via, composição veicular e dados de infraestrutura urbana utilizados para subsidiar e calibrar as simulações microscópicas no SUMO (*Simulation of Urban MObility*).

---

## 1. Características Físicas e Operacionais da Via

A Avenida Presidente Tancredo Neves constitui o principal corredor transversal de articulação do tráfego urbano de Aracaju, conectando a BR-235 (saída para o interior do estado) à zona sul da capital e à orla marítima.

* **Extensão total:** ~15,0 km
* **Classificação funcional:** Via Arterial Principal / Rodovia Urbana (antiga rodovia de contorno)
* **Perfil transversal padrão:** 
  * Pista dupla com canteiro central divisor físico.
  * 3 a 4 faixas de rolamento por sentido nos trechos de maior carregamento (largura média de faixa: 3,20 m a 3,50 m).
  * Ciclovia segregada ao longo do canteiro/bordo e passeios de pedestres revitalizados.
* **Bairros lindeiros e de influência direta (10 zonas de tráfego):** 
  Inácio Barbosa, Jabotiana, Capucho, Ponto Novo, Luzia, Farolândia, Suíssa, Grageru, São Conrado e Atalaia/Aeroporto.
* **Velocidades Regulamentadas:**
  * Velocidade máxima regulamentada: 60 km/h (com fiscalização eletrônica por radares fixos).
  * Velocidade máxima adotada nos `vType` do SUMO (seco): **60,1 km/h** (`16,7 m/s`) para o carro comum — coerente com a regulação.
  * Velocidade média observada em horário de entrepico: 45 km/h a 55 km/h.
  * Velocidade média operacional em horário de pico (manhã): 12 km/h a 22 km/h (saturação em aproximações semafóricas).

---

## 2. Levantamento Volumétrico e Contagens de Tráfego

Os dados de demanda foram extraídos de contagens volumétricas contínuas e classificatórias realizadas pela Superintendência Municipal de Transportes e Trânsito (SMTT/Aracaju) e pelo estudo acadêmico de Macêdo (UFS, 2016).

### 2.1. Volumes Horários por Sentido

* **Volume Médio Diário (VMD estimado):** ~65.000 a 75.000 veículos/dia.
* **Pico da Manhã (07:00 – 08:00):**
  * Volume total no corredor: ~3.000 a 3.200 veículos equivalentes/hora.
  * Sentido predominante: **Norte/Oeste → Sul/Leste** (acesso às zonas comerciais, administrativas e de serviços da capital).
* **Pico da Tarde (17:30 – 18:30):**
  * Volume total no corredor: ~2.900 a 3.100 veículos equivalentes/hora.
  * Sentido predominante: **Sul/Leste → Norte/Oeste** (movimento pendular de retorno residencial e saída da cidade).
* **Período de Entrepico (Horário Normal - 09:00 às 16:00):**
  * Volume médio: ~800 a 1.100 veículos/hora/sentido (tráfego livre a estável).

### 2.2. Composição da Frota Circulante (Pesquisa Classificatória)

A amostragem volumétrica direta em período de pico (amostra de 11.429 veículos/período) resultou na seguinte distribuição. Os percentuais e parâmetros físicos abaixo são **os mesmos** usados pelo gerador de fluxos do repositório (`scripts/gerar_fluxos.py`, função `construir_bloco_veiculos`), nos modos `passenger`, `motorcycle`, `bus`, `truck`, `bicycle` e `emergency`.

| Categoria Veicular | Participação (%) | Volume Típico de Pico (veíc/h) | Parâmetros Adotados no SUMO (`vClass`) |
| :--- | :---: | :---: | :--- |
| **Automóveis / Utilitários leves** | **73,0%** | ~2.190 | `passenger` (comp: 4,5 m; acel: 2,6 m/s²; seco: 16,7 m/s; molhado: 12,5 m/s) |
| **Motocicletas / Ciclomotores** | **18,5%** | ~555 | `motorcycle` (comp: 2,2 m; dinâmica sublane; seco: 20,0 m/s; molhado: 13,9 m/s) |
| **Ônibus Urbanos / Intermunicipais** | **3,5%** | ~105 | `bus` (comp: 12,0 m; paradas programadas; seco: 12,5 m/s; molhado: 10,0 m/s) |
| **Caminhões / Veículos de Carga** | **2,6%** | ~78 | `truck` (comp: 8,5 m; seco: 11,1 m/s; molhado: 9,5 m/s) |
| **Bicicletas** | **2,0%** | ~60 | `bicycle` (comp: 1,6 m; vel: 15–20 km/h; seco: 5,5 m/s; molhado: 4,2 m/s) |
| **Veículos de Emergência (SAMU / Polícia)** | **0,4%** | ~12 | `emergency` (prioridade alta em semáforos; seco: 25,0 m/s; molhado: 20,0 m/s) |

> O script também diferencia dois perfis de carro (`car_padrao` e `car_agressivo`) dentro da classe `passenger`; no seco, o primeiro corresponde a 63,0% e o segundo a 10,0% da frota, somando os **73,0%** totais de automóveis/utilitários leves.

---

## 3. Infraestrutura de Transporte Coletivo e Modos Ativos

* **Transporte Coletivo:**
  * O corredor atende linhas troncais do Sistema Integrado de Transporte Metropolitano de Aracaju.
  * Intervenções estruturantes entregues em 2024 implantaram **24 novos abrigos de passageiros padronizados** ao longo da via.
  * Tempo médio de parada para embarque/desembarque: 20 a 40 segundos por ponto.
* **Travessias e Modos Ativos:**
  * Ciclovia implantada ao longo do canteiro central em trechos contínuos.
  * Faixas de pedestres transversais controladas por botoeiras e sincronizadas com os estágios semafóricos veiculares.

---

## 4. Controle Semafórico e Gestão Operacional

* **Sistema de Controle:** 
  * Parque semafórico composto por controladores eletrônicos atuados pelo tráfego e integrados à central de monitoramento da SMTT.
  * Implantação progressiva do programa de "Onda Verde" nos principais eixos troncais da capital.
* **Pontos Críticos de Conflito Semafórico:**
  1. Cruzamento com a Av. Beira Mar / Trevo do Terminal DIA.
  2. Acesso ao Hospital de Urgências de Sergipe (HUSE) e Av. Desembargador Maynard.
  3. Interseção com a Av. Hermes Fontes.
  4. Cruzamento Largo da Aparecida / Graciliano Ramos (novo acesso inaugurado em 2024).
* **Tempos de Ciclo Típicos (Horário de Pico):** 
  * Ciclos de 90 a 120 segundos, com distribuição aproximada de 60% a 70% de tempo verde reservado para a via principal (Tancredo Neves) e 30% a 40% para as vias transversais coletoras.
* **Implementação no SUMO:**
  * Semáforos convencionais: usados nos cenários base (`pico`, `pico_chuva`, `superpico`).
  * Semáforos adaptativos ("inteligentes"/"radar_novo"): usados nos cenários com a injeção de `mapa/backup/semaforos_adaptativos.add.xml` nos configs terminados em `_radar_novo`.

---

## 5. Cenários de Simulação Implementados

Com base nos dados empíricos, os cenários a seguir foram parametrizados no SUMO para análise de desempenho da malha viária. Os arquivos de configuração realmente existentes em `simulacoes/configs/` são:

| Cenário (descrição) | Arquivo de configuração SUMO | Sinalização | Fator de carregamento | Demanda gerada (script) |
| :--- | :--- | :--- | :---: | :---: |
| Entrepico | `simulacoes/configs/normal_radar_novo.sumocfg` | Inteligente (`semaforos_adaptativos.add.xml`) | 30% do pico | ~1.306 trips (`normal.trips.xml`) |
| Pico matutino | `simulacoes/configs/pico_radar_novo.sumocfg` | Inteligente (`semaforos_adaptativos.add.xml`) | 100% do pico | ~4.438 trips (`pico.trips.xml`) |
| Pico com chuva | `simulacoes/configs/pico_chuva_radar_novo.sumocfg` | Inteligente (`semaforos_adaptativos.add.xml`) | 100% do pico | ~4.438 trips (`pico_chuva.trips.xml`) |
| Super pico | `simulacoes/configs/superpico_radar_novo.sumocfg` | Inteligente (`semaforos_adaptativos.add.xml`) | 200% do pico | ~8.876 trips (`superpico.trips.xml`) |
O repositório também mantém as versões **convencionais** (sem `semaforos_adaptativos.add.xml`) para os mesmos níveis de demanda e condições climáticas:

| Cenário (descrição) | Arquivo de configuração SUMO | Sinalização | Fator de carregamento | Demanda gerada (script) |
| :--- | :--- | :--- | :---: | :---: |
| Pico matutino | `simulacoes/configs/pico.sumocfg` | Convencional | 100% do pico | ~4.438 trips (`pico.trips.xml`) |
| Pico com chuva | `simulacoes/configs/pico_chuva.sumocfg` | Convencional | 100% do pico | ~4.438 trips (`pico_chuva.trips.xml`) |
| Super pico | `simulacoes/configs/superpico.sumocfg` | Convencional | 200% do pico | ~8.876 trips (`superpico.trips.xml`) |

Isso permite comparar o desempenho com e sem o controlamento adaptativo no mesmo nível de demanda e condições climáticas.

### 5.1. Descrição dos cenários

* **Entrepico (`normal_radar_novo.sumocfg`):**
  * Fator de carregamento: 30% do pico (~850 veíc/h).
  * Objetivo: Avaliar o nível de serviço em regime de fluxo contínuo e tempos basais de viagem.

* **Pico matutino (`pico_radar_novo.sumocfg` e `pico.sumocfg`):**
  * Fator de carregamento: 100% da demanda (~2.800 a 3.000 veíc/h).
  * Objetivo: Mapear os comprimentos de fila nas aproximações semafóricas e a eficácia do controlamento semafórico.

* **Pico com chuva (`pico_chuva_radar_novo.sumocfg` e `pico_chuva.sumocfg`):**
  * Fator de carregamento: 100% da demanda com degradação cinemática.
  * Modificações físicas implementadas no script:
    * Redução dos `maxSpeed` dos veículos (ex.: carro comum 16,7 m/s → 12,5 m/s, ≈ -25%).
    * `minGap` ampliado para 3,5 m no carro comum.
    * Acelerações/desacelerações reduzidas em todos os tipos (devido à pista molhada).
    * Incremento de chamados de veículos de emergência (0,4% → 2,0% da frota no cenário molhado).

* **Super pico (`superpico_radar_novo.sumocfg` e `superpico.sumocfg`):**
  * Fator de carregamento: 200% do pico (~5.600 veíc/h).
  * Objetivo: Análise de estresse de infraestrutura, colapso de capacidade e propagação de filas em efeito dominó (spillback).

---

## 6. Fluxo de Geração de Rotas e Execução

A demanda de cada cenário é gerada como **trips de origem/destino por TAZ** (arquivo `*.trips.xml`) e depois roteada pelo SUMO:

1. **Geração dos trips:**
   ```bash
   cd simulacoes/rotas
   python3 ../../scripts/gerar_fluxos.py
   ```
   Isso gera `normal.trips.xml`, `pico.trips.xml`, `pico_chuva.trips.xml`, `superpico.trips.xml` e `superpico_chuva.trips.xml`.

2. **Roteamento com duarouter (com TAZ):**
   ```bash
   bash rotear.sh
   ```
   Cada `*.trips.xml` é convertido em seu `*.rou.xml` correspondente, usando `mapa/backup/bairros.taz.xml` e as opções `--with-taz --repair --ignore-errors --randomize-flows`.

3. **Execução de um cenário:**
   ```bash
   sumsong -c simulacoes/configs/normal_radar_novo.sumocfg
   ```
   (substitua o `.sumocfg` pelo cenário desejado).

Os arquivos `.sumocfg` apontam, entre outros:
* `net-file` → `../../mapa/backup/mapa.net.xml`
* `route-files` → `../rotas/<scenario>.rou.xml,../rotas/pedestres_<scenario>.rou.xml`
* `additional-files` → `bairros.taz.xml`, `bairros.add.xml`, `semaforos_adaptativos.add.xml` (nos `_radar_novo`), `pontos_onibus.add.xml`
* Janela temporal: `begin="25200"` (07:00) até `end="28800"` (08:00), `step-length="0.2"`.

---

## 7. Referências Técnicas e Fontes de Dados

* **MACÊDO, Maira Feitosa Menezes.** *Avaliação da Poluição Atmosférica Veicular com o Modelo AERMOD em Avenida de Aracaju – SE*. Trabalho de Conclusão de Curso (Graduação em Engenharia Ambiental e Sanitária) – Universidade Federal de Sergipe (UFS), São Cristóvão, 2016. [Disponível no Repositório UFS](https://ri.ufs.br/bitstream/riufs/12192/2/Maira_Feitosa_Menezes_Macedo.pdf).
* **SMTT / Prefeitura Municipal de Aracaju.** Relatórios técnicos e dados abertos do Sistema Integrado de Mobilidade Urbana e intervenções viárias no Corredor Tancredo Neves (2024/2025).
* **DETRAN-SE.** Estatísticas do Registro Nacional de Veículos Automotores (RENAVAM) - Frota cadastrada do município de Aracaju/SE.
* **IBGE.** Censo Demográfico 2022 / Estimativas populacionais para o município de Aracaju.
