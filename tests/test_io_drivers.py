"""
Tests para a arquitetura de plugins de drivers de fabricantes.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.io.alakoro_spool import AlakoroPatch
from src.io.drivers import (
    BaseVendorDriver,
    VendorDriverRegistry,
    detect_driver,
    list_available_drivers,
    read_vendor,
)
from src.io.drivers.optional.example_vendor import (
    ExampleVendorDriver,
    write_example_file,
)


class MockVendorDriver(BaseVendorDriver):
    """Driver mock para testes de plugin/entry point."""

    name = "mock_vendor"
    supported_extensions = {".mock"}
    version = "0.1.0"

    @classmethod
    def is_available(cls) -> bool:
        return True

    def read(self, path, **kwargs):
        return MagicMock(spec=AlakoroPatch)


# ──────────────────────────────────────────────────────────────────────────────
# Testes de API pública e registry
# ──────────────────────────────────────────────────────────────────────────────


def test_public_api_exports():
    """A API pública deve exportar as classes/funções esperadas."""
    assert BaseVendorDriver is not None
    assert VendorDriverRegistry is not None
    assert callable(read_vendor)
    assert callable(list_available_drivers)
    assert callable(detect_driver)


def test_registry_lists_example_driver():
    """O registry deve descobrir o driver de exemplo."""
    registry = VendorDriverRegistry()
    names = [d.name for d in registry.list_drivers()]
    assert "example_vendor" in names


def test_registry_available_only_when_is_available():
    """list_available deve filtrar drivers indisponíveis."""
    registry = VendorDriverRegistry()
    available = registry.list_available()
    # MockVendorDriver não está registrado ainda, mas example_vendor sim
    assert any(d.name == "example_vendor" for d in available)


def test_detect_driver_by_extension(tmp_path: Path):
    """Detecta o driver example_vendor por extensão e assinatura."""
    path = tmp_path / "test.exd"
    write_example_file(path)

    registry = VendorDriverRegistry()
    detected = registry.detect_driver(path)
    assert detected is not None
    assert detected.name == "example_vendor"

    assert detect_driver(path) == "example_vendor"


def test_detect_driver_not_found(tmp_path: Path):
    """Arquivos desconhecidos não devem ser detectados."""
    path = tmp_path / "unknown.xyz"
    path.write_text("not a vendor file")
    assert detect_driver(path) is None


# ──────────────────────────────────────────────────────────────────────────────
# Testes de leitura
# ──────────────────────────────────────────────────────────────────────────────


def test_read_vendor_example_driver(tmp_path: Path):
    """read_vendor deve carregar arquivo .exd via driver de exemplo."""
    path = tmp_path / "test.exd"
    write_example_file(path, shape=(10, 20))

    result = read_vendor(path)
    assert isinstance(result, AlakoroPatch)
    assert result.shape == (10, 20)
    assert result.modality == "das"


def test_read_vendor_vendor_hint(tmp_path: Path):
    """vendor_hint deve forçar uso de um driver específico."""
    path = tmp_path / "test.exd"
    write_example_file(path, shape=(5, 8))

    result = read_vendor(path, vendor_hint="example_vendor")
    assert isinstance(result, AlakoroPatch)
    assert result.shape == (5, 8)


def test_read_vendor_vendor_hint_not_found(tmp_path: Path):
    """vendor_hint inexistente deve levantar ValueError."""
    with pytest.raises(ValueError, match="not found"):
        read_vendor("/tmp/fake.txt", vendor_hint="nonexistent")


def test_read_vendor_no_fallback(tmp_path: Path):
    """Se fallback=False e nenhum driver detectado, deve levantar ValueError."""
    path = tmp_path / "unknown.xyz"
    path.write_text("not a vendor file")
    with pytest.raises(ValueError, match="No vendor driver detected"):
        read_vendor(path, fallback=False)


# ──────────────────────────────────────────────────────────────────────────────
# Testes de descoberta por entry point
# ──────────────────────────────────────────────────────────────────────────────


def test_registry_discovers_mock_entry_point(tmp_path: Path):
    """O registry deve descobrir drivers via entry point alakoro.driver."""
    mock_ep = MagicMock()
    mock_ep.name = "mock_vendor"
    mock_ep.load.return_value = MockVendorDriver

    with patch(
        "src.io.drivers.registry.entry_points",
        return_value=[mock_ep],
    ):
        registry = VendorDriverRegistry()
        # Força recarregamento ignorando cache
        registry._drivers = None
        drivers = registry.list_drivers()
        names = [d.name for d in drivers]
        assert "mock_vendor" in names


def test_read_vendor_mock_entry_point(tmp_path: Path):
    """read_vendor deve usar driver descoberto por entry point."""
    mock_file = tmp_path / "data.mock"
    mock_file.write_text("mock")

    mock_ep = MagicMock()
    mock_ep.name = "mock_vendor"
    mock_ep.load.return_value = MockVendorDriver

    with patch(
        "src.io.drivers.registry.entry_points",
        return_value=[mock_ep],
    ):
        registry = VendorDriverRegistry()
        registry._drivers = None
        result = read_vendor(mock_file, registry=registry)
        assert result is not None


# ──────────────────────────────────────────────────────────────────────────────
# Testes de fallback open-source
# ──────────────────────────────────────────────────────────────────────────────


def test_fallback_read_uses_xdas_or_dascore(tmp_path: Path):
    """Fallback deve tentar Xdas/DASCore quando nenhum driver corresponder."""
    path = tmp_path / "fallback.nc"

    # Cria um NetCDF simples via xdas para testar fallback
    try:
        import xdas

        da = xdas.DataArray(
            xdas.VirtualArray(shape=(4, 8)),
            coords={
                "distance": xdas.Coordinate(np.array([0, 1, 2, 3]), "distance"),
                "time": xdas.Coordinate(np.array([0, 1, 2, 3, 4, 5, 6, 7]), "time"),
            },
        )
        xdas.to_netcdf(da, path)
    except Exception as exc:
        pytest.skip(f"Could not create xdas fallback fixture: {exc}")

    result = read_vendor(path)
    assert result is not None


def test_fallback_raises_when_nothing_works(tmp_path: Path):
    """Fallback deve levantar RuntimeError se todos os leitores falharem."""
    path = tmp_path / "bad.txt"
    path.write_text("not readable")
    with pytest.raises(RuntimeError, match="No vendor driver"):
        read_vendor(path)


# ──────────────────────────────────────────────────────────────────────────────
# Testes de metadados
# ──────────────────────────────────────────────────────────────────────────────


def test_example_driver_metadata(tmp_path: Path):
    """metadata() deve retornar shape e atributos sem carregar dados."""
    path = tmp_path / "test.exd"
    write_example_file(path, shape=(10, 20))

    driver = ExampleVendorDriver()
    meta = driver.metadata(path)
    assert meta["shape"] == (10, 20)
    assert meta["distance_count"] == 10
    assert meta["time_count"] == 20
    assert meta["well_id"] == "example-well-01"
