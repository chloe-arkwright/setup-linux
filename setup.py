#!/usr/bin/python
import datetime
import os
import shutil
import subprocess
import sys
import time
import traceback
from typing import TypeAlias, AnyStr, Literal

FilePath: TypeAlias = AnyStr | os.PathLike[AnyStr]
PackageModifyType: TypeAlias = Literal["+"] | Literal["-"]


def configure_sudo_askpass():
    askpass_programs = [
        "ksshaskpass",
        "ssh-askpass",
        "gnome-ssh-askpass",
    ]

    for program in askpass_programs:
        # noinspection PyDeprecation
        if program_path := shutil.which(program):
            os.environ["SUDO_ASKPASS"] = program_path
            break

    if "SUDO_ASKPASS" not in os.environ:
        print("Cannot configure a graphical password prompt for sudo, please install one of:")
        print(f"  {" ".join(askpass_programs)}")
        exit(1)


def run(*cmd: str) -> None:
    subprocess.run(cmd)


def sudo(*cmd: str) -> None:
    subprocess.run(("sudo", "-A") + cmd, env=os.environ)


def save_progress(path: FilePath, progress: str) -> tuple[str, int]:
    save_time = int(time.time())

    with open(path, "w") as file:
        file.write(f"{progress}\n")
        file.write(f"{save_time}\n")

    return progress, save_time


def read_packages(path: FilePath, modification_type: PackageModifyType) -> list[str]:
    packages = []

    with open(path, "r") as file:
        while line := file.readline().strip():
            if line[0] == modification_type:
                packages.append(line[1:])

    return packages


def _1_remove_default_packages(context):
    print("Removing default packages.")

    system_packages = read_packages(
        os.path.join(context["run_directory"], "pkgs"),
        "-"
    )

    flatpaks = read_packages(
        os.path.join(context["run_directory"], "flatpaks"),
        "-"
    )

    if len(system_packages) > 0:
        sudo("dnf", "rm", "--assumeyes", *system_packages)

    if len(flatpaks) > 0:
        run("flatpak", "uninstall", "--assumeyes", *flatpaks)


def _2_upgrade_system(context):
    print("Upgrading system.")
    sudo("dnf", "upgrade", "--assumeyes")
    print("+----------------------------+")
    print("| Please reboot your system. |")
    print("+----------------------------+")

    return True


def _3_install_packages(context):
    print("Installing packages.")

    system_packages = read_packages(
        os.path.join(context["run_directory"], "pkgs"),
        "+"
    )

    flatpaks = read_packages(
        os.path.join(context["run_directory"], "flatpaks"),
        "+"
    )

    if len(system_packages) > 0:
        sudo("dnf", "install", "--assumeyes", *system_packages)

    if len(flatpaks) > 0:
        run("flatpak", "install", "--assumeyes", *flatpaks)


def _4_mount_umf(context):
    try:
        subprocess.run(["df", "/run/media/ellie/umf"], check=True, capture_output=True)
        # If this runs successfully then the drive is already mounted
        return
    except subprocess.CalledProcessError:
        pass

    print("Mounting User Made Files.")

    os.mkdir("/run/media/ellie/umf/")

    with open("/etc/fstab", "a+") as file:
        file.write("UUID=caee500c-1571-444f-bddc-139980822896 /run/media/ellie/umf ext4 defaults 0 0\n")

    sudo("systemctl", "daemon-reload")


def _5_import_secrets(context):
    print("Importing Secrets.")


if __name__ == "__main__":
    if sys.version_info < (3, 14):
        print("Python 3.14 required.")
        exit()

    configure_sudo_askpass()

    STEPS = [
        ("uninstall packages", _1_remove_default_packages),
        ("upgrade system", _2_upgrade_system),
        ("install packages", _3_install_packages),
        ("mount user made files", _4_mount_umf),
        ("import secrets", _5_import_secrets),
    ]
    STEPS_BY_KEY = dict(STEPS)
    STEP_INDEX_BY_KEY = dict((step[0], index) for index, step in enumerate(STEPS))

    run_directory = os.path.dirname(sys.argv[0])
    progress_file = f"{run_directory}/progress"

    progress = None
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            progress = f.readline().strip()
            save_time = datetime.datetime.fromtimestamp(int(f.readline().strip()))
        
    step_index = 0
    if progress is not None:
        step_index = STEP_INDEX_BY_KEY[progress] + 1

    if step_index == len(STEPS):
        print(f"This system appears to already have been set up on {save_time:%c}...")
        print("Would you like to repeat the setup? (y/n)")
        response = input("> ")

        if response == "y":
            step_index = 0
        else:
            print("See you later!")
            exit()

    step_context = {
        "run_directory": run_directory,
        "drive_root": os.path.dirname(run_directory)
    }

    for (step_name, step_fun) in STEPS[step_index:]:
        try:
            result = step_fun(step_context) # Kind of ugly
            save_progress(progress_file, step_name)

            if result:
                exit(0)
        except Exception as e:
            print(f"Failed to execute step {step_index + 1}:")
            traceback.print_exception(e)        
