import json

class Str:
    def __str__(self):
        return json.dumps(self.__dict__, indent=4, ensure_ascii=False, default=str)

# fmt:off
from ub_core.utils.aiohttp_tools import aio
from ub_core.utils.downloader import Download, DownloadedFile
from ub_core.utils.helpers import (
    extract_user_data,
    get_name,
    post_to_telegraph,
    progress,
)
from ub_core.utils.media_helper import (
    MediaExts,
    MediaType,
    bytes_to_mb,
    get_filename_from_headers,
    get_filename_from_url,
    get_tg_media_details,
    get_type,
    make_file_name_tg_safe,
)
from ub_core.utils.shell import (
    AsyncShell,
    check_audio,
    get_duration,
    run_shell_cmd,
    take_ss,
)

# fmt:on