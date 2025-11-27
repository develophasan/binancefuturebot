# 🚨 TESTNET'TEN MAINNET'E GEÇİŞ REHBERİ

## ⚠️ ÖNEMLİ UYARILAR

**GERÇEK PARA RİSKİ VAR!**
- ❌ Test etmeden direkt büyük paralarla başlamayın
- ✅ Önce KÜÇÜK miktarlarla test edin (10-20 USDT)
- ✅ Stop Loss ve Take Profit her zaman aktif
- ✅ Max daily loss limitlerini düşük tutun
- ✅ İlk günler botu dikkatli takip edin

---

## 📋 ADIM ADIM GEÇİŞ

### ADIM 1: Binance'de Gerçek API Key Oluşturma

#### 1.1 Binance Hesabınıza Giriş Yapın
- https://www.binance.com adresine gidin
- Hesabınıza login olun
- **2FA (Two-Factor Authentication) mutlaka aktif olmalı!**

#### 1.2 API Management Sayfasına Gidin
- Sağ üst köşede profil ikonuna tıklayın
- **API Management** seçeneğine tıklayın
- Veya direkt: https://www.binance.com/en/my/settings/api-management

#### 1.3 Yeni API Key Oluşturun
1. **"Create API"** butonuna tıklayın
2. **API Key Label** girin: örn. "AI Trading Bot"
3. **API Key Type**: "System generated" seçin
4. **Passphrase** oluşturun (güçlü bir şifre)
5. 2FA kodunu girin
6. Email onayını yapın

#### 1.4 API Key İzinlerini Ayarlayın (ÇOK ÖNEMLİ!)

**✅ Aktif Olması Gerekenler:**
- ✅ **Enable Futures** (Vadeli işlemler için ZORUNLU)
- ✅ **Enable Reading** (Hesap bilgilerini okumak için)

**❌ DİKKAT - DEVRE DIŞI BIRAKILMALI:**
- ❌ **Enable Spot & Margin Trading** (Spot işlem yapma yetkisi - GEREKLİ DEĞİL)
- ❌ **Enable Withdrawals** (Para çekme - GÜVENLİK İÇİN KAPALI OLMALI!)

**IP Whitelist (Tavsiye Edilir):**
- Botunuzun çalıştığı sunucunun IP adresini ekleyin
- Böylece sadece o IP'den işlem yapılabilir

#### 1.5 API Key ve Secret'i Kaydedin
```
API Key: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**⚠️ UYARI:** Secret key'i sadece bir kez gösterilir! Güvenli bir yere kaydedin.

---

### ADIM 2: Bot Ayarlarını Güncelleme

#### 2.1 API Keys'i Backend .env Dosyasına Ekleyin

Dosya: `/app/backend/.env`

```bash
# Mevcut testnet keylerini yedek olarak comment out edin
# BINANCE_API_KEY=testnet_key...
# BINANCE_API_SECRET=testnet_secret...

# Gerçek Binance API Keys (MAINNET)
BINANCE_API_KEY=your_real_api_key_here
BINANCE_API_SECRET=your_real_api_secret_here

# Proxy listesi (aynı kalacak)
PROXY_LIST=http://username:password@proxy1.com:port,http://username:password@proxy2.com:port
```

#### 2.2 Binance Service'i Mainnet Moduna Alın

Dosya: `/app/backend/services/binance_service.py`

Değişiklik: `testnet=True` → `testnet=False`

**VEYA** daha güvenli yöntem - .env'den kontrol:

`.env` dosyasına ekleyin:
```bash
BINANCE_USE_TESTNET=false  # true = testnet, false = mainnet
```

#### 2.3 Güvenlik Ayarları (Kritik!)

Settings'te şu değerleri düşük tutun:

```python
# İlk gün için tavsiye edilen ayarlar
position_size_value: 10 USDT  # Küçük başlayın
max_leverage: 3  # Yüksek kaldıraç = yüksek risk
max_open_positions: 2  # Maksimum 2 pozisyon
max_trades_per_day: 5  # Günde max 5 işlem
max_daily_loss_usdt: 20 USDT  # Günlük max zarar limiti
```

---

### ADIM 3: Kod Değişiklikleri

#### 3.1 BinanceService Constructor Güncellemesi

**MEVCUT KOD:**
```python
class BinanceService:
    def __init__(self, testnet: bool = True):
        self.testnet = testnet
        if testnet:
            self.futures_base_url = "https://testnet.binancefuture.com"
        else:
            self.futures_base_url = "https://fapi.binance.com"
```

**ÖNERİ - .env'den okusun:**
```python
class BinanceService:
    def __init__(self, testnet: bool = None):
        # .env'den oku, yoksa default False (mainnet)
        if testnet is None:
            testnet = os.environ.get('BINANCE_USE_TESTNET', 'false').lower() == 'true'
        
        self.testnet = testnet
        if testnet:
            self.futures_base_url = "https://testnet.binancefuture.com"
        else:
            self.futures_base_url = "https://fapi.binance.com"  # GERÇEK BORSA
```

#### 3.2 server.py'de Başlatma

```python
# TESTNET: binance_service = BinanceService(testnet=True)
binance_service = BinanceService(testnet=False)  # ✅ MAINNET
```

---

### ADIM 4: Test ve Doğrulama

#### 4.1 Backend'i Yeniden Başlatın
```bash
sudo supervisorctl restart backend
```

#### 4.2 Logları Kontrol Edin
```bash
tail -f /var/log/supervisor/backend.err.log
```

Şunları arayın:
- ✅ "✅ Fetched FUTURES balance: XXXX USDT" (gerçek bakiyeniz)
- ✅ API bağlantısı başarılı
- ❌ "401 Unauthorized" veya "API key invalid" OLMAMALI

#### 4.3 API Bağlantısını Test Edin

**Curl ile test:**
```bash
curl "http://localhost:8001/api/bot/status"
```

Gerçek bakiyenizi görmeli.

#### 4.4 İlk Manuel İşlem Testi

1. AI Kararları sayfasına gidin
2. Bir coin seçin (örn. BTC)
3. "Manuel Gir" butonuna tıklayın
4. **Küçük miktar girin:** 10 USDT
5. Leverage: 2x (güvenli)
6. TP: 2%, SL: 1%
7. "Pozisyon Aç" tıklayın

✅ Eğer pozisyon açılırsa → API çalışıyor!

---

### ADIM 5: Güvenlik Kontrol Listesi

#### ✅ Başlamadan Önce Kontrol Edin:

- [ ] Binance API key'de **Withdrawals KAPALI**
- [ ] **2FA aktif** (hesap güvenliği için)
- [ ] IP whitelist ayarlanmış (opsiyonel ama tavsiye)
- [ ] Küçük miktarlarla test yapıldı (10-20 USDT)
- [ ] Max daily loss limiti ayarlandı (örn. 50 USDT)
- [ ] Stop Loss her zaman aktif
- [ ] Bot loglarını ilk günler takip edeceksiniz

#### ⚠️ Risk Yönetimi:

**İlk Hafta:**
- Pozisyon boyutu: 10-20 USDT
- Max leverage: 2-3x
- Max open positions: 2
- Günlük max zarar: 50 USDT

**Güven Oluştuktan Sonra:**
- Pozisyon boyutu: 50-100 USDT
- Max leverage: 3-5x
- Max open positions: 3-5
- Günlük max zarar: 200 USDT

---

## 🔄 Hızlı Geçiş Özeti

### 1 Dakikada Yapılması Gerekenler:

```bash
# 1. Binance'de API key oluştur (Enable Futures, Disable Withdrawals)

# 2. Backend .env dosyasını güncelle
nano /app/backend/.env
# BINANCE_API_KEY=gerçek_key
# BINANCE_API_SECRET=gerçek_secret
# BINANCE_USE_TESTNET=false

# 3. server.py'de testnet=False yap
nano /app/backend/server.py
# binance_service = BinanceService(testnet=False)

# 4. Backend'i restart et
sudo supervisorctl restart backend

# 5. Küçük miktarla test et (10 USDT)
# Manuel Gir → Test pozisyonu aç

# 6. Başarılıysa → Bot'u aktif et
```

---

## 🚨 Acil Durum Protokolü

### Botu Durdurmak İsterseniz:

**Yöntem 1: Frontend'den**
- Settings → Bot Status → "Pasif" yap

**Yöntem 2: Backend'den**
```bash
# Botu durdur
curl -X POST http://localhost:8001/api/bot/stop

# Veya backend'i tamamen kapat
sudo supervisorctl stop backend
```

**Yöntem 3: API Key'i Devre Dışı Bırak**
- Binance → API Management → API key'i disable et

---

## 📊 İzleme ve Raporlama

### Günlük Kontrol Listesi:

**Her Gün:**
- [ ] Açık pozisyonları kontrol et
- [ ] Günlük PnL'e bak
- [ ] AI kararlarını incele
- [ ] Stop loss'ların yerinde olduğunu kontrol et

**Her Hafta:**
- [ ] Toplam performansı değerlendir
- [ ] Kazanma oranını kontrol et
- [ ] Risk parametrelerini ayarla

---

## ❓ Sık Sorulan Sorular

**S: Testnet pozisyonlarım ne olacak?**
C: Onlar testnet'te kalacak. Gerçek borsayı etkilemez.

**S: Gerçek paradan zarar edersem ne olur?**
C: Max daily loss limiti devreye girer ve bot o gün işlem yapmayı durdurur.

**S: API key çalınırsa?**
C: Withdrawals devre dışı olduğu için para çekilemez. Ama pozisyon açılabilir. Hemen API key'i disable edin.

**S: Bot hata yaparsa?**
C: Stop loss her zaman aktif, maksimum zarar = pozisyon boyutu × SL %

**S: Proxy gerekli mi?**
C: Türkiye'den Binance erişimi engellendiği için evet, proxy şart.

---

## 🎯 Başarı İçin Tavsiyeler

1. **Sabırlı Olun:** İlk haftalarda küçük miktarlarla öğrenin
2. **Risk Yönetimi:** Her zaman SL kullanın, büyük kaldıraçlardan kaçının
3. **Logları Takip Edin:** İlk günler botu yakından izleyin
4. **AI'ya Güvenin Ama Doğrulayın:** Manuel girişleri dikkatli yapın
5. **Kazançları Çekin:** Düzenli olarak kar realizasyonu yapın

---

## 📞 Destek

**Sorun yaşarsanız:**
- Backend loglarını kontrol edin: `tail -f /var/log/supervisor/backend.err.log`
- Frontend console'u kontrol edin
- Binance API status: https://www.binance.com/en/support/announcement

**Acil durumda:**
- Botu durdurun (Settings → Pasif)
- API key'i disable edin (Binance'de)
- Açık pozisyonları manuel kapatın (Binance UI'dan)

---

İyi şanslar! 🚀 Dikkatli ve küçük adımlarla başlayın!
