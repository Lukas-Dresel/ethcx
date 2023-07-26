import logging
import os
import re
import subprocess
from typing import List, Optional
import virtualenv
import pip
import requests
from semantic_version import SimpleSpec, Version

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from .exceptions import DownloadError


def extract_version_from_spec_string(pragma_string: str, version_list: List[Version]) -> Optional[Version]:
    comparator_set_range = pragma_string.replace(" ", "").split("||")
    comparator_regex = re.compile(r"(([<>]?=?|\^)\d+\.\d+\.\d+)+")
    version = None

    for comparator_set in comparator_set_range:
        spec = SimpleSpec(*(i[0] for i in comparator_regex.findall(comparator_set)))
        selected = spec.select(version_list)
        if selected and (not version or version < selected):
            version = selected

    return version

def create_virtualenv(path, python=None):
    args = []
    if python is not None:
        args += ['-p', python]

    args += [path]
    virtualenv.cli_run(args)

def file_type(path):
    with open(path, 'rb') as f:
        d = f.read(2)
        if d[0] == '#!':
            # read shebang line
            d += f.readline()
            interpreter = os.path.basename(d[2:])
            if re.fullmatch('python[23]?[0-9.]*', interpreter):
                version = subprocess.check_output([interpreter, '--version'])
                return version.lower().split()
            else:
                return interpreter.lower(), d
        else:
            # not a shebang file
            
            d += f.read(200)
            #check if it's an ELF file
            if d[:4] == b'\x7fELF':
                return 'elf', d[:8]
            
    return None, None


def download_file_contents_from_url(logger: logging.Logger, url: str, show_progress: bool) -> bytes:
    logger.info(f"Downloading from {url}")
    response = requests.get(url, stream=show_progress)
    if response.status_code == 404:
        raise DownloadError(
            "404 error when attempting to download from {} - are you sure this"
            " version of solidity is available?".format(url)
        )
    if response.status_code != 200:
        raise DownloadError(
            f"Received status code {response.status_code} when attempting to download from {url}"
        )
    if not show_progress:
        return response.content

    total_size = int(response.headers.get("content-length", 0))
    progress_bar = tqdm(total=total_size, unit="iB", unit_scale=True)
    content = bytes()

    for data in response.iter_content(1024, decode_unicode=True):
        progress_bar.update(len(data))
        content += data
    progress_bar.close()

    return content
            
            
    