import os
from enum import Enum
from pathlib import Path
from typing import Optional, Union

from .constants import (
    FILE_LIST_NAMES,
    FLAX_WEIGHTS_NAME,
    HUGGINGFACE_HUB_CACHE,
    PYTORCH_WEIGHTS_NAME,
    TF2_WEIGHTS_NAME,
    TF_WEIGHTS_NAME,
)
from .file_download import cached_download, hf_hub_url
from .hf_api import HfApi


class Frameworks(str, Enum):
    pytorch = "pytorch"
    tensorflow = "tensorflow"
    tensorflow1 = "tensorflow1"
    flax = "flax"


framework_mapping = {
    Frameworks.pytorch: PYTORCH_WEIGHTS_NAME,
    Frameworks.tensorflow: TF2_WEIGHTS_NAME,
    Frameworks.tensorflow1: TF_WEIGHTS_NAME,
    Frameworks.flax: FLAX_WEIGHTS_NAME,
}


REPO_ID_SEPARATOR = "__"
# ^ make sure this substring is not allowed in repo_ids on hf.co


def snapshot_download(
    repo_id: str,
    revision: Optional[str] = None,
    cache_dir: Union[str, Path, None] = None,
    framework: Optional[Frameworks] = None,
) -> str:
    """
    Downloads a whole snapshot of a repo's files at the specified revision.
    This is useful when you want all files from a repo, because you don't know
    which ones you will need a priori.
    All files are nested inside a folder in order to keep their actual filename
    relative to that folder.

    An alternative would be to just clone a repo but this would require that
    the user always has git and git-lfs installed, and properly configured.

    Note: at some point maybe this format of storage should actually replace
    the flat storage structure we've used so far (initially from allennlp
    if I remember correctly).
    Args:
        repo_id (:obj:`str`):
            Repository Id from the Hub in the format `namespace/repository`.
        revision (:obj:`str`, `optional`):
            Specifies the revision on which the repository will be downloaded.
        cache_dir (:obj:`str`, `optional`):
            Directory which you can specify if you want to control where on disk the files are cached.
        framework (:obj:`Frameworks`, `optional`):
            Specify the framework and filters the download files to only load the framework specific ones.
    Return:
        Local folder path (string) of repo snapshot
    """
    if cache_dir is None:
        cache_dir = HUGGINGFACE_HUB_CACHE
    if isinstance(cache_dir, Path):
        cache_dir = str(cache_dir)

    _api = HfApi()
    model_info = _api.model_info(repo_id=repo_id, revision=revision)

    storage_folder = os.path.join(
        cache_dir, repo_id.replace("/", REPO_ID_SEPARATOR) + "." + model_info.sha
    )

    if framework is not None:
        wanted_file_list_names = FILE_LIST_NAMES + [framework_mapping[framework]]
        model_info.siblings = [
            file
            for file in model_info.siblings
            if file.rfilename in wanted_file_list_names
        ]

    for model_file in model_info.siblings:
        url = hf_hub_url(
            repo_id, filename=model_file.rfilename, revision=model_info.sha
        )
        relative_filepath = os.path.join(*model_file.rfilename.split("/"))

        # Create potential nested dir
        nested_dirname = os.path.dirname(
            os.path.join(storage_folder, relative_filepath)
        )
        os.makedirs(nested_dirname, exist_ok=True)

        path = cached_download(
            url, cache_dir=storage_folder, force_filename=relative_filepath
        )

        if os.path.exists(path + ".lock"):
            os.remove(path + ".lock")

    return storage_folder
