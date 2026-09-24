from docs.examples.grahql.app import app as graphql_app
from docs.examples.mail.app import app as mail_app
from docs.examples.Modules.app import app as modules_app

from flaxon.testing import TestClient


def test_modules_example_serves_page_and_order_api() -> None:
    client = TestClient(modules_app)

    page = client.get("/store/")
    assert page.status_code == 200
    assert "Module Store" in page.text

    products = client.get("/store/api/products")
    assert products.status_code == 200
    assert products.json()["products"][0]["name"] == "Flaxon Starter Kit"

    order = client.post(
        "/api/orders/",
        json_data={"product_id": 1, "quantity": 2, "customer_email": "ada@example.com"},
    )
    assert order.status_code == 201
    assert order.json()["total"] == 58.0


def test_mail_example_serves_form_and_validates_contact_data() -> None:
    client = TestClient(mail_app)

    assert client.get("/").status_code == 200
    sent = client.post(
        "/api/contact",
        json_data={"name": "Ada", "email": "ada@example.com", "message": "Hello"},
    )
    assert sent.status_code == 201
    assert sent.json() == {"sent": True}

    invalid = client.post(
        "/api/contact",
        json_data={"name": "Ada", "email": "not-an-email", "message": "Hello"},
    )
    assert invalid.status_code == 422


def test_graphql_example_serves_ui_playgrounds_and_query() -> None:
    client = TestClient(graphql_app)

    assert client.get("/").status_code == 200
    assert client.get("/graphql/graphiql").status_code == 200
    assert client.get("/graphql/altair").status_code == 200

    response = client.post(
        "/graphql",
        json_data={"query": "{ users { id name posts { id title } } }"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["users"][0]["posts"][0]["title"] == "First Post"
