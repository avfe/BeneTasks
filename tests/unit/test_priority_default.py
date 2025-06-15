from backend.main import Task

def test_priority_default_init():
    task = Task(title="x", description="y")
    assert task.priority == 0     # слушатель `@event.listens_for` сработал
