def test_regular_user_cannot_create_origin(client, login_as):
    login_as(username="bob", role="user")
    response = client.post("/api/destinations", json={"name": "Matriz"})
    assert response.status_code == 403


def test_regular_user_cannot_edit_or_delete_origin(client, login_as):
    login_as()
    origin = client.post("/api/destinations", json={"name": "Matriz"}).json()
    login_as(username="bob", role="user")
    assert client.put(f"/api/destinations/{origin['id']}", json={"name": "Otra"}).status_code == 403
    assert client.delete(f"/api/destinations/{origin['id']}").status_code == 403


def test_regular_user_can_list_origins_and_owners(client, login_as):
    login_as(username="bob", role="user")
    assert client.get("/api/destinations").status_code == 200
    assert client.get("/api/owners").status_code == 200


def test_document_type_endpoints_are_removed(client, login_as):
    login_as()
    assert client.get("/api/document-types").status_code == 404
    assert client.post("/api/document-types", json={"name": "Contrato"}).status_code == 404


def test_origin_accepts_optional_parent(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "Matriz"}).json()
    branch = client.post("/api/destinations", json={"name": "Sucursal Norte", "parent_id": root["id"]}).json()

    assert branch["depth"] == 1
    assert branch["path"] == "Matriz / Sucursal Norte"


def test_rename_origin_keeps_parent(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "Matriz"}).json()
    branch = client.post("/api/destinations", json={"name": "Norte", "parent_id": root["id"]}).json()

    renamed = client.put(f"/api/destinations/{branch['id']}", json={"name": "Sucursal Norte"}).json()
    assert renamed["parent_id"] == root["id"]
    assert renamed["name"] == "Sucursal Norte"


def test_origin_cannot_be_moved_under_its_descendant(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "A"}).json()
    child = client.post("/api/destinations", json={"name": "B", "parent_id": root["id"]}).json()
    response = client.put(f"/api/destinations/{root['id']}", json={"name": "A", "parent_id": child["id"]})
    assert response.status_code == 400


def test_delete_origin_with_children_returns_409(client, login_as):
    login_as()
    root = client.post("/api/destinations", json={"name": "Matriz"}).json()
    client.post("/api/destinations", json={"name": "Norte", "parent_id": root["id"]})
    assert client.delete(f"/api/destinations/{root['id']}").status_code == 409


def test_delete_empty_origin(client, login_as):
    login_as()
    origin = client.post("/api/destinations", json={"name": "Temporal"}).json()
    assert client.delete(f"/api/destinations/{origin['id']}").status_code == 204
    assert client.get("/api/destinations").json() == []
