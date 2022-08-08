from .parser import parse_yaml, make_tasks, make_functions
from .telegram_notify import telegram_notify


def main():
    dct = parse_yaml("hello.yaml")
    pipeline_name = dct["pipeline_name"]
    tasks = make_tasks(dct["tasks"])
    functions = make_functions(dct["functions"])

    telegram_token = dct["telegram"]["token"]
    telegram_chat_id = dct["telegram"]["chat_id"]
    telegram_onfailure = dct["telegram"]["onfailure"]
    telegram_onsuccess = dct["telegram"]["onsuccess"]

    status = True
    for task in tasks:
        try:
            task.execute(pipeline_name, functions)
        except Exception as e:
            status = False
            telegram_message = telegram_onfailure.format(task=task, error=e)
            break

    if status:
        telegram_message = telegram_onsuccess

    telegram_notify(
        token=telegram_token,
        chat_id=telegram_chat_id,
        text=telegram_message)
