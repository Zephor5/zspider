# coding=utf-8
import argparse
import sys

from zspider.auth import hash_password
from zspider.utils.models import User


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap the initial ZSpider admin user")
    parser.add_argument("--username", required=True, help="admin username")
    parser.add_argument("--password", required=True, help="admin password")
    parser.add_argument(
        "--update-password",
        action="store_true",
        help="update the password if the admin user already exists",
    )
    return parser.parse_args()


def main():
    from zspider import init

    args = parse_args()
    init.init("web")
    if not init.done:
        print("init fail")
        sys.exit(1)

    user = User.objects(username=args.username).first()
    hashed_password = hash_password(args.password)

    if user is None:
        User(username=args.username, password=hashed_password, role="admin").save()
        print("admin user created:", args.username)
        return

    changed = False
    if user.role != "admin":
        user.role = "admin"
        changed = True
    if args.update_password and user.password != hashed_password:
        user.password = hashed_password
        changed = True

    if changed:
        user.save()
        print("admin user updated:", args.username)
    else:
        print("admin user already exists:", args.username)


if __name__ == "__main__":
    main()
