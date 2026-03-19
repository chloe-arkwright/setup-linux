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
        sep="\n"
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
        subprocess.run(
            ["df", "/run/media/ellie/umf"],
            check=True,
            capture_output=True
        )
        # If this runs successfully then the drive is already mounted
        return
    except subprocess.CalledProcessError:
        pass

    print("Mounting User Made Files.")

    os.mkdir("/run/media/ellie/umf/")

    with open("/etc/fstab", "a+") as file:
        file.write("UUID=caee500c-1571-444f-bddc-139980822896 /run/media/ellie/umf ext4 defaults 0 0\n")

    app.sudo("systemctl", "daemon-reload")


def _5_import_ssh_key(app: Application, name: str):
    app.create_secret_link("ssh", name)
    os.chmod(app.secrets_path(f"ssh/{name}"), 0o700)
    app.create_secret_link("ssh", f"{name}.pub")


def _5_import_secrets(app: Application, **kwargs):
    print("Importing Secrets.")

    if not os.path.exists("~/.gradle"):
        os.makedirs("~/.gradle")

    app.create_secret_link("gradle", "gradle.properties")

    if not os.path.exists("~/.ssh"):
        os.makedirs("~/.ssh")

    _5_import_ssh_key(app, "chloe-arkwright_id_ed25519")
    _5_import_ssh_key(app, "ellie-mcquinn_id_ed25519")

    app.run("gpg", "--import", app.secrets_path("gpg/26-03-13 chloe.gpg"))
    app.run("gpg", "--import", app.secrets_path("gpg/26-03-13 ellie.gpg"))


def _6_link_home(app: Application, **kwargs):
    app.create_link(
        app.data_path("home/public/gitconfig"),
        app.home_path("gitconfig")
    )

    app.create_link(
        app.data_path("home/ellie/.gitconfig"),
        app.home_path(".gitconfig")
    )

    templates_dir = app.run_with_output("xdg-user-dir", "TEMPLATES").strip().decode('utf-8')
    templates_data_dir = app.data_path("home/public/Templates/entries")

    for _, _, files in os.walk(templates_data_dir):
        for file in files:
            app.create_link(
                os.path.join(templates_data_dir, file),
                os.path.join(templates_dir, file)
            )

    bin_data_dir = app.data_path("home/public/bin")
    for _, _, files in os.walk(bin_data_dir):
        for file in files:
            if os.path.basename(file).startswith("."):
                continue
            app.create_link(
                os.path.join(bin_data_dir, file),
                os.path.join(app.home_path(".local/bin"), file)
            )


steps: list[tuple[str, SetupMethod]] = [
    ("uninstall packages", _1_remove_default_packages),
    ("upgrade system", _2_upgrade_system),
    ("install packages", _3_install_packages),
    ("mount user made files", _4_mount_umf),
    ("import secrets", _5_import_secrets),
    ("link home", _6_link_home)
]
