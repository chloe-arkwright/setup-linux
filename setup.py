#!/usr/bin/python
import os, shutil, subprocess, sys, time, traceback
from enum import StrEnum
from datetime import datetime
from typing import TypeAlias, AnyStr, Callable

import setupmethods

FilePath: TypeAlias = AnyStr | os.PathLike[AnyStr]
SetupMethod: TypeAlias = Callable[[FilePath], bool | None]

class PackageModifyType(StrEnum):
    REMOVE = "-"
    ADD = "+"


class Application:
    def __init__(self, root_path: FilePath, ask_pass_path: FilePath):
        self.root_path = root_path
        self.env = os.environ.copy()
        self.env["SUDO_ASKPASS"] = ask_pass_path

    def path(self, sub_path: FilePath) -> FilePath:
        return os.path.join(self.root_path, sub_path)

    # noinspection PyMethodMayBeStatic
    def run(self, *cmd: str) -> None:
        subprocess.run(cmd)

    def sudo(self, *cmd: str) -> None:
        subprocess.run(("sudo", "-A") + cmd, env=self.env)


def get_askpass_path(programs: list[str]) -> FilePath | None:
    for program in programs:
        # noinspection PyDeprecation
        if program_path := shutil.which(program):
            return program_path

    return None


def get_current_progress(progress_file: FilePath, steps: list[tuple[str, SetupMethod]]) -> tuple[int, datetime | None]:
    progress = None
    save_time = None

    if os.path.exists(progress_file):
        with open(progress_file, "r") as file:
            progress = file.readline().strip()
            save_time = datetime.fromtimestamp(int(file.readline().strip()))

    if progress is not None:
        for (index, (name, _)) in enumerate(steps):
            if name == progress:
                return index + 1, save_time
        
        raise KeyError(f"Unknown step: {progress}, bad user config.")
    
    return 0, None


def save_progress(path: FilePath, progress: str):
    save_time = int(time.time())

    with open(path, "w") as file:
        file.write(f"{progress}\n")
        file.write(f"{save_time}\n")


def read_packages(path: FilePath, modification_type: PackageModifyType) -> list[str]:
    packages = []

    with open(path, "r") as file:
        while line := file.readline().strip():
            if line[0] == modification_type:
                packages.append(line[1:])

    return packages


if __name__ == "__main__":
    if sys.version_info < (3, 14):
        print("Python 3.14 required.")
        exit(1)

    askpass_programs = [ "ksshaskpass", "ssh-askpass", "gnome-ssh-askpass" ]

    ask_pass = get_askpass_path(askpass_programs)

    if not ask_pass:
        print("Cannot configure a graphical password prompt for sudo, please install one of:")
        print(f"  {" ".join(askpass_programs)}")
        exit(1)

    app = Application(
        root_path = os.path.join(os.path.dirname(sys.argv[0]), "config"),
        ask_pass_path= ask_pass
    )

    progress_file = app.path("progress")
    steps = setupmethods.steps

    try:
        (step_index, save_time) = get_current_progress(progress_file, steps)
    except KeyError as error:
        print(f"Failed to load the progress file.")
        traceback.print_exception(error)
        exit(1)

    if step_index == len(steps):
        print(f"This system appears to have been set up already on {save_time:%c}...")
        print("Would you like to repeat the setup? (y/n)")
        response = input("> ")

        if response == "y":
            step_index = 0
        else:
            print("See you later!")
            exit(0)

    for (step_name, setup_method) in steps[step_index:]:
        try:
            result = setup_method(app)

            save_progress(progress_file, step_name)

            if result:  # Kind of ugly
                exit(0)
        except Exception as error:
            print(f"Failed to execute step {step_index + 1}:")
            traceback.print_exception(error)
