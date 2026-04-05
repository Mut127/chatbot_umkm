from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from symspellpy import SymSpell, Verbosity
from typing import List, Optional
import torch
import joblib
import re
import json
import requests
import mysql.connector
import os


app = Flask(__name__)
CORS(app)


# Configuration
MODEL_PATH           = "Muthi17/chatbot_umkm"
CONFIDENCE_THRESHOLD = 0.40
MAX_CLARIFICATION    = 3

USE_LLM            = True
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = "google/gemini-2.0-flash-lite-001"


DB_CONFIG = {
    "host":     os.environ.get("MYSQLHOST"),
    "user":     os.environ.get("MYSQLUSER"),
    "password": os.environ.get("MYSQLPASSWORD"),
    "database": os.environ.get("MYSQLDATABASE"), 
    "port":     int(os.environ.get("MYSQLPORT", 3306)),
}


# Model & Tokenizer
model = None
tokenizer = None


def get_model():
    global model, tokenizer
    if model is None:
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    return model, tokenizer

le = joblib.load("label_encoder.pkl")

# Database
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# SymSpell
sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

def build_symspell_dictionary():
    cursor.execute("SELECT judul, deskripsi FROM kbli_2020")
    for row in cursor.fetchall():
        for word in re.findall(r"[a-zA-Z]+", f"{row['judul']} {row['deskripsi']}".lower()):
            sym_spell.create_dictionary_entry(word, 1)
    for word in UMKM_DOMAIN_WORDS:
        sym_spell.create_dictionary_entry(word, 1000)


# External Data
with open("priority_from_desa.json", "r", encoding="utf-8") as f:
    PRIORITY_FROM_DESA: dict[str, set] = {k: set(v) for k, v in json.load(f).items()}


# Session State (in-memory)
user_clarification_count: dict[str, int]  = {}
user_session_text:        dict[str, str]  = {}
user_awaiting_business:   dict[str, bool] = {}


# Static Knowledge Base
UMKM_KNOWLEDGE = {
    "nib": (
        "📋 <strong> Cara Daftar NIB (Nomor Induk Berusaha):</strong>\n"
        "1. Kunjungi oss.go.id dan buat akun\n"
        "2. Login → pilih menu Perizinan Berusaha\n"
        "3. Isi data usaha (nama, bidang usaha, modal, dll)\n"
        "4. Pilih kode KBLI yang sesuai\n"
        "5. NIB langsung diterbitkan otomatis ✅\n\n"
        "💡 NIB gratis dan bisa diurus sendiri secara online.\n\n"
        "📄 <strong>Persyaratan NIB (Nomor Induk Berusaha):</strong>\n" 
        "<strong>Dokumen yang diperlukan untuk Usaha Perseorangan (UMK/Usaha Mikro dan Kecil):</strong>\n" 
        "1. KTP dan NIK pemilik usaha\n"  
        "2. Alamat lengkap usaha\n"  
        "3. Jenis dan nama usaha\n"  
        "4. Nomor telepon dan email aktif\n"  
        "5. Kode KBLI yang sesuai dengan jenis usaha\n"  
        "6. NPWP (jika ada)\n"  
        "7. Lokasi dan luas tempat usaha\n"  
        "8. Jumlah tenaga kerja\n"  
        "9. Rencana investasi atau modal usaha\n"  
        "10. Surat pernyataan bersedia mematuhi peraturan (akan muncul otomatis di sistem OSS)\n\n"  
        "<strong>Untuk Badan Usaha (PT, CV, Yayasan, dll.):</strong>\n"  
        "1. Akta pendirian dan SK Kemenkumham\n"  
        "2. NPWP Badan Usaha\n"  
        "3. Data pengurus/pemilik\n"  
        "4. Alamat email & nomor HP perusahaan\n"  
        "5. Dokumen pendukung lain tergantung jenis badan usaha\n\n"  
        "<strong>Catatan:</strong>\n"  
        "• NIB berlaku seumur hidup\n"  
        "• Gratis dan dapat diurus online di OSS\n\n"
        "Butuh bantuan menemukan kode KBLI? Ceritakan jenis usaha Anda 😊\n"
    ),
    "perizinan": (
        "📄 Informasi Perizinan Usaha (UMKM): \n"
        "Untuk memulai usaha secara legal, ada beberapa perizinan yang perlu dimiliki:\n"
        "1. NIB (Nomor Induk Berusaha) — wajib, daftar di oss.go.id (gratis)\n"
        "2. Sertifikat Standar — untuk usaha risiko menengah\n"
        "3. Izin — untuk usaha risiko tinggi\n\n"
        "Untuk usaha mikro-kecil, biasanya cukup NIB saja.\n"
        "Ketik 'cara daftar NIB' untuk panduan lengkapnya, atau ceritakan usaha Anda \n"
        "dan saya bantu carikan KBLI yang dibutuhkan 😊"
    ),
    "kbli_info": (
        "📖 <strong>Apa itu KBLI?</strong>\n"
        "KBLI (Klasifikasi Baku Lapangan Usaha Indonesia) adalah sistem klasifikasi resmi yang digunakan di Indonesia "
        "untuk mengelompokkan kegiatan ekonomi atau jenis usaha berdasarkan aktivitas utamanya. " 
        "KBLI ini wajib dicantumkan saat pelaku usaha mendaftarkan NIB (Nomor Induk Berusaha) melalui sistem OSS (Online Single Submission).\n\n" 
        "<strong>Fungsi KBLI dalam pengajuan NIB:</strong>\n" 
        "• Menentukan jenis usaha yang dijalankan pelaku usaha.\n" 
        "• Menjadi dasar penentuan perizinan berusaha dan kewajiban lainnya.\n" 
        "• Digunakan oleh pemerintah untuk keperluan statistik, pajak, dan pembinaan usaha.\n" 
        "<strong>Kode terdiri dari 5 digit angka, contoh:</strong><br> \n"
            "• 56102 → Rumah/Warung Makan\n"
            "• 47711 → Perdagangan Eceran Pakaian\n"
            "• 56104 → Penyediaan Makanan Keliling/Tempat Tidak Tetap\n\n"
        "<strong>Cara menentukan KBLI:</strong>\n" 
        "1. Identifikasi kegiatan utama usaha Anda\n" 
        "2. Cari kategori yang paling sesuai di daftar KBLI\n" 
        "3. Gunakan kode 5 digit yang tepat\n\n" 
        "🔍 <strong>Cara Mencari Kode KBLI:</strong>\n" 
        "Untuk mencari kode KBLI yang tepat, Anda bisa:\n\n" 
        "<strong>1. Deskripsikan usaha Anda</strong>\n" 
        "- Ketik jenis usaha atau layanan yang Anda jalankan\n\n" 
        "<strong>2. Contoh input yang baik:</strong>\n" 
        "• \"berikan kode kbli untuk warung makan nasi padang\"\n" 
        "• \"berapa kode kbli untuk toko elektronik handphone\"\n" 
        "• \"saya memiliki usaha jasa service motor\"\n" 
        "• \"berikan kode kbli untuk klinik kesehatan umum\"\n\n" 
        "<strong>3. Sistem akan memberikan:</strong>\n" 
        "• Beberapa pilihan kode KBLI\n"
        "• Judul dan deskripsi lengkap \n" 
        "• Rekomendasi yang paling sesuai\n\n" 
        "💡 <em>Silakan coba sekarang dengan mendeskripsikan usaha Anda!</em>"
    ),
    "halal": (
        "🌙 <strong>Cara Daftar Sertifikasi Halal:</strong>\n"
        "1. Siapkan NIB dan data produk Anda\n"
        "2. Kunjungi ptsp.halal.go.id dan buat akun\n"
        "3. Pilih jalur Self-Declare (gratis untuk usaha mikro) atau reguler\n"
        "4. Isi formulir dan unggah dokumen yang diminta\n"
        "5. Verifikasi oleh pendamping halal\n"
        "6. Sertifikat halal diterbitkan ✅\n\n"
        "<strong>Dokumen yang diperlukan:</strong>\n"
        "1. Sertifikat NIB\n"
        "2. Manual sistem jaminan halal \n"
        "3. Daftar produk dan bahan baku \n"
        "4. Sertifikat halal bahan baku \n"
        "5. Dokumentasi proses produksi\n"
        "6. Daftar penyelia halal \n\n"
        "<strong>Biaya:</strong>\n"
        "• Mikro: Gratis\n"
        "• Kecil: Rp 300.000\n"
        "• Menengah: Rp 2.500.000\n\n"
        "Sertifikat berlaku 4 tahun."
    ),
    "bantuan": (
        "💰 Program Bantuan UMKM:\n\n"
        "• BPUM – Bantuan Produktif Usaha Mikro\n"
        "• KUR – Kredit Usaha Rakyat bunga rendah\n"
        "• LPDB – Pinjaman dari Lembaga Pengelola Dana Bergulir\n"
        "• Pelatihan gratis – Kemenparekraf dan Kemenkop\n"
        "Pastikan usaha Anda sudah punya NIB agar bisa mengakses bantuan ini 😊\n\n"
        "<strong>1. Bantuan Produktif Usaha Mikro (BPUM)</strong>\n"
        "• Dana bantuan Rp 2.4 juta\n"
        "• Untuk usaha mikro terdampak pandemi\n\n"
        "<strong>2. KUR (Kredit Usaha Rakyat)</strong>\n"
        "• Mikro: hingga Rp 50 juta\n"
        "• Kecil: hingga Rp 500 juta\n"
        "• Bunga rendah dan mudah diakses\n\n"
        "<strong>3. Program Pelatihan UMKM</strong>\n"
        "• Pelatihan digital marketing\n"
        "• Manajemen keuangan usaha\n"
        "• Pengembangan produk\n\n" 
        "<strong>Info lebih lanjut:</strong> Hubungi Dinas Koperasi setempat"
    ),
    "menu": (
        "Tentu! Ini yang bisa saya bantu 😊\n\n"
        "🔍 Cari kode KBLI — ceritakan jenis usaha Anda\n"
        "📋 Cara daftar NIB — ketik 'cara daftar NIB'\n"
        "📄 Info perizinan — ketik 'info perizinan usaha'\n"
        "🌙 Sertifikasi Halal — ketik 'info sertifikasi halal'\n"
        "💰 Bantuan UMKM — ketik 'info bantuan UMKM'\n"
        "📖 Apa itu KBLI — ketik 'apa itu KBLI'\n\n"
        "Atau langsung ceritakan usaha Anda dan saya carikan KBLI-nya! 🚀"
    ),
}

SYSTEM_PROMPT = (
    "Anda adalah asisten UMKM bernama BAKUL KAHURIPAN.\n"
    "Topik: UMKM, KBLI, NIB, perizinan usaha, sertifikasi halal, bantuan UMKM.\n"
    "Bahasa: Indonesia yang ramah dan santai.\n\n"
    "ATURAN FORMAT — WAJIB DIIKUTI:\n"
    "- DILARANG gunakan markdown: **bold**, *italic*, ## heading, ---, ___\n"
    "- Emoji maksimal 1 per respons, taruh di akhir kalimat saja\n"
    "- Jika ada daftar, gunakan angka: 1. 2. 3. — bukan bullet atau simbol\n"
    "- Respons maksimal 4 kalimat atau 4 poin. Singkat dan jelas.\n"
    "- JANGAN tanya balik atau ajak ngobrol panjang jika user sudah jelas minta KBLI.\n"
    "- JANGAN tentukan kode KBLI tanpa data dari sistem."
)

CLARIFICATION_REPLIES = [
    "Boleh ceritakan lebih detail usaha Anda? Misalnya, Anda menjual apa atau menyediakan layanan apa? 😊",
    (
        "Supaya saya bisa merekomendasikan KBLI yang tepat, coba jelaskan sedikit lagi — "
        "produk yang dijual, layanan yang ditawarkan, atau lokasi usaha Anda."
    ),
    (
        "Hampir ketemu! Satu detail lagi — apakah usaha Anda di rumah, toko, atau keliling? "
        "Dan produk/layanan utamanya apa?"
    ),
]


# Regex & Keyword Constants
GREETING_RE = re.compile(
    r"^(hai|halo|hi|hello|selamat|permisi|hei|assalamu|p+a+g+i+|sore|malam|"
    r"selamat pagi|selamat siang|selamat sore|selamat malam)[\s!.,]*$",
    re.IGNORECASE,
)

BUSINESS_DESCRIPTION_RE = re.compile(
    r"(saya|aku|kami|kita|sy)\s+"
    r"(punya|memiliki|membuka|buka|mau buka|menjual|berjualan|jualan|"
    r"membuat|bikin|memproduksi|bergerak|berencana|ingin membuka|mau membuka|"
    r"berencana membuka|usaha|dagang|jual|bekerja|kerja|memasok|pasok|"
    r"mendistribusikan|distribusi|mempunyai)",
    re.IGNORECASE,
)

KBLI_QUESTION_RE = re.compile(
    r"(gimana|bagaimana|cara|caranya|apa|apakah|bisa|tolong|bantu|cariin|cari|berapa|kode|cari kode)"
    r".{0,30}(kbli|klasifikasi)"
    r"|"
    r"(kbli).{0,30}(untuk|usaha|jualan|berjualan|jual|buka|membuka)",
    re.IGNORECASE,
)


FOOD_KEYWORDS = {
    "cilok", "bakso", "makanan", "jajanan", "minuman",
    "warung", "kaki", "lima", "gerobak", "kuliner", "dagangan",
    "mie", "ayam", "nasi", "soto", "gorengan", "kue", "es",
    "tahu", "tempe", "pecel", "sate", "seafood", "catering",
}

BUSINESS_KEYWORDS = [
    # Aktivitas umum
    "usaha", "membuka", "membuat", "bikin", "berencana",
    "produksi", "memproduksi", "menghasilkan",
    # Perdagangan
    "jual", "berjualan", "jualan", "dagang", "berdagang",
    "menjual", "memasok", "pasok", "pemasok", "suplai",
    "distributor", "reseller", "dropship", "grosir", "eceran",
    # Tempat / skala
    "toko", "warung", "kios", "gerai", "lapak", "online",
    "keliling", "rumahan", "rumah produksi",
    # Jasa & layanan
    "jasa", "service", "servis", "perbaikan", "reparasi",
    "salon", "laundry", "kos", "kontrakan", "bengkel",
    "ojek", "angkutan", "ekspedisi", "pengiriman",
    # Industri / produksi
    "pabrik", "industri", "konveksi", "percetakan",
    "manufaktur", "pengolahan",
    # Pertanian / peternakan
    "tambak", "ternak", "kebun", "budidaya", "tani", "pertanian",
    "peternakan", "perikanan",
    # Produk makanan spesifik
    "cilok", "bakso", "gorengan", "kue", "nasi", "ayam",
    "tahu", "tempe", "mie", "soto", "catering", "kuliner",
    # Produk non-makanan
    "pakaian", "baju", "sepatu", "tas", "elektronik",
    "handphone", "hp", "komputer",
    # Jasa profesional
    "fotografi", "foto", "desain", "konstruksi", "bangunan",
    "properti", "travel", "wisata",
    # Tempat usaha khusus
    "restoran", "rumah makan", "kedai", "cafe", "kafe",
    "salon kecantikan", "barbershop",
]


TOPIC_RULES = [
    # HALAL — taruh paling atas, sebelum NIB
    ("halal", [
        "sertifikat halal", "sertifikasi halal",
        "halal umkm", "daftar halal",
        "gimana halal", "proses halal", "syarat halal",
        "self declare", "self-declare",
        "cara mendapatkan halal",
        "cara dapat halal",
        "cara memperoleh halal",
        "mendapatkan sertifikat halal",
        "mendapatkan sertifikasi halal",
        "dapat sertifikat halal",
        "dapat sertifikasi halal",
        "buat sertifikat halal",
        "membuat sertifikat halal",
        "urus sertifikat halal",
        "mengurus sertifikat halal",
        "sertifikat halal cara",
        "cara daftar sertifikat halal",   
        "cara daftar halal",             
        "cara halal",
        "info halal",
        "informasi halal",
        "tentang halal",
    ]),
    # NIB 
    ("nib", [
        "nib", "nomor induk berusaha",
        "bikin nib", "buat nib", "daftar nib", "cara nib",
        "urus nib", "gimana nib", "mendaftar nib",
        "pendaftaran nib",
        "langkah nib",
        "cara mendaftar nib",   
        "daftar di oss",
        "daftar oss",
        "oss.go.id",
    ]),
    ("perizinan", [
        "perizinan", "izin usaha", "izin berusaha",
        "surat izin", "legalitas", "legal usaha",
        "info perizinan", "informasi perizinan",
        "berizinan",   
    ]),
    ("kbli_info", [
        "apa itu kbli", "kbli itu apa", "kbli adalah",
        "pengertian kbli", "panduan kbli", "tentang kbli",
    ]),
    ("bantuan", [
        "bantuan umkm", "subsidi", "kur ", "bpum",
        "modal usaha", "pinjaman usaha", "dana umkm",
        "kredit usaha", "bantuan modal", "info bantuan",
    ]),
    # MENU
    ("menu", [
        "info apa", "apa saja", "bisa apa", "bisa bantu apa",
        "kamu bisa apa", "fitur apa", "kemampuan kamu",
        "apa yang bisa", "bisa ngapain",
        "bisa bantu saya apa",  
        "bantu saya apa",  
        "kamu bisa bantu aku apa aja",      
        "kamu bisa bantu",      
        "apa yang kamu bisa",    
        "apa bisa kamu bantu",   
    ]),
]

SPECIFIC_BOOST = {
    "warung makan":  {"contains": ["warung makan", "rumah makan"],                                   "boost": 8, "prefix": "56"},
    "rumah makan":   {"contains": ["warung makan", "rumah makan"],                                   "boost": 8, "prefix": "56"},
    "kedai makan":   {"contains": ["kedai", "makanan"],                                              "boost": 8, "prefix": "56"},
    "pemasok":       {"contains": ["perdagangan besar", "distributor", "pemasok", "grosir", "agen"], "boost": 8, "prefix": "46"},
    "distributor":   {"contains": ["perdagangan besar", "distributor", "pemasok", "grosir", "agen"], "boost": 8, "prefix": "46"},
    "grosir":        {"contains": ["perdagangan besar", "grosir"],                                   "boost": 8, "prefix": "46"},
    "tahu":          {"contains": ["tahu"],                                                           "boost": 6, "prefix": "10"},
    "tempe":         {"contains": ["tempe"],                                                          "boost": 6, "prefix": "10"},
    "jahit":         {"contains": ["jahit", "konveksi", "pakaian"],                                  "boost": 6, "prefix": "14"},
    "menjahit":      {"contains": ["jahit", "konveksi", "pakaian"],                                  "boost": 6, "prefix": "14"},
    "bengkel":       {"contains": ["bengkel", "reparasi", "kendaraan"],                              "boost": 6, "prefix": "45"},
    "salon":         {"contains": ["salon", "kecantikan", "rambut"],                                 "boost": 6, "prefix": "96"},
    "laundry":       {"contains": ["laundry", "linen", "cucian"],                                    "boost": 6, "prefix": "96"},
}

# Kata-kata domain UMKM yang wajib ada di kamus SymSpell
UMKM_DOMAIN_WORDS = [
    "nib", "kbli", "halal", "perizinan", "sertifikat", "sertifikasi",
    "oss", "umkm", "usaha", "izin", "legalitas", "bantuan", "modal",
    "klasifikasi", "lapangan", "berusaha", "nomor", "induk",
    "mikro", "kecil", "menengah", "produksi", "perdagangan",
    "jasa", "industri", "pertanian", "peternakan", "perikanan",
]

THANKS_RE = re.compile(
    r"^(makasih\s*(ya|banget|banyak)?|terima\s*kasih(\s*(ya|banget|banyak))?|"
    r"terimakasih(\s*(ya|banget|banyak))?|thanks(\s*a?\s*lot)?|thank\s*you|"
    r"thx|tq|tengkyu+|syukron|alhamdulillah|oke\s*makasih|ok\s*makasih|"
    r"oke\s*terima\s*kasih|sip\s*makasih)"
    r"[\s!.,]*$",
    re.IGNORECASE,
)

def is_thanks(text: str) -> bool:
    return bool(THANKS_RE.match(text.strip()))


# Text Helpers
def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\bdi([a-zA-Z]+)", r"di \1", text)
    return text


def correct_typo(text: str) -> str:
    corrected = []
    for word in text.split():
        suggestions = sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=2)
        corrected.append(suggestions[0].term if suggestions else word)
    return " ".join(corrected)


# Intent Detection
def is_greeting(text: str) -> bool:
    return bool(GREETING_RE.match(text.strip()))


def is_business_context(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in BUSINESS_KEYWORDS)


def has_business_description(text: str) -> bool:
    return bool(BUSINESS_DESCRIPTION_RE.search(text))


def is_kbli_code(text: str) -> bool:
    # Cek apakah ada kode 4-5 digit dalam teks
    match = re.search(r'\b(\d{4,5})\b', text.strip())
    if match:
        return True
    return False

def is_asking_about_kbli(text: str) -> bool:
    return bool(KBLI_QUESTION_RE.search(text))


def detect_umkm_topic(text: str) -> str | None:
    t = text.lower()
    for topic_key, keywords in TOPIC_RULES:
        if any(kw in t for kw in keywords):
            return topic_key
    return None


def has_food_activity(text: str) -> bool:
    return bool(set(text.split()) & FOOD_KEYWORDS)

# Scoring Helpers
def is_non_business_kbli(judul: str) -> bool:
    blacklist = {"PENDIDIKAN", "GEDUNG", "SEKOLAH", "PEMERINTAH"}
    return any(b in judul.upper() for b in blacklist)


def keyword_relevance(query: str, description: str) -> int:
    score = 0
    desc  = description.lower()
    for word in set(query.split()):
        if len(word) < 3:
            continue
        if word in desc:
            score += 2
        elif any(word in d for d in desc.split()):
            score += 1
    return score


def apply_specific_boost(raw_text: str, kode: str, deskripsi: str) -> int:
    """Boost/penalti berdasarkan kata kunci spesifik."""
    boost = 0
    txt   = raw_text.lower()
    desc  = deskripsi.lower()
    for keyword, rule in SPECIFIC_BOOST.items():
        if keyword in txt:
            if any(c in desc for c in rule["contains"]) and kode.startswith(rule["prefix"]):
                boost += rule["boost"]
            else:
                boost -= 2
    return boost


def detect_priority_prefix(text: str) -> list[str] | None:
    words    = set(text.lower().split())
    prefixes = {p for p, kws in PRIORITY_FROM_DESA.items() if words & kws}
    return list(prefixes) if prefixes else None


# IndoBERT Inference
def model_confidence(text: str) -> float:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=1)[0]
    return torch.max(probs).item()



# Session Helpers
def get_clarification_reply(session_id: str) -> str:
    idx = min(user_clarification_count.get(session_id, 0), len(CLARIFICATION_REPLIES) - 1)
    return CLARIFICATION_REPLIES[idx]


def clear_session(session_id: str) -> None:
    user_session_text.pop(session_id, None)
    user_clarification_count.pop(session_id, None)
    user_awaiting_business.pop(session_id, None)



# Database Helpers

def get_kbli_categories() -> list[dict]:
    cursor.execute("""
        SELECT DISTINCT no, nama_kategori
        FROM kbli_2020
        WHERE no IS NOT NULL AND kode != ''
        ORDER BY no
    """)
    return [
        {"kode": r["no"].strip(), "judul": r["nama_kategori"].strip()}
        for r in cursor.fetchall()
    ]


def sanitize_llm_output(text: str) -> str:
    """Bersihkan output LLM dari simbol markdown dan format liar."""
    # Hapus heading markdown
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Hapus bold/italic
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}([^_\n]+)_{1,2}", r"\1", text)
    # Hapus horizontal rule
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Hapus backtick
    text = re.sub(r"`+([^`]*)`+", r"\1", text)
    # Ganti bullet 
    text = re.sub(r"^[\*\-•]\s+", "- ", text, flags=re.MULTILINE)
    # Rapikan baris kosong berlebihan
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()



# LLM (OpenRouter)

def call_openrouter(messages: list[dict]) -> str:
    import requests

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "http://localhost",
        "X-Title":       "Chatbot KBLI",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.3,
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "choices" not in data:
        raise RuntimeError("OpenRouter response invalid")

    return sanitize_llm_output(data["choices"][0]["message"]["content"])


def generate_chat_response(text: str, best_kbli: dict) -> str:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"Hasil klasifikasi:\n"
                f"Kode: {best_kbli['kode']}\n"
                f"Judul: {best_kbli['judul']}\n"
                f"Deskripsi: {best_kbli['deskripsi']}\n\n"
                "Jelaskan dengan bahasa ramah dan mudah dipahami."
            )},
        ]
        return call_openrouter(messages)

    except Exception as e:
        print("[LLM FAILED]", e)

        # 🔁 FALLBACK AMAN (WAJIB ADA)
        return (
            f"Oke, saya sudah menemukan KBLI yang cocok untuk usaha Anda 😊\n\n"
            f"📌 Kode: {best_kbli['kode']}\n"
            f"📋 Judul: {best_kbli['judul']}\n\n"
            f"Usaha Anda termasuk dalam kategori tersebut. "
            f"Jika ingin, saya bisa bantu jelaskan perizinan atau NIB yang dibutuhkan."
        )


def llm_reply_or(user_text: str, fallback: str):
    if USE_LLM:
        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_text},
            ]
            return jsonify({"reply": call_openrouter(messages)})
        except Exception as e:
            print("[LLM FAILED]", e)
            return jsonify({"reply": fallback})



# Routes

@app.route("/")
def home():
    return render_template("index.html", kbli_categories=get_kbli_categories())

@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data       = request.get_json()
        session_id = data.get("session_id", "default")

        session_text = user_session_text.get(session_id, "")
        raw_text     = data.get("use_text") or data.get("text", "")
        combined_raw = (session_text + " " + raw_text).strip() or raw_text

        if not combined_raw.strip():
            return jsonify({"success": False, "error": "Teks input kosong"})

        text = correct_typo(normalize_text(combined_raw))

        if len(text.split()) < 2:
            return jsonify({
                "success": False,
                "error": "Deskripsi usaha terlalu singkat. Mohon jelaskan lebih detail.",
            })

        priority_prefix = detect_priority_prefix(text)

        # IndoBERT inference
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        with torch.no_grad():
            outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=1)[0]

        topk      = torch.topk(probs, k=10)
        pred_ids  = topk.indices.tolist()
        scores    = topk.values.tolist()
        kode_list = [le.inverse_transform([pid])[0].zfill(5) for pid in pred_ids]

        # Ambil data KBLI dari DB
        if priority_prefix:
            cond = " OR ".join(f"kode LIKE '{p}%'" for p in priority_prefix)
            cursor.execute(f"SELECT kode, judul, deskripsi FROM kbli_2020 WHERE {cond}")
        else:
            cursor.execute("SELECT kode, judul, deskripsi FROM kbli_2020")
        db_map = {r["kode"]: r for r in cursor.fetchall()}

        # Scoring
        is_food = has_food_activity(text)
        results = []

        for i, kode in enumerate(kode_list):
            if kode not in db_map:
                continue

            row       = db_map[kode]
            deskripsi = row["deskripsi"].lower()
            relevance = keyword_relevance(text, deskripsi)

            if is_non_business_kbli(row["judul"].upper()):
                relevance -= 3

            if is_food:
                if any(k in deskripsi for k in ["makanan", "minuman", "restoran", "warung"]):
                    relevance += 4
                else:
                    relevance -= 2

            relevance += apply_specific_boost(combined_raw, kode, deskripsi)

            results.append({
                "kode":      kode,
                "judul":     row["judul"],
                "deskripsi": row["deskripsi"],
                "score":     round(float(scores[i]), 4),
                "relevance": relevance,
            })

        results  = sorted(results, key=lambda x: (x["relevance"], x["score"]), reverse=True)
        filtered = [r for r in results if r["relevance"] >= 1 and r["score"] >= 0.03] or results
        filtered = filtered[:5]

        best_kbli = filtered[0]
        chat_reply = (
            generate_chat_response(text, best_kbli) if USE_LLM
            else (
                f"Oke, saya sudah menemukan KBLI yang cocok untuk usaha Anda! 🎉\n\n"
                f"📌 Kode: {best_kbli['kode']}\n"
                f"📋 Judul: {best_kbli['judul']}\n\n"
                f"Apakah ada yang ingin Anda tanyakan tentang perizinan usaha ini?"
            )
        )

        clear_session(session_id)

        return jsonify({
            "success":         True,
            "input":           text,
            "recommendations": filtered,
            "best_kbli":       best_kbli,
            "chatbot_reply":   chat_reply,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/chat", methods=["POST"])
def chat():
    data       = request.get_json()
    user_text  = data.get("text", "").strip()
    session_id = data.get("session_id", "default")

    if not user_text:
        return jsonify({"reply": "Halo! Ada yang bisa saya bantu?"})

    # Init sesi
    user_clarification_count.setdefault(session_id, 0)
    user_session_text.setdefault(session_id, "")
    user_awaiting_business.setdefault(session_id, False)

    #1. Kode KBLI (4–5 digit) 
    kbli_match = re.search(r'\b(\d{4,5})\b', user_text)
    if kbli_match:
        kode = kbli_match.group(1).zfill(5)
        cursor.execute("SELECT kode, judul, deskripsi FROM kbli_2020 WHERE kode = %s", (kode,))
        row = cursor.fetchone()
        if row:
            return jsonify({
                "reply": (
                    f"Informasi KBLI {row['kode']}:\n\n"
                    f"{row['judul']}\n\n"
                    f"{row['deskripsi']}\n\n"
                    f"Apakah ini KBLI yang Anda cari?"
                )
            })
        return jsonify({"reply": f"Kode KBLI {user_text} tidak ditemukan. Coba periksa kembali ya."})
    
    if is_thanks(user_text):
        return jsonify({
            "reply": (
                "Sama-sama! Semoga usaha Anda semakin lancar dan berkembang. 😊\n\n"
                "Kalau ada yang ingin ditanyakan lagi seputar KBLI, NIB, atau perizinan, "
                "saya siap membantu kapan saja."
            )
        })
    # 2. Topik UMKM (NIB, halal, perizinan, dll) 
    topic = detect_umkm_topic(user_text)
    if topic:
        # Hanya panggil LLM untuk topik menu (butuh variasi), sisanya pakai static
        if topic == "menu":
            return llm_reply_or(user_text, UMKM_KNOWLEDGE[topic])
        return jsonify({"reply": UMKM_KNOWLEDGE[topic]})

    # 3. Salam murni 
    if is_greeting(user_text) and not is_business_context(user_text):
        return jsonify({
            "reply": (
                "Halo! Selamat datang di BAKUL KAHURIPAN 👋\n\n"
                "Saya siap membantu Anda menemukan kode KBLI yang sesuai.\n\n"
                "Coba ceritakan jenis usaha Anda, misalnya:\n"
                "• saya membuka warung makan\n"
                "• saya berjualan pakaian online\n"
                "• saya membuka jasa jahit\n\n"
                "Atau tanyakan seputar NIB, perizinan, atau sertifikasi halal."
            )
        })

    # 4. Tanya KBLI tapi belum sebut jenis usaha 
    if is_asking_about_kbli(user_text):
        if has_business_description(user_text) or is_business_context(user_text):
            # Sudah ada info usaha dalam pertanyaan → langsung classify
            accumulated = (user_session_text.get(session_id, "") + " " + user_text).strip()
            user_session_text[session_id] = accumulated
            return jsonify({"redirect": "predict"})
        else:
            # Belum ada info usaha → minta deskripsi
            user_awaiting_business[session_id] = True
            return jsonify({
                "reply": (
                    "Tentu, saya bantu carikan KBLI-nya!\n\n"
                    "Ceritakan jenis usaha Anda lebih detail, misalnya:\n"
                    "• saya jualan martabak di kios pinggir jalan\n"
                    "• saya buka jasa servis HP di toko\n"
                    "• saya produksi kue rumahan untuk dijual online"
                )
            })

    # 5. Ada deskripsi usaha langsung classify 
    is_describing_business = (
        has_business_description(user_text)
        or is_business_context(user_text)
        or user_awaiting_business.get(session_id, False)
    )

    if is_describing_business:
        accumulated = (user_session_text.get(session_id, "") + " " + user_text).strip()
        user_session_text[session_id] = accumulated

        # Langsung redirect jika teks user_text sudah cukup (>= 3 kata)
        if len(user_text.split()) >= 3:
            clear_session(session_id)
            return jsonify({"redirect": "predict"})

        confidence   = model_confidence(normalize_text(correct_typo(accumulated)))
        clarif_count = user_clarification_count.get(session_id, 0)

        if confidence >= CONFIDENCE_THRESHOLD or clarif_count >= 1:
            clear_session(session_id)
            return jsonify({"redirect": "predict"})

        user_clarification_count[session_id] = clarif_count + 1
        user_awaiting_business[session_id]   = True
        return jsonify({"reply": "Boleh ceritakan sedikit lebih detail?"})

    # 6. Tidak dikenali
    return jsonify({
        "reply": (
            "Saya bisa membantu:\n"
            "1. Mencari kode KBLI — ceritakan jenis usaha Anda\n"
            "2. Info cara daftar NIB — ketik 'cara daftar NIB'\n"
            "3. Info perizinan usaha — ketik 'info perizinan'\n"
            "4. Info sertifikasi halal — ketik 'info halal'\n"
            "5. Info bantuan UMKM — ketik 'info bantuan'"
        )
    })


@app.route("/kbli/<kategori>")
def kbli_kategori_page(kategori):
    cursor.execute("""
        SELECT nama_kategori
        FROM kbli_2020
        WHERE no = %s
        LIMIT 1
    """, (kategori.upper(),))
    kategori_row = cursor.fetchone()

    cursor.execute("""
        SELECT kode, judul, deskripsi
        FROM kbli_2020
        WHERE no = %s
        ORDER BY kode
    """, (kategori.upper(),))
    kbli_list = cursor.fetchall()

    return render_template(
        "detail.html",
        kategori=kategori.upper(),
        kategori_nama=kategori_row["nama_kategori"] if kategori_row else "",
        kbli_list=kbli_list
    )
    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
