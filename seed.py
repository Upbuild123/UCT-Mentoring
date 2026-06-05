import sys
sys.path.insert(0, ".")
import db


MENTORS = [
    ("Gina Kellogg", "gina@upbuild.com"),
    ("Michael Sloyer", "michael@upbuild.com"),
    ("Mary Kuentz", "mary@upbuild.com"),
    ("Vipin Goyal", "vipin@upbuild.com"),
    ("Melissa Arthur", "melissa@upbuild.com"),
    ("Tzipi Weiss", "tzipi@upbuild.com"),
]


def seed():
    db.init_db()

    existing_mentors = {m["email"]: m for m in db.get_mentors()}

    for name, email in MENTORS:
        if email not in existing_mentors:
            m = db.add_mentor(name, email)
            print(f"Created mentor: {name} (token: {m['dashboard_token']})")
        else:
            m = existing_mentors[email]
            db.update_mentor(m["id"], name, email)
            print(f"Updated mentor: {name}")


if __name__ == "__main__":
    seed()
    print("Done.")
