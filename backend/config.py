# File: config.py (FINAL VERSION)
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. LISK BLOCKCHAIN CONFIG ---

LISK_RPC_URL = "https://rpc.sepolia-api.lisk.com"
CONTRACT_ADDRESS = "0x4cc13433651c7fc5C0f9aECf803479455646634c" 

# ABI Minimal (INI ARRAY DARI MAIN.PY YANG DIPINDAH)
CONTRACT_ABI = [
    {
        "inputs": [],
        "name": "getAllHashes",
        "outputs": [{"internalType": "string[]", "name": "", "type": "string[]"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "string", "name": "_pHash", "type": "string"}],
        "name": "getContentData",
        "outputs": [
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "string", "name": "", "type": "string"},
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]


# --- 2. TELEGRAM BOT & HASHING CONFIG ---
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8315707153:AAEfKocj4Y1DAVNAAINBRRH2yg9-0R6J9NI")

HAMMING_THRESHOLD = 25