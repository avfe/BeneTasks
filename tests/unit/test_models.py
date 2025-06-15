from backend.main import Task, User  # type: ignore


def test_task_defaults():
    task = Task(title="read", description="x")
    assert task.priority == 0

def test_user_password_not_plaintext():
    user = User(username="alice", hashed_password="notplain")
    assert "notplain" not in repr(user)
