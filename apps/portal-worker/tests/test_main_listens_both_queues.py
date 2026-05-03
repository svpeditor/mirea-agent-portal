"""main() вызывает оба recover-функции и слушает builds+jobs."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_main_calls_both_recovers_and_listens(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://stub:stub@stub/stub")
    monkeypatch.setenv("REDIS_URL", "redis://stub:6379/0")

    from portal_worker import config as cfg
    cfg.get_settings.cache_clear()

    with patch("portal_worker.main.recover_orphaned_builds") as mb, \
         patch("portal_worker.main.recover_orphaned_jobs") as mj, \
         patch("portal_worker.main.Redis.from_url") as mredis, \
         patch("portal_worker.main.Worker") as mw:

        mw_instance = MagicMock()
        mw.return_value = mw_instance

        from portal_worker.main import main
        main()

        mb.assert_called_once()
        mj.assert_called_once()
        args, kwargs = mw.call_args
        assert args[0] == ["builds", "jobs"]
        mw_instance.work.assert_called_once_with(with_scheduler=False)
