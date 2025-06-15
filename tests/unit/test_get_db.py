from sqlalchemy.orm import Session

from backend.main import get_db


def test_get_db_yields_and_closes_session():
    """
    Проверяем, что get_db() даёт объект Session,
    и что его close() вызывается при закрытии генератора.
    """
    # Создаём генератор
    gen = get_db()
    # Получаем сессию
    db = next(gen)
    assert isinstance(db, Session)

    # Заменяем метод close на «фейковый», чтобы отследить вызов
    closed = {"called": False}
    orig_close = db.close

    def fake_close():
        closed["called"] = True
        orig_close()

    db.close = fake_close

    # Закрываем генератор — это должно сработать через finally и вызвать db.close()
    gen.close()

    assert closed["called"], "Ожидали, что db.close() будет вызван при закрытии генератора"
