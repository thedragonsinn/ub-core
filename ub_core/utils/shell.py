import asyncio
import os
from asyncio.subprocess import Process
from typing import AsyncGenerator


async def run_shell_cmd(cmd: str) -> str:
    """Runs a Shell Command and Returns Output"""
    proc: asyncio.create_subprocess_shell = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    stdout, _ = await proc.communicate()
    return stdout.decode("utf-8")


async def take_ss(video: str, path: str) -> None | str:
    """Returns First Frame of Video for Thumbnails"""
    thumb = f"{path}/i.png"
    await run_shell_cmd(
        f'''ffmpeg -hide_banner -loglevel error -ss 0.1 -i "{video}" -vframes 1 "{thumb}"'''
    )
    if os.path.isfile(thumb):
        return thumb


async def check_audio(file) -> int:
    """Returns True/1 if input has audio else 0/False"""
    result = await run_shell_cmd(
        f'''ffprobe -v error -show_entries format=nb_streams -of default=noprint_wrappers=1:nokey=1 "{file}"'''
    )
    return int(result or 0) - 1


async def get_duration(file) -> int:
    """Returns Input Duration"""
    duration = await run_shell_cmd(
        f'''ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{file}"'''
    )
    return round(float(duration.strip() or 0))


class AsyncShell:
    def __init__(self, process: Process):
        """Not to Be Invoked Directly.\n
        Use AsyncShell.run_cmd"""
        self.process: Process = process
        self.full_std: str = ""
        self.last_line: str = ""
        self.is_done: bool = False
        self._task: asyncio.Task | None = None

    async def read_output(self) -> None:
        """Read StdOut/StdErr and append to full_std and last_line"""
        async for line in self.process.stdout:
            decoded_line = line.decode("utf-8")
            self.full_std += decoded_line
            self.last_line = decoded_line
        self.is_done = True
        await self.process.wait()

    async def get_output(self) -> AsyncGenerator:
        while not self.is_done:
            yield self.full_std if len(self.full_std) < 4000 else self.last_line
            await asyncio.sleep(0)

    def cancel(self) -> None:
        if not self.is_done:
            self.process.kill()
            self._task.cancel()

    @classmethod
    async def run_cmd(cls, cmd: str, name: str = "AsyncShell") -> "AsyncShell":
        """Setup Object, Start Fetching output and return the process Object."""
        sub_process: AsyncShell = cls(
            process=await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
            )
        )
        sub_process._task = asyncio.create_task(sub_process.read_output(), name=name)
        await asyncio.sleep(0.5)
        return sub_process
