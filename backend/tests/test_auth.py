from tests.conftest import login


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_and_me(client):
    headers = login(client, "admin@test.local", "admin-pass")
    me = client.get("/api/auth/me", headers=headers).json()
    assert me["email"] == "admin@test.local"
    assert me["role"] == "admin"


def test_login_is_case_insensitive(client):
    login(client, "ADMIN@test.local", "admin-pass")


def test_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "nope"})
    assert r.status_code == 401


def test_protected_routes_require_token(client):
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/chat", json={"question": "x"}).status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert client.get("/api/auth/me", headers=bad).status_code == 401


def test_only_admin_can_upload_and_manage_users(client, seeded):
    chloe = seeded["chloe"]
    r = client.post(
        "/api/documents",
        files={"file": ("x.md", b"contenu", "text/markdown")},
        headers=chloe,
    )
    assert r.status_code == 403
    assert client.get("/api/admin/users", headers=chloe).status_code == 403


def test_duplicate_user_and_invalid_group(client, admin_headers):
    body = {"email": "dup@test.local", "password": "secret123"}
    assert client.post("/api/admin/users", json=body, headers=admin_headers).status_code == 201
    assert client.post("/api/admin/users", json=body, headers=admin_headers).status_code == 409
    bad = {"email": "x@test.local", "password": "secret123", "groups": ["Bad Group!"]}
    assert client.post("/api/admin/users", json=bad, headers=admin_headers).status_code == 422


def test_admin_cannot_demote_or_delete_self(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert (
        client.patch(f"/api/admin/users/{me['id']}", json={"role": "user"}, headers=admin_headers).status_code
        == 400
    )
    assert client.delete(f"/api/admin/users/{me['id']}", headers=admin_headers).status_code == 400


def test_upload_validation(client, admin_headers):
    r = client.post(
        "/api/documents",
        files={"file": ("photo.png", b"\x89PNG", "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 415
    r = client.post(
        "/api/documents",
        files={"file": ("empty.md", b"   ", "text/markdown")},
        headers=admin_headers,
    )
    assert r.status_code == 422
    r = client.post(
        "/api/documents",
        files={"file": ("ok.md", b"Bonjour", "text/markdown")},
        data={"allowed_groups": "Bad Group!"},
        headers=admin_headers,
    )
    assert r.status_code == 422
