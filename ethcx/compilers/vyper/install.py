"""
Install vyper
"""
import argparse
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import warnings
import zipfile
import virtualenv
from base64 import b64encode
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import requests
from semantic_version import SimpleSpec, Version


from . import wrapper
from ...           import ETHCX_BINARY_PATH_VARIABLE
from ...lock       import get_process_lock
from ...utils      import download_file_contents_from_url, extract_version_from_spec_string, file_type
from ...exceptions import (
    DownloadError,
    CompilerInstallationError,
    CompilerNotInstalled,
    UnexpectedVersionError,
    UnexpectedVersionWarning,
    UnsupportedVersionError,
)



BINARY_DOWNLOAD_BASE = "https://github.com/vyperlang/vyper/releases/download/v{}/{}"
SOURCE_DOWNLOAD_BASE = "https://github.com/vyperlang/vyper/releases/download/v{}/{}"
GITHUB_RELEASES = "https://api.github.com/repos/vyperlang/vyper/releases?per_page=100"

MINIMAL_vyper_VERSION = Version("0.4.11")
LOGGER = logging.getLogger("ethcx.solidity.install")


_default_vyper_binary = None


def _get_os_name() -> str:
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform == "darwin":
        return "macosx"
    if sys.platform == "win32":
        return "windows"
    raise OSError(f"Unsupported OS: '{sys.platform}' - ethcx supports Linux, OSX and Windows")


def _convert_and_validate_vyper_version(version: Union[str, Version]) -> Version:
    # take a user-supplied version as a string or Version
    # validate the value, and return a Version object
    if not isinstance(version, Version):
        version = Version(version.lstrip("v"))
    # if version not in SimpleSpec(">=0.4.11"):
    #     raise UnsupportedVersionError("py-vyper-x does not support vyper versions <0.4.11")
    return version


def set_vyper_version_pragma(
    pragma_string: str, silent: bool = False, check_new: bool = False
) -> Version:
    """
    Set the currently active `solc` binary based on a pragma statement.

    The newest installed version that matches the pragma is chosen. Raises
    `SolcNotInstalled` if no installed versions match.

    Arguments
    ---------
    pragma_string : str
        Pragma statement, e.g. "pragma solidity ^0.4.22;"
    silent : bool, optional
        If True, do not generate any logger output.
    check_new : bool, optional
        If True, also check if there is a newer compatible version that has not
        been installed.

    Returns
    -------
    Version
        The new active `solc` version.
    """
    version = extract_version_from_spec_string(pragma_string, get_installed_vyper_versions())
    if version is None:
        raise CompilerNotInstalled(
            f"No compatible solc version installed."
            f" Use solcx.install_solc_version_pragma('{version}') to install."
        )
    set_vyper_version(version, silent)
    if check_new:
        latest = install_vyper_pragma(pragma_string, False)
        if latest > version:
            LOGGER.info(f"Newer compatible solc version exists: {latest}")

    return version


def install_vyper_pragma(
    pragma_string: str,
    install: bool = True,
    show_progress: bool = False,
    vyper_binary_path: Union[Path, str] = None,
) -> Version:
    """
    Find, and optionally install, the latest compatible `solc` version based on
    a pragma statement.

    Arguments
    ---------
    pragma_string : str
        Pragma statement, e.g. "pragma solidity ^0.4.22;"
    install : bool, optional
        If True, installs the version of `solc`.
    show_progress : bool, optional
        If True, display a progress bar while downloading. Requires installing
        the `tqdm` package.
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Version
        Installed `solc` version.
    """
    version = extract_version_from_spec_string(pragma_string, get_installable_vyper_versions())
    if not version:
        raise UnsupportedVersionError("Compatible solc version does not exist")
    if install:
        install_vyper(version, show_progress=show_progress, vyper_binary_path=vyper_binary_path)

    return version


def _unlink_vyper(vyper_path: Path) -> None:
    vyper_path.unlink()
    if _get_os_name() == "windows":
        shutil.rmtree(vyper_path.parent)


def get_vyper_install_folder(vyper_binary_path: Union[Path, str] = None) -> Path:
    """
    Return the directory where `ethcx` stores installed `vyper` binaries.

    By default, this is `~/.ethcx/vyper/`

    Arguments
    ---------
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Path
        Subdirectory where `vyper` binaries are are saved.
    """
    if os.getenv(ETHCX_BINARY_PATH_VARIABLE):
        path = Path(os.environ[ETHCX_BINARY_PATH_VARIABLE])
    elif vyper_binary_path is not None:
        path = Path(vyper_binary_path)
    else:
        path = Path.home().joinpath(".ethcx")
    
    path = path.joinpath("vyper")
    path.mkdir(exist_ok=True, parents=True)
    return path


def _get_which_vyper() -> Path:
    # get the path for the currently installed `vyper` version, if any
    if _get_os_name() == "windows":
        response = subprocess.check_output(["where.exe", "vyper"], encoding="utf8").strip()
    else:
        response = subprocess.check_output(["which", "vyper"], encoding="utf8").strip()

    return Path(response)


def import_installed_vyper(vyper_binary_path: Union[Path, str] = None) -> List[Version]:
    """
    Search for and copy installed `vyper` versions into the local installation folder.

    Arguments
    ---------
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    List
        Imported vyper versions
    """
    try:
        path_list = [_get_which_vyper()]
    except (FileNotFoundError, subprocess.CalledProcessError):
        path_list = []

    # on OSX, also copy all versions of vyper from cellar
    if _get_os_name() == "macosx":
        path_list.extend(Path("/usr/local/Cellar").glob("solidity*/**/vyper"))

    imported_versions = []
    for path in path_list:
        if file_type(path)[0] != 'elf':
            # we only support importing the ELF version of vyper
            LOGGER.warning(f"Skipping import of non-ELF vyper binary: {path}")
            continue
        try:
            version = wrapper._get_vyper_version(path)
            assert version not in get_installed_vyper_versions()
        except Exception:
            continue

        copy_path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")
        if _get_os_name() == "windows":
            copy_path.mkdir()
            copy_path = copy_path.joinpath("vyper.exe")

        shutil.copy(path, copy_path)
        try:
            # confirm that vyper still works after being copied
            assert version == wrapper._get_vyper_version(copy_path)
            imported_versions.append(version)
        except Exception:
            _unlink_vyper(copy_path)

    return imported_versions


def get_executable(
    version: Union[str, Version] = None, vyper_binary_path: Union[Path, str] = None
) -> Path:
    """
    Return the Path to an installed `vyper` binary.

    Arguments
    ---------
    version : str | Version, optional
        Installed `vyper` version to get the path of. If not given, returns the
        path of the active version.
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Path
        `vyper` executable.
    """
    if not version:
        if not _default_vyper_binary:
            raise CompilerNotInstalled(
                "vyper is not installed. Call vyper.get_installable_vyper_versions()"
                " to view for available versions and vyper.install_vyper() to install."
            )
        return _default_vyper_binary

    version = _convert_and_validate_vyper_version(version)
    vyper_bin = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")
    if _get_os_name() == "windows":
        vyper_bin = vyper_bin.joinpath("vyper.exe")
    if not vyper_bin.exists():
        raise CompilerNotInstalled(
            f"vyper {version} has not been installed."
            f" Use vyper.install_vyper('{version}') to install."
        )
    return vyper_bin


def set_vyper_version(
    version: Union[str, Version], silent: bool = False, vyper_binary_path: Union[Path, str] = None
) -> None:
    """
    Set the currently active `vyper` binary.

    Arguments
    ---------
    version : str | Version, optional
        Installed `vyper` version to get the path of. If not given, returns the
        path of the active version.
    silent : bool, optional
        If True, do not generate any logger output.
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.
    """
    version = _convert_and_validate_vyper_version(version)
    global _default_vyper_binary
    _default_vyper_binary = get_executable(version, vyper_binary_path)
    if not silent:
        LOGGER.info(f"Using vyper version {version}")

def get_downloadable_vyper_binary_assets(headers: Optional[Dict] = None) -> List[Tuple[Version, Tuple[str, str, str]]]:
    """
    Return a list of all `vyper` versions that can be downloaded from Github releases.

    Returns
    -------
    List
        List of Versions objects of installable `vyper` versions and the URLs to download the corresponding binaries.
    """
    pattern_base = "vyper.[0-9].[0-9].[0-9]{1,}\+commit.[0-9a-f]{4,}"
    pattern_linux = f"{pattern_base}.linux"
    pattern_macosx = f"{pattern_base}.darwin"
    pattern_windows = f"{pattern_base}.windows.exe"

    if headers is None and os.getenv("GITHUB_TOKEN") is not None:
        auth = b64encode(os.environ["GITHUB_TOKEN"].encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}

    data = requests.get(GITHUB_RELEASES, headers=headers)
    if data.status_code != 200:
        msg = (
            f"Status {data.status_code} when getting vyper versions from Github:"
            f" '{data.json()['message']}'"
        )
        if data.status_code == 403:
            msg += (
                "\n\nIf this issue persists, generate a Github API token and store"
                " it as the environment variable `GITHUB_TOKEN`:\n"
                "https://github.blog/2013-05-16-personal-api-tokens/"
            )
        raise ConnectionError(msg)

    result_list = []
    for release in data.json():
        try:
            version = Version.coerce(release["tag_name"].lstrip("v"))
        except ValueError:
            # ignore non-standard releases (e.g. the beta versions)
            continue

        windows_binary = None
        linux_binary = None
        macosx_binary = None
        
        for asset in release["assets"]:
            if re.match(pattern_linux, asset["name"]):
                linux_binary = asset['browser_download_url']
            elif re.match(pattern_macosx, asset["name"]):
                macosx_binary = asset['browser_download_url']
            elif re.match(pattern_windows, asset["name"]):
                windows_binary = asset['browser_download_url']

        # if we're on windows, check if we found the windows asset
        if _get_os_name() == "windows" and not windows_binary:
            continue
        # if we're on linux, check if we found the linux asset
        elif _get_os_name() == "linux" and not linux_binary:
            continue
        # if we're on macosx, check if we found the macosx asset
        elif _get_os_name() == "macosx" and not macosx_binary:
            continue

        result_list.append((version, (linux_binary, macosx_binary, windows_binary)))
    return sorted(result_list, reverse=True)

def get_downloadable_vyper_binaries_for_current_os(headers: Optional[Dict] = None) -> List[Tuple[Version, str]]:
    current_os = _get_os_name()
    l = get_downloadable_vyper_binary_assets(headers)
    if current_os == "linux":
        return [(v, b[0]) for v, b in l if b[0] is not None]
    elif current_os == "macosx":
        return [(v, b[1]) for v, b in l if b[1] is not None]
    elif current_os == "windows":
        return [(v, b[2]) for v, b in l if b[2] is not None]
    else:
        raise OSError(f"Unsupported OS: '{current_os}' - ethcx supports Linux, OSX and Windows")

def get_installable_vyper_versions(headers: Optional[Dict] = None) -> List[Version]:
    """
    Return a list of all `vyper` versions that can be installed by ethcx.

    Returns
    -------
    List
        List of Versions objects of installable `vyper` versions.
    """
    version_list = [version for version, _bin_url in get_downloadable_vyper_binaries_for_current_os()]
    # version_list = [i for i in version_list if i >= MINIMAL_vyper_VERSION]
    return version_list


def get_compilable_vyper_versions(headers: Optional[Dict] = None) -> List[Version]:
    """
    Return a list of all `vyper` versions that can be compiled from source by py-vyper-x.

    Arguments
    ---------
    headers : Dict, optional
        Headers to include in the request to Github.

    Returns
    -------
    List
        List of Versions objects of installable `vyper` versions.
    """
    raise NotImplementedError("Compiling from source is not supported for vyper")


def get_installed_vyper_versions(vyper_binary_path: Union[Path, str] = None) -> List[Version]:
    """
    Return a list of currently installed `vyper` versions.

    Arguments
    ---------
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    List
        List of Version objects of installed `vyper` versions.
    """
    install_path = get_vyper_install_folder(vyper_binary_path)
    return sorted([Version(i.name[7:]) for i in install_path.glob("vyper-v*")], reverse=True)


def install_vyper(
    version: Union[str, Version] = "latest",
    show_progress: bool = False,
    vyper_binary_path: Union[Path, str] = None,
) -> Version:
    """
    Download and install a precompiled version of `vyper`.

    Arguments
    ---------
    version : str | Version, optional
        Version of `vyper` to install. Default is the newest available version.
    show_progress : bool, optional
        If True, display a progress bar while downloading. Requires installing
        the `tqdm` package.
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Version
        installed vyper version
    """

    installable = get_downloadable_vyper_binaries_for_current_os()

    if version == "latest":
        version, download_url = installable[0]
    else:
        version = _convert_and_validate_vyper_version(version)
        download_url = next((url for v, url in installable if v == version), None)
        if not download_url:
            raise CompilerInstallationError(f"vyper {version} is not installable by ethcx")
    os_name = _get_os_name()
    process_lock = get_process_lock(str(version))

    with process_lock:
        if _check_for_installed_version(version, vyper_binary_path):
            path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")
            LOGGER.info(f"vyper {version} already installed at: {path}")
            return version

        if os_name == "linux":
            _install_vyper_unix(version, download_url, show_progress, vyper_binary_path)
        elif os_name == "macosx":
            _install_vyper_unix(version, download_url, show_progress, vyper_binary_path)
        elif os_name == "windows":
            _install_vyper_windows(version, download_url, show_progress, vyper_binary_path)

        try:
            _validate_installation(version, vyper_binary_path)
        except CompilerInstallationError as exc:
            if os_name != "windows":
                exc.args = (
                    f"{exc.args[0]} If this issue persists, you can try to compile from "
                    f"source code using `vyper.compile_vyper('{version}')`.",
                )
            raise exc

    return version


def compile_vyper(
    version: Version, show_progress: bool = False, vyper_binary_path: Union[Path, str] = None
) -> Version:
    """
    Install a version of `vyper` by downloading and compiling source code.

    Arguments
    ---------
    version : str | Version, optional
        Version of `vyper` to install. Default is the newest available version.
    show_progress : bool, optional
        If True, display a progress bar while downloading. Requires installing
        the `tqdm` package.
    vyper_binary_path : Path | str, optional
        User-defined path, used to override the default installation directory.

    Returns
    -------
    Version
        installed vyper version
    """
    if _get_os_name() == "windows":
        raise OSError("Compiling from source is not supported on Windows systems")

    if version == "latest":
        version = get_compilable_vyper_versions()[0]
    else:
        version = _convert_and_validate_vyper_version(version)

    process_lock = get_process_lock(str(version))

    with process_lock:
        if _check_for_installed_version(version, vyper_binary_path):
            path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")
            LOGGER.info(f"vyper {version} already installed at: {path}")
            return version

        temp_path = _get_temp_folder()
        download = SOURCE_DOWNLOAD_BASE.format(version, f"solidity_{version}.tar.gz")
        install_path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")

        content = _download_vyper(download, show_progress)
        with tarfile.open(fileobj=BytesIO(content)) as tar:
            tar.extractall(temp_path)
        temp_path = temp_path.joinpath(f"solidity_{version}")

        try:
            LOGGER.info("Running dependency installation script `install_deps.sh`...")
            subprocess.check_call(
                ["sh", temp_path.joinpath("scripts/install_deps.sh")], stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as exc:
            LOGGER.warning(exc, exc_info=True)

        original_path = os.getcwd()
        temp_path.joinpath("build").mkdir(exist_ok=True)
        os.chdir(str(temp_path.joinpath("build").resolve()))
        try:
            for cmd in (["cmake", ".."], ["make"]):
                LOGGER.info(f"Running `{cmd[0]}`...")
                subprocess.check_call(cmd, stderr=subprocess.DEVNULL)
            temp_path.joinpath("build/vyper/vyper").rename(install_path)
        except subprocess.CalledProcessError as exc:
            err_msg = (
                f"{cmd[0]} returned non-zero exit status {exc.returncode}"
                " while attempting to build vyper from the source.\n"
                "This is likely due to a missing or incorrect version of a build dependency."
            )
            if _get_os_name() == "macosx":
                err_msg = (
                    f"{err_msg}\n\nFor suggested installation options: "
                    "https://github.com/iamdefinitelyahuman/py-vyper-x/wiki/Installing-Solidity-on-OSX"  # noqa: E501
                )
            raise CompilerInstallationError(err_msg)

        finally:
            os.chdir(original_path)

        install_path.chmod(install_path.stat().st_mode | stat.S_IEXEC)
        _validate_installation(version, vyper_binary_path)

    return version


def _check_for_installed_version(
    version: Version, vyper_binary_path: Union[Path, str] = None
) -> bool:
    path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")
    return path.exists()


def _get_temp_folder() -> Path:
    path = Path(tempfile.gettempdir()).joinpath(f"vyper-tmp-{os.getpid()}")
    if path.exists():
        shutil.rmtree(str(path))
    path.mkdir()
    return path


def _install_vyper_unix(
    version: Version, download_url: str, show_progress: bool, vyper_binary_path: Union[Path, str, None]
) -> None:
    
    # retrieve the filename from the download url
    filename = download_url.split('/')[-1]
    install_path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")

    content = download_file_contents_from_url(LOGGER, download_url, show_progress)
    with open(install_path, "wb") as fp:
        fp.write(content)

    install_path.chmod(install_path.stat().st_mode | stat.S_IEXEC)


def _install_vyper_windows(
    version: Version, download_url: str, show_progress: bool, vyper_binary_path: Union[Path, str, None]
) -> None:
    install_path = get_vyper_install_folder(vyper_binary_path).joinpath(f"vyper-v{version}")

    temp_path = _get_temp_folder()
    content = download_file_contents_from_url(LOGGER, download_url, show_progress)

    if Path(download_url.split('/')[-1]).suffix == ".exe":
        install_path.mkdir()
        with open(install_path.joinpath("vyper.exe"), "wb") as fp:
            fp.write(content)

    else:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            zf.extractall(str(temp_path))
            temp_path.rename(install_path)


def _validate_installation(version: Version, vyper_binary_path: Union[Path, str, None]) -> None:
    binary_path = get_executable(version, vyper_binary_path)
    try:
        installed_version = wrapper._get_vyper_version(binary_path)
    except Exception:
        _unlink_vyper(binary_path)
        raise CompilerInstallationError(
            "Downloaded binary would not execute, or returned unexpected output."
        )
    if installed_version.truncate() != version.truncate():
        _unlink_vyper(binary_path)
        raise UnexpectedVersionError(
            f"Attempted to install vyper v{version}, but got vyper v{installed_version}"
        )
    if installed_version != version:
        warnings.warn(f"Installed vyper version is v{installed_version}", UnexpectedVersionWarning)
    if not _default_vyper_binary:
        set_vyper_version(version)
    LOGGER.info(f"vyper {version} successfully installed at: {binary_path}")


try:
    # try to set the result of `which`/`where` as the default
    _default_vyper_binary = _get_which_vyper()
except Exception:
    # if not available, use the most recent vyper installed version
    if get_installed_vyper_versions():
        set_vyper_version(get_installed_vyper_versions()[0], silent=True)


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("version")
    argument_parser.add_argument("--vyper-binary-path", default=None)
    args = argument_parser.parse_args()
    install_vyper(args.version, vyper_binary_path=args.vyper_binary_path)
