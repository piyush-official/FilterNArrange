import datetime

from filternarrange_engine.retention.config import RetentionConfig
from filternarrange_engine.retention.sweeper import BlobRef, Sweeper


class _Store:
    def __init__(self, blobs):
        self.blobs = list(blobs)
        self.deleted = []

    def list(self, bucket):
        return [b for b in self.blobs if b.bucket == bucket]

    def delete(self, bucket, key):
        self.deleted.append((bucket, key))


class _Tiers:
    def __init__(self, mapping):
        self.mapping = mapping

    def tier_of(self, owner_id):
        return self.mapping.get(owner_id, "free")


def test_deletes_aged_free_upload_keeps_recent_paid():
    now = datetime.datetime(2026, 6, 7, 12, 0, tzinfo=datetime.timezone.utc)
    cfg = RetentionConfig()  # 24h / 30d
    blobs = [
        # free user, older than 24h → delete
        BlobRef(
            "uploads", "alice/old.csv",
            now - datetime.timedelta(hours=48), "alice"
        ),
        # free user, fresh → keep
        BlobRef(
            "uploads", "alice/fresh.csv",
            now - datetime.timedelta(hours=2), "alice"
        ),
        # paid user, 5 days old → keep (under 30d)
        BlobRef(
            "uploads", "bob/midage.csv",
            now - datetime.timedelta(days=5), "bob"
        ),
        # paid user, 60 days old → delete
        BlobRef(
            "uploads", "bob/ancient.csv",
            now - datetime.timedelta(days=60), "bob"
        ),
    ]
    store = _Store(blobs)
    tiers = _Tiers({"alice": "free", "bob": "paid"})
    s = Sweeper(cfg, store, tiers)

    result = s.sweep(now=now)
    assert result.scanned == 4
    assert result.deleted == 2
    assert set(store.deleted) == {
        ("uploads", "alice/old.csv"),
        ("uploads", "bob/ancient.csv"),
    }


def test_results_use_result_cutoff():
    now = datetime.datetime(2026, 6, 7, 12, 0, tzinfo=datetime.timezone.utc)
    cfg = RetentionConfig(
        upload_free_hours=24, upload_paid_days=30,
        result_free_hours=2, result_paid_days=1,
    )
    blobs = [
        BlobRef(
            "results", "alice/r1.json",
            now - datetime.timedelta(hours=3), "alice"
        ),
        BlobRef(
            "results", "bob/r2.json",
            now - datetime.timedelta(hours=18), "bob"
        ),
    ]
    s = Sweeper(cfg, _Store(blobs), _Tiers({"alice": "free", "bob": "paid"}))
    result = s.sweep(now=now)
    assert result.deleted == 2
