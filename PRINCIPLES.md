# MathHead — Proje Prensipleri

> **Bu dosyanın işi:** Motoru geliştiren herkesin (insan ya da AI) uyması gereken
> değişmez kurallar. Bir kod/karar bu prensiplerden biriyle çelişiyorsa, karar
> değil prensip kazanır. Bu, senin "açıkça tanımlanmış proje prensipleri" ve
> "çitin dışına çıkma" maddelerinin somut hali.

---

## Çekirdek prensipler

1. **Determinizm önce gelir.** Aynı girdi → aynı **verdict** (kesin sonuç: valid/
   invalid/sat/unsat). Tanık (witness) geçerli bir *örnektir*; birden çok çözüm
   varsa hangisi döndüğü değişebilir ama verdict hep aynıdır (ADR-0019). Oynaklık
   motorun *dışında* kalır. *(Duvar #3)*

2. **Sessiz varsayım yok.** Girdi belirsiz, eksik ya da gramer dışıysa motor
   **reddeder** — "herhalde şunu kastetti" diye tahmin *etmez*. Reddin gerekçesi
   nettir. *(Duvar #2)*

3. **`unknown` ve `error` birinci sınıf çıktıdır.** Motor bir sonucu bilmiyorsa
   bunu açıkça söyler; asla sahte bir `valid/sat` **uydurmaz**. Dürüstlük > iyi
   görünmek.

4. **Çit serttir (hard guardrail).** Boyut, derinlik, süre ve sembol sınırları
   aşılamaz. Çözücü sonsuza kadar çalışamaz; zaman aşımı bir *özelliktir*, hata
   değil.

5. **Dış API'yi erken dondur, içini sonra doldur.** `ReasoningResult` sözleşmesi
   ve MCP araç imzaları sabittir. Çekirdek değişse de dış dünya etkilenmez.
   *(Duvar #1: sözleşme kaymasını önler.)*

6. **Dar & sağlam > geniş & sığ.** Her sürüm uçtan uca *çalışan* bir dikey dilim
   ekler. "Yarım ama geniş" yerine "küçük ama tam" tercih edilir.

7. **Her karar yazılır.** Mimariyi etkileyen her seçim `DECISIONS.md`'ye
   (ADR olarak), her iş adımı `Progress.md`'ye işlenir. Küçük kararlar
   *kaybolmaz*. *(Duvar #1)*

8. **Test = spesifikasyon.** Yeni yetenek, önce best-case **ve** worst-case
   testiyle tanımlanır. `unknown`/timeout davranışı da test edilir.

9. **İzlenebilirlik zorunlu.** Her yanıt `meta` taşır: hangi çözücü, hangi sürüm,
   ne kadar sürdü, hangi tohum. Bir sonuç her zaman *yeniden üretilebilir*
   olmalı.

10. **Dış sözleşme motordan bağımsızdır.** Bugün Z3, yarın başka bir çözücü —
    MCP/`ReasoningResult` katmanı değişmez. Bu, gelecekteki motorlara (v4:
    Fizik/Kimya) zemini korur.

---

## Bir değişiklik yapmadan önce kontrol listesi

- [ ] Bu değişiklik hangi prensiple hizalı / çelişiyor?
- [ ] Dış API sözleşmesini (imza/çıktı) değiştiriyor mu? Değiştiriyorsa **dur**,
      önce ADR yaz.
- [ ] Best-case *ve* worst-case testi var mı?
- [ ] Determinizmi bozuyor mu? (yeni rastgelelik / sıra bağımlılığı?)
- [ ] `Progress.md` güncellendi mi, gerekiyorsa yeni ADR açıldı mı?
