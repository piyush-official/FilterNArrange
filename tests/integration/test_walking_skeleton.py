"""End-to-end: signup → upload → detect → filter → convert → download."""
import pathlib
import httpx
import pytest

FIX = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "sample.csv"


def test_walking_skeleton(stack):
    gw = stack["gateway"]
    with httpx.Client(base_url=gw, timeout=30.0) as c:
        r = c.post("/api/v1/auth/signup", json={
            "email": "e2e@filternarrange.io", "password": "hunter2hunter2",
        })
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        h = {"Authorization": f"Bearer {token}"}

        with FIX.open("rb") as f:
            r = c.post("/api/v1/upload", headers=h,
                       files={"file": ("sample.csv", f, "text/csv")})
        assert r.status_code == 200, r.text
        upload_id = r.json()["uploadId"]

        r = c.post("/api/v1/detect", headers=h, json={"uploadId": upload_id})
        assert r.status_code == 200, r.text
        det = r.json()
        assert det["format"] == "csv"
        names = [col["name"] for col in det["schema"]]
        assert {"name", "age", "country"}.issubset(set(names))

        r = c.post("/api/v1/filter/preview", headers=h, json={
            "uploadId": upload_id,
            "filter": {"kind": "column", "keep": ["name", "country"]},
            "sampleSize": 10,
        })
        assert r.status_code == 200, r.text
        prev = r.json()
        assert [c["name"] for c in prev["schema"]] == ["name", "country"]
        assert any(row.get("name") == "Alice" for row in prev["rows"])

        r = c.post("/api/v1/convert", headers=h, json={
            "uploadId": upload_id,
            "filter": {"kind": "column", "keep": ["name", "country"]},
            "outputFormat": "json",
        })
        assert r.status_code == 200, r.text
        result_id = r.json()["resultId"]

        r = c.get(f"/api/v1/download/{result_id}", headers=h, follow_redirects=False)
        assert r.status_code == 302
        location = r.headers["Location"]
        assert location.startswith("http")

        # Fetch the actual blob from the pre-signed URL
        with httpx.Client(timeout=30.0) as raw:
            blob = raw.get(location)
        assert blob.status_code == 200
        body = blob.text
        assert "Alice" in body and "IN" in body
        # age column should have been projected away
        assert "30" not in body or '"age"' not in body
