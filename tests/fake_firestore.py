"""An in-memory stand-in for the Firestore client, covering only what the auth store uses."""

from __future__ import annotations

import itertools
from typing import Any

_ids = itertools.count()


class Snapshot:
    def __init__(self, ref: DocRef) -> None:
        self.reference = ref
        self._data = ref._db.get(ref.path)

    @property
    def exists(self) -> bool:
        return self._data is not None

    def to_dict(self) -> dict[str, Any] | None:
        return dict(self._data) if self._data is not None else None


class DocRef:
    def __init__(self, db: dict, path: str) -> None:
        self._db, self.path = db, path

    def get(self) -> Snapshot:
        return Snapshot(self)

    def create(self, data: dict) -> None:
        if self.path in self._db:
            raise ValueError("already exists")
        self._db[self.path] = dict(data)

    def set(self, data: dict) -> None:
        self._db[self.path] = dict(data)

    def update(self, data: dict) -> None:
        if self.path not in self._db:
            raise KeyError(self.path)
        self._db[self.path].update(data)

    def delete(self) -> None:
        self._db.pop(self.path, None)

    def collection(self, name: str) -> Query:
        return Query(self._db, f"{self.path}/{name}")


class Query:
    def __init__(self, db: dict, path: str, filters=(), order=None, limit=None) -> None:
        self._db, self._path = db, path
        self._filters, self._order, self._limit = list(filters), order, limit

    def document(self, doc_id: str) -> DocRef:
        return DocRef(self._db, f"{self._path}/{doc_id}")

    def add(self, data: dict) -> None:
        self.document(f"auto{next(_ids):08d}").set(data)

    def where(self, *, filter: Any) -> Query:
        assert filter.op_string == "=="
        rule = (filter.field_path, filter.value)
        return Query(self._db, self._path, [*self._filters, rule], self._order, self._limit)

    def order_by(self, field: str, direction: str = "ASCENDING") -> Query:
        return Query(self._db, self._path, self._filters, (field, direction), self._limit)

    def limit(self, n: int) -> Query:
        return Query(self._db, self._path, self._filters, self._order, n)

    def stream(self):
        prefix = self._path + "/"
        refs = [
            DocRef(self._db, p)
            for p in sorted(self._db)
            if p.startswith(prefix) and "/" not in p[len(prefix) :]
        ]
        snaps = [r.get() for r in refs]
        snaps = [s for s in snaps if all(s.to_dict().get(f) == v for f, v in self._filters)]
        if self._order:
            field, direction = self._order
            snaps.sort(key=lambda s: s.to_dict()[field], reverse=direction == "DESCENDING")
        return iter(snaps[: self._limit] if self._limit is not None else snaps)


class FakeFirestore:
    def __init__(self) -> None:
        self._db: dict[str, dict] = {}

    def collection(self, name: str) -> Query:
        return Query(self._db, name)
