import asyncio
from uuid import uuid4
from app.core.task_registry import task_registry as registry1

async def test_singleton():
    from app.core.task_registry import task_registry as registry2
    
    print(f"Registry 1 ID: {id(registry1)}")
    print(f"Registry 2 ID: {id(registry2)}")
    
    job_id = uuid4()
    task = asyncio.create_task(asyncio.sleep(1))
    
    registry1.register(job_id, task)
    
    found_task = registry2.get_task(job_id)
    print(f"Task found in Registry 2: {found_task is not None}")
    
    tasks = registry2.get_all_tasks()
    print(f"All tasks in Registry 2: {list(tasks.keys())}")
    
    registry2.unregister(job_id)
    print(f"Tasks after unregister: {list(registry1.get_all_tasks().keys())}")

if __name__ == "__main__":
    asyncio.run(test_singleton())
