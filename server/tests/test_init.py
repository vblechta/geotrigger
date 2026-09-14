from concurrent.futures import ThreadPoolExecutor, as_completed

from geotrigger import create_app, db
from geotrigger.models import User


def _config(db_path):
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(db_path),
        "SECRET_KEY": "test-secret",
        "WTF_CSRF_ENABLED": False,
    }


def test_create_app_when_tables_already_exist(tmp_path):
    uri_config = _config(tmp_path / "geotrigger.db")
    create_app(uri_config)
    app = create_app(uri_config)
    with app.app_context():
        assert db.session.query(User).count() == 1


def test_concurrent_create_app_does_not_race(tmp_path):
    uri_config = _config(tmp_path / "geotrigger.db")

    def boot():
        return create_app(uri_config)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(boot) for _ in range(4)]
        apps = [future.result() for future in as_completed(futures)]

    with apps[0].app_context():
        assert db.session.query(User).count() == 1
