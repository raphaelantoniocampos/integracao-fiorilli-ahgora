from src.utils.creds import Creds
from src.models.task import Task
from src.tasks.task_runner import TaskRunner
from src.utils.config import Config


class MissingVarsTask(TaskRunner):
    def __init__(self, task: Task):
        super().__init__(
            task=task,
            basic=True,
        )

    def run(self):
        required_vars = Config().data.get("required_vars")
        creds = Creds(required_vars=required_vars)
        missing_vars = creds.get_missing_vars(required_vars=required_vars)
        creds.create_vars(missing_vars)
        self.exit_task()
