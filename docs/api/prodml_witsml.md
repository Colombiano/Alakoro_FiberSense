# ProdML e WITSML

O Alakoro FiberSense oferece suporte a leitura e escrita nos formatos
**ProdML** e **WITSML** da Energistics, amplamente utilizados na industria
de oleo e gas para troca de dados de pocos, wellbores e aquisicoes.

---

## ProdML

O modulo `src.io.prodml` trabalha com objetos `DASAcquisition` do ProdML v2.x
e suporta namespaces conhecidos da familia `http://www.energistics.org/energyml/data/prodmlv2*`.

### Escrever ProdML

```python
from src.io.alakoro_spool import AlakoroPatch
from src.io import prodml

patch = AlakoroPatch(...)

prodml.write(
    patch,
    "acquisition.prodml",
    well_id="W-01",
    wellbore_id="WB-01",
)
```

O arquivo gerado inclui metadados do patch:

- `timeCount` / `channelCount`
- `samplingInterval` (derivado de `sampling_rate_hz`)
- `spatialSamplingInterval` (resolucao espacial)
- `gaugeLength`
- `dataUnits`
- `modality` (`DAS`, `DTS`, `DSS`)
- `startTime`
- referencias a `well` e `wellbore`

### Ler ProdML

```python
patch = prodml.read("acquisition.prodml")
print(patch.shape)
print(patch.well_id)
print(patch.attrs.data_units)
```

A leitura e tolerante a arquivos com ou sem namespace e tenta extrair os
metadados de varios caminhos possiveis dentro do XML.

---

## WITSML

O modulo `src.io.witsml` trabalha com objetos `well`, `wellbore` e `log` do
WITSML v1.3.1.1 e v1.4.1.1.

### Escrever Log WITSML

```python
from src.io import witsml

witsml.write_log(
    patch,
    "das_log.witsml",
    well_id="W-01",
    wellbore_id="WB-01",
    log_name="DASLog",
    mnemonics=["CH0", "CH1"],
    units=["1/s", "1/s"],
)
```

O arquivo inclui `logCurveInfo` para cada canal e a primeira coluna dos dados
representa o indice de tempo.

### Ler Log WITSML

```python
patch = witsml.read_log("das_log.witsml")
print(patch.shape)
print(patch.well_id)
```

A leitura detecta automaticamente o namespace WITSML usado e extrai
mnemonicos/unidades quando `logCurveInfo` esta presente.

### Ler Well / Wellbore

```python
well = witsml.read_well("well.witsml")
print(well.uid, well.name)

wellbore = witsml.read_wellbore("wellbore.witsml")
print(wellbore.uid, wellbore.well_uid)
```

---

## Ponte Semantica Energistics (ProdML ↔ WITSML)

O modulo `src.io.energistics_bridge` oferece um mapeamento semantico profundo
entre ProdML e WITSML, permitindo enriquecer dados de aquisicao com metadados
 de poco/wellbore e converter entre os formatos mantendo a semantica.

### Modelo semantico comum: `SensingAcquisition`

```python
from src.io.energistics_bridge import (
    SensingAcquisition,
    WellReference,
    WellboreReference,
    ChannelInfo,
)

acquisition = SensingAcquisition(
    data=patch.data,
    modality="das",
    units="1/s",
    sampling_rate_hz=1000.0,
    spatial_resolution_m=1.0,
    gauge_length_m=10.0,
    well=WellReference(uid="W-01", name="Well-01", country="Brasil"),
    wellbore=WellboreReference(uid="WB-01", name="WB-01", well_uid="W-01"),
    channels=[
        ChannelInfo(mnemonic="CH0", unit="1/s", index=0),
        ChannelInfo(mnemonic="CH1", unit="1/s", index=1),
    ],
)
```

### Cross-reference ProdML + WITSML

```python
from src.io import energistics_bridge as bridge

# Le ProdML e enriquece com well/wellbore WITSML
acquisition = bridge.cross_reference(
    "acquisition.prodml",
    witsml_well_path="well.witsml",
    witsml_wellbore_path="wellbore.witsml",
)

print(acquisition.well.name)
print(acquisition.wellbore.md_max)
```

A funcao valida consistencia entre os identificadores (UUID/nome) e levanta
`ValueError` em caso de inconsistencia.

### Converter entre formatos

```python
# ProdML -> WITSML Log
bridge.to_witsml_log(acquisition, "output.witsml", log_name="DASLog")

# WITSML Log -> ProdML
bridge.to_prodml(acquisition, "output.prodml")
```

### Enriquecer WITSML com metadados ProdML

```python
acquisition = bridge.from_witsml_log(
    "log.witsml",
    prodml_path="acquisition.prodml",
)
```

---

## Propriedade Intelectual / Intellectual Property

- **ProdML** e **WITSML** sao padroes abertos mantidos pela **Energistics**.
- As implementacoes do Alakoro (`src/io/prodml.py`, `src/io/witsml.py`,
  `src/io/energistics_bridge.py`) sao **implementacoes independentes** e
  **nao sao endossadas pela Energistics**.
- Nenhum schema XSD, documentacao ou codigo oficial da Energistics e
  redistribuido neste repositorio. Apenas os **namespaces publicos** e as
  **estruturas XML descritas nos schemas abertos** sao utilizados.
- O codigo do Alakoro permanece sob **licenca MIT**, mas isso nao se aplica
  aos proprios padroes Energistics, que permanecem sob suas proprias
  politicas de uso.

## Limitacoes

- A implementacao e pragmatica e nao valida contra schemas XSD oficiais.
- Estruturas muito complexas ou variantes de namespace podem exigir
  ajustes pontuais; abra uma issue se encontrar um arquivo que nao
  consiga ser lido.
