// ==================== UTIL ====================
function scrollBottom() {
  const chat = document.getElementById("chatbotMessages");
  chat.scrollTop = chat.scrollHeight;
}

// ==================== SESSION ====================
const SESSION_ID = "user-1";

// ==================== ADD MESSAGE ====================
function addUserMessage(text) {
  const chat = document.getElementById("chatbotMessages");

  const msg = document.createElement("div");
  msg.className = "chat-message user";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  msg.appendChild(bubble);
  chat.appendChild(msg);
  scrollBottom();
}

function addBotMessage(html) {
  const chat = document.getElementById("chatbotMessages");

  const msg = document.createElement("div");
  msg.className = "chat-message bot";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = html;

  msg.appendChild(bubble);
  chat.appendChild(msg);
  scrollBottom();
}

// ==================== TYPING ====================
function showTyping() {
  hideTyping();

  const chat = document.getElementById("chatbotMessages");
  const msg = document.createElement("div");
  msg.id = "typing";
  msg.className = "chat-message bot";

  msg.innerHTML = `<div class="bubble">🤖 Sedang mengetik...</div>`;
  chat.appendChild(msg);
  scrollBottom();
}

function hideTyping() {
  document.getElementById("typing")?.remove();
}

// ==================== INPUT ====================
async function handleUserMessage() {
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text) return;

  addUserMessage(text);
  input.value = "";
  showTyping();

  const reply = await getKBLIRecommendation(text);

  hideTyping();
  addBotMessage(reply);
}



function handleEnter(e) {
  if (e.key === "Enter") {
    e.preventDefault();
    handleUserMessage();
  }
}
// ==================== QUICK QUESTIONS ====================
function askQuestion(type) {
  let question = "";
  let response = "";

    switch (type) {
            case "panduan-kbli":
              question = "Panduan KBLI (Klasifikasi Baku Lapangan Usaha)";
              response = `📋 <strong>Panduan KBLI:</strong>
                        KBLI (Klasifikasi Baku Lapangan Usaha Indonesia) adalah sistem klasifikasi resmi yang digunakan di Indonesia untuk mengelompokkan kegiatan ekonomi atau jenis usaha berdasarkan aktivitas utamanya. KBLI ini wajib dicantumkan saat pelaku usaha mendaftarkan NIB (Nomor Induk Berusaha) melalui sistem OSS (Online Single Submission).<br>
                        <strong>Fungsi KBLI dalam pengajuan NIB:</strong>
                        Menentukan jenis usaha yang dijalankan pelaku usaha. 
                        Menjadi dasar penentuan perizinan berusaha dan kewajiban lainnya.
                        Digunakan oleh pemerintah untuk keperluan statistik, pajak, dan pembinaan usaha. <br>
                        <strong>Cara menentukan KBLI:</strong><br>
                        1. Identifikasi kegiatan utama usaha Anda<br>
                        2. Cari kategori yang paling sesuai di daftar KBLI<br>
                        3. Gunakan kode 5 digit yang tepat<br>
                        <strong>Contoh:</strong><br>
                        • Warung makan: 56101<br>
                        • Toko kelontong: 47211<br>
                        • Jasa potong rambut: 96021 </br>
                        🔍 <strong>Cara Mencari Kode KBLI:</strong><br>
                        Untuk mencari kode KBLI yang tepat, Anda bisa:<br>
                        <strong> 1. Deskripsikan usaha Anda</strong> <br>- Ketik jenis usaha atau layanan yang Anda jalankan<br>
                        <strong> 2. Contoh input yang baik:</strong><br>
                        • "warung makan nasi padang"<br>
                        • "toko elektronik handphone"<br>
                        • "jasa service motor"<br>
                        • "klinik kesehatan umum"<br>
                        <strong> 3. Sistem akan memberikan:</strong><br>
                        • Beberapa pilihan kode KBLI<br>
                        • Judul dan deskripsi lengkap<br>
                        • Rekomendasi yang paling sesuai<br>
                        💡 <em>Silakan coba sekarang dengan mendeskripsikan usaha Anda!</em>`;
              break;

            case "persyaratan-nib":
              question = "Persyaratan Pengajuan NIB";
              response = `📄 <strong>Persyaratan NIB (Nomor Induk Berusaha):</strong></br>
                        <strong>Dokumen yang diperlukan untuk Usaha Perseorangan (UMK/Usaha Mikro dan Kecil):</strong><br>
                        1.	KTP dan NIK pemilik usaha<br>
                        2.	Alamat lengkap usaha<br>
                        3.	Jenis dan nama usaha<br>
                        4.	Nomor telepon dan email aktif<br>
                        5.	Kode KBLI yang sesuai dengan jenis usaha<br>
                        6.	NPWP (jika ada)<br>
                        7.	Lokasi dan luas tempat usaha<br>
                        8.	Jumlah tenaga kerja<br>
                        9.	Rencana investasi atau modal usaha<br>
                        10.	Surat pernyataan bersedia mematuhi peraturan (akan muncul otomatis di sistem OSS)</br>
                        <strong>Untuk Badan Usaha (PT, CV, Yayasan, dll.):</strong><br>
                        1.	Akta pendirian dan SK Kemenkumham<br>
                        2.	NPWP Badan Usaha<br>
                        3.	Data pengurus/pemilik<br>
                        4.	Alamat email & nomor HP perusahaan<br>
                        5.	Dokumen pendukung lain tergantung jenis badan usaha</br>
                        <strong>Catatan:</strong><br>
                        • NIB berlaku seumur hidup<br>
                        • Gratis dan dapat diurus online di OSS`;
              break;

            case "langkah-nib":
              question = "Langkah-langkah Pengajuan NIB";
              response = `📝 <strong>Langkah-langkah Pengajuan NIB </strong><br>
                        Pengajuan NIB dilakukan secara online melalui platform resmi OSS (Online Single Submission). NIB dapat diperoleh oleh pelaku usaha perseorangan maupun non-perseorangan (seperti PT, CV, koperasi, yayasan). <br>
                        <strong>Adapun Langkah-langkah Pengajuan NIB : </strong><br>
                        1. Akses Website OSS. Buka https://oss.go.id Pilih menu "Daftar" dan buat akun OSS jika belum memiliki.<br>
                        2. Lengkapi data diri dan data usaha.<br>
                        3. Pilih KBLI sesuai usaha.<br>
                        4. Submit dan cetak NIB.<br>
                        <strong>Catatan:</strong> Gunakan KBLI 2020 yang sesuai agar tidak terkendala dalam proses perizinan lanjutan. Simpan baik-baik file NIB dan akun OSS kamu.`;
              break;

            case "persyaratan-halal":
              question = "Persyaratan Sertifikat Halal";
              response = `🥘 <strong>Persyaratan Sertifikat Halal:</strong><br>
                        <strong>Dokumen yang diperlukan:</strong><br>
                        1. Sertifikat NIB<br>
                        2. Manual sistem jaminan halal<br>
                        3. Daftar produk dan bahan baku<br>
                        4. Sertifikat halal bahan baku<br>
                        5. Dokumentasi proses produksi<br>
                        6. Daftar penyelia halal<br>
                        <strong>Biaya:</strong><br>
                        • Mikro: Gratis<br>
                        • Kecil: Rp 300.000<br>
                        • Menengah: Rp 2.500.000`;
              break;

            case "langkah-halal":
              question = "Langkah-langkah Sertifikat Halal";
              response = `✅ <strong>Langkah-langkah Sertifikat Halal:</strong></br>
                        1. <strong>Persiapan</strong> dokumen persyaratan<br>
                        2. <strong>Daftar</strong> di SIHALAL https://bpjph.halal.go.id/ <br>
                        3. <strong>Upload</strong> semua dokumen<br>
                        4. <strong>Pembayaran</strong> biaya sertifikasi<br>
                        5. <strong>Pemeriksaan</strong> dokumen oleh LPPOM MUI<br>
                        6. <strong>Audit</strong> ke lokasi produksi<br>
                        7. <strong>Keputusan</strong> komisi fatwa MUI<br>
                        8. <strong>Penerbitan</strong> sertifikat halal</br>
                        <strong>Masa berlaku:</strong> 4 tahun`;
              break;

            case "bantuan-umkm":
              question = "Program Bantuan UMKM";
              response = `💰 <strong>Program Bantuan UMKM:</strong><br>
                        <strong>1. Bantuan Produktif Usaha Mikro (BPUM)</strong><br>
                        • Dana bantuan Rp 2.4 juta<br>
                        • Untuk usaha mikro terdampak pandemi<br>
                        <strong>2. KUR (Kredit Usaha Rakyat)</strong><br>
                        • Mikro: hingga Rp 50 juta<br>
                        • Kecil: hingga Rp 500 juta<br>
                        • Bunga rendah dan mudah diakses<br>
                        <strong>3. Program Pelatihan UMKM</strong><br>
                        • Pelatihan digital marketing<br>
                        • Manajemen keuangan usaha<br>
                        • Pengembangan produk<br>
                        <strong>Info lebih lanjut:</strong> Hubungi Dinas Koperasi setempat`;
              break;

          }

  addUserMessage(question);
  showTyping();

  setTimeout(() => {
    hideTyping();
    addBotMessage(response);
    autoCollapseQuestions();
  }, 1000);
}


// ==================== COLLAPSE ====================
function toggleQuestions() {
  const q = document.getElementById("quickQuestions");
  q.classList.toggle("expanded");
  q.classList.toggle("collapsed");
}

function autoCollapseQuestions() {
  const q = document.getElementById("quickQuestions");
  if (q?.classList.contains("expanded")) {
    setTimeout(() => {
      q.classList.remove("expanded");
      q.classList.add("collapsed");
    }, 1000);
  }
}

// ==================== API FLASK ====================
async function getKBLIRecommendation(text) {
  try {
    // 1️⃣ Panggil chat dulu
    let res = await fetch("http://127.0.0.1:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        session_id: SESSION_ID
      })
    });

    let data = await res.json();

    // Kalau chat bisa jawab langsung (bantuan, panduan, dll)
    if (data.reply) {
      return data.reply.replace(/\n/g, "<br>");
    }

    // 2️⃣ Kalau diarahkan ke predict
    if (data.redirect === "predict") {

      // 👉 DI SINI LOGIC REDIRECT BERJALAN
      res = await fetch("http://127.0.0.1:5000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          session_id: SESSION_ID
        })
      });

      data = await res.json();

      if (!data.success) {
        return "⚠️ Saya butuh deskripsi usaha yang lebih jelas ya 🙂";
      }

      let reply = "";

      if (data.chatbot_reply) {
        reply += data.chatbot_reply.replace(/\n/g, "<br>") + "<br><br>";
      }

      reply += "🔍 <b>Rekomendasi KBLI:</b><br><br>";

      data.recommendations.forEach(r => {
        reply += `<b>${r.kode} - ${r.judul}</b><br>${r.deskripsi}<br><br>`;
      });

      return reply;
    }

  } catch (err) {
    console.error(err);
    return "🚫 Server sedang tidak tersedia.";
  }
}


// ==================== CHAT API ====================
async function getChatResponse(text) {
  try {
    const res = await fetch("http://127.0.0.1:5000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    });

    return await res.json();
  } catch {
    return { reply: "🚫 Server sedang tidak tersedia." };
  }
}



// ==================== INIT ====================
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("chatInput")?.focus();
});
