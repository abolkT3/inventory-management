"""
Tests for restocking API endpoints.
"""
import pytest

import mock_data


@pytest.fixture(autouse=True)
def clear_restocking_orders():
    """Submitted orders live in memory; isolate each test from the others."""
    mock_data.restocking_orders.clear()
    yield
    mock_data.restocking_orders.clear()


class TestRestockRecommendations:
    """Test suite for the restocking recommendation endpoint."""

    def test_zero_budget_recommends_nothing(self, client):
        """A zero budget cannot fund any item."""
        response = client.get("/api/restocking/recommendations?budget=0")
        assert response.status_code == 200

        data = response.json()
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_recommendations_structure(self, client):
        """Each recommendation has the fields the UI needs."""
        response = client.get("/api/restocking/recommendations?budget=1000000")
        assert response.status_code == 200

        data = response.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            for field in ["sku", "name", "category", "trend", "quantity_on_hand",
                          "forecasted_demand", "shortfall", "quantity", "unit_cost",
                          "line_total", "lead_time_days"]:
                assert field in item
            assert item["quantity"] > 0

    def test_recommendations_stay_within_budget(self, client):
        """Total cost never exceeds the budget, and totals add up."""
        for budget in [500, 5000, 20000, 1000000]:
            data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
            assert data["total_cost"] <= budget
            assert abs(sum(i["line_total"] for i in data["items"]) - data["total_cost"]) < 0.01
            assert abs(data["budget"] - data["total_cost"] - data["remaining_budget"]) < 0.01

    def test_quantity_never_exceeds_shortfall(self, client):
        """An item is never over-ordered beyond its shortfall."""
        data = client.get("/api/restocking/recommendations?budget=1000000").json()
        for item in data["items"]:
            assert item["quantity"] <= item["shortfall"]
            assert item["shortfall"] == item["forecasted_demand"] - item["quantity_on_hand"]

    def test_decreasing_trend_items_are_excluded(self, client):
        """Items with falling demand are not recommended."""
        data = client.get("/api/restocking/recommendations?budget=1000000").json()
        assert all(i["trend"] != "decreasing" for i in data["items"])
        assert "MTR-304" not in [i["sku"] for i in data["items"]]

    def test_items_without_shortfall_are_excluded(self, client):
        """PSU-501 has more on hand than forecast demand."""
        data = client.get("/api/restocking/recommendations?budget=1000000").json()
        assert "PSU-501" not in [i["sku"] for i in data["items"]]

    def test_larger_budget_never_recommends_fewer_units(self, client):
        """Raising the budget cannot reduce total recommended units."""
        small = client.get("/api/restocking/recommendations?budget=2000").json()
        large = client.get("/api/restocking/recommendations?budget=20000").json()
        assert sum(i["quantity"] for i in large["items"]) >= sum(i["quantity"] for i in small["items"])

    def test_increasing_trend_ranked_first(self, client):
        """With a small budget the top-ranked item is one with rising demand."""
        data = client.get("/api/restocking/recommendations?budget=3000").json()
        assert len(data["items"]) > 0
        assert data["items"][0]["trend"] == "increasing"

    def test_negative_budget_rejected(self, client):
        """A negative budget fails validation."""
        response = client.get("/api/restocking/recommendations?budget=-5")
        assert response.status_code == 422


class TestRestockOrders:
    """Test suite for submitting and listing restocking orders."""

    def _first_line(self, client):
        data = client.get("/api/restocking/recommendations?budget=1000000").json()
        item = data["items"][0]
        return {"sku": item["sku"], "quantity": item["quantity"]}, item

    def test_no_orders_initially(self, client):
        """The list starts empty."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_order(self, client):
        """Submitting an order returns 201 with server-computed price and lead time."""
        line, item = self._first_line(client)
        response = client.post("/api/restocking/orders", json={"items": [line], "budget": 1000000})
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["lead_time_days"] == item["lead_time_days"]
        assert abs(order["total_cost"] - item["line_total"]) < 0.01
        assert order["items"][0]["unit_price"] == item["unit_cost"]
        assert "T" in order["submitted_date"]
        assert "T" in order["expected_delivery"]

    def test_expected_delivery_matches_lead_time(self, client):
        """Expected delivery is submitted date plus the lead time."""
        from datetime import datetime
        line, _ = self._first_line(client)
        order = client.post("/api/restocking/orders", json={"items": [line], "budget": 1000000}).json()

        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = datetime.fromisoformat(order["expected_delivery"])
        assert (expected - submitted).days == order["lead_time_days"]

    def test_order_lead_time_is_slowest_item(self, client):
        """Order lead time is the maximum across its lines (Controllers 14d, Circuit Boards 7d)."""
        items = client.get("/api/inventory").json()
        controller = next(i for i in items if i["category"] == "Controllers")
        board = next(i for i in items if i["category"] == "Circuit Boards")
        order = client.post("/api/restocking/orders", json={
            "items": [{"sku": board["sku"], "quantity": 1}, {"sku": controller["sku"], "quantity": 1}],
            "budget": 1000000,
        }).json()
        assert order["lead_time_days"] == 14

    def test_created_order_appears_in_list_newest_first(self, client):
        """Submitted orders are listed newest first."""
        line, _ = self._first_line(client)
        first = client.post("/api/restocking/orders", json={"items": [line], "budget": 1000000}).json()
        second = client.post("/api/restocking/orders", json={"items": [line], "budget": 1000000}).json()

        listed = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in listed] == [second["id"], first["id"]]
        assert first["order_number"] != second["order_number"]

    def test_order_over_budget_rejected(self, client):
        """The server rechecks the budget using its own prices."""
        line, _ = self._first_line(client)
        response = client.post("/api/restocking/orders", json={"items": [line], "budget": 1})
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()
        assert client.get("/api/restocking/orders").json() == []

    def test_unknown_sku_rejected(self, client):
        """An unknown SKU returns 400."""
        response = client.post("/api/restocking/orders", json={
            "items": [{"sku": "NOPE-000", "quantity": 1}], "budget": 1000,
        })
        assert response.status_code == 400
        assert "unknown sku" in response.json()["detail"].lower()

    def test_empty_items_rejected(self, client):
        """An order must contain at least one line."""
        response = client.post("/api/restocking/orders", json={"items": [], "budget": 1000})
        assert response.status_code == 422

    def test_non_positive_quantity_rejected(self, client):
        """Quantities must be positive."""
        sku = client.get("/api/inventory").json()[0]["sku"]
        for qty in [0, -3]:
            response = client.post("/api/restocking/orders", json={
                "items": [{"sku": sku, "quantity": qty}], "budget": 1000000,
            })
            assert response.status_code == 422
