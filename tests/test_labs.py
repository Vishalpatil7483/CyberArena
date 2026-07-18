"""Lab browsing, progress, and dashboard statistics tests."""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.lab import Lab, LabDifficulty, ProgressStatus, UserLabProgress
from tests.test_auth import get_csrf, login, register


def make_lab(
    slug: str = "test-lab",
    title: str = "Test Lab",
    active: bool = True,
    points: int = 100,
) -> None:
    """Insert a lab directly for tests."""
    with SessionLocal() as db:
        db.add(
            Lab(
                title=title,
                slug=slug,
                description="A lab used by the test suite.",
                difficulty=LabDifficulty.EASY,
                category="Web Security",
                estimated_time_minutes=30,
                points=points,
                is_active=active,
            )
        )
        db.commit()


def auth_client(client: TestClient) -> TestClient:
    """Register and sign in the default test user."""
    register(client)
    login(client)
    return client


def start_lab(client: TestClient, slug: str = "test-lab"):
    token = get_csrf(client, f"/labs/{slug}")
    return client.post(
        f"/labs/{slug}/start",
        data={"csrf_token": token},
        follow_redirects=False,
    )


def complete_lab(client: TestClient, slug: str = "test-lab"):
    token = get_csrf(client, f"/labs/{slug}")
    return client.post(
        f"/labs/{slug}/complete",
        data={"csrf_token": token},
        follow_redirects=False,
    )


def progress_count(slug: str = "test-lab") -> int:
    with SessionLocal() as db:
        lab = db.query(Lab).filter_by(slug=slug).one()
        return db.query(UserLabProgress).filter_by(lab_id=lab.id).count()


class TestLabListing:
    def test_lists_active_labs(self, client: TestClient) -> None:
        make_lab(slug="lab-one", title="Alpha Lab")
        make_lab(slug="lab-two", title="Beta Lab")
        response = client.get("/labs")
        assert response.status_code == 200
        assert "Alpha Lab" in response.text
        assert "Beta Lab" in response.text

    def test_inactive_labs_hidden(self, client: TestClient) -> None:
        make_lab(slug="hidden-lab", title="Hidden Lab", active=False)
        response = client.get("/labs")
        assert response.status_code == 200
        assert "Hidden Lab" not in response.text

    def test_anonymous_can_browse(self, client: TestClient) -> None:
        make_lab()
        assert client.get("/labs").status_code == 200
        assert client.get("/labs/test-lab").status_code == 200


class TestLabDetail:
    def test_shows_lab_fields(self, client: TestClient) -> None:
        make_lab(title="Detail Lab", points=250)
        response = client.get("/labs/test-lab")
        assert response.status_code == 200
        assert "Detail Lab" in response.text
        assert "250 pts" in response.text
        assert "Web Security" in response.text
        assert "Easy" in response.text
        assert "30 min" in response.text

    def test_invalid_slug_404(self, client: TestClient) -> None:
        response = client.get(
            "/labs/no-such-lab", headers={"accept": "application/json"}
        )
        assert response.status_code == 404

    def test_inactive_lab_404(self, client: TestClient) -> None:
        make_lab(slug="inactive", active=False)
        response = client.get(
            "/labs/inactive", headers={"accept": "application/json"}
        )
        assert response.status_code == 404

    def test_anonymous_sees_sign_in_prompt(self, client: TestClient) -> None:
        make_lab()
        response = client.get("/labs/test-lab")
        assert "Sign in to start this lab" in response.text


class TestStartLab:
    def test_requires_login(self, client: TestClient) -> None:
        make_lab()
        response = client.post(
            "/labs/test-lab/start",
            data={"csrf_token": "x"},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 401

    def test_start_creates_progress(self, client: TestClient) -> None:
        make_lab()
        auth_client(client)
        response = start_lab(client)
        assert response.status_code == 303
        assert response.headers["location"] == "/labs/test-lab"
        assert progress_count() == 1

        detail = client.get("/labs/test-lab")
        assert "In progress" in detail.text
        assert "Mark completed" in detail.text

    def test_duplicate_start_prevented(self, client: TestClient) -> None:
        make_lab()
        auth_client(client)
        start_lab(client)
        start_lab(client)
        assert progress_count() == 1

    def test_start_unknown_lab_404(self, client: TestClient) -> None:
        auth_client(client)
        token = get_csrf(client, "/labs")
        response = client.post(
            "/labs/ghost/start",
            data={"csrf_token": token},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 404


class TestCompleteLab:
    def test_requires_login(self, client: TestClient) -> None:
        make_lab()
        response = client.post(
            "/labs/test-lab/complete",
            data={"csrf_token": "x"},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 401

    def test_complete_marks_completed(self, client: TestClient) -> None:
        make_lab()
        auth_client(client)
        start_lab(client)
        response = complete_lab(client)
        assert response.status_code == 303

        with SessionLocal() as db:
            progress = db.query(UserLabProgress).one()
            assert progress.status == ProgressStatus.COMPLETED
            assert progress.completed_at is not None
            assert progress.started_at is not None

        detail = client.get("/labs/test-lab")
        assert "Completed" in detail.text

    def test_complete_without_start_creates_single_record(
        self, client: TestClient
    ) -> None:
        make_lab()
        auth_client(client)
        complete_lab(client)
        assert progress_count() == 1
        with SessionLocal() as db:
            assert db.query(UserLabProgress).one().status == ProgressStatus.COMPLETED

    def test_complete_is_idempotent(self, client: TestClient) -> None:
        make_lab()
        auth_client(client)
        complete_lab(client)
        with SessionLocal() as db:
            first_completed_at = db.query(UserLabProgress).one().completed_at
        complete_lab(client)
        assert progress_count() == 1
        with SessionLocal() as db:
            assert db.query(UserLabProgress).one().completed_at == first_completed_at


class TestProgressPersistence:
    def test_progress_survives_logout_login(self, client: TestClient) -> None:
        make_lab()
        auth_client(client)
        complete_lab(client)

        token = get_csrf(client, "/dashboard")
        client.post("/logout", data={"csrf_token": token}, follow_redirects=False)
        login(client)

        detail = client.get("/labs/test-lab")
        assert "Completed" in detail.text


class TestDashboardStats:
    def test_stats_shown(self, client: TestClient) -> None:
        make_lab(slug="lab-a", title="Lab A")
        make_lab(slug="lab-b", title="Lab B")
        make_lab(slug="lab-c", title="Lab C")
        make_lab(slug="lab-d", title="Lab D")
        auth_client(client)
        complete_lab(client, "lab-a")
        start_lab(client, "lab-b")

        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Total labs" in response.text
        assert "25%" in response.text  # 1 of 4 completed

    def test_stats_ignore_inactive_labs(self, client: TestClient) -> None:
        make_lab(slug="active-lab")
        make_lab(slug="gone-lab", active=False)
        auth_client(client)
        complete_lab(client, "active-lab")

        response = client.get("/dashboard")
        assert "100%" in response.text

    def test_zero_labs_no_division_error(self, client: TestClient) -> None:
        auth_client(client)
        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "0%" in response.text
