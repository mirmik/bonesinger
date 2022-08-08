import re
from .parser import parse_yaml, make_tasks, make_functions
from .telegram_notify import telegram_notify
import argparse


def do_step(task, functions, pipeline_name, telegram_onfailure, script_executor):
    try:
        task.execute(pipeline_name, functions, executor=script_executor)
    except Exception as e:
        status = False
        telegram_message = telegram_onfailure.format(task=task, error=e)
        return False, telegram_message
    return True, ""


def find_task(tasks, name):
    for task in tasks:
        if task.name == name:
            return task
    raise Exception(f"Task {name} not found")


def main():
    parser = argparse.ArgumentParser(description='Nightexec')
    # add option script
    parser.add_argument('-s', '--script', help='script file', required=True)
    parser.add_argument('-n', '--step', help='step name', default="", required=False)
    args = parser.parse_args()

    filepath = args.script
    dct = parse_yaml(filepath)
    pipeline_name = dct["pipeline_name"]
    tasks = make_tasks(dct["tasks"])
    functions = make_functions(dct["functions"])

    telegram_token = dct["telegram"]["token"]
    telegram_chat_id = dct["telegram"]["chat_id"]
    telegram_onfailure = dct["telegram"]["onfailure"]
    telegram_onsuccess = dct["telegram"]["onsuccess"]
    script_executor = dct["script_executor"]

    status = True
    if args.step == "":
        for task in tasks:
            task_status, task_telegram_message = do_step(task,
                                                         functions,
                                                         pipeline_name,
                                                         telegram_onfailure,
                                                         script_executor=script_executor)
            if not task_status:
                status = False
                telegram_message = task_telegram_message
    else:
        status, telegram_message = do_step(find_task(tasks, args.step),
                                           functions,
                                           pipeline_name,
                                           telegram_onfailure,
                                           script_executor=script_executor)

    if status:
        telegram_message = telegram_onsuccess

    telegram_notify(
        token=telegram_token,
        chat_id=telegram_chat_id,
        text=telegram_message)
