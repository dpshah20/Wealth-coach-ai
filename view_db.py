import argparse
import sqlite3
from pathlib import Path


def print_header(title: str) -> None:
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick SQLite viewer for wealth_coach.db")
    parser.add_argument("--db", default="instance/wealth_coach.db", help="Path to sqlite DB file")
    parser.add_argument("--limit", type=int, default=10, help="Rows to show for message previews")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database file not found: {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print_header("DATABASE INFO")
    print(f"DB Path: {db_path.resolve()}")

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cur.fetchall()]
    print(f"Tables: {', '.join(tables) if tables else 'None'}")

    print_header("USER SUMMARY")
    cur.execute(
        """
        SELECT id, first_name, surname, email, age, onboarding_completed, created_at
        FROM user_profiles
        ORDER BY id
        """
    )
    users = cur.fetchall()
    print(f"Total Users: {len(users)}")
    for user in users:
        name = f"{user['first_name'] or ''} {user['surname'] or ''}".strip() or "(no name)"
        print(
            f"- id={user['id']}, name={name}, email={user['email'] or '(no email)'}, "
            f"age={user['age']}, onboarded={user['onboarding_completed']}"
        )

    print_header("CHAT COUNTS BY USER")
    cur.execute(
        """
        SELECT u.id, COALESCE(u.email, '(no email)') AS email, COUNT(c.id) AS msg_count
        FROM user_profiles u
        LEFT JOIN chat_messages c ON c.user_id = u.id
        GROUP BY u.id, u.email
        ORDER BY u.id
        """
    )
    counts = cur.fetchall()
    if not counts:
        print("No users found.")
    for row in counts:
        print(f"- user_id={row['id']}, email={row['email']}, messages={row['msg_count']}")

    print_header("RECENT MESSAGES")
    cur.execute(
        """
        SELECT c.id, c.user_id, c.role, c.content, c.created_at
        FROM chat_messages c
        ORDER BY c.id DESC
        LIMIT ?
        """,
        (max(1, args.limit),),
    )
    rows = cur.fetchall()
    if not rows:
        print("No chat messages found.")
    for row in rows:
        preview = (row["content"] or "").replace("\n", " ").strip()
        if len(preview) > 100:
            preview = preview[:97] + "..."
        print(
            f"- msg_id={row['id']}, user_id={row['user_id']}, role={row['role']}, "
            f"time={row['created_at']}, text={preview}"
        )

    conn.close()


if __name__ == "__main__":
    main()
