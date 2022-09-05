import re
from .parser import parse_yaml, make_tasks, make_functions
from .telegram_notify import telegram_notify
from .executors import NativeExecutor, DockerExecutor
import argparse
import threading
import os
import signal
import sys

CANCEL_TOKEN = False


def do_step(task,
            functions,
            pipeline_name,
            telegram_onfailure,
            executor,
            matrix,
            prefix):
    try:
        task.execute(pipeline_name,
                     functions,
                     executor=executor,
                     matrix=matrix,
                     prefix=prefix)
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


def start_watchdog(time_in_seconds):
    def run_watchdog(pid):
        import time
        import os
        import signal

        start_time = time.time()
        while True:
            if CANCEL_TOKEN:
                return
            if time.time() - start_time > time_in_seconds:
                os.kill(pid, signal.SIGKILL)
                break
            time.sleep(1)

        print(
            "**********************\nScript finished by Watchdog.\n**********************")
        os.kill(pid, signal.SIGKILL)

    pid = os.getpid()
    t = threading.Thread(target=run_watchdog, args=(pid,))
    t.start()


def set_cancel_token():
    global CANCEL_TOKEN
    CANCEL_TOKEN = True


def main():
    parser = argparse.ArgumentParser(description='Nightexec')
    # add option script
    parser.add_argument('script', help='script file')
    parser.add_argument('-n', '--step', help='step name',
                        default="", required=False)
    args = parser.parse_args()

    print("Start script:", args.script)

    filepath = args.script
    dct = parse_yaml(filepath)
    pipeline_name = dct["pipeline_name"]
    tasks = make_tasks(dct["tasks"])

    if "watchdog" in dct:
        start_watchdog(dct["watchdog"])

    if "functions" in dct:
        functions = make_functions(dct["functions"])
    else:
        functions = {}

    if "telegram" in dct:
        telegram_token = dct["telegram"]["token"]
        telegram_chat_id = dct["telegram"]["chat_id"]
        telegram_onfailure = dct["telegram"]["onfailure"]
        telegram_onsuccess = dct["telegram"]["onsuccess"]
    else:
        telegram_onfailure = "undefined"
    if "script_executor" in dct:
        script_executor = dct["script_executor"]
    else:
        script_executor = "/bin/bash"

    executor = NativeExecutor(script_executor=script_executor)
    if "runs-on-docker" in dct:
        executor = DockerExecutor(image=dct["runs-on-docker"]["image"],
                                  script_executor=script_executor,
                                  addfiles=dct["runs-on-docker"]["add"])

    if "matrix" in dct:
        matrix = dct["matrix"]
    else:
        matrix = {}

    if "prefix" in dct:
        prefix = dct["prefix"]
    else:
        prefix = ""

    for matrix_value in matrix_iterator(matrix):
        if args.step == "":
            for task in tasks:
                status, telegram_message = do_step(task,
                                                   functions,
                                                   pipeline_name,
                                                   telegram_onfailure,
                                                   executor=executor,
                                                   matrix=matrix_value,
                                                   prefix=prefix)
                if not status:
                    if "telegram" in dct:
                        telegram_notify(
                            telegram_token, telegram_chat_id, telegram_message)
                    set_cancel_token()
                    return
        else:
            status, telegram_message = do_step(find_task(tasks, args.step),
                                               functions,
                                               pipeline_name,
                                               telegram_onfailure,
                                               executor=executor,
                                               matrix=matrix_value,
                                               prefix=prefix)

            if not status:
                if "telegram" in dct:
                    telegram_notify(
                        telegram_token, telegram_chat_id, telegram_message)
                set_cancel_token()
                return

    if "telegram" in dct:
        telegram_notify(
            token=telegram_token,
            chat_id=telegram_chat_id,
            text=telegram_onsuccess)

    set_cancel_token()


if __name__ == "__main__":
    main()
