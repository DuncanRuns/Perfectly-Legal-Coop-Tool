# Perfectly Legal Coop Tool
Minecraft Speedrunning Coop Tool to share a clipboard for the use of [Ninjabrain Bot](https://github.com/Ninjabrain1/Ninjabrain-Bot) and a world upload compatible with a [HiveLoad](https://github.com/DuncanRuns/HiveLoad) server.

![image](https://user-images.githubusercontent.com/59705125/168005385-10b7f4d9-6a3b-43ce-8387-d95c49bbf4c7.png)


## Features

- Separate client and server.
- Coop Clipboard
    - `Receive Clipboard` requires no password; if enabled, it will only copy the server's shared clipboard **when updated** (not constantly).
    - `Send Clipboard` requires a password; if enabled with the correct password, a copied minecraft overworld position command (f3+c) will be sent to the server.
- World Upload
    - **(Windows Only)** `Use Latest Window` can be enabled to get the  instance folder from the latest selected Minecraft window.
    - A `MultiMC Instances Folder` can be set for use of world uploading. This is only available  if `Use Latest Window` is disabled.
    - The `Upload Latest World` button uploads the latest world to the connected server; if the password is correct, the server will store the world in an upload folder. This will fail if not connected to a server. If `Use Latest Window` is disabled, this will fail if no `MultiMC Instances Folder` is set. If `Use Latest Window` is enabled, this will fail if no Minecraft window is found.
    - The `Test` button shows what the latest world currently is without uploading. If `Use Latest Window` is disabled, this will fail if no `MultiMC Instances Folder` is set. If `Use Latest Window` is enabled, this will fail if no Minecraft window is found.
