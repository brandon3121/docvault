def test_regular_user_cannot_create_destination(client, login_as):
    login_as(username="bob", role="user")
    response = client.post("/api/destinations", json={"name": "Archivo"})
    assert response.status_code == 403


def test_regular_user_can_list_catalogs(client, login_as):
    login_as(username="bob", role="user")
    assert client.get("/api/destinations").status_code == 200
    assert client.get("/api/document-types").status_code == 200
    assert client.get("/api/owners").status_code == 200


def test_destinations_are_returned_as_tree(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "Finanzas"}).json()
    child = client.post("/api/destinations", json={"name": "Facturas", "parent_id": root["id"]}).json()

    assert child["depth"] == 1
    assert child["path"] == "Finanzas / Facturas"
    names = [item["name"] for item in client.get("/api/destinations").json()]
    assert names == ["Finanzas", "Facturas"]


def test_destination_cannot_be_moved_under_its_descendant(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "A"}).json()
    child = client.post("/api/destinations", json={"name": "B", "parent_id": root["id"]}).json()
    response = client.put(f"/api/destinations/{root['id']}", json={"name": "A", "parent_id": child["id"]})
    assert response.status_code == 400


def test_duplicate_document_type_returns_409(client, login_as):
    login_as()
    assert client.post("/api/document-types", json={"name": "Contrato"}).status_code == 201
    assert client.post("/api/document-types", json={"name": "contrato"}).status_code == 409


def test_owner_search_ignores_accents_and_case(client, login_as):
    login_as()
    client.post("/api/owners", json={"full_name": "José Pérez"})
    client.post("/api/owners", json={"full_name": "Ana Gómez"})

    results = client.get("/api/owners", params={"q": "PEREZ"}).json()
    assert [owner["full_name"] for owner in results] == ["José Pérez"]


def test_owner_search_is_limited_to_20(client, login_as):
    login_as()
    for index in range(25):
        client.post("/api/owners", json={"full_name": f"Persona {index:02d}"})
    assert len(client.get("/api/owners", params={"q": "persona"}).json()) == 20
