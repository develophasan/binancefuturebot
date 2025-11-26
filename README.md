# Binance Futures AI Long Bot

**Long-Only** yapay zeka destekli otomatik Binance Futures trading botu.

## 🎯 Özellikler

- ✅ **AI Destekli Karar Mekanizması**: OpenAI GPT-4o ile akıllı ticaret kararları
- ✅ **Long-Only Strateji**: Sadece yükseliş pozisyonları
- ✅ **Risk Yönetimi**: Katı stop-loss, take-profit ve günlük zarar limitleri
- ✅ **Teknik Analiz**: EMA, RSI, ATR, volatilite ve hacim analizi
- ✅ **Dinamik Coin Takibi**: Popüler coinler + günlük en çok artanlar
- ✅ **Testnet Desteği**: Gerçek para riski olmadan test
- ✅ **Modern Dashboard**: React tabanlı, gerçek zamanlı izleme

## 🏗️ Teknoloji Stack

### Backend
- **FastAPI** - Python async web framework
- **MongoDB** - Veritabase
- **Binance API** - Futures trading
- **TA-Lib** - Teknik indikatörler
- **Emergent LLM** - AI entegrasyonu (OpenAI GPT-4o)

### Frontend
- **React** - UI framework
- **Tailwind CSS** - Styling
- **Shadcn/UI** - Component library
- **React Router** - Navigation
- **Axios** - HTTP client

## 🚀 Kurulum ve Çalıştırma

### Backend

Backend otomatik olarak başlatılır. Logları kontrol etmek için:

```bash
tail -f /var/log/supervisor/backend.*.log
```

### Binance API Anahtarları (Opsiyonel)

Testnet için API anahtarları `/app/backend/.env` dosyasına eklenmelidir:

```env
BINANCE_TESTNET_API_KEY=your_testnet_api_key
BINANCE_TESTNET_SECRET_KEY=your_testnet_secret_key
```

**Not**: API anahtarları olmadan bot "mock mode"da çalışır (test verisi kullanır).

## 🎮 Kullanım

### Dashboard
- Bot durumu, açık pozisyonlar, günlük PnL
- 24 saatlik en çok yükselen coinler
- Gerçek zamanlı güncelleme

### Pozisyonlar
- Açık ve kapalı pozisyonlar
- Giriş/çıkış fiyatları, TP/SL seviyeleri, PnL takibi

### AI Kararları
- AI tarafından verilen tüm kararlar
- LONG / SKIP kararları, Güven skoru ve sebep

### Ayarlar
- Bot aktif/pasif, Pozisyon boyutu, Kaldıraç aralığı
- Risk parametreleri, İşlem limitleri

## 🤖 AI Karar Mekanizması

Bot her 5 dakikada bir piyasayı analiz eder ve teknik indikatörler, hacim analizi, funding rate gibi verileri AI'ya gönderir. AI, muhafazakar bir yaklaşımla LONG veya SKIP kararı verir.

## 📊 Varsayılan Ayarlar

- Pozisyon: 10 USDT | Leverage: 2-5x | TP: 0.25% | SL: 0.05%
- Max Açık: 3 | Max Günlük: 10 | Max Zarar: 10 USDT | 7/24

## ⚠️ Uyarı

Bu bot eğitim ve test amaçlıdır. **Finansal tavsiye değildir. Kendi riskiniz dahilinde kullanın.**
