import requests, os, psutil, sys, jwt, pickle, json, binascii, time, urllib3, base64, datetime, re, socket, threading, ssl, pytz, aiohttp, asyncio, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from protobuf_decoder.protobuf_decoder import Parser
from xC4 import *
from xHeaders import *
from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from threading import Thread, Lock
from Pb2 import DEcwHisPErMsG_pb2, MajoRLoGinrEs_pb2, PorTs_pb2, MajoRLoGinrEq_pb2, sQ_pb2, Team_msg_pb2
from cfonts import render, say
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ADMIN_UID = "760840390"
COMMAND_PREFIX = "/"
BOT_NAME = "AlliFF BOT"
OWNER_NAME = "AlliFF"
OWNER_TELEGRAM = "@AlliFF_BOT"
HELP_MSG_1 = ""
HELP_MSG_2 = ""
ADMIN_MSG = ""
ONLINE_MSG = ""
EMOJI_MSG = ""

# متغيرات لتخزين إعدادات APIs المخصصة من config.json
CUSTOM_APIS = {}
current_config = {}

def load_config():
    global ADMIN_UID, BOT_NAME, OWNER_NAME, OWNER_TELEGRAM, HELP_MSG_1, HELP_MSG_2, ADMIN_MSG, ONLINE_MSG, EMOJI_MSG, SUCCESS_MSG, ERROR_MSG, PROCESSING_MSG, CUSTOM_COMMANDS, SYSTEM_MESSAGES, COMMAND_PREFIX, current_config, CUSTOM_APIS
    try:
        if os.path.exists('config.json'):
            with open('config.json', 'r', encoding='utf-8') as f:
                current_config = json.load(f)
                config = current_config
                ADMIN_UID = str(config.get('admin_uid', ADMIN_UID))
                BOT_NAME = config.get('bot_name', BOT_NAME)
                OWNER_NAME = config.get('owner_name', OWNER_NAME)
                OWNER_TELEGRAM = config.get('owner_telegram', OWNER_TELEGRAM)
                COMMAND_PREFIX = config.get("command_prefix", "/")
                CUSTOM_COMMANDS = config.get("commands", {})
                SYSTEM_MESSAGES = config.get("system_messages", {})
                
                # تحميل إعدادات APIs المخصصة من config.json
                CUSTOM_APIS = config.get("custom_apis", {})
                print(f"[CONFIG] Loaded {len(CUSTOM_APIS)} custom APIs from config.json")
                
                messages = config.get('messages', {})
                HELP_MSG_1 = messages.get('help_msg_1', "")
                HELP_MSG_2 = messages.get('help_msg_2', "")
                
                raw_admin_msg = messages.get('admin_msg', "")
                try:
                    ADMIN_MSG = raw_admin_msg.format(owner_name=OWNER_NAME, owner_telegram=OWNER_TELEGRAM)
                except:
                    ADMIN_MSG = raw_admin_msg
                
                raw_online_msg = messages.get('online_msg', "")
                try:
                    ONLINE_MSG = raw_online_msg.format(bot_name=BOT_NAME, color=get_random_color())
                except:
                    ONLINE_MSG = raw_online_msg
                
                EMOJI_MSG = messages.get('emoji_msg', "")
                
                SUCCESS_MSG = SYSTEM_MESSAGES.get("success_msg", "[B][C][00FF00]✅ DoNe")
                ERROR_MSG = SYSTEM_MESSAGES.get("error_msg", "[B][C][FF0000]❌ ERORR")
                PROCESSING_MSG = SYSTEM_MESSAGES.get("global_wait", "[B][C][FFFF00]⏳ Processing your request...")
                
                print(f"[CONFIG] Loaded configuration for {BOT_NAME}")
                return config
    except Exception as e:
        print(f"[CONFIG] Error loading config.json: {e}")
    return {}

def get_api_config(cmd_name):
    """الحصول على إعدادات API من config.json (إذا وجدت) أو من الإعدادات الافتراضية"""
    # الأولوية للإعدادات المخصصة من config.json
    if cmd_name in CUSTOM_APIS and CUSTOM_APIS[cmd_name].get("url"):
        return CUSTOM_APIS[cmd_name]
    
    # إعدادات افتراضية (تستخدم فقط إذا لم توجد إعدادات في config.json)
    DEFAULT_APIS = {
        "mk": {"url": "https://ragnar-mk-spm-production.up.railway.app/spam?user_id={id}", "success_keyword": "success"},
        "stop_mk": {"url": "https://ragnar-mk-spm-production.up.railway.app/stop?user_id={id}", "success_keyword": "success"},
        "spam": {"url": "https://ragnar-mk-spm-production.up.railway.app/spam?user_id={id}", "success_keyword": "success"},
        "stop_spam": {"url": "https://ragnar-mk-spm-production.up.railway.app/stop?user_id={id}", "success_keyword": "success"},
        "ghost": {"url": "http://alliff-d5m-api-ghost.hf.space/api/ghost?teamcode={team_code}&name={name}", "success_keyword": "success"},
        "lag_ghost": {"url": "http://alliff-d5m-api-ghost.hf.space/api/ghost_attack?teamcode={team_code}&name={name}", "success_keyword": "success"},
        "msg": {"url": "http://91.99.5.210:8005/msg?teamcode={team_code}&msg={message}", "success_keyword": "success"},
        "friends": {"url": "http://alliff-d5m-friends.hf.space/spam?uid={uid}", "success_keyword": "success"},
        "sp_clan": {"url": "http://alliff-d5m-clan.hf.space/SpamClan?clan_id={clan_id}", "success_keyword": "success"}
    }
    return DEFAULT_APIS.get(cmd_name, {})

def get_system_msg(cmd_name, type):
    key = f"{cmd_name}_{type}"
    if key in SYSTEM_MESSAGES:
        return SYSTEM_MESSAGES[key]
    if type == "success": return SUCCESS_MSG
    if type == "error": return ERROR_MSG
    return PROCESSING_MSG

def check_cmd(msg, name):
    full = CUSTOM_COMMANDS.get(name, COMMAND_PREFIX + name)
    return msg.strip().startswith(full)

def get_args(msg, name):
    full = CUSTOM_COMMANDS.get(name, COMMAND_PREFIX + name)
    return msg.strip()[len(full):].strip()



server2 = "ME"
key2 = "winter"
BYPASS_TOKEN = ""
attack_running = False
attack_teamcode = None
stop_attack = False
attack_task = None
attack_duration = 45
attack_delay = 0.15

online_writer = None
whisper_writer = None
spam_room = False
spammer_uid = None
spam_chat_id = None
spam_uid = None
Spy = False
Chat_Leave = False
is_muted = False
mute_until = 0
spam_requests_sent = 0
bot_start_time = time.time()

connection_pool = None
command_cache = {}
last_request_time = {}
RATE_LIMIT_DELAY = 0.1
MAX_CACHE_SIZE = 50
CLEANUP_INTERVAL = 300

command_stats = {}

EMOTE_DATA = None

active_requests = 0
max_concurrent_requests = 5
request_lock = Lock()

maintenance_mode = False

def load_emote_data():
    global EMOTE_DATA
    try:
        with open('emote.json', 'r', encoding='utf-8') as f:
            EMOTE_DATA = json.load(f)
        print(f"[INFO] Loaded {len(EMOTE_DATA)} emotes from emote.json")
    except Exception as e:
        print(f"[ERROR] Failed to load emote.json: {e}")
        EMOTE_DATA = []

def cleanup_cache():
    current_time = time.time()
    to_remove = [k for k, v in last_request_time.items() 
                 if current_time - v > CLEANUP_INTERVAL]
    for k in to_remove:
        last_request_time.pop(k, None)
    
    if len(command_cache) > MAX_CACHE_SIZE:
        oldest_keys = sorted(command_cache.keys())[:len(command_cache)//2]
        for key in oldest_keys:
            command_cache.pop(key, None)

def get_rate_limited_response(user_id):
    user_key = str(user_id)
    current_time = time.time()
    
    if user_key in last_request_time:
        time_since_last = current_time - last_request_time[user_key]
        if time_since_last < RATE_LIMIT_DELAY:
            return False
    
    last_request_time[user_key] = current_time
    return True

async def update_tokens():
    try:
        update_response = requests.get(
            "https://api-like-alliff-v3.vercel.app/reload_tokens",
            timeout=30
        )
        if update_response.status_code == 200:
            data = update_response.json()
            print(f"[TOKEN UPDATE] {data.get('message', 'Tokens updated')}")
            return True
        return False
    except:
        print("[TOKEN UPDATE] Failed to update tokens")
        return False

async def update_tokens_background():
    try:
        await asyncio.sleep(1)
        success = await update_tokens()
        if success:
            print("[BACKGROUND] Tokens updated successfully")
        else:
            print("[BACKGROUND] Token update failed")
    except Exception as e:
        print(f"[BACKGROUND] Error updating tokens: {e}")

def send_likes(uid):
    try:
        print(f"[DEBUG] Sending like request for UID: {uid}")
        likes_api_response = requests.get(
            f"http://alliff-d5m-api-like.hf.space/like?uid={uid}",
            timeout=30
        )
        
        print(f"[DEBUG] API Response Status: {likes_api_response.status_code}")
        
        if likes_api_response.status_code == 200:
            data = likes_api_response.json()
            
            status = data.get("status")
            
            if status == 1:
                nickname = data.get("PlayerNickname", "Unknown")
                likes_before = data.get("LikesBefore", 0)
                likes_after = data.get("LikesAfter", 0)
                likes_added = data.get("LikesGivenByAPI", 0)
                
                if likes_added == 0:
                    response = get_system_msg("like", "limit")
                else:
                    response = f"""[00FF00]✅ Likes Sent Successfully"""
                
                print(f"[DEBUG] Success response: {response}")
                return response
                
            elif status == 2:
                response = get_system_msg("like", "limit")
                print(f"[DEBUG] Limit response: {response}")
                return response
                
            else:
                response = f"[FF0000]❌ API Error: Status {data.get('status', 'Unknown')}"
                print(f"[DEBUG] API error response: {response}")
                return response
                
        else:
            response = f"[FF0000]Like API Error: {likes_api_response.status_code}"
            print(f"[DEBUG] HTTP error response: {response}")
            return response
            
    except Exception as e:
        response = f"[FF0000]Like API connection failed: {str(e)}"
        print(f"[DEBUG] Connection error response: {response}")
        return response

async def send_emote_packet_fixed(target_uid, emote_id, key, iv, region=None):
    try:
        emote_packet = await send_emote_packet(target_uid, emote_id, key, iv)
        return emote_packet
    except TypeError:
        emote_packet = await send_emote_packet(target_uid, emote_id, key, iv, region)
        return emote_packet

Hr = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': 'v1 1',
    'ReleaseVersion': "OB53"
}

def get_random_color():
    colors = [
        "[FF0000]", "[00FF00]", "[0000FF]", "[FFFF00]", "[FF00FF]", "[00FFFF]", "[FFFFFF]", "[FFA500]",
        "[DC143C]", "[00CED1]", "[9400D3]", "[F08080]", "[20B2AA]", "[FF1493]", "[7CFC00]", "[B22222]",
        "[FF4500]", "[DAA520]", "[00BFFF]", "[00FF7F]", "[4682B4]", "[6495ED]", "[DDA0DD]", "[E6E6FA]",
        "[2E8B57]", "[3CB371]", "[6B8E23]", "[808000]", "[B8860B]", "[CD5C5C]", "[8B0000]", "[FF6347]"
    ]
    return random.choice(colors)

def is_admin(uid):
    return str(uid) == ADMIN_UID

def set_maintenance_mode(enable):
    global maintenance_mode
    maintenance_mode = enable
    return maintenance_mode

def is_maintenance_mode():
    return maintenance_mode

def is_bot_muted():
    global is_muted, mute_until
    if is_muted and time.time() < mute_until:
        return True
    elif is_muted and time.time() >= mute_until:
        is_muted = False
        mute_until = 0
        return False
    return False

def update_command_stats(command):
    if command not in command_stats:
        command_stats[command] = 0
    command_stats[command] += 1

async def check_concurrent_limit():
    global active_requests
    with request_lock:
        if active_requests >= max_concurrent_requests:
            return False
        active_requests += 1
        return True

def release_request():
    global active_requests
    with request_lock:
        if active_requests > 0:
            active_requests -= 1

async def encrypted_proto(encoded_hex):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_message = pad(encoded_hex, AES.block_size)
    encrypted_payload = cipher.encrypt(padded_message)
    return encrypted_payload
    
async def GeNeRaTeAccEss(uid , password):
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"}
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"}
    try:
        async with connection_pool.post(url, headers=Hr, data=data) as response:
            if response.status != 200: 
                return "Failed to get access token"
            data = await response.json()
            open_id = data.get("open_id")
            access_token = data.get("access_token")
            return (open_id, access_token) if open_id and access_token else (None, None)
    except:
        return (None, None)

async def EncRypTMajoRLoGin(open_id, access_token):
    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire"
    major_login.platform_id = 1
    major_login.client_version = "1.123.1"
    major_login.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Verizon"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1920
    major_login.screen_height = 1080
    major_login.screen_dpi = "280"
    major_login.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    major_login.memory = 3003
    major_login.gpu_renderer = "Adreno (TM) 640"
    major_login.gpu_version = "OpenGL ES 3.1 v1.46"
    major_login.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    major_login.client_ip = "223.191.51.89"
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.device_type = "Handheld"
    memory_available = major_login.memory_available
    memory_available.version = 55
    memory_available.hidden_value = 81
    major_login.access_token = access_token
    major_login.platform_sdk_id = 1
    major_login.network_operator_a = "Verizon"
    major_login.network_type_a = "WIFI"
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.external_storage_total = 36235
    major_login.external_storage_available = 31335
    major_login.internal_storage_total = 2519
    major_login.internal_storage_available = 703
    major_login.game_disk_storage_available = 25010
    major_login.game_disk_storage_total = 26628
    major_login.external_sdcard_avail_storage = 32992
    major_login.external_sdcard_total_storage = 36235
    major_login.login_by = 3
    major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    major_login.channel_type = 3
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019118695"
    major_login.graphics_api = "OpenGLES2"
    major_login.supported_astc_bitset = 16383
    major_login.login_open_id_type = 4
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = 13564
    major_login.release_channel = "android"
    major_login.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    major_login.android_engine_init_flag = 110009
    major_login.if_push = 1
    major_login.is_vpn = 1
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    string = major_login.SerializeToString()
    return await encrypted_proto(string)

async def MajorLogin(payload):
    url = "https://loginbp.ggpolarbear.com/MajorLogin"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    try:
        async with connection_pool.post(url, data=payload, headers=Hr, ssl=ssl_context) as response:
            if response.status == 200: 
                return await response.read()
            return None
    except:
        return None


async def GetLoginData(base_url, payload, token):
    url = f"{base_url}/GetLoginData"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    Hr['Authorization']= f"Bearer {token}"
    try:
        async with connection_pool.post(url, data=payload, headers=Hr, ssl=ssl_context) as response:
            if response.status == 200: 
                return await response.read()
            return None
    except:
        return None

async def DecRypTMajoRLoGin(MajoRLoGinResPonsE):
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(MajoRLoGinResPonsE)
    return proto

async def DecRypTLoGinDaTa(LoGinDaTa):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(LoGinDaTa)
    return proto

async def DecodeWhisperMessage(hex_packet):
    packet = bytes.fromhex(hex_packet)
    proto = DEcwHisPErMsG_pb2.DecodeWhisper()
    proto.ParseFromString(packet)
    return proto
    
async def decode_team_packet(hex_packet):
    packet = bytes.fromhex(hex_packet)
    proto = sQ_pb2.recieved_chat()
    proto.ParseFromString(packet)
    return proto
    
async def xAuThSTarTuP(TarGeT, token, timestamp, key, iv):
    uid_hex = hex(TarGeT)[2:]
    uid_length = len(uid_hex)
    encrypted_timestamp = await DecodE_HeX(timestamp)
    encrypted_account_token = token.encode().hex()
    encrypted_packet = await EnC_PacKeT(encrypted_account_token, key, iv)
    encrypted_packet_length = hex(len(encrypted_packet) // 2)[2:]
    if uid_length == 9: 
        headers = '0000000'
    elif uid_length == 8: 
        headers = '00000000'
    elif uid_length == 10: 
        headers = '000000'
    elif uid_length == 7: 
        headers = '000000000'
    else: 
        print('Unexpected length') 
        headers = '0000000'
    return f"0115{headers}{uid_hex}{encrypted_timestamp}00000{encrypted_packet_length}{encrypted_packet}"
     
async def cHTypE(H):
    if not H: 
        return 'Squid'
    elif H == 1: 
        return 'CLan'
    elif H == 2: 
        return 'PrivaTe'
    
async def SEndMsG(H , message , Uid , chat_id , key , iv):
    TypE = await cHTypE(H)
    if TypE == 'Squid': 
        msg_packet = await xSEndMsgsQ(message , chat_id , key , iv)
    elif TypE == 'CLan': 
        msg_packet = await xSEndMsg(message , 1 , chat_id , chat_id , key , iv)
    elif TypE == 'PrivaTe': 
        msg_packet = await xSEndMsg(message , 2 , Uid , Uid , key , iv)
    return msg_packet

async def SEndPacKeT(OnLinE , ChaT , TypE , PacKeT):
    if TypE == 'ChaT' and ChaT: 
        whisper_writer.write(PacKeT) 
        await whisper_writer.drain()
    elif TypE == 'OnLine': 
        online_writer.write(PacKeT) 
        await online_writer.drain()
    else: 
        return 'UnsoPorTed TypE ! >> ErrrroR (:():' 

async def handle_friend_request_accepted(inviter_id, key, iv, current_chat_type, current_chat_id):
    welcome_message = f"""[C][B][FFD700]╔══════════════════════════╗
[FFFFFF]Thanks for accepting friend request
[FFFFFF]To know the commands list 
[FFFFFF]Send me any emoji you have 
[FFD700]╠══════════════════════════╣
[FF0000]DEV : @AlliFF_BOT
[FFD700]╚══════════════════════════╝"""
    
    P = await SEndMsG(current_chat_type, welcome_message, inviter_id, current_chat_id, key, iv)
    return P

async def handle_emoji_received(sender_id, key, iv, current_chat_type, current_chat_id):
    response_message = EMOJI_MSG if EMOJI_MSG else f"""[C][B][00FFFF]────────────────────
[33FFF3][b][c]To know the commands enter:
[99FF80][c][b]/help
[00FFFF]────────────────────
[C][B][FFD700]⚡ Only AlliFF YT 2K
[00FFFF]────────────────────"""
    
    P = await SEndMsG(current_chat_type, response_message, sender_id, current_chat_id, key, iv)
    return P

async def attack_loop(team_code, uid, chat_id, chat_type, key, iv, region):
    global attack_running, stop_attack
    
    print(f"[ATTACK] Starting attack on team {team_code}")
    
    try:
        initial_msg = f"[B][C][FF0000]⚔️ Starting Attack Mode!\n🎯 Target Team: {team_code}\n⏰ Duration: {attack_duration} seconds"
        P = await SEndMsG(chat_type, initial_msg, uid, chat_id, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        
        start_packet = await FS(key, iv)
        leave_packet = await ExiT(None, key, iv)
        
        attack_start_time = time.time()
        cycle_count = 0
        
        while time.time() - attack_start_time < attack_duration and not stop_attack:
            try:
                join_packet = await GenJoinSquadsPacket(team_code, key, iv)
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
                await asyncio.sleep(0.1)
                
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', start_packet)
                await asyncio.sleep(0.1)
                
                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave_packet)
                
                cycle_count += 1
                
                if cycle_count % 10 == 0:
                    elapsed = int(time.time() - attack_start_time)
                    progress_msg = f"[B][C][FFA500]⚔️ Attack Progress\n🔁 Cycles: {cycle_count}\n⏱️ Time: {elapsed}/{attack_duration}s"
                    P = await SEndMsG(chat_type, progress_msg, uid, chat_id, key, iv)
                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                
                await asyncio.sleep(attack_delay)
                
            except Exception as e:
                print(f"[ATTACK] Error in cycle {cycle_count}: {e}")
                await asyncio.sleep(0.5)
        
        if stop_attack:
            completion_msg = f"[B][C][FF0000]🛑 Attack Stopped!\n🎯 Team: {team_code}\n🔁 Cycles Completed: {cycle_count}"
        else:
            completion_msg = f"[B][C][00FF00]✅ Attack Completed!\n🎯 Team: {team_code}\n🔁 Total Cycles: {cycle_count}\n⏱️ Duration: {attack_duration}s"
        
        P = await SEndMsG(chat_type, completion_msg, uid, chat_id, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        
    except Exception as e:
        print(f"[ATTACK] Error in attack_loop: {e}")
        error_msg = f"[B][C][FF0000]❌ Attack Error: {str(e)}"
        P = await SEndMsG(chat_type, error_msg, uid, chat_id, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    finally:
        attack_running = False
        stop_attack = False
        print(f"[ATTACK] Attack loop stopped for team {team_code}")

async def handle_squad_with_id_command(squad_size, target_id, sender_uid, current_chat_type, current_chat_id, key, iv, region):
    try:
        print(f"[SQUAD] Creating {squad_size}-player squad and inviting {target_id}")
        
        PAc = await OpEnSq(key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', PAc)
        
        await asyncio.sleep(1)
        
        C = await cHSq(squad_size, sender_uid, key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', C)
        
        await asyncio.sleep(1)
        
        V_target = await SEnd_InV(squad_size, target_id, key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', V_target)
        
        V_sender = await SEnd_InV(squad_size, sender_uid, key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', V_sender)
        
        await asyncio.sleep(5)
        
        E = await ExiT(None, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', E)
        
        await asyncio.sleep(2)
        change_to_solo = await cHSq(1, sender_uid, key, iv, region)
        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', change_to_solo)
        
        P = await SEndMsG(current_chat_type, f"[B][C][00FF00]✅ Done", sender_uid, current_chat_id, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        
        return True
        
    except Exception as e:
        print(f"[SQUAD] Error: {e}")
        P = await SEndMsG(current_chat_type, get_system_msg("squad", "error"), sender_uid, current_chat_id, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return False

async def TcPOnLine(ip, port, key, iv, AutHToKen, reconnect_delay=0.5):
    global online_writer , spam_room , whisper_writer , spammer_uid , spam_chat_id , spam_uid , XX , uid , Spy,data2, Chat_Leave
    while True:
        try:
            reader , writer = await asyncio.open_connection(ip, int(port))
            online_writer = writer
            bytes_payload = bytes.fromhex(AutHToKen)
            online_writer.write(bytes_payload)
            await online_writer.drain()
            while True:
                data2 = await reader.read(9999)
                if not data2: 
                    break
                
                if data2.hex().startswith('0500') and len(data2.hex()) > 1000:
                    try:
                        packet = await DeCode_PackEt(data2.hex()[10:])
                        packet = json.loads(packet)
                        OwNer_UiD , CHaT_CoDe , SQuAD_CoDe = await GeTSQDaTa(packet)

                        JoinCHaT = await AutH_Chat(3 , OwNer_UiD , CHaT_CoDe, key,iv)
                        await SEndPacKeT(whisper_writer , online_writer , 'ChaT' , JoinCHaT)

                        message = f'[B][C]{get_random_color()}\n🎯 AlliFF BOT Online!\n[B][C][00FF00]Commands: Use /help'
                        P = await SEndMsG(0 , message , OwNer_UiD , OwNer_UiD , key , iv)
                        await SEndPacKeT(whisper_writer , online_writer , 'ChaT' , P)

                    except Exception as e:
                        pass

            online_writer.close() 
            await online_writer.wait_closed() 
            online_writer = None

        except Exception as e: 
            print(f"- ErroR With {ip}:{port} - {e}") 
            online_writer = None
        await asyncio.sleep(reconnect_delay)

async def process_command_async(func, *args, **kwargs):
    can_process = await check_concurrent_limit()
    if not can_process:
        return {"status": "busy", "message": "Bot is busy. Please try again later."}
    
    try:
        result = await func(*args, **kwargs)
        return result
    finally:
        release_request()

# ==================== دوال الأوامر التي تستخدم APIs من config.json ====================

async def call_api(url, success_keyword, params):
    """دالة عامة لاستدعاء API مع دعم الرد النصي أو JSON"""
    formatted_url = url.format(**params)
    print(f"[API] Calling: {formatted_url}")
    
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(formatted_url, timeout=timeout) as resp:
                text = await resp.text()
                print(f"[API] Response ({resp.status}): {text[:200]}")
                
                if resp.status == 200:
                    try:
                        data = await resp.json()
                        if success_keyword in str(data).lower():
                            return True, data
                        if data.get("status") == success_keyword:
                            return True, data
                        if data.get("success") == True or data.get("success") == "true":
                            return True, data
                        if data.get("xS") == True:
                            return True, data
                        return False, data
                    except:
                        if success_keyword.lower() in text.lower():
                            return True, {"message": text}
                        return False, {"message": text}
                else:
                    print(f"[API] HTTP Error: {resp.status}")
                    return False, {"error": f"HTTP {resp.status}"}
    except asyncio.TimeoutError:
        print(f"[API] Timeout error for {formatted_url}")
        return False, {"error": "Timeout"}
    except Exception as e:
        print(f"[API] Error: {e}")
        return False, {"error": str(e)}

async def mk_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("mk")
    print(f'[MK] Called by {user_id}')
    
    processing_msg = get_system_msg("mk", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 2:
        P = await SEndMsG(chat_type_param, get_system_msg("mk", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    target_id = parts[1]
    if not target_id.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("mk", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    # الحصول على إعدادات API من config.json
    api_config = get_api_config("mk")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("mk", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"id": target_id})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("mk", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("mk", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def stop_mk_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("stop_mk")
    print(f'[STOP_MK] Called by {user_id}')
    
    processing_msg = get_system_msg("stop_mk", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 2:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_mk", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    target_id = parts[1]
    if not target_id.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("stop_mk", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("stop_mk")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_mk", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"id": target_id})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_mk", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_mk", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def spam_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("spam")
    print(f'[SPAM] Called by {user_id}')
    
    processing_msg = get_system_msg("spam", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 2:
        P = await SEndMsG(chat_type_param, get_system_msg("spam", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    target_id = parts[1]
    if not target_id.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("spam", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("spam")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("spam", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"id": target_id})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("spam", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("spam", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def stop_spam_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("stop_spam")
    print(f'[STOP_SPAM] Called by {user_id}')
    
    processing_msg = get_system_msg("stop_spam", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 2:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_spam", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    target_id = parts[1]
    if not target_id.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("stop_spam", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("stop_spam")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_spam", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"id": target_id})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_spam", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("stop_spam", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def ghost_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("ghost")
    print(f'[GHOST] Called by {user_id}')
    
    processing_msg = get_system_msg("ghost", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 3:
        P = await SEndMsG(chat_type_param, get_system_msg("ghost", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    team_code = parts[1]
    name = parts[2]
    
    if not team_code.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("ghost", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("ghost")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("ghost", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"team_code": team_code, "name": name})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("ghost", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("ghost", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def lag_ghost_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("lag_ghost")
    print(f'[LAG_GHOST] Called by {user_id}')
    
    processing_msg = get_system_msg("lag_ghost", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 3:
        P = await SEndMsG(chat_type_param, get_system_msg("lag_ghost", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    team_code = parts[1]
    name = parts[2]
    
    if not team_code.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("lag_ghost", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("lag_ghost")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("lag_ghost", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"team_code": team_code, "name": name})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("lag_ghost", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("lag_ghost", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def msg_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("msg")
    print(f'[MSG] Called by {user_id}')
    
    processing_msg = get_system_msg("msg", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 3:
        P = await SEndMsG(chat_type_param, get_system_msg("msg", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    team_code = parts[1]
    message = ' '.join(parts[2:])
    
    if not team_code.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("msg", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("msg")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("msg", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"team_code": team_code, "message": message})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("msg", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("msg", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def friends_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("friends")
    print(f'[FRIENDS] Called by {user_id}')
    
    processing_msg = get_system_msg("friends", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 2:
        P = await SEndMsG(chat_type_param, get_system_msg("friends", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    target_uid = parts[1]
    if not target_uid.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("friends", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("friends")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("friends", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"uid": target_uid})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("friends", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("friends", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

async def sp_clan_task(user_id, chat_id_param, chat_type_param, msg):
    update_command_stats("sp_clan")
    print(f'[SP_CLAN] Called by {user_id}')
    
    processing_msg = get_system_msg("sp_clan", "processing")
    P = await SEndMsG(chat_type_param, processing_msg, user_id, chat_id_param, key, iv)
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
    
    parts = msg.strip().split()
    if len(parts) < 2:
        P = await SEndMsG(chat_type_param, get_system_msg("sp_clan", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    clan_id = parts[1]
    if not clan_id.isdigit():
        P = await SEndMsG(chat_type_param, get_system_msg("sp_clan", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    api_config = get_api_config("sp_clan")
    api_url = api_config.get("url")
    success_keyword = api_config.get("success_keyword", "success")
    
    if not api_url:
        P = await SEndMsG(chat_type_param, get_system_msg("sp_clan", "error"), user_id, chat_id_param, key, iv)
        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
        return
    
    success, _ = await call_api(api_url, success_keyword, {"clan_id": clan_id})
    
    if success:
        P = await SEndMsG(chat_type_param, get_system_msg("sp_clan", "success"), user_id, chat_id_param, key, iv)
    else:
        P = await SEndMsG(chat_type_param, get_system_msg("sp_clan", "error"), user_id, chat_id_param, key, iv)
    
    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)

# ==================== نهاية دوال الأوامر ====================

async def TcPChaT(ip, port, AutHToKen, key, iv, LoGinDaTaUncRypTinG, ready_event, region , reconnect_delay=0.5):
    print(region, 'TCP CHAT')

    global spam_room , whisper_writer , spammer_uid , spam_chat_id , spam_uid , online_writer , chat_id , XX , uid , Spy,data2, Chat_Leave, is_muted, mute_until
    global attack_running, attack_teamcode, stop_attack, attack_task
    
    while True:
        try:
            reader , writer = await asyncio.open_connection(ip, int(port))
            whisper_writer = writer
            bytes_payload = bytes.fromhex(AutHToKen)
            whisper_writer.write(bytes_payload)
            await whisper_writer.drain()
            ready_event.set()
            if LoGinDaTaUncRypTinG.Clan_ID:
                clan_id = LoGinDaTaUncRypTinG.Clan_ID
                clan_compiled_data = LoGinDaTaUncRypTinG.Clan_Compiled_Data
                print('\n - TarGeT BoT in CLan ! ')
                print(f' - Clan Uid > {clan_id}')
                print(f' - BoT ConnEcTed WiTh CLan ChaT SuccEssFuLy ! ')
                pK = await AuthClan(clan_id , clan_compiled_data , key , iv)
                if whisper_writer: 
                    whisper_writer.write(pK) 
                    await whisper_writer.drain()
            while True:
                data = await reader.read(9999)
                if not data: 
                    break
                
                if data.hex().startswith("120000"):
                    msg = await DeCode_PackEt(data.hex()[10:])
                    chatdata = json.loads(msg)
                    try:
                        response = await DecodeWhisperMessage(data.hex()[10:])
                        current_uid = response.Data.uid
                        current_chat_id = response.Data.Chat_ID
                        current_chat_type = response.Data.chat_type
                        inPuTMsG = response.Data.msg.lower()
                    except:
                        response = None

                    if response:
                        if is_maintenance_mode() and not is_admin(current_uid):
                            P = await SEndMsG(current_chat_type, 
                                f"""[FF0000]❌ Maintenance Mode Active

[C][B][FF0000]╔══════════════════╗
[FFFFFF]⚠️ MAINTENANCE MODE
[FFFFFF]⚠️ Bot is under maintenance
[FFFFFF]⚠️ Please try again later
[FF0000]╚══════════════════╝
[FFFFFF]⚡ Maintenance in progress""", 
                                current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            continue
                        
                        if not get_rate_limited_response(current_uid):
                            continue

                        if is_bot_muted():
                            continue

                        if inPuTMsG.strip() == "" or inPuTMsG.strip().startswith(":") or inPuTMsG.strip().startswith("("):
                            update_command_stats("emoji")
                            print(f'Player {current_uid} sent an emoji')
                            
                            emoji_response = await handle_emoji_received(
                                current_uid, key, iv, 
                                current_chat_type, current_chat_id
                            )
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', emoji_response)
                            continue

                        if check_cmd(inPuTMsG, 'debug'):
                            update_command_stats("debug")
                            debug_msg = f"[FF0000]✅ AlliFF BOT ONLINE! UID: {current_uid}"
                            P = await SEndMsG(current_chat_type, debug_msg, current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            continue
                            
                        if check_cmd(inPuTMsG, 'maintenance'):
                            current_cmd = 'maintenance'
                            update_command_stats("maintenance")
                            
                            if not is_admin(current_uid):
                                P = await SEndMsG(current_chat_type, 
                                    f"""[FF0000]❌ Unauthorized Access

[C][B][FF0000]╔══════════╗
[FFFFFF]⚠️ Maintenance Mode
[FFFFFF]⚠️ This command is for admin only
[FF0000]╚══════════╝
[FFFFFF]⚡ Contact admin for assistance""", 
                                    current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            
                            set_maintenance_mode(True)
                            
                            P = await SEndMsG(current_chat_type, 
                                f"""[FF0000]✅ Maintenance Mode Activated

[C][B][FF0000]╔══════════════╗
[FFFFFF]⚠️ MAINTENANCE MODE
[FFFFFF]⚠️ Bot is under maintenance
[FF0000]╚══════════════╝
[FFFFFF]⚡ Only admin commands work""", 
                                current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            continue

                        if check_cmd(inPuTMsG, 'unmaintenance'):
                            current_cmd = 'unmaintenance'
                            update_command_stats("unmaintenance")
                            
                            if not is_admin(current_uid):
                                P = await SEndMsG(current_chat_type, 
                                    f"""[FF0000]❌ Unauthorized Access

[C][B][FF0000]╔══════════╗
[FFFFFF]⚠️ Maintenance Mode
[FFFFFF]⚠️ This command is for admin only
[FF0000]╚══════════╝
[FFFFFF]⚡ Contact admin for assistance""", 
                                    current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            
                            set_maintenance_mode(False)
                            
                            P = await SEndMsG(current_chat_type, 
                                f"""[00FF00]✅ Maintenance Mode Deactivated

[C][B][00FF00]╔══════════════════╗
[FFFFFF]✅ MAINTENANCE ENDED
[FFFFFF]✅ Bot is now operational
[00FF00]╚══════════════════╝
[FFFFFF]⚡ All services restored""", 
                                current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            continue
                            
                        if check_cmd(inPuTMsG, 'attack'):
                            current_cmd = 'attack'
                            update_command_stats("attack")
                            print(f'Processing /attack command from {current_uid}')
                            
                            parts = inPuTMsG.strip().split()
                            if len(parts) < 2:
                                P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            else:
                                team_code = parts[1]
                                
                                if not team_code.isdigit():
                                    P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                if attack_running:
                                    P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                stop_attack = False
                                attack_running = True
                                attack_teamcode = team_code
                                
                                attack_task = asyncio.create_task(
                                    attack_loop(team_code, current_uid, current_chat_id, current_chat_type, key, iv, region)
                                )
                                continue
                                
                        if check_cmd(inPuTMsG, 'emote'):
                            current_cmd = 'emote'
                            update_command_stats("emote")
                            print(f'Processing /emote command from {current_uid}')
                            
                            if not EMOTE_DATA:
                                P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            
                            parts = inPuTMsG.strip().split()
                            
                            if len(parts) < 4:
                                P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            
                            try:
                                team_code = parts[1]
                                emote_num = parts[2]
                                uids = parts[3:]
                                
                                if not team_code.isdigit():
                                    P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                if not emote_num.isdigit() or not (1 <= int(emote_num) <= 409):
                                    P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                if len(uids) < 1 or len(uids) > 4:
                                    P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                for uid_check in uids:
                                    if not uid_check.isdigit():
                                        P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                        await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                        continue
                                
                                emote_id = None
                                emote_num_int = int(emote_num)
                                for emote in EMOTE_DATA:
                                    if int(emote["Number"]) == emote_num_int:
                                        emote_id = emote["Id"]
                                        break
                                
                                if not emote_id:
                                    P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                confirm_msg = f"[B][C][00FF00]⚡ Sending emote {emote_num} to {len(uids)} players..."
                                P = await SEndMsG(current_chat_type, confirm_msg, current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                
                                join_packet = await GenJoinSquadsPacket(team_code, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', join_packet)
                                await asyncio.sleep(2)
                                
                                success_count = 0
                                for target_uid in uids:
                                    try:
                                        emote_packet = await Emote_k(int(target_uid), emote_id, key, iv, region)
                                        await SEndPacKeT(whisper_writer, online_writer, 'OnLine', emote_packet)
                                        success_count += 1
                                        await asyncio.sleep(0.5)
                                    except Exception as e:
                                        print(f"Error sending emote to {target_uid}: {e}")
                                
                                leave_packet = await ExiT(None, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave_packet)
                                
                                result_msg = f"[B][C][00FF00]✅ Done\n📤 Sent to: {success_count}/{len(uids)} players\n🎭 Emote: {emote_num}"
                                P = await SEndMsG(current_chat_type, result_msg, current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                                
                            except Exception as e:
                                P = await SEndMsG(current_chat_type, f"[B][C][FF0000]❌ ERORR: {str(e)}", current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                print(f"Error in /emote command: {e}")
                                continue
                        
                        elif check_cmd(inPuTMsG, 'like'):
                            current_cmd = 'like'
                            update_command_stats("like")
                            
                            processing_msg = get_system_msg(current_cmd, "processing")
                            P = await SEndMsG(current_chat_type, processing_msg, current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            
                            try:
                                parts = inPuTMsG.strip().split()
                                if len(parts) < 2:
                                    P = await SEndMsG(current_chat_type, "[B][C][FF0000]❌ Please provide UID: /like [uid]", current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                target_uid = parts[1].strip()
                                
                                if target_uid.isdigit():
                                    like_result = send_likes(target_uid)
                                    P = await SEndMsG(current_chat_type, like_result, current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                else:
                                    P = await SEndMsG(current_chat_type, "[B][C][FF0000]❌ Invalid UID format. UID must be numbers only", current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            except Exception as e:
                                print(f"[ERROR] in /like command: {e}")
                                P = await SEndMsG(current_chat_type, f"[B][C][FF0000]❌ Error processing request: {str(e)}", current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                        
                        elif check_cmd(inPuTMsG, 'friends'):
                            asyncio.create_task(process_command_async(friends_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue
                                
                        elif check_cmd(inPuTMsG, 'sp_clan'):
                            asyncio.create_task(process_command_async(sp_clan_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue
                        
                        elif check_cmd(inPuTMsG, 'mk'):
                            asyncio.create_task(process_command_async(mk_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif check_cmd(inPuTMsG, 'stop_mk'):
                            asyncio.create_task(process_command_async(stop_mk_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif check_cmd(inPuTMsG, 'ghost'):
                            asyncio.create_task(process_command_async(ghost_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif check_cmd(inPuTMsG, 'lag_ghost'):
                            asyncio.create_task(process_command_async(lag_ghost_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif check_cmd(inPuTMsG, 'msg'):
                            asyncio.create_task(process_command_async(msg_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif check_cmd(inPuTMsG, 'spam'):
                            asyncio.create_task(process_command_async(spam_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif check_cmd(inPuTMsG, 'stop_spam'):
                            asyncio.create_task(process_command_async(stop_spam_task, current_uid, current_chat_id, current_chat_type, inPuTMsG))
                            continue

                        elif inPuTMsG.startswith("/admin"):
                            update_command_stats("admin")
                            print(f"Help triggered by {current_uid}")
                            
                            processing_msg = get_system_msg("admin", "processing")
                            P = await SEndMsG(current_chat_type, processing_msg, current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            
                            if is_admin(current_uid):
                                base_msg = ADMIN_MSG if ADMIN_MSG else f"""[C][B][FF0000]╔══════════╗
[FFFFFF]✨ folow on Telegram    
[FFFFFF]          ⚡ @AlliFF_BOT_V1
[FFFFFF]                   thank for support 
[FF0000]╠══════════╣
[FFD700]⚡ OWNER : [FFFFFF]AlliFF    
[FFD700]✨ Name on Telegram  : [FFFFFF]@AlliFF_BOT  
[FF0000]╚══════════╝
[FFD700]✨ Developer —͟͞͞ </> AlliFF ⚡"""
                                message = base_msg + f"""

[C][B][00FF00]╔══════════════╗
[FFFFFF]⚡ Admin Commands:
[FFFFFF]⚡ /maintenance - Enable maintenance
[FFFFFF]⚡ /unmaintenance - Disable maintenance
[FFFFFF]⚡ /stop - Stop the bot
[00FF00]╚══════════════╝"""
                            else:
                                message = ADMIN_MSG if ADMIN_MSG else f"""[C][B][FF0000]╔══════════╗
[FFFFFF]✨ folow on Telegram    
[FFFFFF]          ⚡ @AlliFF_BOT_V1
[FFFFFF]                   thank for support 
[FF0000]╠══════════╣
[FFD700]⚡ OWNER : [FFFFFF]AlliFF    
[FFD700]✨ Name on Telegram  : [FFFFFF]@AlliFF_BOT  
[FF0000]╚══════════╝
[FFD700]✨ Developer —͟͞͞ </> AlliFF ⚡"""
                            
                            try:
                                P = await SEndMsG(current_chat_type, message, current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                            except Exception as e:
                                P = await SEndMsG(current_chat_type, get_system_msg("admin", "error"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                        
                        if check_cmd(inPuTMsG, 'stop') and is_admin(current_uid):
                            update_command_stats("stop")
                            P = await SEndMsG(current_chat_type, get_system_msg("stop", "success"), current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            await connection_pool.close()
                            os._exit(0)
                        
                        elif (check_cmd(inPuTMsG, '3') or check_cmd(inPuTMsG, '5') or check_cmd(inPuTMsG, '6')):
                            parts = inPuTMsG.strip().split()
                            squad_size = int(inPuTMsG.strip()[1])
                            
                            if len(parts) == 2:
                                target_id = int(parts[1])
                                
                                if squad_size < 3 or squad_size > 6:
                                    P = await SEndMsG(current_chat_type, get_system_msg("squad", "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                
                                async def squad_with_id_task():
                                    await handle_squad_with_id_command(squad_size, target_id, current_uid, current_chat_type, current_chat_id, key, iv, region)
                                
                                asyncio.create_task(process_command_async(squad_with_id_task))
                                continue
                            
                            else:
                                update_command_stats(f"squad_{squad_size}")
                                
                                processing_msg = get_system_msg(str(squad_size), "processing")
                                P = await SEndMsG(current_chat_type, processing_msg, current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                
                                try:
                                    message = f"[B][C]{get_random_color()}\n🎯 {squad_size}-Player Squad!\nAccept Fast"
                                    P = await SEndMsG(current_chat_type, message, current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    
                                    PAc = await OpEnSq(key, iv, region)
                                    await SEndPacKeT(whisper_writer, online_writer, 'OnLine', PAc)
                                    C = await cHSq(squad_size, current_uid, key, iv, region)
                                    await asyncio.sleep(0.3)
                                    await SEndPacKeT(whisper_writer, online_writer, 'OnLine', C)
                                    V = await SEnd_InV(squad_size, current_uid, key, iv, region)
                                    await asyncio.sleep(0.3)
                                    await SEndPacKeT(whisper_writer, online_writer, 'OnLine', V)
                                    E = await ExiT(None, key, iv)
                                    await asyncio.sleep(2)
                                    await SEndPacKeT(whisper_writer, online_writer, 'OnLine', E)
                                    
                                    P = await SEndMsG(current_chat_type, get_system_msg(str(squad_size), "success"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                                except Exception as e:
                                    P = await SEndMsG(current_chat_type, get_system_msg(str(squad_size), "error"), current_uid, current_chat_id, key, iv)
                                    await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                    continue
                        
                        elif check_cmd(inPuTMsG, 'solo'):
                            current_cmd = 'solo'
                            update_command_stats("solo")
                            
                            processing_msg = get_system_msg(current_cmd, "processing")
                            P = await SEndMsG(current_chat_type, processing_msg, current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            
                            try:
                                P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "success"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                leave = await ExiT(current_uid, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'OnLine', leave)
                                continue
                            except:
                                P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue

                        elif check_cmd(inPuTMsG, 'help'):
                            current_cmd = 'help'
                            update_command_stats("help")
                            
                            processing_msg = get_system_msg(current_cmd, "processing")
                            P = await SEndMsG(current_chat_type, processing_msg, current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            
                            try:
                                message1 = HELP_MSG_1 if HELP_MSG_1 else f"""[C][B][ADD8E6]═══AlliFF BOT |
[E0FFFF]⚡ For emote without bot
[AFEEEE]⚡ /emote [team_code] [emote_number] [uid1] [uid2] [uid3] [uid4]

[E0FFFF]⚡ Send likes to player
[AFEEEE]⚡ /like [uid]

[E0FFFF]⚡ Create 3 player squad
[AFEEEE]⚡ /3

[E0FFFF]⚡ Create 5 player squad
[AFEEEE]⚡ /5

[E0FFFF]⚡ Create 6 player squad
[AFEEEE]⚡ /6

[E0FFFF]⚡ Create squad and invite specific player
[AFEEEE]⚡ /3 [id]
[AFEEEE]⚡ /5 [id]
[AFEEEE]⚡ /6 [id]

[E0FFFF]⚡ Intensive attack (45 seconds)
[AFEEEE]⚡ /attack [team_code]

[E0FFFF]⚡ Stop attack
[AFEEEE]⚡ /stop_attack

[AFEEEE]━━━━━━━━━━━━[E0FFFF]"""
                                
                                message2 = HELP_MSG_2 if HELP_MSG_2 else f"""[C][B][FFD700] AlliFF BOT | [FFFF00][B]

[FFFF00]⚡ Return bot to solo
[00FFFF]⚡ /solo

[FFFF00]⚡ Know who is admin
[00FFFF]⚡ /Admin

[FFFF00]⚡ Room invites spam
[00FFFF]⚡ /mk [id]

[FFFF00]⚡ Stop room spam
[00FFFF]⚡ /stop_mk [id]

[FFFF00]⚡ Send ghosts to team
[00FFFF]⚡ /ghost [team_code] [name]

[FFFF00]⚡ Lag attack on team
[00FFFF]⚡ /lag_ghost [team_code] [name]

[FFFF00]⚡ Messages in team
[00FFFF]⚡ /msg [team_code] [message]

[FFFF00]⚡ Squad spam
[00FFFF]⚡ /spam [id]

[FFFF00]⚡ Stop spam
[00FFFF]⚡ /stop_spam [id]

[FFFF00]⚡ Friends spam
[00FFFF]⚡ /friends [uid]

[FFFF00]⚡ Clan join spam
[00FFFF]⚡ /sp_clan [uid_clan]

[00FFFF]━━━━━━━━━━━━[FFFF00]"""

                                P1 = await SEndMsG(current_chat_type, message1, current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P1)
                                
                                await asyncio.sleep(0.5)
                                
                                P2 = await SEndMsG(current_chat_type, message2, current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P2)
                                continue
                            except:
                                P = await SEndMsG(current_chat_type, get_system_msg(current_cmd, "error"), current_uid, current_chat_id, key, iv)
                                await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                                continue
                        
                        elif inPuTMsG.strip().startswith(COMMAND_PREFIX):
                            update_command_stats("unknown")
                            P = await SEndMsG(current_chat_type, get_system_msg("unknown", "error"), current_uid, current_chat_id, key, iv)
                            await SEndPacKeT(whisper_writer, online_writer, 'ChaT', P)
                            continue
                            
            whisper_writer.close() 
            await whisper_writer.wait_closed() 
            whisper_writer = None
                    	
        except Exception as e: 
            print(f"ErroR {ip}:{port} - {e}") 
            whisper_writer = None
        await asyncio.sleep(reconnect_delay)

async def MaiiiinE():
    global connection_pool
    connection_pool = aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=20),
        connector=aiohttp.TCPConnector(limit=20, limit_per_host=10)
    )
    
    load_emote_data()
    config = load_config()
    
    Uid = str(config.get('account_uid', ''))
    Pw = str(config.get('account_password', ''))

    if not Uid or not Pw:
        print("ErroR - Account UID or Password not found in config.json")
        await connection_pool.close()
        return None

    open_id , access_token = await GeNeRaTeAccEss(Uid , Pw)
    if not open_id or not access_token: 
        print("ErroR - InvaLid AccounT") 
        await connection_pool.close()
        return None
    
    PyL = await EncRypTMajoRLoGin(open_id , access_token)
    MajoRLoGinResPonsE = await MajorLogin(PyL)
    if not MajoRLoGinResPonsE: 
        print("TarGeT AccounT => BannEd / NoT ReGisTeReD ! ") 
        await connection_pool.close()
        return None
    
    MajoRLoGinauTh = await DecRypTMajoRLoGin(MajoRLoGinResPonsE)
    UrL = MajoRLoGinauTh.url
    print(f"URL: {UrL}")
    region = MajoRLoGinauTh.region

    ToKen = MajoRLoGinauTh.token
    TarGeT = MajoRLoGinauTh.account_uid
    key = MajoRLoGinauTh.key
    iv = MajoRLoGinauTh.iv
    timestamp = MajoRLoGinauTh.timestamp
    
    LoGinDaTa = await GetLoginData(UrL , PyL , ToKen)
    if not LoGinDaTa: 
        print("ErroR - GeTinG PorTs From LoGin DaTa !") 
        await connection_pool.close()
        return None
        
    LoGinDaTaUncRypTinG = await DecRypTLoGinDaTa(LoGinDaTa)
    OnLinePorTs = LoGinDaTaUncRypTinG.Online_IP_Port
    ChaTPorTs = LoGinDaTaUncRypTinG.AccountIP_Port
    
    try:
        OnLineParts = OnLinePorTs.split(":")
        if len(OnLineParts) >= 2:
            OnLineiP = OnLineParts[0]
            OnLineporT = OnLineParts[1]
        else:
            print(f"Invalid Online Ports format: {OnLinePorTs}")
            await connection_pool.close()
            return None
            
        ChaTParts = ChaTPorTs.split(":")
        if len(ChaTParts) >= 2:
            ChaTiP = ChaTParts[0]
            ChaTporT = ChaTParts[1]
        else:
            print(f"Invalid Chat Ports format: {ChaTPorTs}")
            await connection_pool.close()
            return None
    except Exception as e:
        print(f"Error splitting ports: {e}")
        await connection_pool.close()
        return None
    
    acc_name = LoGinDaTaUncRypTinG.AccountName
    print(f"Token: {ToKen}")
    print(f"Online: {OnLineiP}:{OnLineporT}")
    print(f"Chat: {ChaTiP}:{ChaTporT}")
    
    AutHToKen = await xAuThSTarTuP(int(TarGeT) , ToKen , int(timestamp) , key , iv)
    ready_event = asyncio.Event()
    
    task1 = asyncio.create_task(TcPChaT(ChaTiP, ChaTporT , AutHToKen , key , iv , LoGinDaTaUncRypTinG , ready_event ,region))
     
    await ready_event.wait()
    await asyncio.sleep(1)
    task2 = asyncio.create_task(TcPOnLine(OnLineiP , OnLineporT , key , iv , AutHToKen))
    os.system('clear')
    print(render('AlliFF', colors=['white', 'green'], align='center'))
    print('')
    print(f" - AlliFF BOT STarTinG And OnLine on TarGet : {TarGeT} | BOT NAME : {acc_name}\n")
    print(f" - BoT sTaTus > GooD | OnLinE ! (:")    
    print(f" - winter | Bot Uptime: {time.strftime('%H:%M:%S', time.gmtime(time.time() - bot_start_time))}")    
    await asyncio.gather(task1 , task2)
    
async def watch_config():
    last_mtime = 0
    if os.path.exists('config.json'):
        last_mtime = os.path.getmtime('config.json')
    
    while True:
        try:
            await asyncio.sleep(2)
            if os.path.exists('config.json'):
                current_mtime = os.path.getmtime('config.json')
                if current_mtime > last_mtime:
                    print("[WATCHER] Config file changed, reloading...")
                    load_config()
                    last_mtime = current_mtime
        except Exception as e:
            print(f"[WATCHER] Error: {e}")

async def StarTinG():
    watcher_task = asyncio.create_task(watch_config())
    
    while True:
        try: 
            await asyncio.wait_for(MaiiiinE() , timeout = 7 * 60 * 60)
        except asyncio.TimeoutError: 
            print("Token ExpiRed ! , ResTartinG")
        except Exception as e: 
            print(f"ErroR TcP - {e} => ResTarTinG ...")
        finally:
            if connection_pool:
                await connection_pool.close()

if __name__ == '__main__':
    asyncio.run(StarTinG())