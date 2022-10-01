import os
import datetime


class Logger:
    _instance = None

    def init(self, directory=None):
        if directory is None:
            directory = "~/.bonesinger-log/"

        self.directory = os.path.expanduser(directory)
        self.logname = self.generate_logfile_name()
        self.file = self.create_logfile(self.directory, self.logname)

    def generate_logfile_name(self):
        date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        return f"log-{date}.txt"

    def create_logfile(self, directory, name):
        if not os.path.exists(directory):
            os.makedirs(directory)
        path = os.path.join(directory, name)

        # remvoe the file if it exists
        if os.path.exists(path):
            os.remove(path)

        # open the file
        return open(path, 'w')

    def print(self, *args):
        strargs = [str(arg) for arg in args]
        print(*strargs)
        self.file.write(" ".join(strargs) + "\n")
        self.file.flush()

    def close_log(self):
        print("Close logfile")
        self.file.close()

    @staticmethod
    def instance():
        if Logger._instance is None:
            Logger._instance = Logger()
        return Logger._instance

    def print_last_log(self):
        # get last modified file in directory
        files = os.listdir(self.directory)
        files.sort(key=lambda x: os.path.getmtime(os.path.join(self.directory, x)))

        print("Last log:", files[-1])

        # print the last file
        with open(os.path.join(self.directory, files[-1]), 'r') as f:
            print(f.read())
