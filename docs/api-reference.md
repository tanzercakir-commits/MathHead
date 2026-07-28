# MathHead — API Referansı (otomatik üretilmiş)

> **UYARI:** Bu dosya `scripts/gen_api_reference.py` tarafından, MCP'ye
> kayıtlı araçlardan üretilir. ELLE DÜZENLEME. Güncellemek için:
> `python scripts/gen_api_reference.py`. Sözleşme ayrıntısı: `docs/mcp-api.md`.

Toplam **64 araç**.

### `entailment(premises, conclusion)`

Öncüller sonucu MANTIKSAL OLARAK gerektirir mi? (premises ⊨ conclusion)

### `consistency(statements)`

Bu ifadeler AYNI ANDA doğru olabilir mi? (tutarlılık / satisfiability)

### `model(statements)`

İfadeleri sağlayan SOMUT bir örnek (değişken ataması) döndürür.

### `prove(premises, conclusion)`

Öncüller sonucu gerektiriyorsa NEDEN gösterir — minimal çekirdek + adım adım türetim.

### `equivalent(a, b)`

İki ifade mantıksal olarak DENK mi? (her atamada aynı doğruluk değeri)

### `classify(formula)`

Bir formülü sınıflandır: totoloji / çelişki / olumsal (contingent).

### `enumerate_models(statements, limit=10)`

İfadeleri sağlayan FARKLI modelleri (en fazla `limit`) numaralandırır.

### `optimize(constraints, objective, sense='max')`

Kısıtları sağlayıp sayısal `objective`'i en büyük/küçük (`sense`) yapan çözümü bul.

### `max_satisfy(hard, soft, weights=None)`

Zorunlu (`hard`) kısıtları sağlayıp EN ÇOK (ağırlıklı) `soft` kısıtı sağla (MaxSAT).

### `prove_inequality(goal, assumptions=None)`

`goal` eşitsizliği TÜM gerçel değerler için (varsayımlar altında) geçerli mi?

### `prove_nonnegative(expression, assumptions=None)`

`expression ≥ 0` her gerçel değer için (varsayımlar altında) geçerli mi?

### `find_real_solution(constraints)`

Doğrusal-olmayan kısıt kümesini GERÇEL sayılarda sağlayan bir nokta bulur.

### `verify_equality(left, right)`

İki ifade DENK mi? (AI'ın "= şuna eşittir" iddiasını bağımsız denetler.)

### `verify_solution(equation, symbol, claimed)`

`claimed` değerleri `equation`'ın çözümü MÜ ve TAM MI? (AI'ın çözüm iddiası.)

### `verify_steps(steps)`

Bir ifade zincirinde her adım öncekiyle DENK mi — ilk hatalı geçişi bulur.

### `cross_check(left, right)`

`left = right` iddiasını Z3 VE SymPy ile BAĞIMSIZ doğrular; mutabakat arar.

### `check_certificate(certificate)`

Bir sonucu ÜRETEN motordan (Z3/SymPy) BAĞIMSIZ, yalnız stdlib ile doğrular.

### `simplify(expression)`

Bir cebirsel ifadeyi sadeleştirir (ör. 'sin(x)**2 + cos(x)**2' -> '1').

### `solve(equation, symbol)`

Bir denklemi bir değişken için çözer (ör. 'x**2 == 4', symbol='x').

### `differentiate(expression, symbol, order=1)`

İfadenin `symbol`'e göre `order`. mertebeden türevini alır.

### `integrate(expression, symbol)`

İfadenin `symbol`'e göre belirsiz integralini alır (+C).

### `limit(expression, symbol, point='0', direction='both')`

`symbol` → `point` iken ifadenin limiti. direction: both | + | - (tek yön).

### `series(expression, symbol, point='0', order=6)`

İfadenin `symbol`=`point` etrafında `order`. mertebeden Taylor/seri açılımı.

### `solve_system(equations, symbols)`

Bir denklem SİSTEMİNİ birden çok değişken için çözer.

### `determinant(matrix)`

Kare bir matrisin determinantı. Hücreler sayısal veya sembolik olabilir.

### `matrix_inverse(matrix)`

Kare bir matrisin tersi (A⁻¹). Tekil (singular, det=0) ise DÜRÜSTÇE hata.

### `eigenvalues(matrix)`

Kare bir matrisin özdeğerleri (eigenvalue) + cebirsel katlılık (multiplicity).

### `matrix_rank(matrix)`

Bir matrisin rankı (doğrusal bağımsız satır/sütun sayısı). Kare olması şart değil.

### `matrix_multiply(a, b)`

İki matrisin çarpımı A·B. İç boyutlar (A sütun = B satır) uyumsuzsa dürüst hata.

### `matrix_solve(matrix, rhs)`

`A x = b` doğrusal sistemini matris formunda çözer.

### `eigenvectors(matrix)`

Özdeğer + cebirsel katlılık + özvektör(ler). Özdeğere göre sıralı (determinizm).

### `rref(matrix)`

İndirgenmiş satır eşelon form (RREF) + pivot sütun indeksleri.

### `nullspace(matrix)`

Boş uzayın (null space / çekirdek) bir tabanı. Boş liste = yalnız sıfır (trivial).

### `lu_decomposition(matrix)`

LU ayrıştırma: A = P·L·U. Dönüş: `L`, `U` matrisleri + `perm` (satır takasları).

### `gcd(a, b)`

İki tam sayının en büyük ortak böleni (GCD).

### `lcm(a, b)`

İki tam sayının en küçük ortak katı (LCM).

### `is_prime(n)`

`n` asal mı? (deterministik asallık testi). Dönüş: `result` = true/false.

### `factorize(n)`

`n`'i asal çarpanlarına ayırır. Dönüş: `[{"prime":p,"exponent":e}, ...]` (artan).

### `modular_inverse(a, m)`

`a`'nın `m` modülünde çarpımsal tersi. Yoksa (gcd(a,m)≠1) dürüst hata.

### `chinese_remainder(moduli, residues)`

Çin Kalan Teoremi (CRT): x ≡ residues[i] (mod moduli[i]). Bağdaşmazsa dürüst hata.

### `linear_diophantine(a, b, c)`

`a·x + b·y = c` denklemini TAM SAYILARDA çözer (parametre `t_0`).

### `permutations(n, k)`

P(n,k) — `n` nesneden `k`'lı sıralı seçim sayısı (k>n ise 0).

### `combinations(n, k)`

C(n,k) — `n` nesneden `k`'lı sırasız seçim sayısı (binom katsayısı).

### `factorial(n)`

n! — ilk `n` pozitif tam sayının çarpımı (0! = 1).

### `partition_count(n)`

p(n) — `n`'i pozitif tam sayı toplamı olarak yazma yollarının sayısı.

### `solve_recurrence(recurrence, func='y', var='n', initial=None)`

Doğrusal özyineleme bağıntısını KAPALI FORMA çözer.

### `gradient(expression, variables)`

∇f — `expression`'ın her değişkene göre kısmi türevleri (liste).

### `jacobian(expressions, variables)`

Jacobian matrisi — vektör-değerli fonksiyonun kısmi türev matrisi.

### `hessian(expression, variables)`

Hessian matrisi — skaler fonksiyonun ikinci kısmi türev matrisi (simetrik).

### `definite_integral(expression, symbol, lower, upper)`

Belirli integral ∫ₐᵇ f dx. Sınırlar sonsuz olabilir ("oo"/"-oo").

### `summation(expression, index, lower, upper)`

Toplam Σ — `index`=lower..upper için `expression` toplamı (kapalı form olabilir).

### `product(expression, index, lower, upper)`

Çarpım Π — `index`=lower..upper için `expression` çarpımı.

### `solve_ode(equation, func='y', var='x')`

Sıradan diferansiyel denklemi (ODE) çözer. Türev: `y'`, `y''` (üs işareti).

### `mean(data)`

Bir sayı listesinin aritmetik ortalaması (tam/rasyonel).

### `variance(data, sample=False)`

Varyans. sample=True → örneklem (n-1); aksi halde yığın (n).

### `standard_deviation(data, sample=False)`

Standart sapma = √varyans (sample seçeneği variance ile aynı).

### `median(data)`

Ortanca. Çift sayıda gözlemde ortadaki ikinin ortalaması.

### `distribution(name, params, at=None)`

Adlandırılmış dağılımın E[X]/Var/std (sembolik/tam) özellikleri.

### `pythagorean_coloring(n)`

{1..n}'i 2 renge, tek renkli Pythagoras üçlüsü olmadan boyamayı dener.

### `pigeonhole(n)`

`n+1` güvercinin `n` kutuya sığamayacağını ispatlar (güvercin yuvası ilkesi).

### `van_der_waerden(n, k, colors=2)`

{1..n}'i `colors` renge, tek renkli k-terimli aritmetik dizi olmadan boyamayı dener.

### `schur_number(n, colors)`

{1..n}'i `colors` sum-free renge bölmeyi dener (Schur sayısı S(colors) çekirdeği).

### `graph_coloring(edges, colors, n=None)`

Grafı `colors` renge boyar (komşular farklı). NP-tam graph k-coloring.

### `subset_sum(numbers, target)`

`numbers`'ın bir alt kümesi `target`'a toplanır mı? (NP-tam subset-sum).
