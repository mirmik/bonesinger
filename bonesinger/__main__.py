from .parser import parse_yaml_url, get_url_content, parse_yaml_content
from .executors import NativeExecutor, DockerExecutor
from .docker import make_docker_image
import argparse
import threading
import os
import pprint
from .core import Core
from .util import merge_dicts_and_lists, merge_dicts
from .log import Logger
import signal
import pkg_resources

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


def get_dictionaries(pathes):
    dicts = []
    for path in pathes:
        content = get_url_content(path)
        dct = parse_yaml_content(content)
        if dct is not None:
            if "include" in dct:
                for include in dct["include"]:
                    dicts.extend(get_dictionaries([include]))

            dicts.append(dct)

        # lines of content
        lines = content.splitlines()
        for l in lines:
            if l.startswith("#!include"):
                include_url = l[len("#!include"):].strip()
                print("Include:", include_url)
                dicts.extend(get_dictionaries([include_url]))
    return dicts


def doit(logger, args):
    logger.print("Start script:", args.scripts)

    filepathes = args.scripts
    dct = {}

    script_dictionaries = get_dictionaries(filepathes)
    dct = merge_dicts_and_lists(*script_dictionaries)

    if "docker" in dct:
        if "script" in dct["docker"]:
            make_docker_image(dct["docker"]["script"], name=dct["docker"]["name"])
            args.docker = dct["docker"]["name"]

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

    hide_links = False
    if "security" in dct:
        if "hide_links" in dct["security"]:
            hide_links = dct["security"]["hide_links"]

    core = Core(executor=executor,
                matrix=matrix,
                prefix=prefix,
                debug=args.debug,
                pipeline_records=dct["pipeline"],
                on_success_records=dct.get("on_success", None),
                on_failure_records=dct.get("on_failure", None),
                pipeline_template=pipeline_template,
                security_options={"hide_links": hide_links})

    if args.entrance is not None:
        if args.debug:
            logger.print("Entrance:", args.entrance)
        core.execute_entrypoint(args.entrance)
    elif len(dct["pipeline"]) == 1:
        core.execute_entrypoint(dct["pipeline"][0]["name"])
    else:
        logger.print("Entrance is not specified. Use --entrance to specify it.")


def sigint_handler(signum, frame):
    Logger.instance().print("SIGINT received. Canceling...")
    Logger.instance().close_log()
    exit(-1)


def main():
    parser = argparse.ArgumentParser(description='bonesinger')
    # add multiple arguments
    parser.add_argument('scripts', nargs='*', type=str, help='Path to script')
    parser.add_argument('--entrance', type=str, help='Pipeline to execute')
    parser.add_argument('--debug', action='store_true', help='Debug mode')
    parser.add_argument('--lastlog', action='store_true', help='Show last log')
    parser.add_argument('--docker', type=str,
                        help='Docker image to use', default=None)
    parser.add_argument('-n', '--step', help='step name',
                        default="", required=False)
    parser.add_argument('--version', action='store_true', help='Show version')
    args = parser.parse_args()

    __version__ = "undefined"
    try:
        __version__ = pkg_resources.require("bonesinger")[0].version
    except:
        pass

    # get current package version
    if args.version:
        print("bonesinger version:", __version__)

        exit(0)

    if args.lastlog:
        Logger.print_last_log()
        return

    logger = Logger.instance()
    logger.init(directory=None)

    signal.signal(signal.SIGINT, sigint_handler)

    if len(args.scripts) == 0:
        logger.print("No script given.")
    else:
        logger.print("bonesinger version:", __version__)
        doit(logger, args)

    logger.close_log()


if __name__ == "__main__":
    main()
