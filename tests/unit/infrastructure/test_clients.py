from unittest.mock import MagicMock, patch

from app.infrastructure.config.clients import get_embedding_model, get_qdrant_client


def test_get_qdrant_client():
    client = get_qdrant_client()
    assert client is not None


def test_get_embedding_model():
    with patch("app.infrastructure.config.clients.TextEmbedding") as MockTextEmbedding:
        mock_model = MagicMock()
        MockTextEmbedding.return_value = mock_model

        # Reset global state to ensure the block is executed
        with patch("app.infrastructure.config.clients._embedding_model", None):
            # Test first call (initializes model)
            model1 = get_embedding_model()
            assert model1 is mock_model
            MockTextEmbedding.assert_called_once_with(
                model_name="BAAI/bge-small-en-v1.5"
            )

            # Test second call (returns cached)
            # We patch _embedding_model as mock_model directly to verify caching
            with patch(
                "app.infrastructure.config.clients._embedding_model", mock_model
            ):
                model2 = get_embedding_model()
                assert model2 is mock_model
