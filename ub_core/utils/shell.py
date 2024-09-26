import asyncio
import os
from asyncio.subprocess import Process
from typing import TYPE_CHECKING, Any

from pyrogram.enums import ParseMode

if TYPE_CHECKING:
    from ..core.types.message import Message


async def run_shell_cmd(
    cmd: str, timeout: int = 300, ret_val: Any | None = None
) -> str:
    """Runs a Shell Command and Returns Output"""
    process: asyncio.create_subprocess_shell = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )

    try:
        async with asyncio.timeout(timeout):
            stdout, _ = await process.communicate()
            return stdout.decode("utf-8")

    except (asyncio.CancelledError, TimeoutError):
        process.kill()
        if ret_val is not None:
            return ret_val
        raise


async def take_ss(video: str, path: str, timestamp: int | float = 0.1) -> None | str:
    """Returns First Frame [if time stamp is none] of Video for Thumbnails"""
    thumb = f"{path}/i.png"
    await run_shell_cmd(
        f'''ffmpeg -hide_banner -loglevel error -ss {timestamp} -i "{video.strip()}" -vframes 1 "{thumb}"'''
    )
    if os.path.isfile(thumb):
        return thumb


async def check_audio(file: str) -> int:
    """Returns True/1 if input has audio else 0/False"""
    result = await run_shell_cmd(
        f'''ffprobe -v error -show_entries format=nb_streams -of default=noprint_wrappers=1:nokey=1 "{file.strip()}"'''
    )
    return int(result or 0) - 1


async def get_duration(file: str) -> int:
    """Returns Input Duration"""
    duration = await run_shell_cmd(
        f'''ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file.strip()}"'''
    )
    return round(float(duration.strip() or 0))


class AsyncShell:
    def __init__(self, process: Process):
        """Not to Be Invoked Directly.\n
        Use AsyncShell.run_cmd"""
        self.process: Process = process
        self.stdout: str = ""
        self.last_line: str = ""
        self.is_done: bool = False
        self._task: asyncio.Task | None = None

    async def read_output(self) -> None:
        """Read StdOut/StdErr and append to stdout and last_line"""
        async for line in self.process.stdout:
            decoded_line = line.decode("utf-8")
            self.stdout += decoded_line
            self.last_line = decoded_line
        self.is_done = True

    async def send_output(self, message: "Message") -> None:
        sleep_duration: int = 1
        old_output: str = ""

        while not self.is_done:
            new_output = self.stdout if len(self.stdout) < 4000 else self.last_line
            if not new_output.strip() or new_output == old_output:
                await asyncio.sleep(0)
                continue

            if sleep_duration >= 10:
                sleep_duration = 2
            await asyncio.sleep(sleep_duration)
            sleep_duration += 2

            await message.edit(
                text=f"<pre language=shell>{new_output}</pre>",
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML,
            )
            old_output = new_output

        await self.process.wait()

    def cancel(self) -> None:
        if not self.is_done:
            self.process.kill()
            self._task.cancel()

    async def create_stdout_task(self, name: str):
        self._task = asyncio.create_task(self.read_output(), name=name)
        await asyncio.sleep(0.5)

    @classmethod
    async def run_cmd(cls, cmd: str, name: str = "AsyncShell") -> "AsyncShell":
        """Setup Object, Start Fetching output and return the process Object."""
        sub_process: AsyncShell = cls(
            process=await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )
        )
        await sub_process.create_stdout_task(name=name)
        return sub_process


class InteractiveShell:
    def __init__(self, process: Process):
        """Not to Be Invoked Directly.\n
        Use InteractiveShell.spawn_shell"""
        self.process: Process = process
        self.stdout: str = ""
        self.last_line: str = ""
        self.is_running: bool = True
        self._task: asyncio.Task | None = None

    async def read_output(self) -> None:
        """Read StdOut/StdErr and append to stdout and last_line"""
        async for line in self.process.stdout:
            decoded_line = line.decode("utf-8")

            if decoded_line.strip() == "ish cmd is done":
                self.is_running = False
                continue

            self.stdout += decoded_line
            self.last_line = decoded_line

        self.is_running = False

    async def send_output(self, message: "Message") -> None:
        sleep_duration: int = 1
        old_output: str = ""

        while self.is_running:
            new_output = self.stdout if len(self.stdout) < 4000 else self.last_line
            if not new_output.strip() or new_output == old_output:
                await asyncio.sleep(0)
                continue

            if sleep_duration >= 10:
                sleep_duration = 2
            await asyncio.sleep(sleep_duration)
            sleep_duration += 2

            await message.edit(
                text=f"<pre language=shell>{new_output}</pre>",
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML,
            )
            old_output = new_output

    async def write_input(self, text: str):
        self.process.stdin.write(
            bytes(text + "\necho 'ish cmd is done'\n", encoding="utf-8")
        )
        await self.process.stdin.drain()
        self.is_running = True

    def flush_stdout(self):
        self.stdout = self.last_line = ""

    def cancel(self) -> None:
        self.process.kill()
        self._task.cancel()

    async def create_stdout_task(self, name: str):
        self._task = asyncio.create_task(self.read_output(), name=name)
        await asyncio.sleep(0.5)

    @classmethod
    async def spawn_shell(cls, name: str = "InteractiveShell") -> "InteractiveShell":
        """Setup Interactive mode, Start Fetching output and return the process Object."""
        sub_process: InteractiveShell = cls(
            process=await asyncio.create_subprocess_exec(
                "bash",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        )
        await sub_process.create_stdout_task(name=name)
        return sub_process
