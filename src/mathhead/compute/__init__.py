"""
mathhead.compute — Sembolik hesap katmanı (CAS, SymPy tabanlı).

DURUM: v2+ için ayrılmış (rezerve). v1 SADECE mantık çekirdeğine (core/Z3)
odaklanır; bu paket kasıtlı olarak boş bırakılmıştır ki v1 dilimi "dar & sağlam"
kalsın (proje prensibi: vertical slice). Yol haritası için Plan.md'ye bakın.

Buraya gelecek yetenekler (Plan.md ile senkron):
    * sadeleştirme (simplify), denklem/eşitsizlik çözme (solve)
    * türev / integral / limit (calculus)
    * çözücü sonuçlarının insan-okur adımlara dökülmesi (explanation)
"""
