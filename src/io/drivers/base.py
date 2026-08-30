"""
Alakoro FiberSense — Base para drivers de fabricantes (vendor drivers)

Define a interface que plugins proprietários devem implementar.
O core Alakoro permanece sob licença MIT; drivers proprietários podem
ser distribuídos em pacotes separados com suas próprias licenças.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union

from src.io.alakoro_spool import AlakoroPatch, AlakoroSpool


class BaseVendorDriver(ABC):
    """
    Interface base para drivers de fabricantes de equipamentos DFOS/DAS.

    Cada driver proprietário deve herdar desta classe e registrar-se via
    entry point ``alakoro.driver`` no grupo de entry points do setuptools.
    """

    #: Nome curto e único do fabricante (ex: "silixa", "optodas", "febus").
    name: str = ""

    #: Extensões de arquivo suportadas (ex: {".h5", ".tdms"}).
    supported_extensions: Set[str] = set()

    #: Versão do driver.
    version: str = "0.0.0"

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """
        Retorna True se o driver puder ser usado (SDK instalado, licença OK, etc.).
        """
        ...

    @classmethod
    def detect(cls, path: Union[str, Path]) -> bool:
        """
        Retorna True se o arquivo/diretório parecer ser deste fabricante.
        A implementação padrão verifica a extensão.
        """
        path = Path(path)
        if path.is_dir():
            # Por padrão, diretórios não são detectados automaticamente;
            # subclasses podem sobrescrever.
            return False
        return path.suffix.lower() in cls.supported_extensions

    @abstractmethod
    def read(
        self, path: Union[str, Path], **kwargs: Any
    ) -> Union[AlakoroPatch, AlakoroSpool]:
        """
        Lê um arquivo ou diretório e retorna AlakoroPatch ou AlakoroSpool.
        """
        ...

    def metadata(self, path: Union[str, Path], **kwargs: Any) -> Dict[str, Any]:
        """
        Retorna metadados do arquivo/diretório sem carregar os dados.
        """
        return {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, version={self.version})"
