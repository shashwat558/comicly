"""One-off: assign pre-auth orphan books (owner_id NULL) to a user.

Usage: uv run python scripts/claim_books.py --email you@example.com
"""
import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from sqlalchemy import select, update

from app.core.db import SessionLocal
from app.models.book import Book
from app.models.user import User


async def main(email: str) -> None:
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == email.strip().lower()))
        ).scalar_one_or_none()
        if user is None:
            print(f"No user with email {email}")
            return
        orphans = (
            await db.execute(select(Book).where(Book.owner_id.is_(None)))
        ).scalars().all()
        if not orphans:
            print("No orphan books found.")
            return
        await db.execute(
            update(Book).where(Book.owner_id.is_(None)).values(owner_id=user.id)
        )
        await db.commit()
        print(f"Assigned {len(orphans)} book(s) to {email}:")
        for b in orphans:
            print(f"  {b.id}  {b.title}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    asyncio.run(main(args.email))
