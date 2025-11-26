# Cloudflare Worker Kurulum Talimatları

## Adım 1: Cloudflare Hesabı Oluşturun

1. https://dash.cloudflare.com/sign-up adresine gidin
2. Ücretsiz hesap oluşturun (kredi kartı gerekmiyor)

## Adım 2: Worker Oluşturun

1. Cloudflare Dashboard'a giriş yapın
2. Sol menüden **Workers & Pages** seçin
3. **Create Application** butonuna tıklayın
4. **Create Worker** seçin
5. Worker'a isim verin (ör: `binance-proxy`)
6. **Deploy** butonuna tıklayın

## Adım 3: Worker Kodunu Yapıştırın

1. Worker oluşturulduktan sonra **Quick Edit** butonuna tıklayın
2. Açılan editörde tüm kodu silin
3. `/app/cloudflare-worker.js` dosyasındaki kodu kopyalayın
4. Editöre yapıştırın
5. **Save and Deploy** butonuna tıklayın

## Adım 4: Worker URL'ini Alın

Worker deploy edildikten sonra bir URL alacaksınız:
```
https://binance-proxy.YOUR-SUBDOMAIN.workers.dev
```

Bu URL'i kopyalayın!

## Adım 5: URL'i Sisteme Ekleyin

Worker URL'inizi buraya yapıştırın, ben sisteme entegre edeyim.

Örnek:
```
https://binance-proxy.myname.workers.dev
```

---

## Test Etmek İçin

Worker çalışıyor mu test etmek için tarayıcınızda:
```
https://YOUR-WORKER-URL/testnet/api/v3/time
```

Şöyle bir cevap görmeli siniz:
```json
{"serverTime":1732599123456}
```

---

## Önemli Notlar

✅ **Ücretsiz Tier Limitleri:**
- 100,000 request/day
- Her request 10ms CPU time
- Bot için fazlasıyla yeterli

✅ **Güvenlik:**
- API keyler backend'de kalır
- Worker sadece proxy görevi görür
- CORS koruması var

✅ **Performans:**
- Cloudflare global CDN
- Çok hızlı yanıt süreleri
- Binance'den daha stabil

---

## Sorun Giderme

**Worker çalışmıyor:**
- Kod'u doğru yapıştırdığınızdan emin olun
- Save and Deploy'a bastığınızdan emin olun
- URL'i doğru kopyaladığınızdan emin olun

**403/401 hataları:**
- API keyler backend .env dosyasında olmalı
- Worker sadece proxy, authentication backend'de

**Rate limit:**
- Ücretsiz tier 100k request/day
- Botu 5 dakikada bir çalıştırıyoruz, sorun olmaz
