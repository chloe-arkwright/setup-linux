#!/usr/bin/python
import os
import shutil
import subprocess
import sys
import time
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


def _1_remove_default_packages(system_packages: list[str], flatpaks: list[str]):
    print("Removing default packages.")

    if len(system_packages) > 0:
        sudo("dnf", "rm", "--assumeyes", *system_packages)

    if len(flatpaks) > 0:
        run("flatpak", "uninstall", "--assumeyes", *flatpaks)


def _2_upgrade_system():
    print("Upgrading system.")
    sudo("dnf", "upgrade", "--assumeyes")


def _3_install_packages(system_packages: list[str], flatpaks: list[str]):
    print("Installing packages.")

    if len(system_packages) > 0:
        sudo("dnf", "install", "--assumeyes", *system_packages)

    if len(flatpaks) > 0:
        run("flatpak", "install", "--assumeyes", *flatpaks)


def _4_mount_umf():
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


def _5_import_secrets():
    print("Importing Secrets.")


if __name__ == "__main__":
    LAST_STEP_LABEL = "5"

    configure_sudo_askpass()

    progress = None

    tool_folder = os.path.dirname(sys.argv[0])
    progress_file = f"{tool_folder}/progress"

    if os.path.exists(progress_file):
        print("Progress file found!")

        with open(progress_file, "r") as f:
            progress = f.readline().strip()
            save_time = int(f.readline().strip())

    if progress == LAST_STEP_LABEL:
        print(f"This system appears to already have been set up on {save_time}...")
        print("Would you like to repeat the setup? (y/n)")
        response = input("> ")

        if response == "y":
            progress = None
            save_time = 0
        else:
            print("See you later!")
            exit()

    if not progress:
        packages_to_remove = read_packages(f"{tool_folder}/pkgs", "-")
        flatpaks_to_remove = read_packages(f"{tool_folder}/flatpaks", "-")

        _1_remove_default_packages(packages_to_remove, flatpaks_to_remove)
        progress, save_time = save_progress(progress_file, "1")

    if progress == "1":
        _2_upgrade_system()
        progress, save_time = save_progress(progress_file, "2")
        print("+----------------------------+")
        print("| Please reboot your system. |")
        print("+----------------------------+")
        exit()

    if progress == "2":
        packages_to_add = read_packages(f"{tool_folder}/pkgs", "+")
        flatpaks_to_add = read_packages(f"{tool_folder}/flatpaks", "+")

        _3_install_packages(packages_to_add, flatpaks_to_add)
        progress, save_time = save_progress(progress_file, "3")

    if progress == "3":
        _4_mount_umf()
        progress, save_time = save_progress(progress_file, "4")

    if progress == "4":
        _5_import_secrets()
        progress, save_time = save_progress(progress_file, "5")
