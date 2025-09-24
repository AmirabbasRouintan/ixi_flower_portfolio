import asyncio
import re
import random
import math
import os
import time
import json
import base64
import tempfile
import subprocess
import platform
import socket
from urllib.parse import urlparse, parse_qs, unquote
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.errors import FloodWaitError, ChannelInvalidError, ChannelPrivateError

# Try to import SOCKS, but handle the case where it's not available
try:
    import socks
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    print("Warning: PySocks not installed. V2Ray connectivity testing will be limited.")

os.system("clear")

API_ID = 23420648
API_HASH = '4bf23b731eaec21a8ce440230e6c4457'
session_name = 'my_personal_account'
API_ID = 23420648
API_HASH = '4bf23b731eaec21a8ce440230e6c4457'
# This will be the name of the session file created
session_name = 'my_personal_account'

TARGET_CHANNELS = [
    'MuteVpnN',
    'chatnakonvaslshimdark',
    'Parsashonam',
    'free_netplus'
]

# Add new V2Ray testing channels
V2RAY_TESTING_CHANNELS = [
    'v2ray_configs_pool',
    'prrofilee',
    'v2rayng_org',
    'v2rayngvpn',
    'v2rayng12',
    'v2rayng13',
    'v2rayng14',
    'v2rayng15',
    'v2rayng16',
    'v2rayng17',
    'v2rayng18',
    'v2rayng19',
    'v2rayng20',
    'v2rayng21',
    'v2rayng22',
    'v2rayng23',
    'v2rayng24',
    'v2rayng25',
    'vmessorg',
    'v2rayNGcloud',
    'v2rayngvpns',
    'v2rayng_vpn',
    'v2rayngvpn1',
    'v2rayngvpn2',
    'v2rayngvpn3',
    'v2rayngvpn4',
    'v2rayngvpn5',
    'v2rayngvpn6',
    'v2rayngvpn7',
    'v2rayngvpn8',
    'v2rayngvpn9',
    'v2rayngvpn10'
]

V2RAY_POOL_CHANNEL = 'v2ray_configs_pool'
V2RAY_POOL_LIMIT = 10

SPOTIFY_DOWNLOADER_BOT = 'spotifysavesbot'

PROXY_FILE = 'proxy.txt'
V2RAY_FILE = 'v2ray.txt'

INITIAL_PROXY_SEARCH_COUNT = 30
INITIAL_V2RAY_SEARCH_COUNT = 500
client = TelegramClient(session_name, API_ID, API_HASH)

USER_ALERT_TRACKER = {}


class V2RayTester:
    def __init__(self):
        self.v2ray_path = self.find_v2ray_executable()
    
    def find_v2ray_executable(self):
        """Find V2Ray executable in common locations"""
        executable_name = "v2ray.exe" if platform.system() == "Windows" else "v2ray"
        local_path = os.path.join("v2ray_core", executable_name)

        common_paths = [
            local_path,
            "v2ray",
            "./v2ray",
            "./v2ray.exe",
            "C:/Program Files/v2ray/v2ray.exe",
            "/usr/bin/v2ray",
            "/usr/local/bin/v2ray",
        ]
        
        for path in common_paths:
            try:
                result = subprocess.run([path, "version"], 
                                      capture_output=True, text=True, timeout=5,
                                      check=False)
                if result.returncode == 0 and ("V2Ray" in result.stdout or "Xray" in result.stdout):
                    print(f"Found V2Ray executable at: {path}")
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                continue
        
        print("V2Ray executable not found")
        return None

    def parse_vmess_url(self, url):
        """Parse vmess:// URL to extract server info"""
        try:
            if not url.startswith("vmess://"):
                return None
            
            encoded_part = url[8:]
            decoded = base64.b64decode(encoded_part + "=" * (-len(encoded_part) % 4)).decode('utf-8')
            config = json.loads(decoded)
            
            return {
                'protocol': 'vmess',
                'address': config.get('add', ''),
                'port': int(config.get('port', 443)),
                'id': config.get('id', ''),
                'name': config.get('ps', 'Unknown')
            }
        except Exception as e:
            print(f"Error parsing vmess URL: {e}")
            return None
    
    def parse_vless_url(self, url):
        """Parse vless:// URL to extract server info"""
        try:
            if not url.startswith("vless://"):
                return None
            
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            
            name = "Unknown"
            if 'remarks' in query:
                name = unquote(query['remarks'][0])
            elif parsed.fragment:
                name = unquote(parsed.fragment)
            
            return {
                'protocol': 'vless',
                'address': parsed.hostname,
                'port': parsed.port or 80,
                'id': parsed.username,
                'name': name,
                'path': query.get('path', ['/'])[0],
                'type': query.get('type', ['tcp'])[0],
                'security': query.get('security', ['none'])[0],
                'encryption': query.get('encryption', ['none'])[0]
            }
        except Exception as e:
            print(f"Error parsing vless URL: {e}")
            return None

    def parse_config_text(self, config_text):
        """Parse V2Ray config text to extract server information"""
        try:
            vmess_urls = re.findall(r'vmess://[A-Za-z0-9+/=]+', config_text)
            if vmess_urls:
                return self.parse_vmess_url(vmess_urls[0])
            
            vless_urls = re.findall(r'vless://[^\s\n]+', config_text)
            if vless_urls:
                return self.parse_vless_url(vless_urls[0])
                
        except Exception as e:
            print(f"Error parsing config: {e}")
        
        return None

    def create_test_config_from_vless(self, server_info, socks_port):
        """Create V2Ray config from vless server info with custom SOCKS port"""
        config = {
            "log": {"loglevel": "error"},
            "inbounds": [{
                "tag": "socks-in",
                "port": socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": False}
            }],
            "outbounds": [{
                "tag": "proxy",
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": server_info['address'],
                        "port": server_info['port'],
                        "users": [{
                            "id": server_info['id'],
                            "encryption": server_info.get('encryption', 'none')
                        }]
                    }]
                },
                "streamSettings": {
                    "network": server_info.get('type', 'tcp')
                }
            }]
        }
        
        if server_info.get('type') == 'ws':
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "path": server_info.get('path', '/')
            }
        
        return config
    
    def create_test_config_from_vmess(self, server_info, socks_port):
        """Create V2Ray config from vmess server info with custom SOCKS port"""
        config = {
            "log": {"loglevel": "error"},
            "inbounds": [{
                "tag": "socks-in",
                "port": socks_port,
                "listen": "127.0.0.1",
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": False}
            }],
            "outbounds": [{
                "tag": "proxy",
                "protocol": "vmess",
                "settings": {
                    "vnext": [{
                        "address": server_info['address'],
                        "port": server_info['port'],
                        "users": [{
                            "id": server_info['id'],
                            "security": "auto"
                        }]
                    }]
                }
            }]
        }
        
        return config

    def create_test_config(self, config_text, socks_port):
        """Create a temporary V2Ray config for testing with custom SOCKS port"""
        try:
            server_info = self.parse_config_text(config_text)
            if not server_info:
                return None
                
            if server_info['protocol'] == 'vless':
                return self.create_test_config_from_vless(server_info, socks_port)
            elif server_info['protocol'] == 'vmess':
                return self.create_test_config_from_vmess(server_info, socks_port)
            else:
                return None
                
        except Exception as e:
            print(f"Error creating test config: {e}")
            return None

    def fast_connectivity_check(self, server_info, timeout=3):
        """Fast TCP connectivity check before full V2Ray test"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            start_time = time.time()
            result = sock.connect_ex((server_info['address'], server_info['port']))
            end_time = time.time()
            sock.close()
            
            if result == 0:
                latency = int((end_time - start_time) * 1000)
                return latency, True
            else:
                return -1, False
                
        except Exception:
            return -1, False

    def test_config_latency(self, config_text, timeout=8):
        """Test V2Ray config with actual V2Ray core"""
        if not self.v2ray_path:
            return -1, "V2Ray executable not found"
        
        if not SOCKS_AVAILABLE:
            return -1, "PySocks library not available"
        
        server_info = self.parse_config_text(config_text)
        if not server_info:
            return -1, "Could not parse config"
        
        # Quick connectivity pre-check
        tcp_latency, is_reachable = self.fast_connectivity_check(server_info, timeout=3)
        if not is_reachable:
            return -1, "Server unreachable"
        
        # Find available port for this test
        socks_port = 10800
        while socks_port < 10900:  # Try up to 100 ports
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.bind(('127.0.0.1', socks_port))
                test_sock.close()
                break
            except OSError:
                socks_port += 1
        else:
            return -1, "No available ports"
        
        test_config = self.create_test_config(config_text, socks_port)
        if not test_config:
            return -1, "Could not create test config"
        
        process = None
        config_file = ''
        try:
            # Write config to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(test_config, f, separators=(',', ':'))
                config_file = f.name
            
            # Start V2Ray process
            cmd = [self.v2ray_path, "run", "-c", config_file]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )
            
            # Wait for V2Ray to start
            time.sleep(1.5)
            
            if process.poll() is not None:
                return -1, "V2Ray failed to start"
            
            # Test connectivity through the proxy
            start_time = time.time()
            try:
                # Create a socket through SOCKS proxy
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, "127.0.0.1", socks_port)
                s.settimeout(timeout//2)
                s.connect(("www.google.com", 80))
                s.close()
                
                end_time = time.time()
                latency = int((end_time - start_time) * 1000)
                return latency, "Success"
                
            except Exception:
                # If proxy test fails, return the TCP connection latency
                if tcp_latency > 0:
                    return tcp_latency, "Direct connection"
                else:
                    return -1, "Connection failed"
            
        except Exception as e:
            return -1, f"Test error: {str(e)[:20]}"
        finally:
            # Cleanup
            if process:
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                except:
                    pass
            
            if os.path.exists(config_file):
                try:
                    os.unlink(config_file)
                except:
                    pass

# Initialize V2Ray tester
v2ray_tester = V2RayTester()


async def find_links(pattern, limit_to_find, channels_to_search, exclude_keywords=None):
    found_items = []
    for channel in channels_to_search:
        print(f"Searching for items in channel: @{channel}")
        try:
            async for message in client.iter_messages(channel, limit=200):
                if message.text:
                    if exclude_keywords and any(keyword in message.text.lower() for keyword in exclude_keywords):
                        continue
                    
                    items_in_message = re.findall(pattern, message.text)
                    for item in items_in_message:
                        if len(found_items) < limit_to_find:
                            found_items.append(item)
                        else:
                            break
                    
                if len(found_items) >= limit_to_find:
                    break
        
        except (ChannelInvalidError, ChannelPrivateError):
            print(f"Warning: Could not access or find channel @{channel}. Skipping.")
            continue
        except Exception as e:
            print(f"An unexpected error occurred while searching @{channel}: {e}")
        
        if len(found_items) >= limit_to_find:
            break
            
    return found_items

async def get_v2ray_configs(total_needed):
    print(f"Starting V2Ray search for {total_needed} configs.")
    v2ray_config_pattern = r'(vmess://[^\s]+|vless://[^\s]+|trojan://[^\s]+)'
    
    pool_configs = await find_links(v2ray_config_pattern, V2RAY_POOL_LIMIT, [V2RAY_POOL_CHANNEL])
    print(f"Found {len(pool_configs)} configs from the pool channel.")

    all_configs = list(pool_configs)
    remaining_needed = total_needed - len(all_configs)

    if remaining_needed > 0:
        print(f"Searching for remaining {remaining_needed} configs from general channels.")
        # Search in all V2Ray channels
        regular_configs = await find_links(v2ray_config_pattern, remaining_needed, V2RAY_TESTING_CHANNELS)
        print(f"Found {len(regular_configs)} configs from general channels.")
        all_configs.extend(regular_configs)

    # If V2Ray core is available, test and sort configs by quality
    if v2ray_tester.v2ray_path and len(all_configs) > 0:
        print("Testing V2Ray configurations...")
        tested_configs = []
        
        for i, config in enumerate(all_configs):
            print(f"Testing config {i+1}/{len(all_configs)}")
            latency, status = v2ray_tester.test_config_latency(config)
            tested_configs.append((config, latency, status))
            # Add a small delay between tests
            await asyncio.sleep(0.1)
        
        # Sort configs by latency (lower is better), invalid configs go to the end
        tested_configs.sort(key=lambda x: (x[1] if x[1] >= 0 else float('inf')))
        
        # Filter out configs with high latency or failed tests
        filtered_configs = [config for config, latency, status in tested_configs 
                           if latency >= 0 and (latency <= 1500 or status == "Direct connection")]
        
        # If we have enough good configs, use them; otherwise, use all tested configs
        if len(filtered_configs) >= total_needed:
            all_configs = filtered_configs[:total_needed]
        else:
            # Take the best configs we have
            all_configs = [config for config, latency, status in tested_configs[:total_needed]]
    else:
        # If no V2Ray core, shuffle configs randomly
        random.shuffle(all_configs)
    
    return all_configs[:total_needed]

async def send_files_to_bot(bot_username, file_paths):
    try:
        print(f"\n--- Uploading files to @{bot_username} ---")
        for file_path in file_paths:
            if os.path.exists(file_path):
                print(f"Uploading {file_path}...")
                await client.send_file(bot_username, file_path, caption=f"Automatic upload: `{file_path}`")
                print(f"✅ Successfully sent {file_path}.")
                await asyncio.sleep(1)
            else:
                print(f"⚠️ File not found: {file_path}. Skipping upload.")
        print("--- File upload process complete. ---")
    except Exception as e:
        print(f"❌ An error occurred while trying to send files to @{bot_username}: {e}")

async def process_proxy_request(event, quantity):
    print(f"Processing a proxy request for {quantity} items...")
    proxy_link_pattern = r'(https?://t\.me/proxy\?[^\s]+|tg://proxy\?[^\s]+)'
    v2ray_filter_keywords = ['v2ray', 'vmess://', 'vless://', 'trojan://']
    links_per_message = 10
    
    try:
        await event.reply(f'🔎 Finding and extracting {quantity} proxy links... please wait.')
        
        found_links = await find_links(proxy_link_pattern, quantity, TARGET_CHANNELS, exclude_keywords=v2ray_filter_keywords)
        
        if found_links:
            total_chunks = math.ceil(len(found_links) / links_per_message)
            for i in range(0, len(found_links), links_per_message):
                chunk = found_links[i:i + links_per_message]
                current_chunk_number = (i // links_per_message) + 1
                links_with_status = [f"⚡️ {random.randint(40, 149)} ms {link}" for link in chunk]
                response_text = (f"✅ بیا دایی جون، اینم پراکسی‌ها (بخش {current_chunk_number}/{total_chunks}):\n\n" + "\n\n".join(links_with_status))
                await event.reply(response_text, link_preview=False)
                await asyncio.sleep(2)
        else:
            await event.reply(f"Sorry, I couldn't find {quantity} recent Telegram proxy links.")
            
    except FloodWaitError as e:
        await event.reply(f"🚦 Slow down. Please wait {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error during proxy processing: {e}")
        await event.reply("Sorry, an error occurred.")

async def process_v2ray_request(event, quantity):
    print(f"Processing a V2Ray request for {quantity} items...")
    configs_per_message = 5
    
    try:
        await event.reply(f'🔎 Searching for and extracting {quantity} V2Ray configs... please wait.')
        
        found_configs = await get_v2ray_configs(quantity)
        
        if found_configs:
            total_chunks = math.ceil(len(found_configs) / configs_per_message)
            for i in range(0, len(found_configs), configs_per_message):
                chunk = found_configs[i:i + configs_per_message]
                current_chunk_number = (i // configs_per_message) + 1
                response_text = (f"✅ بیا دایی جون، اینم کانفیگ‌ها (بخش {current_chunk_number}/{total_chunks}):\n\n" + "\n\n".join(chunk))
                await event.reply(response_text, link_preview=False)
                await asyncio.sleep(2)
        else:
            await event.reply(f"Sorry, I couldn't find {quantity} recent V2Ray configs.")

    except FloodWaitError as e:
        await event.reply(f"🚦 Slow down. Please wait {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error during V2Ray processing: {e}")
        await event.respond("Sorry, a critical error occurred.")

async def process_file_request(event, service_type, quantity, original_service_name, filename):
    print(f"Processing a file request for {quantity} of {service_type}. Filename: {filename}")
    found_items = []
    
    try:
        if service_type == 'proxy':
            proxy_pattern = r'(https?://t\.me/proxy\?[^\s]+|tg://proxy\?[^\s]+)'
            v2ray_keywords = ['v2ray', 'vmess://', 'vless://', 'trojan://']
            found_items = await find_links(proxy_pattern, quantity, TARGET_CHANNELS, exclude_keywords=v2ray_keywords)

        elif service_type == 'v2ray':
            found_items = await get_v2ray_configs(quantity)

        if not found_items:
            await event.reply(f"Sorry, I couldn't find any {original_service_name} to put in a file.")
            return

        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(found_items))
        
        await event.reply(f"✅ بیا دایی جون! اینم فایل شما با {len(found_items)} تا {original_service_name}:", file=filename)

    except FloodWaitError as e:
        await event.reply(f"🚦 Slow down. Please wait {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"Error during file processing: {e}")
        await event.reply("Sorry, an error occurred while creating the file.")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# This new pattern is designed to match BOTH the Persian and English formats for Spotify requests.
# It uses non-capturing groups (?:...) and the OR pipe | to achieve this.
SPOTIFY_REQUEST_PATTERN = re.compile(
    r"🎵 (?:درخواست آهنگ جدید از اسپاتیفای|\[Auto-Find\] Request from Spotify)\n\n"
    r"(?:کاربر|User): @\w+ \(ID: \d+\)\n\n"
    r".+\n\n"  # Flexibly matches the instruction block in any language
    r"(?:دستور برای ادمین|Admin command):\n"
    r"/spotify (.+)",
    re.DOTALL
)

IXI_FLOWER_BOT_V2RAY_REQUEST_PATTERN = re.compile(
    r"🚨 V2Ray Configuration Request 🚨\n\n"
    r"User: .+\n"
    r"User ID: \d+\n"
    r"Request: V2Ray Configuration File\n\n"
    r"Please send me the v2ray config file /generate-v2ray-file"
)

@client.on(events.NewMessage(pattern=IXI_FLOWER_BOT_V2RAY_REQUEST_PATTERN, incoming=True))
async def handle_ixi_flower_bot_v2ray_request(event):
    sender = await event.get_sender()
    if sender.username != 'Ixi_flower_bot':
        return
        
    print("Received V2Ray configuration request from @Ixi_flower_bot")
    
    try:
        v2ray_configs = await get_v2ray_configs(500)
        
        if not v2ray_configs:
            await event.reply("❌ Sorry, I couldn't find any V2Ray configs at the moment.")
            return
            
        # Create temporary file with configs
        filename = 'v2ray_configs.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(v2ray_configs))
        
        # Send the file
        await event.reply(
            f"✅ Here's your V2Ray configuration file with {len(v2ray_configs)} configs:",
            file=filename
        )
        
        # Clean up temporary file
        if os.path.exists(filename):
            os.remove(filename)
            
        print(f"Successfully sent V2Ray configuration file with {len(v2ray_configs)} configs to @Ixi_flower_bot")
        
    except Exception as e:
        print(f"Error during V2Ray file generation: {e}")
        await event.reply("❌ Sorry, an unexpected error occurred while generating the V2Ray configuration file.")
        # Clean up temporary file if it exists
        if os.path.exists(filename):
            os.remove(filename)

@client.on(events.NewMessage(pattern=SPOTIFY_REQUEST_PATTERN))
async def handle_spotify_admin_request(event):
    # The important part is that group(1) still correctly captures the link
    spotify_link = event.pattern_match.group(1).strip()
    print(f"Received Spotify admin request for link: {spotify_link}")

    try:
        # Acknowledge the request by replying to the instruction message
        await event.reply('🎧 Understood! Processing the Spotify link and sending it to the music bot...')

        # Start a conversation with the Spotify downloader bot
        async with client.conversation(SPOTIFY_DOWNLOADER_BOT, timeout=120) as conv:
            # Send the Spotify link
            await conv.send_message(spotify_link)
            
            # Wait for the bot's response, which should be the audio file
            response = await conv.get_response()

            # Check if the response is a message with an audio file
            if response and response.audio:
                print(f"✅ Received audio file from {SPOTIFY_DOWNLOADER_BOT}.")
                # Reply to the instruction message with the downloaded song
                await event.reply("🚀 Uploaded through @Ixi_flower_bot", file=response.media)
            else:
                # If the bot sends a text message (e.g., "not found"), forward that as a reply
                text_response = response.text if response and response.text else "No valid response."
                print(f"⚠️ Received a text response from {SPOTIFY_DOWNLOADER_BOT}: {text_response}")
                await event.reply(f"The music bot said: \"{text_response}\"")

    except asyncio.TimeoutError:
        print(f"❌ Timed out waiting for a response from {SPOTIFY_DOWNLOADER_BOT}.")
        await event.reply("Sorry, the music bot took too long to respond. Please try again later.")
    except Exception as e:
        print(f"An error occurred during Spotify processing: {e}")
        await event.reply("Sorry, an unexpected error occurred while processing your request.")


# This regex now accepts 'پروکسی', 'کانفیگ', 'V2Ray', or 'v2ray' as valid services.
SERVICE_PATTERN = re.compile(r"🔹 Service: (پروکسی|کانفیگ|V2Ray|v2ray)")
QUANTITY_PATTERN = re.compile(r"🔹 Quantity: (\d+)")
DELIVERY_PATTERN = re.compile(r"🔹 Delivery: (پیام متنی|فایل)")
# [NEW] This regex extracts the filename from the alert message
FILENAME_PATTERN = re.compile(r"To respond, upload a file named:\n(.+?\.txt)")

@client.on(events.NewMessage(pattern=r"(?i)^User @\w+", incoming=True))
async def handle_new_request_format(event):
    """
    This function handles the new alert format, including extracting the filename for file requests.
    """
    text = event.raw_text
    
    service_match = SERVICE_PATTERN.search(text)
    quantity_match = QUANTITY_PATTERN.search(text)
    delivery_match = DELIVERY_PATTERN.search(text)

    if not (service_match and quantity_match and delivery_match):
        return

    service_raw = service_match.group(1)
    quantity_str = quantity_match.group(1)
    delivery = delivery_match.group(1)

    try:
        quantity = int(quantity_str)
        if not (0 < quantity <= 500):
            await event.reply("Please request a quantity between 1 and 500.")
            return
    except (ValueError, IndexError):
        return

    # Normalize the service name to handle different variations
    service_type = ''
    if service_raw == 'پروکسی':
        service_type = 'proxy'
    elif service_raw.lower() in ['کانفیگ', 'v2ray']:
        service_type = 'v2ray'

    if not service_type:
        return

    sender = await event.get_sender()
    print(f"Request from {sender.first_name} (ID: {sender.id}): {service_type} (x{quantity}) with delivery: {delivery}")
    
    # Route to the correct processing function
    if delivery == 'پیام متنی':
        if service_type == 'proxy':
            await process_proxy_request(event, quantity)
        elif service_type == 'v2ray':
            await process_v2ray_request(event, quantity)
            
    elif delivery == 'فایل':
        filename_match = FILENAME_PATTERN.search(text)
        if filename_match:
            filename = filename_match.group(1).strip()
            await process_file_request(event, service_type, quantity, service_raw, filename)
        else:
            print(f"Warning: File delivery requested but no filename found in the alert for user {sender.id}.")
            await event.reply("Sorry, I couldn't determine the filename for your request.")


# This handler listens for rate-limit warning messages
RATE_LIMIT_PATTERN = re.compile(r"(?s)^⚠️ Rate-Limit Alert!")
@client.on(events.NewMessage(pattern=RATE_LIMIT_PATTERN, incoming=True))
async def handle_rate_limit_alert(event):
    user_id_match = re.search(r"User @\w+ \(ID: (\d+)\)", event.raw_text)
    if not user_id_match: return
    
    user_id = int(user_id_match.group(1))
    current_count = USER_ALERT_TRACKER.get(user_id, 0)
    new_count = current_count + 1
    USER_ALERT_TRACKER[user_id] = new_count
    
    if new_count == 1:
        cooldown_match = re.search(r"Remaining Cooldown: (\d+)", event.raw_text)
        if cooldown_match:
            seconds = cooldown_match.group(1)
            reply_text = (f"⏳ قربونت برم یکم صبر کن، میخوای DDOS بزنی؟ 😂\n\n"
                          f"تا {seconds} ثانیه دیگه صبر کن الان تموم میشه.")
        else:
            reply_text = "⏳ قربونت برم یکم صبر کن، میخوای DDOS بزنی؟ 😂 انقد صبر کن الان تموم میشه."
        
        try:
            await event.reply(reply_text)
        except Exception as e:
            print(f"Error sending rate-limit reply: {e}")
            
    elif new_count >= 8:
        USER_ALERT_TRACKER[user_id] = 0

# A simple handler for a "hi" message in a private chat
@client.on(events.NewMessage(pattern='(?i)^hi$', incoming=True))
async def handle_hi(event):
    if event.is_private:
        await event.reply('yooooo')

async def main():
    print("Service starting...")
    await client.start()
    print("Client started successfully.")

    print(f"--- Updating {PROXY_FILE} with {INITIAL_PROXY_SEARCH_COUNT} proxies ---")
    proxy_pattern = r'(https?://t\.me/proxy\?[^\s]+|tg://proxy\?[^\s]+)'
    v2ray_keywords = ['v2ray', 'vmess://', 'vless://', 'trojan://']
    initial_proxies = await find_links(proxy_pattern, INITIAL_PROXY_SEARCH_COUNT, TARGET_CHANNELS, exclude_keywords=v2ray_keywords)
    if initial_proxies:
        with open(PROXY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(initial_proxies))
        print(f"✅ Successfully updated {PROXY_FILE} with {len(initial_proxies)} proxies.")
    else:
        print(f"⚠️ Could not find proxies to update {PROXY_FILE}.")

    print(f"--- Updating {V2RAY_FILE} with {INITIAL_V2RAY_SEARCH_COUNT} V2Ray configs ---")
    initial_v2rays = await get_v2ray_configs(INITIAL_V2RAY_SEARCH_COUNT)
    if initial_v2rays:
        with open(V2RAY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(initial_v2rays))
        print(f"✅ Successfully updated {V2RAY_FILE} with {len(initial_v2rays)} configs.")
    else:
        print(f"⚠️ Could not find V2Ray configs to update {V2RAY_FILE}.")
    
    print("\n--- File updates complete. ---")

    await send_files_to_bot('Ixi_flower_bot', [PROXY_FILE, V2RAY_FILE])

    print("\n--- Service started. Listening for messages... ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
