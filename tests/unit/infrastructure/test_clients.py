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


def test_get_langfuse_handler_none_if_keys_missing():
    from app.infrastructure.config.clients import get_langfuse_handler

    with patch("app.infrastructure.config.clients.settings") as mock_settings:
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""

        with patch("app.infrastructure.config.clients._langfuse_handler", None):
            handler = get_langfuse_handler()
            assert handler is None


def test_get_langfuse_handler_created_if_keys_present():
    from app.infrastructure.config.clients import get_langfuse_handler

    with patch("app.infrastructure.config.clients.settings") as mock_settings:
        mock_settings.langfuse_public_key = "pub-key"
        mock_settings.langfuse_secret_key = "sec-key"
        mock_settings.langfuse_host = "http://localhost:3000"

        with patch("app.infrastructure.config.clients._langfuse_handler", None):
            with patch("langfuse.callback.CallbackHandler") as MockCallbackHandler:
                mock_handler = MagicMock()
                MockCallbackHandler.return_value = mock_handler

                handler = get_langfuse_handler()

                assert handler is mock_handler
                MockCallbackHandler.assert_called_once_with(
                    public_key="pub-key",
                    secret_key="sec-key",
                    host="http://localhost:3000",
                )
