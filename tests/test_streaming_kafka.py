"""
Testes para KafkaStreamDriver (com mocks, sem broker real).
"""

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.io.alakoro_spool import AlakoroPatch
from src.io.streaming import KafkaStreamDriver

try:
    import kafka

    HAS_KAFKA = True
except ImportError:
    HAS_KAFKA = False


def _make_patch():
    import dascore as dc
    from dascore.core.attrs import PatchAttrs

    n_t, n_c = 6, 4
    data = np.random.randn(n_t, n_c).astype(np.float64)
    patch = dc.Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c),
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(data_category="das", data_units="1/s"),
    )
    return AlakoroPatch(patch)


@pytest.mark.skipif(not HAS_KAFKA, reason="kafka-python not installed")
def test_kafka_driver_connect_publishes_profile():
    driver = KafkaStreamDriver("localhost:9092")

    mock_consumer = MagicMock()
    mock_producer = MagicMock()

    with patch("kafka.KafkaConsumer", return_value=mock_consumer), \
         patch("kafka.KafkaProducer", return_value=mock_producer):
        driver.connect(profile={"well_id": "W-01", "gauge_length_m": 10.0})

    assert driver._consumer is mock_consumer
    assert driver._producer is mock_producer
    mock_producer.send.assert_called_once()
    args, kwargs = mock_producer.send.call_args
    assert args[0] == "alakoro.profile"
    value = kwargs.get("value") if "value" in kwargs else args[1]
    payload = json.loads(value.decode("utf-8"))
    assert payload["profileType"] == "DASAcquisitionProfile"
    assert payload["profile"]["well_id"] == "W-01"


@pytest.mark.skipif(not HAS_KAFKA, reason="kafka-python not installed")
def test_kafka_driver_produce_uses_avro():
    driver = KafkaStreamDriver("localhost:9092")
    driver._producer = MagicMock()

    patch = _make_patch()
    driver.produce(patch, key="patch-01")

    driver._producer.send.assert_called_once()
    args, kwargs = driver._producer.send.call_args
    assert args[0] == "alakoro.data"
    assert kwargs["key"] == b"patch-01"
    assert isinstance(kwargs["value"], bytes)
    assert len(kwargs["value"]) > 0


@pytest.mark.skipif(not HAS_KAFKA, reason="kafka-python not installed")
def test_kafka_driver_stream_reconstructs_patch():
    driver = KafkaStreamDriver("localhost:9092")

    patch = _make_patch()
    payload = patch.to_avro_bytes()

    msg = MagicMock()
    msg.topic = "alakoro.data"
    msg.value = payload

    mock_consumer = MagicMock()
    mock_consumer.__iter__ = MagicMock(return_value=iter([msg]))
    driver._consumer = mock_consumer

    results = list(driver.stream())
    assert len(results) == 1
    assert isinstance(results[0], AlakoroPatch)
    assert results[0].modality == "das"
    assert np.allclose(results[0].data, patch.data)


@pytest.mark.skipif(not HAS_KAFKA, reason="kafka-python not installed")
def test_kafka_driver_stream_profile_message():
    driver = KafkaStreamDriver("localhost:9092")

    msg = MagicMock()
    msg.topic = "alakoro.profile"
    msg.value = json.dumps({"profileType": "DASAcquisitionProfile"}).encode("utf-8")

    mock_consumer = MagicMock()
    mock_consumer.__iter__ = MagicMock(return_value=iter([msg]))
    driver._consumer = mock_consumer

    results = list(driver.stream())
    assert len(results) == 1
    assert results[0]["profileType"] == "DASAcquisitionProfile"
