import main

def test_startup_creates_admin(monkeypatch):
    """
    Запускаем стартовый хук второй раз — он должен
    найти admin и НЕ создавать дубликат.
    """
    # считаем текущее количество пользователей
    db = main.SessionLocal()
    try:
        before = db.query(main.User).count()
    finally:
        db.close()

    # вызываем повторно
    main.startup()

    db = main.SessionLocal()
    try:
        after = db.query(main.User).count()
    finally:
        db.close()

    assert after == before  # кол-во записей не изменилось
