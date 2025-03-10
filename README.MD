# UB-Core
A fully modular and pluggable Telegram bot base.
Comes with a lot of built in goodies and fixes.


## Example Project:
[Plain-UB](https://github.com/thedragonsinn/plain-ub) is based on and made using ub-core.
it expands on core's initial features and transforms them into usable modules like [these](https://github.com/thedragonsinn/plain-ub/tree/main/app/plugins/files) and many more.


## Table of Contents

- [Installation](https://github.com/thedragonsinn/ub-core/tree/main#Installation) 

- [Standalone Usage](https://github.com/thedragonsinn/ub-core/tree/main#Standalone_Usage)

- Core:
     - [Client](https://github.com/thedragonsinn/ub-core/tree/main#Client) 
     - [Database](https://github.com/thedragonsinn/ub-core/tree/main#Database) 
     - [Message](https://github.com/thedragonsinn/ub-core/tree/main#Message) 
     - [Conversation](https://github.com/thedragonsinn/ub-core/tree/main#Conversation) 
     - [Handlers](https://github.com/thedragonsinn/ub-core/tree/main#Handlers) 
     - [UnifiedMessageHandler](https://github.com/thedragonsinn/ub-core/tree/main#UnifiedMessageHandler) 
     - [Dispatcher](https://github.com/thedragonsinn/ub-core/tree/main#Dispatcher) 
     - [Logging](https://github.com/thedragonsinn/ub-core/tree/main#Logging)
     
- [Default Plugins](https://github.com/thedragonsinn/ub-core/tree/main#DefaultPlugins)

- [Updater](https://github.com/thedragonsinn/ub-core/tree/main#Updater)

- Utils:
     - [Download](https://github.com/thedragonsinn/ub-core/tree/main#Utils)
     - [AioHttp utils](https://github.com/thedragonsinn/ub-core/tree/main#Utils)
     - [Media Helper](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/utils/media_helper.py)
     - [Shell](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/utils/shell.py)


## Documentation 


### Installation

- Single Client:
    ```bash
      pip install git+https://github.com/thedragonsinn/ub-core
    ```

- Dual Client:
    ```bash
      pip install git+https://github.com/thedragonsinn/ub-core@dual_mode
    ```

> Difference between Single and Dual clients: [here](https://github.com/thedragonsinn/ub-core/tree/main#Comparing_Branches)


### Client
A custom [Client](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/core/client.py#L44) with a few [Extra methods](https://github.com/thedragonsinn/ub-core/tree/main/ub_core/core/methods) and [Decorators](https://github.com/thedragonsinn/ub-core/tree/main/ub_core/core/decorators).

  - **[send_message](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/core/methods/send_message.py#L13)**: _automatically sends text as document when it goes above 4096 chars (TG limit)._
    

  - **[channel_logger](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/methods/channel_loggers.py)**: _Logs texts/message to your log channel, StdOut/StdError and log file. The type argument can be used to log at different logging levels like info, error warning etc._
    

  - **[@add_cmd](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/core/decorators/add_cmd.py#L10)**: _Uses a custom command manager instead of pyrogram's. Useful when you wanna add sudo or multi user mode or run [dual_mode](https://github.com/thedragonsinn/ub-core/tree/main#Comparing_Branches). This decorator will negate the need to add handlers for each type of user/clients._
    

   - **[@on_message](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/core/decorators/on_message.py#L14)**: _adds back edited support as a keyword argument "filters_edited" and uses a custom dispatcher._
    

  - **[@on_edited_message](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/core/decorators/on_edited_message.py#L9)**: _use a [custom dispatcher](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/core/handlers/dispatcher.py#L31)._
   
```python
    # import the instance that was created on core initialisation.
    # use this instance only.
    from ub_core import bot
```


### Database 
Core relies on a MongoDB database and uses a [Custom Collection class.](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/db.py#L19)
> Optional for main branch, Required for dual_mode

  * Inbuilt using DB_URL
```python
    from ub_core import CustomDB

    # Create a CustomDB instance instead of DB_CLIENT["collection_name"]
    coll = CustomDB["test_collection"]
    
    # Now you can use the extra methods as well as the original mongo db methods available in the original collection class.
```

  * Using a Separate DB_URL using a [CustomDatabase](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/db.py#L100)

```python
    from ub_core import CustomDatabase

    # Create a Database Class with a new URI that returns CustomCollection
    db = CustomDatabase(db_uri=DB_URI, db_name=DATABASE_NAME)

    coll=db[collection_name]
    # Now you can use the extra methods as well as the original mongo db methods available in the original collection class.
```

### Conversation
A custom [Conversation](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/conversation.py) module to programitcally interact with incoming and outgoing messages.
``` python 
    from ub_core import bot, Convo
    from pyrogram import filters
    
    async with Convo(
            client=bot, 
            chat_id=1234, 

             # Optional ease of access filters can be used with/without each others

            # custom filters 
            filters=filters.text,
            # only accept message from a specific user 
            from_user=12345,
            # only accept a message that is replied to a specific user
            reply_to_user_id=bot.me.id,
            # only accept a message that is replied to a specific message 
            reply_to_message_id=69,

            timeout=10,
        ) as convo:
            await convo.get_response(timeout=10)
            await convo.send_message(text="abc", get_response=True, timeout=8)
            # and so on
    
    
    # Bound Method for quick single usage.
    response = await Convo.get_resp(
            client=bot, chat_id=1234, filters=filters, timeout=timeout
    )
        # Will return First text it receives in chat.
```


### Handlers 
By default core registers some handlers automatically on groups 0 and 1.

**_It is strongly recommended to not register your handlers in groups 0 and 1._**

- **Group 0:** 

    Group 0 is for background workers that want to receive all incoming messages. they all call `update.continue_propagation()` to ensure they're not blocking any incoming updates.
    
    _[Conversation](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/handlers/conversation.py) relies on this to wait for incoming messages, so make sure to not block this handler group._



- **Group 1:**

    Group 1 is used for handling incoming commands and is responsible for @add_cmd to work.
    it WILL call `update.stop_propagation()` when a command is received and executed so command messages won't trigger the rest of the handlers and create duplicate triggers.(_Conversation being in group 0 is exempt from this._)
    
    _[Command Handler](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/handlers/command.py) A Single Handler to handle owner and optional Sudo/ Super **[sudo but with same level of access as owner]** users relies on this._


### UnifiedMessageHandler
[UnifiedMessageHandler](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/handlers/unified_message_handler.py#L6) combines the _MessageHandler_ and _EditedMessageHandler_ classes using inheritance to bring back Pyro v1 filters.edited functionality.

import and use this handler class in your bot.add_handler() to register a single handler for normal and edited messages.


### Dispatcher 
The [Dispatcher](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/handlers/dispatcher.py) 
- automatically wraps functions or commands into a `asyncio.Task` to allow cancellation of a command.
- creates a custom message object and passes that into your functions instead of pyrogram's message class.
- checks for reactions to prevent false triggers if instructed 
- gracefully catches and logs errors that might occur while your function is running and logs them to log channel.
- deletes command message if it's from owner
- calls `stop_propagation` if the current call is a command.


### Logging
Ub-core comes with a logging handler that automatically logs any errors to the log channel that occur in the background so you won't miss out on any potential app breaking errors.

It also automatically restarts your python interpreter when it detects network issues happening in pyrogram.

> Both of these start automatically and work in background, you don't have to manage them.


### Message
A custom [Message](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/types/message.py#L37) class to expand on pyrogram's class to add extra goodies.

Check the class for in depth details.


### DefaultPlugins 
Core comes with a few basic quality of life [plugins](https://github.com/thedragonsinn/ub-core/tree/main/ub_core/default_plugins) already added to it.

> py, sh, shell, ish, load  commands are only accessible by the owner/super users and are only available when DEV_MODE is set to 1 in env.


### Utils
- [Download](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/utils/downloader.py#L31) class with optional live [progress](https://github.com/thedragonsinn/ub-core/blob/80db8c0365a1088fdcddd5a92aa2249e65469e5e/ub_core/utils/helpers.py#L64) on TG.

    You can use this built in downloader to download large files.
    ```python
    from ub_core.utils import Download 
    ```
    
- [Aio](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/utils/aiohttp_tools.py#L15) class with a few useful methods and a static website hosting to pass hosts like koyeb, render etc's health checks. _(site only runs when a port is provided in env using API_PORT var)_
    
    ```python
    # import the instance of Aio that was created on initialisation of core.
    from ub_core.utils import aio
    ```    


### Updater 
The [built in Updater](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/default_plugins/update.py#L82) is made to work directly with the bot repo that integrates the core as well as updating the core.

So running `.update ` will check updates for the current workdir's .git repository i.e your integrated bot's working dir.

To update core run `.update -c`


## Comparing_Branches
The default main branch only has a single client and can be run either as an User or a Bot at a time.

The [dual_mode](https://github.com/thedragonsinn/ub-core/tree/dual_mode) branch on the other hand has a [DualClient](https://github.com/thedragonsinn/ub-core/blob/main/ub_core/core/client.py#L71) that can run both an User and a Bot at the same time.

It also unlocks the possibility of running some commands inline for sudo/supers in their saved messages or DMs where the bot/user is not present to respond on normal text based commands.

> Note: unlike main branch, dual_mode requires database access to save mode data.

## Standalone_Usage
Core can be ran as standalone bot with only the inbuilt modules on owner's access.

Core accepts either a BOT_TOKEN or a SESSION_STRING.
> if you pass in both, only one will be used if the installed branch is main.

For required variables check [sample-config.env](https://github.com/thedragonsinn/ub-core/blob/main/sample-config.env)

Create a config.env or export those vars to environment along with `ENV_VARS` set as 1 to instruct core to fetch vars from environment.

type `run-ub-core` command to start core.
> script is automatically installed when you install core using pip
