#!/usr/bin/env python3
"""Rebuild a damaged Companion db.sqlite from every row that can still be read.

Companion loads all controls at startup, so a single malformed row means no
buttons on any Stream Deck. This copies schema + readable rows into a fresh
file, keeps user_version/application_id, and prints skipped rows and the new
file's integrity_check.

Usage (Companion stopped, run on a COPY):
    sudo systemctl stop companion
    cp /run/companion-v50/db.sqlite /tmp/db.sqlite.malformed
    python3 companion-db-repair.py /tmp/db.sqlite.malformed /tmp/db.sqlite.repaired
    # integrity "ok" -> put it in place as the companion user, then start Companion
"""
import sqlite3
import sys

src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])

for pragma in ("user_version", "application_id"):
    value = src.execute(f"pragma {pragma}").fetchone()[0]
    dst.execute(f"pragma {pragma}={value}")

objs = src.execute(
    "select type, name, sql from sqlite_master "
    "where sql is not null and name not like 'sqlite_%' "
    "order by type = 'table' desc"
).fetchall()
for _typ, _name, sql in objs:
    dst.execute(sql)

skipped = []
for typ, name, _sql in objs:
    if typ != "table":
        continue
    ncols = len(src.execute(f'pragma table_info("{name}")').fetchall())
    placeholders = ",".join("?" * ncols)
    copied = 0
    for (rid,) in src.execute(f'select rowid from "{name}"').fetchall():
        try:
            row = src.execute(f'select * from "{name}" where rowid=?', (rid,)).fetchone()
        except sqlite3.DatabaseError:
            key = None
            try:
                key = src.execute(f'select id from "{name}" where rowid=?', (rid,)).fetchone()
            except sqlite3.DatabaseError:
                pass
            skipped.append((name, rid, key))
            continue
        dst.execute(f'insert into "{name}" values ({placeholders})', row)
        copied += 1
    print(name, copied)

dst.commit()
print("skipped", skipped)
print("integrity", dst.execute("pragma integrity_check").fetchone()[0])
dst.execute("pragma journal_mode=wal")
dst.close()
