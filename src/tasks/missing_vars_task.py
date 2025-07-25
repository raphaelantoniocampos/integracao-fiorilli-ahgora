from src.utils.creds import Creds
from src.models.task import Task
from src.tasks.task_runner import TaskRunner


class MissingVarsTask(TaskRunner):
    def __init__(self, task: Task):
        super().__init__(
            task=task,
            basic=True,
        )

    def run(self):
        creds = Creds()
        missing_vars = creds.get_missing_vars()
        creds.create_vars(missing_vars)
        self.exit_task()
