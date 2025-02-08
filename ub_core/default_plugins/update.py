import asyncio

from ub_core import BOT, Config, Message, __version__, bot
from ub_core.utils import aio, run_shell_cmd

REPO = Config.REPO


async def get_commits() -> str | None:
    try:
        async with asyncio.timeout(10):
            await asyncio.to_thread(REPO.git.fetch)
    except TimeoutError:
        return

    commits: str = ""
    for idx, commit in enumerate(REPO.iter_commits("HEAD..origin/main")):
        commits += (
            f"<b>#{commit.count()}</b> <i>{commit.author}</i>\n"
            f"<a href='{Config.UPSTREAM_REPO}/commit/{commit}'>{commit.message}</a>\n\n"
        )

        if idx >= 15:
            break

    return commits


async def pull_commits() -> None | bool:
    REPO.git.reset("--hard")
    try:
        async with asyncio.timeout(10):
            await asyncio.to_thread(
                REPO.git.pull, Config.UPSTREAM_REPO, "--rebase=true"
            )
            return True
    except TimeoutError:
        return


async def get_core_update():
    return -1, ""
    # noinspection PyUnreachableCode
    tag_info = await aio.get_json(
        "https://api.github.com/repos/thedragonsinn/ub-core/tags"
    )
    name = tag_info[0]["name"].strip("v")

    latest_version_parts = [int(i) for i in name.split(".")]
    current_version_parts = [int(x) for x in __version__.split(".")]

    for current, latest in zip(current_version_parts, latest_version_parts):
        if current < latest:
            return -1, name  # Current is older
        elif current > latest:
            return 1, name  # Current is Newer

    return 0, name  # No update


@bot.add_cmd(cmd="update")
async def updater(bot: BOT, message: Message) -> None | Message:
    """
    CMD: UPDATE
    INFO: Pull / Check for updates.
    FLAGS:
        -pull to pull updates
        -c to update core
    USAGE:
        .update | .update -pull
    """
    reply: Message = await message.reply("Checking for Updates....")

    if "-c" in message.flags:
        update_status, version = await get_core_update()

        if update_status == -1:
            await asyncio.gather(
                run_shell_cmd(
                    f"pip install -q --no-cache-dir --force-reinstall git+{Config.UPDATE_REPO}@dual_mode"
                ),
                reply.edit(
                    f"An update is available!: {version}\n<code>Pulling and Restarting...</code>"
                ),
            )
            bot.raise_sigint()

        elif update_status == 0:
            await reply.edit(f"Already on latest version: {__version__}")

        else:
            await reply.edit(
                f"Currently on a test version: {__version__} ahead of {version}"
            )

        return

    commits: str = await get_commits()

    if commits is None:
        await reply.edit("Timeout... Try again.")
        return

    if not commits:
        await reply.edit(text="Already Up To Date.", del_in=5)
        return

    if "-pull" not in message.flags:
        await reply.edit(
            text=f"<b>Update Available:</b>\n{commits}", disable_preview=True
        )
        return

    if not (await pull_commits()):  # NOQA
        await reply.edit("Timeout...Try again.")
        return

    await asyncio.gather(
        bot.log_text(text=f"#Updater\nPulled:\n{commits}", disable_preview=True),
        reply.edit("<b>Update Found</b>\n<code>Pulling....</code>"),
        run_shell_cmd(
            f"pip install -q --no-cache-dir --force-reinstall git+{Config.UPDATE_REPO}@dual_mode"
        ),
    )

    bot.raise_sigint()
