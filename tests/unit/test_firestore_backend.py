import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import timedelta

from fast_cache import FirestoreBackend


@pytest.fixture
def firestore_backend():
    with (
        patch("google.cloud.firestore.Client") as MockSyncClient,
        patch("google.cloud.firestore.AsyncClient") as MockAsyncClient,
    ):
        mock_sync_db = MagicMock()
        mock_async_db = MagicMock()
        MockSyncClient.return_value = mock_sync_db
        MockAsyncClient.return_value = mock_async_db

        backend = FirestoreBackend(credential_path=None, namespace="test-ns")
        backend._sync_db = mock_sync_db
        backend._async_db = mock_async_db
        yield backend


# ---- SYNC TESTS ----
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


def test_expire(firestore_backend):
    doc_ref = MagicMock()
    firestore_backend._sync_db.collection.return_value.document.return_value = doc_ref

    # Test setting with expiration
    firestore_backend.set("foo", "bar", expire=1)
    doc_ref.set.assert_called_once()

    # Mock expired document
    doc_ref.get.return_value.exists = True
    doc_ref.get.return_value.to_dict.return_value = {
        "value": b"pickled-bar",
        "expires_at": 0,  # Already expired
    }

    with patch("time.time", return_value=1000):  # Current time > expires_at
        assert firestore_backend.get("foo") is None


# ---- ASYNC TESTS ----
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


@pytest.mark.asyncio
async def test_async_delete(firestore_backend):
    doc_ref = MagicMock()
    doc_ref.delete = AsyncMock()
    firestore_backend._async_db.collection.return_value.document.return_value = doc_ref

    await firestore_backend.adelete("foo")
    doc_ref.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_clear(firestore_backend):
    doc1 = MagicMock()
    doc2 = MagicMock()
    doc1.reference.delete = AsyncMock()
    doc2.reference.delete = AsyncMock()

    async def mock_stream():
        yield doc1
        yield doc2

    firestore_backend._async_db.collection.return_value.stream.return_value = (
        mock_stream()
    )

    await firestore_backend.aclear()
    doc1.reference.delete.assert_awaited_once()
    doc2.reference.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_has(firestore_backend):
    doc_ref = MagicMock()
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {"expires_at": None}
    doc_ref.get = AsyncMock(return_value=mock_doc)
    firestore_backend._async_db.collection.return_value.document.return_value = doc_ref

    assert await firestore_backend.ahas("foo")


@pytest.mark.asyncio
async def test_async_expire(firestore_backend):
    doc_ref = MagicMock()
    doc_ref.set = AsyncMock()
    doc_ref.get = AsyncMock()
    firestore_backend._async_db.collection.return_value.document.return_value = doc_ref

    # Test setting with expiration
    await firestore_backend.aset("foo", "bar", expire=1)
    doc_ref.set.assert_awaited_once()

    # Mock expired document
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "value": b"pickled-bar",
        "expires_at": 0,  # Already expired
    }
    doc_ref.get.return_value = mock_doc

    with patch("time.time", return_value=1000):  # Current time > expires_at
        assert await firestore_backend.aget("foo") is None