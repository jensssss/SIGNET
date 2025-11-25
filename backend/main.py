# File: main.py (FINAL & CLEANED)

import os
import logging
import tempfile
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from web3 import Web3

# Telegram Imports
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Local Imports
from signet_hasher import get_video_phash, get_image_phash, calculate_hamming
from config import (BOT_TOKEN, LISK_RPC_URL, CONTRACT_ADDRESS, CONTRACT_ABI, HAMMING_THRESHOLD) # IMPOR CONFIG FINAL
import yt_dlp

# Setup Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Globals
ptb_application = None
w3 = None
contract = None

# --- 1. BLOCKCHAIN CONNECTION ---
def connect_blockchain():
    global w3, contract
    try:
        w3 = Web3(Web3.HTTPProvider(LISK_RPC_URL))
        if w3.is_connected():
            logger.info(f"✅ Connected to Lisk Sepolia Network")
            contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)
        else:
            logger.error("❌ Failed to connect to Lisk RPC")
    except Exception as e:
        logger.error(f"❌ Blockchain Connection Error: {e}")

# --- 2. CORE VERIFICATION LOGIC (REAL DB) ---
def check_verification_logic(user_hash: str):
    """Mencari hash terdekat langsung dari Smart Contract Lisk"""
    best_distance = 999
    matched_metadata = None
    
    try:
        if not contract:
            raise Exception("Contract not initialized.")
            
        blockchain_hashes = contract.functions.getAllHashes().call()
        logger.info(f"🔍 Scanning {len(blockchain_hashes)} hashes from Lisk Registry...")

        # Search Loop
        best_match_hash = ""
        for db_hash in blockchain_hashes:
            dist = calculate_hamming(user_hash, db_hash)
            if dist < best_distance:
                best_distance = dist
                best_match_hash = db_hash
        
        is_valid = best_distance <= HAMMING_THRESHOLD

        # Jika valid, ambil detail info publishernya
        if is_valid:
            data = contract.functions.getContentData(best_match_hash).call()
            matched_metadata = {"publisher": data[0], "title": data[1], "desc": data[2]}

        return is_valid, best_distance, matched_metadata

    except Exception as e:
        logger.error(f"Error verifying against blockchain: {e}")
        return False, 999, None

# --- 3. TELEGRAM BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 **SIGNET Online (Lisk Network).**\nKirim Video/Foto/Link untuk verifikasi keaslian di Lisk Blockchain.")

# FIX: Modifikasi fungsi agar menerima flag is_video untuk hashing yang benar
async def process_bot_media(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path: str, is_video: bool):
    status_msg = await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=update.message.message_id + 1, # Edit pesan terakhir
        text="🧠 Menghitung fingerprint & Querying Lisk Blockchain..."
    )
    
    try:
        # 1. Hashing (Memilih hasher yang benar)
        if is_video:
            user_hash = get_video_phash(file_path)
        else:
            with open(file_path, "rb") as f:
                user_hash = get_image_phash(f.read())
        
        # 2. Cek Blockchain
        is_valid, distance, metadata = check_verification_logic(user_hash)
        
        if is_valid and metadata:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=f"✅ **VERIFIED CONTENT!**\n\n"
                     f"📜 **Title:** {metadata['title']}\n"
                     f"🏢 **Publisher:** `{metadata['publisher']}`\n"
                     f"🔢 **Distance:** {distance} (Authentic)\n"
                     f"🔗 **Source:** Lisk Sepolia Registry",
                parse_mode='Markdown'
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=f"⚠️ **UNVERIFIED / UNKNOWN**\n\n"
                     f"Konten ini belum terdaftar di SIGNET Registry.\n"
                     f"Distance Terdekat: {distance}",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text=f"❌ System Error: {str(e)}"
        )
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# Handler Pintar: Gambar & Video
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_obj = None
    is_video = False
    ext = ".tmp"

    # 1. Deteksi Tipe File
    if update.message.video or ('video' in update.message.document.mime_type if update.message.document else False):
        file_obj = await (update.message.video or update.message.document).get_file()
        is_video = True
        ext = ".mp4"
    elif update.message.photo or ('image' in update.message.document.mime_type if update.message.document else False):
        file_obj = await (update.message.photo[-1] if update.message.photo else update.message.document).get_file()
        is_video = False
        ext = ".jpg"
    
    if not file_obj:
        await update.message.reply_text("❌ Format media tidak didukung.")
        return

    # 2. UX FIX: Pesan status awal
    await update.message.reply_text("⏳ Mendownload konten...")
    
    # 3. Download & Proses
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
        await file_obj.download_to_drive(f.name)
        # Panggil fungsi pemroses, bawa flag is_video
        await process_bot_media(update, context, f.name, is_video)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" not in url: return
    
    # Kita asumsikan konten dari URL adalah video untuk demo
    is_video = True 
    await update.message.reply_text("🔗 Link terdeteksi. Downloading...")
    temp_dir = tempfile.mkdtemp()
    try:
        ydl_opts = {'format': 'best[ext=mp4]', 'outtmpl': os.path.join(temp_dir, 'vid.%(ext)s'), 'quiet': True, 'max_filesize': 50*1024*1024}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            for file in os.listdir(temp_dir):
                if file.endswith(".mp4"):
                    await process_bot_media(update, context, os.path.join(temp_dir, file), is_video) # <--- Pass is_video=True
                    return
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal download: {str(e)}")

# --- 4. LIFECYCLE ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_blockchain()
    
    logger.info("🚀 Starting Telegram Bot...")
    global ptb_application
    ptb_application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(60).write_timeout(60).build()
    
    ptb_application.add_handler(CommandHandler('start', start))
    ptb_application.add_handler(MessageHandler(filters.VIDEO | filters.PHOTO | filters.Document.VIDEO | filters.Document.IMAGE, handle_media)) # Tambah FILTER PHOTO
    ptb_application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_url))
    
    await ptb_application.initialize()
    await ptb_application.start()
    await ptb_application.updater.start_polling()
    yield
    logger.info("🛑 Stopping Telegram Bot...")
    await ptb_application.updater.stop()
    await ptb_application.stop()
    await ptb_application.shutdown()

app = FastAPI(title="SIGNET Real Lisk Server", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- 5. API ENDPOINTS (Untuk Web Dashboard) ---

@app.post("/api/v1/hash-file-upload")
async def hash_file_upload(file: UploadFile = File(...), title: str = Form(...), desc: str = Form(...)):
    """Endpoint untuk Frontend Web menghitung hash sebelum upload ke blockchain."""
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Perbaikan Logika: Deteksi Tipe File di sini
        if file.content_type.startswith("video") or file.filename.endswith(('.mp4', '.mov')):
            p_hash = get_video_phash(temp_path)
        elif file.content_type.startswith("image") or file.filename.endswith(('.jpg', '.png', '.jpeg')):
            with open(temp_path, "rb") as f:
                 p_hash = get_image_phash(f.read())
        else:
            raise HTTPException(status_code=400, detail="Tipe file tidak didukung untuk hashing.")

        return JSONResponse(content={"status": "SUCCESS", "p_hash": p_hash})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(temp_dir)

@app.get("/")
def root(): return {"message": "SIGNET Server Running (Lisk Connected)"}