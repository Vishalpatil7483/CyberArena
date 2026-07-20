"""Profile, leaderboard, and achievement tests."""

from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.achievement import Achievement, UserAchievement
from app.models.user import User
from app.services.achievements import evaluate_achievements
from app.services.profiles import get_profile_stats, get_user_rank
from app.services.seed import seed_achievements
from tests.test_auth import login, register
from tests.test_challenges import FLAG, auth_client, make_challenge, submit
from tests.test_labs import make_lab


def seed_achievement_rows() -> None:
    with SessionLocal() as db:
        seed_achievements(db)


def register_and_login(
    client: TestClient, username: str, email: str | None = None
) -> None:
    register(client, username=username, email=email or f"{username}@example.com")
    login(client, identifier=username)


class TestPrivateProfile:
    def test_requires_login(self, client: TestClient) -> None:
        response = client.get("/profile", headers={"accept": "application/json"})
        assert response.status_code == 401

    def test_shows_account_and_stats(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge(points=50)
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)

        response = client.get("/profile")
        assert response.status_code == 200
        assert "alice" in response.text
        assert "alice@example.com" in response.text
        assert "student" in response.text
        assert "Success rate" in response.text
        assert "Recent activity" in response.text
        assert "Test Challenge" in response.text  # activity item

    def test_success_rate_counts_all_attempts(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, "wrong-guess")
        submit(client, "test-lab", challenge_id, FLAG)

        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            stats = get_profile_stats(db, user)
        assert stats.completed_challenges == 1
        assert stats.total_attempts == 2
        assert stats.success_rate == 50


class TestPublicProfile:
    def test_shows_public_data_only(self, client: TestClient) -> None:
        register(client)
        response = client.get("/users/alice")
        assert response.status_code == 200
        assert "alice" in response.text
        assert "alice@example.com" not in response.text  # email never exposed

    def test_no_internal_ids_exposed(self, client: TestClient) -> None:
        register(client)
        with SessionLocal() as db:
            user_id = str(db.query(User).filter_by(username="alice").one().id)
        response = client.get("/users/alice")
        assert user_id not in response.text

    def test_case_insensitive_lookup(self, client: TestClient) -> None:
        register(client)
        assert client.get("/users/ALICE").status_code == 200

    def test_unknown_username_404(self, client: TestClient) -> None:
        response = client.get(
            "/users/ghost", headers={"accept": "application/json"}
        )
        assert response.status_code == 404

    def test_inactive_user_404(self, client: TestClient) -> None:
        register(client)
        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            user.is_active = False
            db.commit()
        response = client.get(
            "/users/alice", headers={"accept": "application/json"}
        )
        assert response.status_code == 404


class TestLeaderboard:
    def test_sorted_by_points_desc(self, client: TestClient) -> None:
        make_lab()
        big = make_challenge(title="Big", flag="flag-big", points=200)
        small = make_challenge(
            title="Small", flag="flag-small", points=50, order_index=2
        )

        register_and_login(client, "top_user")
        submit(client, "test-lab", big, "flag-big")
        client.post("/logout")  # session cleared server-side on next login

        register_and_login(client, "low_user")
        submit(client, "test-lab", small, "flag-small")

        response = client.get("/leaderboard")
        assert response.status_code == 200
        assert response.text.index("top_user") < response.text.index("low_user")

    def test_tiebreak_older_account_first(self, client: TestClient) -> None:
        register(client, username="older", email="older@example.com")
        register(client, username="newer", email="newer@example.com")
        response = client.get("/leaderboard")
        assert response.text.index("older") < response.text.index("newer")

    def test_highlights_current_user(self, client: TestClient) -> None:
        register_and_login(client, "me_user")
        response = client.get("/leaderboard")
        assert "You" in response.text
        assert "table-active" in response.text

    def test_excludes_inactive_users(self, client: TestClient) -> None:
        register(client, username="hidden_user", email="h@example.com")
        with SessionLocal() as db:
            user = db.query(User).filter_by(username="hidden_user").one()
            user.is_active = False
            db.commit()
        response = client.get("/leaderboard")
        assert "hidden_user" not in response.text

    def test_pagination(self, client: TestClient) -> None:
        with SessionLocal() as db:
            for i in range(30):
                db.add(
                    User(
                        username=f"user_{i:02d}",
                        email=f"user{i:02d}@example.com",
                        password_hash="x",
                    )
                )
            db.commit()

        page1 = client.get("/leaderboard")
        page2 = client.get("/leaderboard?page=2")
        assert "user_00" in page1.text
        assert "user_29" not in page1.text
        assert "user_29" in page2.text
        # out-of-range page clamps rather than erroring
        assert client.get("/leaderboard?page=999").status_code == 200

    def test_rank_calculation(self, client: TestClient) -> None:
        make_lab()
        challenge_id = make_challenge(points=100)
        register_and_login(client, "ranked_user")
        submit(client, "test-lab", challenge_id, FLAG)
        register(client, username="unranked", email="u@example.com")

        with SessionLocal() as db:
            ranked = db.query(User).filter_by(username="ranked_user").one()
            unranked = db.query(User).filter_by(username="unranked").one()
            assert get_user_rank(db, ranked) == 1
            assert get_user_rank(db, unranked) == 2


class TestAchievements:
    def test_first_blood_awarded_on_first_solve(self, client: TestClient) -> None:
        seed_achievement_rows()
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        response = submit(client, "test-lab", challenge_id, FLAG)
        follow = client.get(response.headers["location"])
        assert "First Blood" in follow.text  # flash message

        profile = client.get("/profile")
        assert "First Blood" in profile.text

    def test_lab_completion_achievements(self, client: TestClient) -> None:
        seed_achievement_rows()
        make_lab()  # category defaults to Web Security
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)

        profile = client.get("/profile")
        assert "Explorer" in profile.text
        assert "Web Apprentice" in profile.text

    def test_points_club_awarded(self, client: TestClient) -> None:
        seed_achievement_rows()
        make_lab()
        challenge_id = make_challenge(points=120)
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)

        profile = client.get("/profile")
        assert "100 Points Club" in profile.text
        assert "250 Points Club" not in profile.text

    def test_evaluation_idempotent(self, client: TestClient) -> None:
        seed_achievement_rows()
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)

        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            first = db.query(UserAchievement).filter_by(user_id=user.id).count()
            newly = evaluate_achievements(db, user.id)
            second = db.query(UserAchievement).filter_by(user_id=user.id).count()
        assert newly == []
        assert first == second

    def test_no_duplicate_achievement_records(self, client: TestClient) -> None:
        seed_achievement_rows()
        make_lab()
        challenge_id = make_challenge()
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)

        with SessionLocal() as db:
            user = db.query(User).filter_by(username="alice").one()
            pairs = [
                (ua.user_id, ua.achievement_id)
                for ua in db.query(UserAchievement).filter_by(user_id=user.id)
            ]
        assert len(pairs) == len(set(pairs))

    def test_seed_idempotent(self) -> None:
        seed_achievement_rows()
        seed_achievement_rows()
        with SessionLocal() as db:
            slugs = [a.slug for a in db.query(Achievement).all()]
        assert len(slugs) == len(set(slugs)) == 11


class TestDashboardPreview:
    def test_dashboard_shows_rank_and_top5(self, client: TestClient) -> None:
        seed_achievement_rows()
        make_lab()
        challenge_id = make_challenge(points=50)
        auth_client(client)
        submit(client, "test-lab", challenge_id, FLAG)

        response = client.get("/dashboard")
        assert response.status_code == 200
        assert "Current rank" in response.text
        assert "#1" in response.text
        assert "Top 5 defenders" in response.text
        assert "First Blood" in response.text  # latest achievement
        assert "Next up:" in response.text  # progress toward 100 Points Club
        assert "100 Points Club" in response.text
