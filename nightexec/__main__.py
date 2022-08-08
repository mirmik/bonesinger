import re
from .parser import parse_yaml, make_tasks, make_functions
from .telegram_notify import telegram_notify
import argparse


def do_step(task,
            functions,
            pipeline_name,
            telegram_onfailure,
            script_executor,
            matrix):
    try:
        task.execute(pipeline_name,
                     functions,
                     script_executor=script_executor,
                     matrix=matrix)
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


def matrix_iterator(matrix):
    def prod(lst):
        res = 1
        for x in lst:
            res *= x
        return res

    keys = sorted(matrix.keys())
    values_list = [matrix[key] for key in keys]
    count_of_elements = prod([len(values) for values in values_list])
    for i in range(count_of_elements):
        matrix_value = {}
        for j in range(len(keys)):
            matrix_value[keys[j]] = values_list[j][i % len(values_list[j])]
        yield matrix_value


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

    if "matrix" in dct:
        matrix = dct["matrix"]
    else:
        matrix = {}

    for matrix_value in matrix_iterator(matrix):
        status = True
        if args.step == "":
            for task in tasks:
                task_status, task_telegram_message = do_step(task,
                                                             functions,
                                                             pipeline_name,
                                                             telegram_onfailure,
                                                             script_executor=script_executor,
                                                             matrix=matrix_value)
                if not task_status:
                    status = False
                    telegram_message = task_telegram_message
        else:
            status, telegram_message = do_step(find_task(tasks, args.step),
                                               functions,
                                               pipeline_name,
                                               telegram_onfailure,
                                               script_executor=script_executor,
                                               matrix=matrix_value)

    if status:
        telegram_message = telegram_onsuccess

    telegram_notify(
        token=telegram_token,
        chat_id=telegram_chat_id,
        text=telegram_message)
