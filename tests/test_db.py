import os
import pytest
import sys
sys.path.insert(0, ".")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", str(tmp_path / "test.db"))
    import db
    db.init_db()
    return db


def test_add_and_get_mentor(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    assert mentor["name"] == "Alice"
    assert mentor["email"] == "alice@example.com"
    assert len(mentor["dashboard_token"]) > 8
    fetched = db.get_mentor_by_id(mentor["id"])
    assert fetched["name"] == "Alice"


def test_add_and_get_student(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    assert student["name"] == "Bob"
    fetched = db.get_student_by_id(student["id"])
    assert fetched["mentor_id"] == mentor["id"]


def test_create_and_update_assessment(isolated_db):
    db = isolated_db
    import json
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    ratings = json.dumps({"Communication": 4})
    reflections = json.dumps({"What went well?": "Everything"})
    assessment = db.create_assessment(student["id"], 1, ratings, reflections)
    assert assessment["status"] == "submitted"
    assert assessment["student_token"] is not None
    assert assessment["mentor_token"] is not None
    db.update_assessment(assessment["id"], status="complete", transcript="Hello world")
    updated = db.get_assessment_by_id(assessment["id"])
    assert updated["status"] == "complete"
    assert updated["transcript"] == "Hello world"


def test_get_assessments_by_mentor(isolated_db):
    db = isolated_db
    import json
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    db.create_assessment(student["id"], 1, "{}", "{}")
    db.create_assessment(student["id"], 2, "{}", "{}")
    rows = db.get_assessments_by_mentor(mentor["id"])
    assert len(rows) == 2


def test_ai_review_and_mentor_feedback(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    assessment = db.create_assessment(student["id"], 1, "{}", "{}")
    db.save_ai_review(assessment["id"], "Great job!")
    review = db.get_ai_review(assessment["id"])
    assert review["content"] == "Great job!"
    db.save_mentor_feedback(assessment["id"], "Keep it up")
    feedback = db.get_mentor_feedback(assessment["id"])
    assert feedback["feedback_text"] == "Keep it up"


def test_get_all_assessments(isolated_db):
    db = isolated_db
    mentor = db.add_mentor("Alice", "alice@example.com")
    student = db.add_student("Bob", mentor["id"])
    db.create_assessment(student["id"], 1, "{}", "{}")
    rows = db.get_all_assessments()
    assert len(rows) == 1
    assert rows[0]["student_name"] == "Bob"
    assert rows[0]["mentor_name"] == "Alice"
