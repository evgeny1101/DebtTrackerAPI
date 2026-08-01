def _register_and_login(client):
    reg = client.post("/api/auth/register", json={"username": "test", "password": "secret123"})
    return reg.json()["accessToken"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_debt(client, token, **overrides):
    defaults = {"name": "Test debt", "debtType": "I_OWE", "initialAmount": 1000}
    defaults.update(overrides)
    return client.post("/api/debts", json=defaults, headers=_auth_header(token))


class TestRecordPayment:
    def test_record_payment_decreases_current_amount(self, client):
        token = _register_and_login(client)
        _create_debt(client, token)
        res = client.post(
            "/api/debts/1/payments",
            json={"amount": 400},
            headers=_auth_header(token),
        )
        assert res.status_code == 201
        assert res.json()["amount"] == 400
        assert res.json()["debtId"] == 1

        debt = client.get("/api/debts/1", headers=_auth_header(token))
        assert debt.json()["currentAmount"] == 600

    def test_record_payment_clamps_to_zero(self, client):
        token = _register_and_login(client)
        _create_debt(client, token, initialAmount=100)
        res = client.post(
            "/api/debts/1/payments",
            json={"amount": 999},
            headers=_auth_header(token),
        )
        assert res.status_code == 201

        debt = client.get("/api/debts/1", headers=_auth_header(token))
        assert debt.json()["currentAmount"] == 0

    def test_payment_on_fully_paid_debt(self, client):
        token = _register_and_login(client)
        _create_debt(client, token, initialAmount=100)
        client.post(
            "/api/debts/1/payments",
            json={"amount": 100},
            headers=_auth_header(token),
        )
        res = client.post(
            "/api/debts/1/payments",
            json={"amount": 50},
            headers=_auth_header(token),
        )
        assert res.status_code == 400
        assert res.json()["detail"] == "Долг уже полностью погашен"

    def test_payment_on_nonexistent_debt(self, client):
        token = _register_and_login(client)
        res = client.post(
            "/api/debts/999/payments",
            json={"amount": 100},
            headers=_auth_header(token),
        )
        assert res.status_code == 404

    def test_payment_on_another_users_debt(self, client):
        token1 = _register_and_login(client)
        _create_debt(client, token1, name="Alice debt")

        reg2 = client.post("/api/auth/register", json={"username": "bob2", "password": "secret123"})
        token2 = reg2.json()["accessToken"]

        res = client.post(
            "/api/debts/1/payments",
            json={"amount": 50},
            headers=_auth_header(token2),
        )
        assert res.status_code == 404

    def test_payment_with_custom_date(self, client):
        token = _register_and_login(client)
        _create_debt(client, token)
        custom_date = 900000000000
        res = client.post(
            "/api/debts/1/payments",
            json={"amount": 100, "dateMillis": custom_date},
            headers=_auth_header(token),
        )
        assert res.status_code == 201
        assert res.json()["dateMillis"] == custom_date


class TestDeletePayment:
    def test_delete_restores_current_amount(self, client):
        token = _register_and_login(client)
        _create_debt(client, token, initialAmount=500)
        client.post(
            "/api/debts/1/payments",
            json={"amount": 200},
            headers=_auth_header(token),
        )
        res = client.delete("/api/debts/1/payments/1", headers=_auth_header(token))
        assert res.status_code == 200
        data = res.json()
        assert data["amount"] == 200
        assert data["debtId"] == 1
        assert data["currentAmount"] == 500

        debt = client.get("/api/debts/1", headers=_auth_header(token))
        assert debt.json()["currentAmount"] == 500

    def test_delete_nonexistent_payment(self, client):
        token = _register_and_login(client)
        _create_debt(client, token)
        res = client.delete("/api/debts/1/payments/999", headers=_auth_header(token))
        assert res.status_code == 404


class TestListPayments:
    def test_list_payments_for_debt(self, client):
        token = _register_and_login(client)
        _create_debt(client, token, initialAmount=500)
        client.post("/api/debts/1/payments", json={"amount": 100, "dateMillis": 1000}, headers=_auth_header(token))
        client.post("/api/debts/1/payments", json={"amount": 50, "dateMillis": 2000}, headers=_auth_header(token))

        res = client.get("/api/debts/1/payments", headers=_auth_header(token))
        assert res.status_code == 200
        payments = res.json()
        assert len(payments) == 2
        assert payments[0]["dateMillis"] == 2000
        assert payments[1]["dateMillis"] == 1000

    def test_list_payments_for_nonexistent_debt(self, client):
        token = _register_and_login(client)
        res = client.get("/api/debts/999/payments", headers=_auth_header(token))
        assert res.status_code == 404

    def test_list_all_payments(self, client):
        token = _register_and_login(client)
        _create_debt(client, token, name="Debt A")
        _create_debt(client, token, name="Debt B")
        client.post("/api/debts/1/payments", json={"amount": 100}, headers=_auth_header(token))
        client.post("/api/debts/2/payments", json={"amount": 200}, headers=_auth_header(token))

        res = client.get("/api/payments", headers=_auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 2
