#!/usr/bin/python
import os, shutil, subprocess, sys, time, traceback
from enum import StrEnum
from datetime import datetime
from typing import TypeAlias
from collections.abc import Callable

import setupmethods

FilePath: TypeAlias = str

class PackageModifyType(StrEnum):
    REMOVE = "-"
    ADD = "+"


class Application:
    def __init__(self, config_root: FilePath, ask_pass_path: FilePath):
        self.config_root = config_root
        self.env = os.environ.copy()
        self.env['SUDO_ASKPASS'] = str(ask_pass_path)
        self.home = self.env['HOME']

    def path(self, sub_path: FilePath) -> FilePath:
        return os.path.realpath(os.path.join(self.config_root, sub_path))
    
    def home_path(self, sub_path: FilePath) -> FilePath:
        return os.path.join(self.home, sub_path)
    
    def data_path(self, sub_path): 
        return app.path(f"data/{sub_path}")
    
    def create_link(self, source: FilePath, destination: FilePath):
        if not (os.path.exists(destination) or os.path.lexists(destination)):
            os.symlink(
                src = source,
                dst = destination
            )

    def create_secret_link(self, folder: str, relative_path: str) -> None:
        self.create_link(
            app.data_path(f"secrets/{folder}/{relative_path}"),
            self.home_path(f".{folder}/{relative_path}")
        )

    def run_with_output(self, *cmd: str) -> bytes:
        return subprocess.check_output(cmd)

    # noinspection PyMethodMayBeStatic
    def run(self, *cmd: str) -> None:
        subprocess.run(cmd)

    def sudo(self, *cmd: str) -> None:
        subprocess.run(("sudo", "-A") + cmd, env = self.env)


SetupMethod: TypeAlias = Callable[[Application], bool | None]


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
        print(
            "Cannot configure a graphical password prompt for sudo, please install one of:",
            f"  {" ".join(askpass_programs)}",
            sep = "\n"
        )

        exit(1)

    app = Application(
        config_root = os.path.join(os.path.dirname(sys.argv[0]), "config"),
        ask_pass_path = ask_pass
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
        print(
            f"This system appears to have been set up already on {save_time:%c}...",
            "Would you like to repeat the setup? (y/n)",
            sep = "\n"
        )
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
