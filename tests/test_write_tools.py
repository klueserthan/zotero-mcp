"""
Tests for Zotero MCP write tools.

Tests cover: create_item, update_item, delete_item, create_collection,
add_to_collection, remove_from_collection, and get_item_template.

All pyzotero API calls are mocked so tests run without a live Zotero instance.
"""

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx() -> MagicMock:
    """Return a mock MCP Context with info/warn/error stubs."""
    ctx = MagicMock()
    ctx.info = MagicMock()
    ctx.warn = MagicMock()
    ctx.error = MagicMock()
    return ctx


def _make_item(
    key: str = "ABC12345",
    title: str = "Test Item",
    item_type: str = "journalArticle",
    **extra,
) -> dict:
    """Build a minimal Zotero item dict."""
    data = {
        "key": key,
        "itemType": item_type,
        "title": title,
        "creators": [],
        "tags": [],
        "collections": [],
        "date": "",
        "abstractNote": "",
        "url": "",
        "DOI": "",
        **extra,
    }
    return {"key": key, "data": data, "meta": {}}


def _make_collection(
    key: str = "COL12345", name: str = "My Collection", parent: str | None = None
) -> dict:
    """Build a minimal Zotero collection dict."""
    data = {"key": key, "name": name}
    if parent:
        data["parentCollection"] = parent
    return {"key": key, "data": data}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_zotero_client():
    """Patch get_zotero_client so no real Zotero instance is needed."""
    with patch("zotero_mcp.server.get_zotero_client") as mock_get:
        mock_zot = MagicMock()
        mock_get.return_value = mock_zot
        yield mock_zot


# ---------------------------------------------------------------------------
# Import the tool functions (after patch target is established)
# FastMCP's @mcp.tool decorator wraps functions in FunctionTool objects.
# Access the underlying callable via .fn so tests can invoke them directly.
# ---------------------------------------------------------------------------
from zotero_mcp.server import add_to_collection as _add_to_collection
from zotero_mcp.server import create_collection as _create_collection
from zotero_mcp.server import create_item as _create_item
from zotero_mcp.server import delete_item as _delete_item
from zotero_mcp.server import get_item_template as _get_item_template
from zotero_mcp.server import remove_from_collection as _remove_from_collection
from zotero_mcp.server import update_item as _update_item

add_to_collection = _add_to_collection.fn
create_collection = _create_collection.fn
create_item = _create_item.fn
delete_item = _delete_item.fn
get_item_template = _get_item_template.fn
remove_from_collection = _remove_from_collection.fn
update_item = _update_item.fn


# ===========================================================================
# zotero_get_item_template
# ===========================================================================


class TestGetItemTemplate:
    def test_returns_template_json(self, mock_zotero_client):
        template = {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "abstractNote": "",
            "publicationTitle": "",
            "volume": "",
            "issue": "",
            "pages": "",
            "date": "",
            "DOI": "",
            "url": "",
            "tags": [],
            "collections": [],
        }
        mock_zotero_client.item_template.return_value = template
        ctx = _make_ctx()

        result = get_item_template(item_type="journalArticle", ctx=ctx)

        assert "journalArticle" in result
        assert "```json" in result
        mock_zotero_client.item_template.assert_called_once_with("journalArticle")

    def test_error_on_invalid_type(self, mock_zotero_client):
        mock_zotero_client.item_template.side_effect = Exception("Invalid item type")
        ctx = _make_ctx()

        result = get_item_template(item_type="invalidType", ctx=ctx)

        assert "Error" in result
        assert "Invalid item type" in result


# ===========================================================================
# zotero_create_item
# ===========================================================================


class TestCreateItem:
    def test_creates_basic_item(self, mock_zotero_client):
        template = {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
            "date": "",
            "abstractNote": "",
            "url": "",
            "DOI": "",
        }
        mock_zotero_client.item_template.return_value = template.copy()
        mock_zotero_client.create_items.return_value = {
            "success": {"0": "NEW12345"},
            "unchanged": {},
            "failed": {},
        }
        ctx = _make_ctx()

        result = create_item(
            item_type="journalArticle",
            title="Test Paper",
            ctx=ctx,
        )

        assert "Successfully created" in result
        assert "NEW12345" in result
        call_args = mock_zotero_client.create_items.call_args[0][0]
        assert call_args[0]["title"] == "Test Paper"

    def test_creates_item_with_all_fields(self, mock_zotero_client):
        template = {
            "itemType": "journalArticle",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
            "date": "",
            "abstractNote": "",
            "url": "",
            "DOI": "",
            "publicationTitle": "",
            "volume": "",
        }
        mock_zotero_client.item_template.return_value = template.copy()
        mock_zotero_client.create_items.return_value = {
            "success": {"0": "NEW67890"},
            "unchanged": {},
            "failed": {},
        }
        ctx = _make_ctx()

        result = create_item(
            item_type="journalArticle",
            title="Full Paper",
            creators=[
                {"creatorType": "author", "firstName": "Jane", "lastName": "Doe"}
            ],
            date="2024-06-15",
            abstract="A test abstract",
            tags=["ml", "ai"],
            collections=["COL12345"],
            url="https://example.com",
            doi="10.1234/test",
            extra_fields={"publicationTitle": "Nature", "volume": "42"},
            ctx=ctx,
        )

        assert "Successfully created" in result
        payload = mock_zotero_client.create_items.call_args[0][0][0]
        assert payload["title"] == "Full Paper"
        assert payload["date"] == "2024-06-15"
        assert payload["abstractNote"] == "A test abstract"
        assert payload["tags"] == [{"tag": "ml"}, {"tag": "ai"}]
        assert payload["collections"] == ["COL12345"]
        assert payload["url"] == "https://example.com"
        assert payload["DOI"] == "10.1234/test"
        assert payload["publicationTitle"] == "Nature"
        assert payload["volume"] == "42"

    def test_parses_json_string_creators(self, mock_zotero_client):
        template = {
            "itemType": "book",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
            "date": "",
            "abstractNote": "",
            "url": "",
            "DOI": "",
        }
        mock_zotero_client.item_template.return_value = template.copy()
        mock_zotero_client.create_items.return_value = {
            "success": {"0": "NEW_JSON"},
            "unchanged": {},
            "failed": {},
        }
        ctx = _make_ctx()

        result = create_item(
            item_type="book",
            title="JSON Test",
            creators='[{"creatorType": "author", "firstName": "A", "lastName": "B"}]',
            tags='["tag1", "tag2"]',
            collections='["COL1"]',
            extra_fields='{"publisher": "Acme"}',
            ctx=ctx,
        )

        assert "Successfully created" in result

    def test_rejects_malformed_json_creators(self, mock_zotero_client):
        ctx = _make_ctx()

        result = create_item(
            item_type="book",
            title="Bad JSON",
            creators="not-valid-json",
            ctx=ctx,
        )

        assert "Error" in result
        assert "creators" in result

    def test_rejects_empty_title(self, mock_zotero_client):
        ctx = _make_ctx()

        result = create_item(item_type="book", title="  ", ctx=ctx)

        assert "Error" in result
        assert "empty" in result.lower()

    def test_warns_on_unknown_extra_field(self, mock_zotero_client):
        template = {
            "itemType": "book",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
            "date": "",
            "abstractNote": "",
            "url": "",
            "DOI": "",
        }
        mock_zotero_client.item_template.return_value = template.copy()
        mock_zotero_client.create_items.return_value = {
            "success": {"0": "NEW_WARN"},
            "unchanged": {},
            "failed": {},
        }
        ctx = _make_ctx()

        create_item(
            item_type="book",
            title="Warn Test",
            extra_fields={"nonexistentField": "value"},
            ctx=ctx,
        )

        ctx.warn.assert_called()

    def test_reports_api_failure(self, mock_zotero_client):
        template = {
            "itemType": "book",
            "title": "",
            "creators": [],
            "tags": [],
            "collections": [],
            "date": "",
            "abstractNote": "",
            "url": "",
            "DOI": "",
        }
        mock_zotero_client.item_template.return_value = template.copy()
        mock_zotero_client.create_items.return_value = {
            "success": {},
            "unchanged": {},
            "failed": {"0": {"code": 400, "message": "Bad request"}},
        }
        ctx = _make_ctx()

        result = create_item(item_type="book", title="Fail Test", ctx=ctx)

        assert "Failed" in result
        assert "Bad request" in result

    def test_handles_exception(self, mock_zotero_client):
        mock_zotero_client.item_template.side_effect = Exception("Network error")
        ctx = _make_ctx()

        result = create_item(item_type="book", title="Error Test", ctx=ctx)

        assert "Error" in result
        assert "Network error" in result


# ===========================================================================
# zotero_update_item
# ===========================================================================


class TestUpdateItem:
    def test_updates_title(self, mock_zotero_client):
        existing = _make_item(title="Old Title")
        mock_zotero_client.item.return_value = existing
        ctx = _make_ctx()

        result = update_item(item_key="ABC12345", title="New Title", ctx=ctx)

        assert "Successfully updated" in result
        assert "New Title" in result
        mock_zotero_client.update_item.assert_called_once()
        updated = mock_zotero_client.update_item.call_args[0][0]
        assert updated["data"]["title"] == "New Title"

    def test_updates_multiple_fields(self, mock_zotero_client):
        existing = _make_item()
        mock_zotero_client.item.return_value = existing
        ctx = _make_ctx()

        result = update_item(
            item_key="ABC12345",
            title="Updated",
            date="2025",
            abstract="New abstract",
            tags=["updated-tag"],
            url="https://new.url",
            doi="10.9999/new",
            ctx=ctx,
        )

        assert "Successfully updated" in result
        updated = mock_zotero_client.update_item.call_args[0][0]
        assert updated["data"]["title"] == "Updated"
        assert updated["data"]["date"] == "2025"
        assert updated["data"]["abstractNote"] == "New abstract"
        assert updated["data"]["tags"] == [{"tag": "updated-tag"}]
        assert updated["data"]["url"] == "https://new.url"
        assert updated["data"]["DOI"] == "10.9999/new"

    def test_preserves_unspecified_fields(self, mock_zotero_client):
        existing = _make_item(title="Keep This", date="2020")
        mock_zotero_client.item.return_value = existing
        ctx = _make_ctx()

        update_item(item_key="ABC12345", abstract="Only this changes", ctx=ctx)

        updated = mock_zotero_client.update_item.call_args[0][0]
        assert updated["data"]["title"] == "Keep This"
        assert updated["data"]["date"] == "2020"
        assert updated["data"]["abstractNote"] == "Only this changes"

    def test_item_not_found(self, mock_zotero_client):
        mock_zotero_client.item.return_value = None
        ctx = _make_ctx()

        result = update_item(item_key="NOTFOUND", title="X", ctx=ctx)

        assert "No item found" in result

    def test_parses_json_extra_fields(self, mock_zotero_client):
        existing = _make_item()
        mock_zotero_client.item.return_value = existing
        ctx = _make_ctx()

        result = update_item(
            item_key="ABC12345",
            extra_fields='{"volume": "99"}',
            ctx=ctx,
        )

        assert "Successfully updated" in result
        updated = mock_zotero_client.update_item.call_args[0][0]
        assert updated["data"]["volume"] == "99"

    def test_handles_exception(self, mock_zotero_client):
        mock_zotero_client.item.side_effect = Exception("Timeout")
        ctx = _make_ctx()

        result = update_item(item_key="ABC12345", title="X", ctx=ctx)

        assert "Error" in result
        assert "Timeout" in result


# ===========================================================================
# zotero_delete_item
# ===========================================================================


class TestDeleteItem:
    def test_deletes_item(self, mock_zotero_client):
        existing = _make_item(title="Doomed Item")
        mock_zotero_client.item.return_value = existing
        ctx = _make_ctx()

        result = delete_item(item_key="ABC12345", ctx=ctx)

        assert "Successfully deleted" in result
        assert "Doomed Item" in result
        mock_zotero_client.delete_item.assert_called_once_with(existing)

    def test_item_not_found(self, mock_zotero_client):
        mock_zotero_client.item.return_value = None
        ctx = _make_ctx()

        result = delete_item(item_key="GONE", ctx=ctx)

        assert "No item found" in result

    def test_handles_exception(self, mock_zotero_client):
        mock_zotero_client.item.side_effect = Exception("Forbidden")
        ctx = _make_ctx()

        result = delete_item(item_key="ABC12345", ctx=ctx)

        assert "Error" in result
        assert "Forbidden" in result


# ===========================================================================
# zotero_create_collection
# ===========================================================================


class TestCreateCollection:
    def test_creates_collection(self, mock_zotero_client):
        mock_zotero_client.create_collections.return_value = {
            "success": {"0": "NEWCOL01"},
            "unchanged": {},
            "failed": {},
        }
        ctx = _make_ctx()

        result = create_collection(name="My New Collection", ctx=ctx)

        assert "Successfully created" in result
        assert "NEWCOL01" in result
        payload = mock_zotero_client.create_collections.call_args[0][0]
        assert payload == [{"name": "My New Collection"}]

    def test_creates_subcollection(self, mock_zotero_client):
        mock_zotero_client.create_collections.return_value = {
            "success": {"0": "SUBCOL01"},
            "unchanged": {},
            "failed": {},
        }
        ctx = _make_ctx()

        result = create_collection(
            name="Sub Collection",
            parent_collection="PARENT01",
            ctx=ctx,
        )

        assert "Successfully created" in result
        assert "PARENT01" in result
        payload = mock_zotero_client.create_collections.call_args[0][0]
        assert payload == [{"name": "Sub Collection", "parentCollection": "PARENT01"}]

    def test_rejects_empty_name(self, mock_zotero_client):
        ctx = _make_ctx()

        result = create_collection(name="  ", ctx=ctx)

        assert "Error" in result
        assert "empty" in result.lower()

    def test_reports_api_failure(self, mock_zotero_client):
        mock_zotero_client.create_collections.return_value = {
            "success": {},
            "unchanged": {},
            "failed": {"0": {"code": 409, "message": "Conflict"}},
        }
        ctx = _make_ctx()

        result = create_collection(name="Conflict Test", ctx=ctx)

        assert "Failed" in result
        assert "Conflict" in result

    def test_handles_exception(self, mock_zotero_client):
        mock_zotero_client.create_collections.side_effect = Exception("Server down")
        ctx = _make_ctx()

        result = create_collection(name="Error Test", ctx=ctx)

        assert "Error" in result
        assert "Server down" in result


# ===========================================================================
# zotero_add_to_collection
# ===========================================================================


class TestAddToCollection:
    def test_adds_item(self, mock_zotero_client):
        item = _make_item(title="Paper to Add")
        mock_zotero_client.item.return_value = item
        mock_zotero_client.collection.return_value = _make_collection(
            name="Target Coll"
        )
        ctx = _make_ctx()

        result = add_to_collection(
            collection_key="COL12345",
            item_key="ABC12345",
            ctx=ctx,
        )

        assert "Successfully added" in result
        assert "Paper to Add" in result
        assert "Target Coll" in result
        mock_zotero_client.addto_collection.assert_called_once_with("COL12345", item)

    def test_item_not_found(self, mock_zotero_client):
        mock_zotero_client.item.return_value = None
        ctx = _make_ctx()

        result = add_to_collection(
            collection_key="COL12345",
            item_key="MISSING",
            ctx=ctx,
        )

        assert "No item found" in result

    def test_handles_exception(self, mock_zotero_client):
        mock_zotero_client.item.side_effect = Exception("Auth failed")
        ctx = _make_ctx()

        result = add_to_collection(
            collection_key="COL12345",
            item_key="ABC12345",
            ctx=ctx,
        )

        assert "Error" in result
        assert "Auth failed" in result


# ===========================================================================
# zotero_remove_from_collection
# ===========================================================================


class TestRemoveFromCollection:
    def test_removes_item(self, mock_zotero_client):
        item = _make_item(title="Paper to Remove")
        mock_zotero_client.item.return_value = item
        mock_zotero_client.collection.return_value = _make_collection(
            name="Source Coll"
        )
        ctx = _make_ctx()

        result = remove_from_collection(
            collection_key="COL12345",
            item_key="ABC12345",
            ctx=ctx,
        )

        assert "Successfully removed" in result
        assert "Paper to Remove" in result
        assert "Source Coll" in result
        assert "NOT been deleted" in result
        mock_zotero_client.deletefrom_collection.assert_called_once_with(
            "COL12345", item
        )

    def test_item_not_found(self, mock_zotero_client):
        mock_zotero_client.item.return_value = None
        ctx = _make_ctx()

        result = remove_from_collection(
            collection_key="COL12345",
            item_key="MISSING",
            ctx=ctx,
        )

        assert "No item found" in result

    def test_handles_exception(self, mock_zotero_client):
        mock_zotero_client.item.side_effect = Exception("Rate limited")
        ctx = _make_ctx()

        result = remove_from_collection(
            collection_key="COL12345",
            item_key="ABC12345",
            ctx=ctx,
        )

        assert "Error" in result
        assert "Rate limited" in result
