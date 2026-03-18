import os
import subprocess

from setup import Application, SetupMethod, read_packages, PackageModifyType


def _1_remove_default_packages(app: Application, **kwargs):
    print("Removing default packages.")

    system_packages = read_packages(app.path("pkgs"), PackageModifyType.REMOVE)
    flatpaks = read_packages(app.path("flatpaks"), PackageModifyType.REMOVE)

    if len(system_packages) > 0:
        app.sudo("dnf", "rm", "--assumeyes", *system_packages)

    if len(flatpaks) > 0:
        app.run("flatpak", "uninstall", "--assumeyes", *flatpaks)


def _2_upgrade_system(app: Application, **kwargs):
    print("Upgrading system.")
    app.sudo("dnf", "upgrade", "--assumeyes")
    print(
        "+----------------------------+",
        "| Please reboot your system. |",
        "+----------------------------+",
        sep = "\n"
    )

    return True


def _3_install_packages(app: Application, **kwargs):
    print("Installing packages.")

    system_packages = read_packages(app.path("pkgs"), PackageModifyType.ADD)
    flatpaks = read_packages(app.path("flatpaks"), PackageModifyType.ADD)

    if len(system_packages) > 0:
        app.sudo("dnf", "install", "--assumeyes", *system_packages)

    if len(flatpaks) > 0:
        app.run("flatpak", "install", "--assumeyes", *flatpaks)


def _4_mount_umf(app: Application, **kwargs):
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

    app.sudo("systemctl", "daemon-reload")


def _5_import_secrets(app: Application, **kwargs):
    print("Importing Secrets.")

    if not os.path.exists("~/.gradle"):
        os.makedirs("~/.gradle")

    app.create_secret_link("gradle", "gradle.properties")
    
    if not os.path.exists("~/.ssh"):
        os.makedirs("~/.ssh")
    
    app.create_secret_link("ssh", "chloe-arkwright_id_ed25519")
    os.chmod(app.path("data/secrets/ssh/chloe-arkwright_id_ed25519"), 0o700)
    app.create_secret_link("ssh", "chloe-arkwright_id_ed25519.pub")
    app.create_secret_link("ssh", "ellie-mcquinn_id_ed25519")
    os.chmod(app.path("data/secrets/ssh/ellie-mcquinn_id_ed25519"), 0o700)
    app.create_secret_link("ssh", "ellie-mcquinn_id_ed25519.pub")

    app.run("gpg", "--import", app.path("data/secrets/gpg/26-03-13 chloe.gpg"))
    app.run("gpg", "--import", app.path("data/secrets/gpg/26-03-13 ellie.gpg"))


def _6_link_home(app: Application, **kwargs):
    pass


steps: list[tuple[str, SetupMethod]] = [
    ("uninstall packages", _1_remove_default_packages),
    ("upgrade system", _2_upgrade_system),
    ("install packages", _3_install_packages),
    ("mount user made files", _4_mount_umf),
    ("import secrets", _5_import_secrets),
    # ("link home", _6_link_home)
]
