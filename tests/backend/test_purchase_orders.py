"""
Tests for purchase order API endpoints.
"""
import pytest

import mock_data


@pytest.fixture(autouse=True)
def clear_purchase_orders():
    """Created purchase orders live in memory; isolate each test from the others."""
    mock_data.purchase_orders.clear()
    yield
    mock_data.purchase_orders.clear()


def make_request(backlog_item_id, **overrides):
    """Build a valid create-purchase-order payload."""
    payload = {
        "backlog_item_id": backlog_item_id,
        "supplier_name": "Industrial Supply Co",
        "quantity": 100,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-12-31",
        "notes": "Rush order",
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def backlog_item_id(client):
    """ID of an existing backlog item."""
    return client.get("/api/backlog").json()[0]["id"]


class TestPurchaseOrderEndpoints:
    """Test suite for purchase order endpoints."""

    def test_create_purchase_order(self, client, backlog_item_id):
        """Test creating a purchase order for a backlog item."""
        response = client.post("/api/purchase-orders", json=make_request(backlog_item_id))
        assert response.status_code == 201

        po = response.json()
        assert po["id"].startswith("PO-")
        assert po["backlog_item_id"] == backlog_item_id
        assert po["supplier_name"] == "Industrial Supply Co"
        assert po["quantity"] == 100
        assert abs(po["unit_cost"] - 12.5) < 0.01
        assert po["expected_delivery_date"] == "2025-12-31"
        assert po["status"] == "Pending"
        assert po["notes"] == "Rush order"
        assert "created_date" in po

    def test_create_purchase_order_without_notes(self, client, backlog_item_id):
        """Test that notes are optional."""
        payload = make_request(backlog_item_id)
        del payload["notes"]

        response = client.post("/api/purchase-orders", json=payload)
        assert response.status_code == 201
        assert response.json()["notes"] is None

    def test_create_purchase_order_ids_are_unique(self, client):
        """Test that each purchase order gets its own ID."""
        items = client.get("/api/backlog").json()
        assert len(items) >= 2

        first = client.post("/api/purchase-orders", json=make_request(items[0]["id"])).json()
        second = client.post("/api/purchase-orders", json=make_request(items[1]["id"])).json()
        assert first["id"] != second["id"]

    def test_get_purchase_order_by_backlog_item(self, client, backlog_item_id):
        """Test fetching a purchase order by its backlog item ID."""
        created = client.post("/api/purchase-orders", json=make_request(backlog_item_id)).json()

        response = client.get(f"/api/purchase-orders/{backlog_item_id}")
        assert response.status_code == 200
        assert response.json() == created

    def test_get_nonexistent_purchase_order(self, client, backlog_item_id):
        """Test fetching a purchase order for a backlog item that has none."""
        response = client.get(f"/api/purchase-orders/{backlog_item_id}")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_create_purchase_order_unknown_backlog_item(self, client):
        """Test creating a purchase order for a backlog item that doesn't exist."""
        response = client.post("/api/purchase-orders", json=make_request("nonexistent-999"))
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_duplicate_purchase_order(self, client, backlog_item_id):
        """Test that a backlog item can only have one purchase order."""
        first = client.post("/api/purchase-orders", json=make_request(backlog_item_id))
        assert first.status_code == 201

        second = client.post("/api/purchase-orders", json=make_request(backlog_item_id))
        assert second.status_code == 409
        assert len(mock_data.purchase_orders) == 1

    @pytest.mark.parametrize("overrides", [
        {"quantity": 0},
        {"quantity": -5},
        {"unit_cost": -1},
        {"supplier_name": "   "},
    ])
    def test_create_purchase_order_invalid_values(self, client, backlog_item_id, overrides):
        """Test that invalid quantity, cost and supplier values are rejected."""
        response = client.post(
            "/api/purchase-orders", json=make_request(backlog_item_id, **overrides)
        )
        assert response.status_code == 400
        assert mock_data.purchase_orders == []

    def test_create_purchase_order_missing_fields(self, client, backlog_item_id):
        """Test that required fields are enforced."""
        response = client.post("/api/purchase-orders", json={"backlog_item_id": backlog_item_id})
        assert response.status_code == 422


class TestBacklogPurchaseOrderStatus:
    """Test that the backlog endpoint reflects purchase order status."""

    def test_backlog_without_purchase_orders(self, client):
        """Test that no backlog item has a purchase order initially."""
        for item in client.get("/api/backlog").json():
            assert item["has_purchase_order"] is False
            assert item["purchase_order_id"] is None

    def test_backlog_reflects_created_purchase_order(self, client, backlog_item_id):
        """Test that the backlog item gets the new purchase order's ID."""
        po = client.post("/api/purchase-orders", json=make_request(backlog_item_id)).json()

        items = client.get("/api/backlog").json()
        with_po = [i for i in items if i["id"] == backlog_item_id][0]
        assert with_po["has_purchase_order"] is True
        assert with_po["purchase_order_id"] == po["id"]

        # Other backlog items are unaffected
        for item in items:
            if item["id"] != backlog_item_id:
                assert item["has_purchase_order"] is False
                assert item["purchase_order_id"] is None
