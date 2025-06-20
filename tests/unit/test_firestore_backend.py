import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import timedelta

from fast_cache import FirestoreBackend


@pytest.fixture
def firestore_backend():
    with patch("google.cloud.firestore.Client") as MockSyncClient, \
         patch("google.cloud.firestore.AsyncClient") as MockAsyncClient:
        mock_sync_db = MagicMock()
        mock_async_db = MagicMock()
        MockSyncClient.return_value = mock_sync_db
        MockAsyncClient.return_value = mock_async_db

        backend = FirestoreBackend(credential_path=None, namespace="test-ns")
        backend._sync_db = mock_sync_db
        backend._async_db = mock_async_db
        yield backend


def test_set_and_get(firestore_backend):
    # Mock Firestore document
    doc_ref = MagicMock()
    firestore_backend._sync_db.collection.return_value.document.return_value = doc_ref

    # Simulate set
    firestore_backend.set("foo", "bar")
    doc_ref.set.assert_called_once()

    # Simulate get
    doc_ref.get.return_value.exists = True
    doc_ref.get.return_value.to_dict.return_value = {
        "value": firestore_backend._sync_db.collection.return_value.document.return_value.set.call_args[
            0
        ][0]["value"],
        "expires_at": None,
    }
    # Patch pickle.loads to just return "bar"
    with patch("pickle.loads", return_value="bar"):
        assert firestore_backend.get("foo") == "bar"


def test_delete(firestore_backend):
    doc_ref = MagicMock()
    firestore_backend._sync_db.collection.return_value.document.return_value = doc_ref
    firestore_backend.delete("foo")
    doc_ref.delete.assert_called_once()


def test_clear(firestore_backend):
    doc1 = MagicMock()
    doc2 = MagicMock()
    firestore_backend._sync_db.collection.return_value.stream.return_value = [
        doc1,
        doc2,
    ]
    firestore_backend.clear()
    doc1.reference.delete.assert_called_once()
    doc2.reference.delete.assert_called_once()


def test_has(firestore_backend):
    doc_ref = MagicMock()
    firestore_backend._sync_db.collection.return_value.document.return_value = doc_ref
    doc_ref.get.return_value.exists = True
    doc_ref.get.return_value.to_dict.return_value = {"expires_at": None}
    assert firestore_backend.has("foo")


@pytest.mark.asyncio
async def test_async_set_and_get(firestore_backend):
    doc_ref = MagicMock()
    doc_ref.set = AsyncMock()

    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "value": b"pickled-bar",
        "expires_at": None,
    }
    doc_ref.get = AsyncMock(return_value=mock_doc)
    firestore_backend._async_db.collection.return_value.document.return_value = doc_ref

    await firestore_backend.aset("foo", "bar")
    doc_ref.set.assert_awaited_once()

    with patch("pickle.loads", return_value="bar"):
        assert await firestore_backend.aget("foo") == "bar"
