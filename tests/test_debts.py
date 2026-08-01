def _register_and_login(client):
    reg = client.post("/api/auth/register", json={"username": "test", "password": "secret123"})
    return reg.json()["accessToken"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestCreateDebt:
    def test_create_with_all_fields(self, client):
        token = _register_and_login(client)
        res = client.post(
            "/api/debts",
            json={
                "name": "Coffee",
                "debtType": "I_OWE",
                "initialAmount": 500,
                "createdAt": 1000000000000,
                "reminderIntervalDays": 7,
            },
            headers=_auth_header(token),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Coffee"
        assert data["type"] == "I_OWE"
        assert data["initialAmount"] == 500
        assert data["currentAmount"] == 500
        assert data["createdAt"] == 1000000000000
        assert data["reminderIntervalDays"] == 7
        assert data["lastReminderTimestamp"] is None

    def test_create_defaults(self, client):
        token = _register_and_login(client)
        res = client.post(
            "/api/debts",
            json={"name": "Lunch", "debtType": "OWE_ME", "initialAmount": 1000},
            headers=_auth_header(token),
        )
        assert res.status_code == 201
        data = res.json()
        assert data["currentAmount"] == data["initialAmount"] == 1000
        assert data["reminderIntervalDays"] is None
        assert data["createdAt"] > 0

    def test_create_owe_me_type(self, client):
        token = _register_and_login(client)
        res = client.post(
            "/api/debts",
            json={"name": "Loan", "debtType": "OWE_ME", "initialAmount": 2000},
            headers=_auth_header(token),
        )
        assert res.status_code == 201
        assert res.json()["type"] == "OWE_ME"


class TestListDebts:
    def test_list_empty(self, client):
        token = _register_and_login(client)
        res = client.get("/api/debts", headers=_auth_header(token))
        assert res.status_code == 200
        assert res.json() == []

    def test_list_all(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "A", "debtType": "I_OWE", "initialAmount": 100},
            headers=_auth_header(token),
        )
        client.post(
            "/api/debts",
            json={"name": "B", "debtType": "OWE_ME", "initialAmount": 200},
            headers=_auth_header(token),
        )
        res = client.get("/api/debts", headers=_auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_list_active_only(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "Paid", "debtType": "I_OWE", "initialAmount": 100},
            headers=_auth_header(token),
        )
        client.post(
            "/api/debts",
            json={"name": "Unpaid", "debtType": "I_OWE", "initialAmount": 200},
            headers=_auth_header(token),
        )
        client.post(
            "/api/debts/1/payments",
            json={"amount": 100},
            headers=_auth_header(token),
        )
        res = client.get("/api/debts?active=true", headers=_auth_header(token))
        assert res.status_code == 200
        debts = res.json()
        assert len(debts) == 1
        assert debts[0]["name"] == "Unpaid"


class TestGetDebt:
    def test_get_own_debt(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "Test", "debtType": "I_OWE", "initialAmount": 50},
            headers=_auth_header(token),
        )
        res = client.get("/api/debts/1", headers=_auth_header(token))
        assert res.status_code == 200
        assert res.json()["name"] == "Test"

    def test_get_nonexistent(self, client):
        token = _register_and_login(client)
        res = client.get("/api/debts/999", headers=_auth_header(token))
        assert res.status_code == 404

    def test_get_another_users_debt(self, client):
        token1 = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "Alice debt", "debtType": "I_OWE", "initialAmount": 100},
            headers=_auth_header(token1),
        )

        reg2 = client.post("/api/auth/register", json={"username": "bob2", "password": "secret123"})
        token2 = reg2.json()["accessToken"]

        res = client.get("/api/debts/1", headers=_auth_header(token2))
        assert res.status_code == 404


class TestUpdateDebt:
    def test_full_update_recalculates_current_amount(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "Original", "debtType": "I_OWE", "initialAmount": 1000},
            headers=_auth_header(token),
        )
        client.post(
            "/api/debts/1/payments",
            json={"amount": 300},
            headers=_auth_header(token),
        )

        res = client.put(
            "/api/debts/1",
            json={
                "name": "Updated",
                "initialAmount": 2000,
                "reminderIntervalDays": 14,
            },
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Updated"
        assert data["initialAmount"] == 2000
        assert data["currentAmount"] == 1700
        assert data["reminderIntervalDays"] == 14

    def test_update_nonexistent(self, client):
        token = _register_and_login(client)
        res = client.put(
            "/api/debts/999",
            json={"name": "Ghost", "initialAmount": 100},
            headers=_auth_header(token),
        )
        assert res.status_code == 404

    def test_type_not_changed_on_update(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "Type test", "debtType": "I_OWE", "initialAmount": 100},
            headers=_auth_header(token),
        )
        res = client.put(
            "/api/debts/1",
            json={"name": "Still I_OWE", "initialAmount": 200},
            headers=_auth_header(token),
        )
        assert res.json()["type"] == "I_OWE"


class TestPatchCurrentAmount:
    def test_patch_current_amount(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "Patchable", "debtType": "I_OWE", "initialAmount": 500},
            headers=_auth_header(token),
        )
        res = client.patch(
            "/api/debts/1/current-amount",
            json={"amount": 42},
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        assert res.json()["currentAmount"] == 42


class TestPatchReminderTimestamp:
    def test_patch_reminder_timestamp(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={
                "name": "RemindMe",
                "debtType": "I_OWE",
                "initialAmount": 100,
                "reminderIntervalDays": 3,
            },
            headers=_auth_header(token),
        )
        ts = 1785700000000
        res = client.patch(
            "/api/debts/1/reminder-timestamp",
            json={"timestamp": ts},
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        assert res.json()["lastReminderTimestamp"] == ts


class TestDeleteDebt:
    def test_delete_cascades_payments(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "ToDelete", "debtType": "I_OWE", "initialAmount": 300},
            headers=_auth_header(token),
        )
        client.post(
            "/api/debts/1/payments",
            json={"amount": 100},
            headers=_auth_header(token),
        )
        res = client.delete("/api/debts/1", headers=_auth_header(token))
        assert res.status_code == 204

        payments = client.get("/api/payments", headers=_auth_header(token))
        assert payments.json() == []

    def test_delete_nonexistent(self, client):
        token = _register_and_login(client)
        res = client.delete("/api/debts/999", headers=_auth_header(token))
        assert res.status_code == 404


class TestReminders:
    def test_with_reminders(self, client):
        token = _register_and_login(client)
        client.post(
            "/api/debts",
            json={"name": "NoReminder", "debtType": "I_OWE", "initialAmount": 100},
            headers=_auth_header(token),
        )
        client.post(
            "/api/debts",
            json={
                "name": "WithReminder",
                "debtType": "I_OWE",
                "initialAmount": 200,
                "reminderIntervalDays": 7,
            },
            headers=_auth_header(token),
        )
        res = client.get("/api/debts/with-reminders", headers=_auth_header(token))
        assert res.status_code == 200
        debts = res.json()
        assert len(debts) == 1
        assert debts[0]["name"] == "WithReminder"
