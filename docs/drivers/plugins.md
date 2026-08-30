# Plugins de Drivers Proprietários

O Alakoro FiberSense lê dados de diversos formatos abertos (TDMS, SEG-Y, HDF5, NetCDF, MiniSEED, DASDAE, etc.) através das integrações com **DASCore** e **Xdas**. No entanto, fabricantes de equipamentos DFOS/DAS frequentemente fornecem seus próprios formatos binários ou SDKs comerciais. Para suportar esses casos sem poluir o core MIT do projeto, adotamos uma arquitetura de **plugins opcionais de drivers de fabricantes**.

## Princípios

1. **Core MIT permanece aberto**: o código-fonte do `alakoro-fibersense` não inclui SDKs, binários ou documentação confidencial de fabricantes.
2. **Plugins separados**: cada driver proprietário vive em seu próprio pacote Python (ex.: `alakoro-silixa-driver`, `alakoro-febus-driver`), podendo ter licença comercial ou proprietária.
3. **Descoberta automática**: plugins se registram via entry point `alakoro.driver` no `pyproject.toml`.
4. **Fallback open-source**: se nenhum driver proprietário corresponder, o Alakoro tenta DASCore e Xdas automaticamente.

## API do driver

Todo driver deve herdar de `BaseVendorDriver` e implementar os métodos obrigatórios:

```python
from src.io.drivers import BaseVendorDriver
from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool

class MeuDriver(BaseVendorDriver):
    name = "meu_fabricante"           # nome curto e único
    supported_extensions = {".bin"}   # extensões suportadas
    version = "1.0.0"

    @classmethod
    def is_available(cls) -> bool:
        """Retorna True se o SDK/licença estiver disponível."""
        return True

    def read(self, path, **kwargs) -> AlakoroPatch | AlakoroSpool:
        """Lê o arquivo e retorna AlakoroPatch ou AlakoroSpool."""
        ...

    def metadata(self, path, **kwargs) -> dict:
        """Retorna metadados sem carregar os dados."""
        return {}
```

## Registro via entry point

No `pyproject.toml` do pacote do plugin:

```toml
[project.entry-points."alakoro.driver"]
meu_fabricante = "meu_pacote.driver:MeuDriver"
```

Ao ser instalado, o plugin é descoberto automaticamente por `VendorDriverRegistry`.

## Uso no Alakoro

```python
from src.io.drivers import read_vendor, list_available_drivers, detect_driver

# Lista drivers disponíveis
print(list_available_drivers())

# Detecta o driver apropriado
print(detect_driver("/dados/poco.exd"))

# Lê usando detecção automática (com fallback DASCore/Xdas)
patch = read_vendor("/dados/poco.exd")

# Força um driver específico
patch = read_vendor("/dados/poco.bin", vendor_hint="meu_fabricante")

# Desabilita fallback
patch = read_vendor("/dados/poco.bin", fallback=False)
```

## Driver de exemplo

O pacote inclui o driver open-source `example_vendor` (`src/io/drivers/optional/example_vendor.py`) que demonstra a API completa usando arquivos `.exd` baseados em HDF5. Ele é carregado automaticamente quando `h5py` está disponível.

```python
from src.io.drivers.optional.example_vendor import write_example_file, ExampleVendorDriver
from src.io.drivers import read_vendor

path = write_example_file("/tmp/demo.exd", shape=(100, 500))
patch = read_vendor(path)
print(patch.shape)
```

## Questões de propriedade intelectual

- **Não inclua SDKs ou documentação confidencial** no repositório principal do Alakoro.
- **Mantenha o plugin em repositório/pacote separado** com a licença apropriada.
- **Não faça engenharia reversa** de formatos protegidos por acordo de confidencialidade ou legislação local.
- **API pública genérica**: o Alakoro expõe apenas `BaseVendorDriver` e funções de leitura; detalhes do formato permanecem no plugin.
- Para drivers baseados em formatos documentados publicamente, considere contribuir com um leitor open-source via DASCore ou Xdas em vez de um plugin proprietário.
