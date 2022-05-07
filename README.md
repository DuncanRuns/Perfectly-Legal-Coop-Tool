# Perfectly Legal Coop Tool
Minecraft Speedrunning Coop Tool to share a clipboard for the use of [Ninjabrain Bot](https://github.com/Ninjabrain1/Ninjabrain-Bot) and a world upload compatible with a [HiveLoad](https://github.com/DuncanRuns/HiveLoad) server.

![image](https://user-images.githubusercontent.com/59705125/167260060-c169e018-09d3-4a9b-9066-4e1a36c5e00a.png)

## Features

- Separate client and server.
- Coop Clipboard
    - `Receive Clipboard` requires no password; if enabled, it will only copy the server's shared clipboard **when updated** (not constantly).
    - `Send Clipboard` requires a password; if enabled with the correct password, a copied minecraft overworld position command (f3+c) will be sent to the server.
- World Upload
    - A `MultiMC Instances Folder` can be set for use of world uploading.
    - The `Upload Latest World` button uploads the latest world to the connected server; if the password is correct, the server will store the world in an upload folder. This will fail if no `MultiMC Instances Folder` is set, or if not connected to a server.
    - The `Test` button shows what the latest world currently is without uploading. This will fail if no `MultiMC Instances Folder` is set.
