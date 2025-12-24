import types
import sys
import importlib
from unittest.mock import MagicMock

import numpy as np
import pytest

import app.search_utils as su


def test_generate_embedding_mocked():
    emb = su.generate_embedding("hello world")
    assert emb == [0.1, 0.2, 0.3]

    empty = su.generate_embedding("")
    assert empty is None


def test_get_model_lazy_singleton(monkeypatch):
    """
    Ensure get_model uses a singleton and does NOT try to load the real SentenceTransformer.
    """
    # Reset internal model reference
    su._model = None

    # Create dummy module with DummyTransformer
    calls = {"count": 0}

    class DummyTransformer:
        def __init__(self, name):
            calls["count"] += 1
            self.name = name

        def encode(self, text):
            return np.array([0.1, 0.2, 0.3])

    dummy_module = types.SimpleNamespace(SentenceTransformer=DummyTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", dummy_module)

    m1 = su.get_model()
    m2 = su.get_model()

    assert m1 is m2
    assert calls["count"] == 1  # constructed only once


def test_cosine_similarity_various():
    v1 = [1, 0, 0]
    v2 = [1, 0, 0]
    v3 = [0, 1, 0]

    assert abs(su.cosine_similarity(v1, v2) - 1.0) < 1e-6
    assert abs(su.cosine_similarity(v1, v3)) < 1e-6
    assert su.cosine_similarity(None, v2) == 0.0
    assert su.cosine_similarity(v1, None) == 0.0
    assert su.cosine_similarity([0, 0, 0], [1, 2, 3]) == 0.0


def test_generate_embedding_coverage():
    """
    Test the actual generate_embedding function in app/search_utils.py
    by reloading the module to bypass the conftest fixture that mocks it.
    """
    import app.search_utils

    # Reload to restore the original function logic, bypassing the fixture mock
    importlib.reload(app.search_utils)

    # Configure the global mock for sentence_transformers (injected by conftest)
    st_module = sys.modules["sentence_transformers"]

    mock_model_instance = MagicMock()
    st_module.SentenceTransformer.return_value = mock_model_instance
    mock_model_instance.encode.return_value = [0.5, 0.5, 0.5]

    # Test the None case
    assert app.search_utils.generate_embedding(None) is None

    # Test with valid input
    result = app.search_utils.generate_embedding("hello world")
    assert result == [0.5, 0.5, 0.5]

    # Verify interaction
    st_module.SentenceTransformer.assert_called_with("all-MiniLM-L6-v2")
    mock_model_instance.encode.assert_called_with("hello world")
