# Türkçe başlangıç

GraphPilot, LangGraph ile çalışan ve araç kullanabilen bir AI agent projesidir. Groq ilk sağlayıcıdır; diğer LiteLLM sağlayıcıları model ayarıyla seçilebilir. Her modelin tool veya görüntü desteği aynı değildir.

1. Ana README'deki kurulumu yapın ve sanal ortamı etkinleştirin.
2. `python -m graphpilot.cli demo` ile anahtarsız örneği çalıştırın. Bu örnek gerçek model çağırmaz.
3. `.env.example` dosyasını `.env` olarak kopyalayın.
4. `python -m graphpilot.cli configure` ile Groq anahtarını gizli giriş alanından kaydedin.
5. `python -m graphpilot.cli doctor` ile anahtarın varlığını kontrol edin.
6. `python -m graphpilot.cli run "Yapılacaklar listesini liste.txt dosyasına yaz"` komutunu çalıştırın.

Dosya yazma ve telefon işlemleri önce onay ister. Önerilen aracın adını ve parametrelerini okuyun. Onay verilmezse işlem yapılmaz. Oturumlar `.graphpilot/sessions.sqlite` dosyasında tutulur.

USB telefon kullanımı için ayrı `usbphone-control` paketini aynı sanal ortama kurun ve `--phone` seçeneğini ekleyin. ADB yolunu `.env` içindeki `ADB_PATH` alanına yazabilirsiniz. USB hata ayıklama ve RSA izni telefondan sizin tarafınızdan açılmalıdır.

Kullanıcı hedefi söyler: “Bu iş ilanına benim için başvur” veya “Bu siteden öğrenci belgemi indir”.
Agent gerekli uygulamayı ve ekran adımlarını kendisi seçer; kullanıcıya Chrome'u açmasını tarif ettirmez.
0.2.0 sürümünde telefonda site açma, Downloads listesini okuma ve dosyayı SHA-256 ile kontrol ederek
bilgisayara alma araçları vardır. [Akışlar ve sınırlar](phone-goals.md) ayrıntıları açıklar.
Her telefon eylemi hâlâ host onayı gerektirir. Türkçe karakterlerle form doldurma henüz desteklenmez;
OTP/CAPTCHA ve eksik başvuru bilgileri gerektiğinde kullanıcı devreye girer.

İlk sürüm yerel bir pilottur. Canlı Groq testi için API anahtarı, gerçek telefon testi için bağlı Android cihaz gerekir. Otomatik test sonuçları, gerçek cihazda tamamlanmış bir görev olarak sunulmaz.
