"""Manage ground-segment users.

    python ground/manage.py add-user nadhem --role operator     # asks for the password
    python ground/manage.py add-user jury --role viewer
    python ground/manage.py list-users
    python ground/manage.py del-user jury
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add-user"); a.add_argument("username"); a.add_argument("--role", choices=store.ROLES, default="viewer")
    a.add_argument("--password", help="for scripts only; omit to be asked")
    sub.add_parser("list-users")
    d = sub.add_parser("del-user"); d.add_argument("username")
    args = ap.parse_args()
    con = store.db()
    if args.cmd == "add-user":
        pw = args.password or getpass.getpass("Password (at least 10 characters): ")
        if not args.password and pw != getpass.getpass("Repeat password: "):
            sys.exit("passwords do not match")
        store.add_user(con, args.username, pw, args.role)
        print(f"user '{args.username}' saved with role {args.role}")
    elif args.cmd == "list-users":
        for u, r in con.execute("SELECT username, role FROM users ORDER BY username"):
            print(f"{u:20s} {r}")
    else:
        con.execute("DELETE FROM users WHERE username=?", (args.username,))
        con.execute("UPDATE refresh SET revoked=1 WHERE username=?", (args.username,))
        print(f"user '{args.username}' removed and signed out")


if __name__ == "__main__":
    main()
