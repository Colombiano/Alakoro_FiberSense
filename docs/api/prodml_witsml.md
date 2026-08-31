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

## Limitacoes

- A implementacao e pragmatica e nao valida contra schemas XSD oficiais.
- Estruturas muito complexas ou variantes de namespace podem exigir
  ajustes pontuais; abra uma issue se encontrar um arquivo que nao
  consiga ser lido.
