import sys
sys.path.insert(0, ".")
import db


def seed():
    db.init_db()

    mentors_data = [
        ("Michael", "michael@upbuild.com"),
        ("Vipin", "vipin@example.com"),
    ]

    existing_mentors = {m["name"]: m for m in db.get_mentors()}
    mentor_ids = {}

    for name, email in mentors_data:
        if name not in existing_mentors:
            m = db.add_mentor(name, email)
            mentor_ids[name] = m["id"]
            print(f"Created mentor: {name} (dashboard_token: {m['dashboard_token']})")
        else:
            mentor_ids[name] = existing_mentors[name]["id"]
            print(f"Mentor already exists: {name}")

    students_data = [
        ("Student 1", "Michael"),
        ("Student 2", "Vipin"),
    ]

    existing_students = {s["name"]: s for s in db.get_students()}

    for name, mentor_name in students_data:
        if name not in existing_students:
            s = db.add_student(name, mentor_ids[mentor_name])
            print(f"Created student: {name} (mentor: {mentor_name})")
        else:
            print(f"Student already exists: {name}")


if __name__ == "__main__":
    seed()
    print("Seeding complete.")
