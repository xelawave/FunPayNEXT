from collections import OrderedDict
from contextlib import closing
import logging
import sqlite3
from threading import Lock


logger = logging.getLogger("FunPayAPI.runner")
MAX_SENT_MESSAGES = 4096


class SentMessages:
    """Track recent local sends without modifying the messages on FunPay."""

    def __init__(self, account_id: int, database: str | None):
        self.account_id = account_id
        self.database = database
        self.ids: OrderedDict[tuple[int, int], None] = OrderedDict()
        self.lock = Lock()
        if database is not None:
            try:
                with closing(sqlite3.connect(database)) as db, db:
                    db.execute(
                        "CREATE TABLE IF NOT EXISTS sent_messages ("
                        " sequence INTEGER PRIMARY KEY, account_id INTEGER NOT NULL,"
                        " chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL,"
                        " UNIQUE (account_id, chat_id, message_id))"
                    )
                    rows = db.execute(
                        "SELECT chat_id, message_id FROM sent_messages WHERE account_id = ?"
                        " ORDER BY sequence DESC LIMIT ?",
                        (account_id, MAX_SENT_MESSAGES),
                    ).fetchall()
                    self.ids.update((key, None) for key in reversed(rows))
            except sqlite3.Error:
                logger.warning("Could not load sent message IDs", exc_info=True)

    def contains(self, chat_id: int, message_id: int) -> bool:
        with self.lock:
            return (chat_id, message_id) in self.ids

    def remember(self, chat_id: int, message_id: int) -> None:
        key = (chat_id, message_id)
        with self.lock:
            if key in self.ids:
                return
            self.ids[key] = None
            if len(self.ids) > MAX_SENT_MESSAGES:
                self.ids.popitem(last=False)
            if self.database is None:
                return
            try:
                with closing(sqlite3.connect(self.database)) as db, db:
                    db.execute(
                        "INSERT OR IGNORE INTO sent_messages (account_id, chat_id, message_id)"
                        " VALUES (?, ?, ?)",
                        (self.account_id, chat_id, message_id),
                    )
                    db.execute(
                        "DELETE FROM sent_messages WHERE account_id = ? AND sequence < ("
                        " SELECT sequence FROM sent_messages WHERE account_id = ?"
                        " ORDER BY sequence DESC LIMIT 1 OFFSET ?)",
                        (self.account_id, self.account_id, MAX_SENT_MESSAGES - 1),
                    )
            except sqlite3.Error:
                logger.warning("Could not save sent message ID", exc_info=True)
