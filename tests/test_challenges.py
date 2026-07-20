"""Challenge engine tests: flag submission, points, lab auto-completion."""

import uuid

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.core.security import hash_flag, verify_flag
from app.models.challenge import Challenge, ChallengeType, UserChallengeProgress
from app.models.lab import Lab, ProgressStatus, UserLabProgress
from app.models.user import User
from tests.test_auth import get_csrf, login, register
from tests.test_labs import make_lab

FLAG = "CTF{test_flag_value}"


def make_challenge(
    lab_slug: str = "test-lab",
    title: str = "Test Challenge",
    flag: str = FLAG,
    points: int = 50,
    order_index: int = 1,
    active: bool = True,
) -> str:
    """Insert a challenge for tests; returns its id as a string."""
    with SessionLocal() as db:
        lab = db.query(Lab).filter_by(slug=lab_slug).one()
        challenge = Challenge(
            lab_id=lab.id,
            title=title,
            description="A challenge used by the test suite.",
            challenge_type=ChallengeType.FLAG,
            points=points,
            flag_hash=hash_flag(flag),
            order_index=order_index,
            hint="Test hint text.",
            is_active=active,
        )
        db.add(challenge)
        db.commit()
        return str(challenge.id)


def submit(
    client: TestClient, lab_slug: str, challenge_id: str, flag: str
):
    token = get_csrf(client, f"/labs/{lab_slug}/challenge/{challenge_id}")
    return client.post(
        f"/labs/{lab_slug}/challenge/{challenge_id}/submit",
        data={"flag": flag, "csrf_token": token},
        follow_redirects=False,
    )


def auth_client(client: TestClient) -> None:
    register(client)
    login(client)


def get_progress(challenge_id: str) -> UserChallengeProgress | None:
    with SessionLocal() as db:
        return (
            db.query(UserChallengeProgress)
            .filter_by(challenge_id=uuid.UUID(challenge_id))
            .one_or_none()
        )


class TestFlagHelpers:
    def test_flag_not_stored_plaintext(self) -> None:
        hashed = hash_flag(FLAG)
        assert FLAG not in hashed
        assert hashed.startswith("$2b$")

    def test_verify_trims_whitespace(self) -> None:
        hashed = hash_flag(f"  {FLAG}  ")
        assert verify_flag(FLAG, hashed)
        assert verify_flag(f"  {FLAG}\n", hashed)

    def test_verify_case_sensitive(self) -> None:
        hashed = hash_flag(FLAG)
        assert not verify_flag(FLAG.lower(), hashed)


class TestChallengePage:
    def test_challenge_page_renders(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        response = client.get(f"/labs/test-lab/challenge/{challenge_id}")
        assert response.status_code == 200
        assert "Test Challenge" in response.text
        assert "Challenge 1 of 1" in response.text
        assert "50 pts" in response.text
        assert "Test hint text." in response.text

    def test_flag_hash_never_exposed(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        response = client.get(f"/labs/test-lab/challenge/{challenge_id}")
        assert "$2b$" not in response.text

    def test_lab_detail_lists_challenges(self, client: TestClient) -> None:
        make_lab()
        make_challenge()
        response = client.get("/labs/test-lab")
        assert "Test Challenge" in response.text

    def test_invalid_challenge_id_404(self, client: TestClient) -> None:
        make_lab()
        for bad in (str(uuid.uuid4()), "not-a-uuid"):
            response = client.get(
                f"/labs/test-lab/challenge/{bad}",
                headers={"accept": "application/json"},
            )
            assert response.status_code == 404

    def test_invalid_lab_404(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        response = client.get(
            f"/labs/no-such-lab/challenge/{challenge_id}",
            headers={"accept": "application/json"},
        )
        assert response.status_code == 404

    def test_challenge_from_other_lab_404(self, client: TestClient) -> None:
        make_lab()
        make_lab(slug="other-lab", title="Other Lab")
        challenge_id = make_challenge(lab_slug="other-lab")
        response = client.get(
            f"/labs/test-lab/challenge/{challenge_id}",
            headers={"accept": "application/json"},
        )
        assert response.status_code == 404

    def test_inactive_challenge_404(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge(active=False)
        response = client.get(
            f"/labs/test-lab/challenge/{challenge_id}",
            headers={"accept": "application/json"},
        )
        assert response.status_code == 404


class TestSubmission:
    def test_unauthorized_submission_401(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        response = client.post(
            f"/labs/test-lab/challenge/{challenge_id}/submit",
            data={"flag": FLAG},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 401

    def test_correct_flag(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        response = submit(client, "test-lab", challenge_id, FLAG)
        assert response.status_code == 303

        follow = client.get(response.headers["location"])
        assert "Correct!" in follow.text
        progress = get_progress(challenge_id)
        assert progress is not None
        assert progress.is_completed
        assert progress.attempts == 1
        assert progress.completed_at is not None

    def test_correct_flag_with_whitespace(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, f"  {FLAG} ")
        assert get_progress(challenge_id).is_completed

    def test_incorrect_flag(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        response = submit(client, "test-lab", challenge_id, "CTF{wrong}")
        follow = client.get(response.headers["location"])
        assert "Incorrect flag" in follow.text
        progress = get_progress(challenge_id)
        assert not progress.is_completed
        assert progress.attempts == 1

    def test_attempts_increment(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, "wrong-1")
        submit(client, "test-lab", challenge_id, "wrong-2")
        submit(client, "test-lab", challenge_id, FLAG)
        progress = get_progress(challenge_id)
        assert progress.attempts == 3
        assert progress.is_completed

    def test_duplicate_submission_no_extra_award(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)
        # Second submit after completion: attempts frozen, still completed.
        response = client.post(
            f"/labs/test-lab/challenge/{challenge_id}/submit",
            data={
                "flag": FLAG,
                "csrf_token": get_csrf(client, "/labs/test-lab"),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        progress = get_progress(challenge_id)
        assert progress.attempts == 1
        assert progress.is_completed

    def test_missing_csrf_rejected(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        client.post(
            f"/labs/test-lab/challenge/{challenge_id}/submit",
            data={"flag": FLAG},
            follow_redirects=False,
        )
        progress = get_progress(challenge_id)
        assert progress is None or not progress.is_completed


class TestLabAutoCompletion:
    def test_lab_completes_when_all_challenges_done(
        self, client: TestClient
    ) -> None:
        make_lab()
        first = make_challenge(title="First", flag="flag-1", order_index=1)
        second = make_challenge(title="Second", flag="flag-2", order_index=2)
        auth_client(client)

        submit(client, "test-lab", first, "flag-1")
        with SessionLocal() as db:
            lab_progress = db.query(UserLabProgress).one()
            assert lab_progress.status == ProgressStatus.IN_PROGRESS

        response = submit(client, "test-lab", second, "flag-2")
        follow = client.get(response.headers["location"])
        assert "lab completed" in follow.text

        with SessionLocal() as db:
            lab_progress = db.query(UserLabProgress).one()
            assert lab_progress.status == ProgressStatus.COMPLETED
            assert lab_progress.completed_at is not None

    def test_completion_idempotent(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)
        with SessionLocal() as db:
            first_completed_at = db.query(UserLabProgress).one().completed_at

        submit(client, "test-lab", challenge_id, FLAG)
        with SessionLocal() as db:
            assert db.query(UserLabProgress).one().completed_at == first_completed_at

    def test_partial_completion_leaves_lab_in_progress(
        self, client: TestClient
    ) -> None:
        make_lab()
        first = make_challenge(title="First", flag="flag-1")
        make_challenge(title="Second", flag="flag-2", order_index=2)
        auth_client(client)
        submit(client, "test-lab", first, "flag-1")
        with SessionLocal() as db:
            assert db.query(UserLabProgress).one().status == ProgressStatus.IN_PROGRESS


class TestDashboardStats:
    def test_dashboard_shows_challenge_stats(self, client: TestClient) -> None:
        make_lab()
        first = make_challenge(title="First", flag="flag-1", points=70)
        make_challenge(title="Second", flag="flag-2", points=30, order_index=2)
        auth_client(client)
        submit(client, "test-lab", first, "flag-1")

        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Points earned" in response.text
        assert ">70<" in response.text  # points from the solved challenge
        assert "Challenges solved" in response.text

    def test_points_awarded_once(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge(points=50)
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)
        submit(client, "test-lab", challenge_id, FLAG)

        from app.services.challenges import get_challenge_stats

        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            stats = get_challenge_stats(db, user.id)
        assert stats.points_earned == 50
        assert stats.completed == 1
