from .parser import parse_yaml
from .executors import NativeExecutor, DockerExecutor
import argparse
import threading
import os
import pprint
from .core import Core

CANCEL_TOKEN = False


def do_step(pipeline_name,
            task,
            executor,
            matrix,
            prefix):
    try:
        task.execute(pipeline_name=pipeline_name,
                     executor=executor,
                     matrix=matrix,
                     prefix=prefix)
    except Exception as e:
        print(f"Step {task.name} failed: {e}")
        return False
    return True, ""


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


def merge_dicts(dict_args):
    """ Deep merge dicts common way, but extend lists if it has some keys. """
    result = {}
    for dictionary in dict_args:
        for key, value in dictionary.items():
            if key in result and isinstance(result[key], dict):
                result[key] = merge_dicts(result[key], value)
            elif key in result and isinstance(result[key], list):
                result[key] = result[key] + value
            else:
                result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description='bonesinger')
    # add multiple arguments
    parser.add_argument('scripts', nargs='*', type=str, help='Path to script')
    parser.add_argument('--entrance', type=str, help='Pipeline to execute')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--docker', type=str, help='Docker image to use', default=None)
    parser.add_argument('-n', '--step', help='step name',
                        default="", required=False)
    args = parser.parse_args()

    print("Start script:", args.scripts)

    filepathes = args.scripts
    dct = {}
    dct = merge_dicts([parse_yaml(fpath) for fpath in filepathes])

    if args.debug:
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(dct)

    if "script_executor" in dct:
        script_executor = dct["script_executor"]
    else:
        script_executor = "/bin/bash"

    executor = NativeExecutor(script_executor=script_executor)
    if args.docker is not None:
        executor = DockerExecutor(image=args.docker,
                                  script_executor=script_executor)

    if "matrix" in dct:
        matrix = dct["matrix"]
    else:
        matrix = {}

    if "prefix" in dct:
        prefix = "\n".join(dct["prefix"])
    else:
        prefix = ""

    if "pipeline_template" in dct:
        pipeline_template = dct["pipeline_template"]
    else:
        pipeline_template = {}

    core = Core(executor=executor,
                matrix=matrix,
                prefix=prefix,
                debug=args.debug,
                pipeline_records=dct["pipeline"],
                on_success_records=dct.get("on_success", None),
                on_failure_records=dct.get("on_failure", None),
                pipeline_template=pipeline_template)

    if args.entrance is not None:
        if args.debug:
            print("Entrance:", args.entrance)
        core.execute_entrypoint(args.entrance)
    elif len(dct["pipeline"]) == 1:
        core.execute_entrypoint(dct["pipeline"][0]["name"])
    else:
        print("Entrance is not specified. Use --entrance to specify it.")


if __name__ == "__main__":
    main()
