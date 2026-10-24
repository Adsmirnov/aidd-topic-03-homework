from datetime import datetime, timezone
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from dashboard.models import Share
from dashboard.tasks import update_last_price


class DashboardTests(APITestCase):
    def setUp(self) -> None:
        self.api_user = get_user_model().objects.create_user(
            username="api-user", email="api@example.com", password="test-password"
        )
        self.apple_share = Share.objects.create(
            figi="BBG000B9XRY4",
            isin="US0378331005",
            name="Apple",
            ticker="AAPL",
            currency="usd",
            uid="a9eb4238-eba9-488c-b102-b6140fd08e38",
            last_price=100.50,
            is_trend_high=True,
        )
        self.client.force_authenticate(user=self.api_user)

        self.second_company = {
            "figi": "BBG000B9XRY5",
            "isin": "US0378331004",
            "name": "Company_test",
            "ticker": "TESTTEST",
            "currency": "usd",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e39",
            "last_price": 1.50,
            "is_trend_high": False,
        }

    def test_share_list_html(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_list(self):
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        apple_share = response.json().get("results")[0]
        self.assertEqual(apple_share["id"], self.apple_share.id)
        self.assertEqual(apple_share["figi"], self.apple_share.figi)
        self.assertEqual(apple_share["isin"], self.apple_share.isin)
        self.assertEqual(apple_share["name"], self.apple_share.name)
        self.assertEqual(apple_share["ticker"], self.apple_share.ticker)
        self.assertEqual(apple_share["currency"], self.apple_share.currency)

    def test_share_detail(self):
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.get(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_share_detail_invalid(self):
        response = self.client.get("/api/v1/shares/2/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_share_detail_html_invalid(self):
        response = self.client.get(reverse("dashboard:detail", args=[999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch(
        "dashboard.services.graph.post",
        return_value={
            "candles": [
                {
                    "time": "2026-10-24T12:00:00Z",
                    "close": {"units": 100, "nano": 250_000_000},
                }
            ]
        },
    )
    def test_share_detail_html_renders_graph(self, post_mock):
        response = self.client.get(
            reverse("dashboard:detail", args=[self.apple_share.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "plotly-graph-div")
        post_mock.assert_called_once()

    def test_api_read_is_public_and_write_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post("/api/v1/shares/", self.second_company, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_share_update(self):
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "id": share_detail["id"],
                "figi": self.apple_share.figi,
                "isin": self.apple_share.isin,
                "uid": self.apple_share.uid,
                "name": f"{self.apple_share.name}_test",
                "ticker": self.apple_share.ticker,
                "currency": self.apple_share.currency,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["figi"], self.apple_share.figi)
        self.assertEqual(body["name"], f"{self.apple_share.name}_test")

    def test_share_update_invalid(self):
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.put(
            f"/api/v1/shares/{share_detail['id']}/",
            {
                "figi": self.apple_share.figi,
                "name": f"{self.apple_share.name}_test",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_create(self):
        response = self.client.post(
            "/api/v1/shares/", self.second_company, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["figi"], self.second_company["figi"])
        self.assertEqual(body["name"], self.second_company["name"])
        self.assertEqual(body["ticker"], self.second_company["ticker"])

        response = self.client.get("/api/v1/shares/")
        self.assertEqual(len(response.data["results"]), 2)

    def test_share_create_invalid(self):
        response = self.client.post(
            "/api/v1/shares/", {"figi": "BBG000B9XRY5"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_share_delete(self):
        response = self.client.get("/api/v1/shares/")
        share_detail = response.json().get("results")[0]
        response = self.client.delete(f"/api/v1/shares/{share_detail['id']}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get("/api/v1/shares/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_share_delete_invalid(self):
        response = self.client.delete("/api/v1/shares/3/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_web_share_crud_requires_authentication(self):
        response = self.client.get(reverse("dashboard:create"))
        self.assertRedirects(response, reverse("dashboard:index"))

        self.client.force_login(self.api_user)
        share_data = {
            "figi": "BBG000B9XRY6",
            "isin": "US0378331003",
            "name": "Created Company",
            "ticker": "CREATE",
            "currency": "usd",
            "uid": "a9eb4238-eba9-488c-b102-b6140fd08e40",
        }
        response = self.client.post(reverse("dashboard:create"), share_data)
        self.assertRedirects(response, reverse("dashboard:index"))
        created_share = Share.objects.get(figi=share_data["figi"])

        share_data["name"] = "Updated Company"
        response = self.client.post(
            reverse("dashboard:update", args=[created_share.pk]), share_data
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        created_share.refresh_from_db()
        self.assertEqual(created_share.name, "Updated Company")

        response = self.client.post(reverse("dashboard:delete", args=[created_share.pk]))
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertFalse(Share.objects.filter(pk=created_share.pk).exists())

    @patch("dashboard.tasks.get_last_data", return_value=(101.25, datetime.now(timezone.utc)))
    def test_quote_update_saves_fractional_price_and_updated_at(self, get_last_data_mock):
        Share.objects.filter(pk=self.apple_share.pk).update(
            updated_at=datetime(2000, 1, 1, tzinfo=timezone.utc)
        )

        update_last_price()

        self.apple_share.refresh_from_db()
        self.assertEqual(self.apple_share.last_price, 101.25)
        self.assertTrue(self.apple_share.is_trend_high)
        self.assertGreater(self.apple_share.updated_at.year, 2000)
        get_last_data_mock.assert_called_once()

    def test_quotation_conversion_preserves_fractional_value(self):
        from dashboard.services.tinkoff_api import parse_api_datetime, quotation_to_float

        self.assertEqual(
            quotation_to_float({"units": 100, "nano": 250_000_000}), 100.25
        )
        self.assertEqual(
            parse_api_datetime("2026-10-24T12:30:00Z").utcoffset().total_seconds(), 0
        )

    def test_api_filter_limits_share_results(self):
        Share.objects.create(**self.second_company)

        response = self.client.get("/api/v1/shares/?ticker=AAPL")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["ticker"], "AAPL")

    def test_api_search_and_ordering(self):
        Share.objects.create(**self.second_company)

        search_response = self.client.get("/api/v1/shares/?search=Apple")
        order_response = self.client.get("/api/v1/shares/?ordering=ticker")

        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertEqual(search_response.data["results"][0]["ticker"], "AAPL")
        self.assertEqual(
            [share["ticker"] for share in order_response.data["results"]],
            ["AAPL", "TESTTEST"],
        )

    def test_share_is_registered_in_admin(self):
        self.assertIn(Share, admin.site._registry)

    def test_registration_success_creates_user_and_starts_session(self):
        response = self.client.post(
            reverse("user:registration"),
            {
                "email": "NEW.USER@example.com",
                "password1": "Strong-test-password-42",
                "password2": "Strong-test-password-42",
            },
        )

        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertTrue(get_user_model().objects.filter(username="new.user@example.com").exists())

    @patch("dashboard.services.tinkoff_api.TINKOFF_TOKEN", "test-token")
    @patch("dashboard.services.tinkoff_api.requests.post")
    def test_tinkoff_request_uses_bearer_token_and_timeout(self, request_mock):
        request_mock.return_value.json.return_value = {"instruments": []}

        from dashboard.services.tinkoff_api import post

        response = post("InstrumentsService/Shares", {})

        self.assertEqual(response, {"instruments": []})
        self.assertEqual(
            request_mock.call_args.kwargs["headers"]["Authorization"],
            "Bearer test-token",
        )
        self.assertEqual(request_mock.call_args.kwargs["timeout"], (5, 30))

    @patch(
        "dashboard.management.commands.add_shares.post",
        return_value={
            "instruments": [
                {
                    "figi": "BBG000B9XRY7",
                    "isin": "US0378331002",
                    "name": "Imported Company",
                    "ticker": "IMPORT",
                    "currency": "usd",
                    "uid": "a9eb4238-eba9-488c-b102-b6140fd08e41",
                }
            ]
        },
    )
    def test_add_shares_imports_instruments(self, post_mock):
        call_command("add_shares")

        self.assertTrue(Share.objects.filter(figi="BBG000B9XRY7").exists())
        post_mock.assert_called_once()

    def test_auth_with_missing_fields_renders_form_errors(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse("user:auth"), {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_registration_with_missing_fields_renders_form_errors(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse("user:registration"), {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_successful_login_and_logout(self):
        get_user_model().objects.create_user(
            username="login@example.com",
            email="login@example.com",
            password="test-password",
        )

        response = self.client.post(
            reverse("user:auth"),
            {"email": "login@example.com", "password": "test-password"},
        )
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertIn("_auth_user_id", self.client.session)

        response = self.client.get(reverse("user:logout"))
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertNotIn("_auth_user_id", self.client.session)
