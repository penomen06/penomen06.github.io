// Sayfalar build_pages.py ile önceden doldurulmuş olarak gelir (arama motorları için).
// Bu betik tarayıcıda canlı veriyi yükler: anasayfa/kategori listesini yeniler,
// haber sayfasında benzer haberleri gösterir ve yönetim modunu çalıştırır.
const $ = s => document.querySelector(s);
const PAGE = document.body.dataset.page;          // "list" | "article" | "contact"
const CAT = document.body.dataset.cat || "hepsi"; // liste sayfasında kategori
const ID = document.body.dataset.id || "";        // haber sayfasında haber ID'si
let all = [], cfg = {}, feeds = {}, query = "", shown = 24;
const PALETTE = ["var(--tech)", "var(--gundem)", "#b7791f", "#8b5cf6", "#0e7490", "#db2777", "#4d7c0f"];

const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const safeUrl = u => /^(https?:\/\/|\/(?!\/))/i.test(u || "") ? u : "";

// Eski "#/haber/ID" bağlantıları yeni sayfalara yönlensin
const oldHash = location.hash.match(/^#\/haber\/(.+)$/);

// ---------------------------------------------------------------- yönetim
const host = location.hostname.endsWith(".github.io") ? location.hostname : "";
const REPO = document.body.dataset.repo || (host ? host.split(".")[0] + "/" + host : "");
function form(file, title, fields = {}){
  const p = new URLSearchParams({template: file, title});
  for (const [k, v] of Object.entries(fields)) if (v) p.set(k, v);
  return `https://github.com/${REPO}/issues/new?${p}`;
}
function isAdmin(){
  const want = new URLSearchParams(location.search).has("yonetim");
  try { if (want) localStorage.setItem("yonetim", "1"); return want || localStorage.getItem("yonetim") === "1"; }
  catch { return want; }
}
if (isAdmin()) document.body.classList.add("yonetim");
$("#a-exit").onclick = () => {
  try { localStorage.removeItem("yonetim"); } catch {}
  location.href = location.pathname;
};
$("#a-add").href = form("1-haber-ekle.yml", "[Haber] ");
$("#a-log").href = `https://github.com/${REPO}/issues?q=is%3Aissue`;
$("#a-src").onclick = () => $("#panel").classList.toggle("open");

function adminLinks(){
  $("#a-set").href = form("4-site-ayarlari.yml", "[Ayarlar] Site ayarları", {
    baslik: cfg.title, altyazi: cfg.subtitle, aciklama: cfg.description, renk: cfg.accent,
    altbilgi: cfg.footer, adet: String(cfg.per_feed || ""), kelimeler: (cfg.blocked_words || []).join("\n"),
    google: cfg.google_verification, iletisim: cfg.contact_email});
  const cats = cfg.categories || {};
  $("#panel-in").innerHTML = `<a class="lnk" target="_blank" rel="noopener" href="${esc(form("5-kaynak-kategori.yml", "[Kaynak] Yeni kaynak"))}">＋ Yeni kaynak veya kategori ekle</a>` +
    Object.entries(cats).map(([k, label]) => `<h4>${esc(label)}
      <a class="lnk" style="font-weight:500;font-size:12px;margin-left:8px" target="_blank" rel="noopener" href="${esc(form("5-kaynak-kategori.yml", "[Kaynak] " + label + " adını değiştir", {kategori: label}))}">adını değiştir / kaldır</a></h4>
      <ul>${(feeds[k] || []).map(u => `<li>${esc(u)} — <a class="lnk" target="_blank" rel="noopener" href="${esc(form("5-kaynak-kategori.yml", "[Kaynak] Kaldır", {kategori: label, rss: u}))}">kaldır</a></li>`).join("") || "<li>Kaynak yok</li>"}</ul>`).join("") +
    `<p style="font-size:12px;color:var(--muted);margin:14px 0 0">Formda yapmak istediğin işlemi "İşlem" kutusundan seç. Gönderdikten 1–2 dakika sonra sitede görünür.</p>`;
}

function adminRow(item){
  if (!item.id) return "";
  const t = item.title.slice(0, 60);
  return `<div class="adm"><span>ID <code>${esc(item.id)}</code></span>
    <a target="_blank" rel="noopener" href="${esc(form("2-haber-duzenle.yml", "[Düzenle] " + t, {haber_id: item.id, baslik: item.title, aciklama: (item.summary || "").length < 4000 ? item.summary : "", resim: item.image, link: item.link}))}">✏️ Düzenle / manşet</a>
    <a target="_blank" rel="noopener" href="${esc(form("3-haber-sil.yml", "[Sil] " + t, {haber_id: item.id}))}">🗑️ Sil</a></div>`;
}

// ---------------------------------------------------------------- liste görünümü
function ago(iso){
  const s = (Date.now() - new Date(iso)) / 1000;
  if (s < 60) return "az önce";
  if (s < 3600) return Math.floor(s/60) + " dk önce";
  if (s < 86400) return Math.floor(s/3600) + " sa önce";
  return new Date(iso).toLocaleDateString("tr-TR", {day:"numeric", month:"long"});
}
const urlOf = item => item.url || `/haber/${encodeURIComponent(item.id)}/`;
const img = item => safeUrl(item.image) ? `<img src="${esc(item.image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.remove()">` : "";
const wrapLink = (item, inner) => item.id ? `<a href="${esc(urlOf(item))}">${inner}</a>` : inner;
const preview = t => String(t || "").replace(/!\[[^\]]*\]\([^)]*\)|<img[^>]*>/gi, " ").replace(/\s+/g, " ").trim();
function chip(item){
  if (item.manual) return `<span class="chip" style="--c:var(--editor)">Editör</span>`;
  const keys = Object.keys(cfg.categories || {});
  const label = (cfg.categories || {})[item.category] || item.category;
  return `<span class="chip" style="--c:${PALETTE[Math.max(0, keys.indexOf(item.category)) % PALETTE.length]}">${esc(label)}</span>`;
}
const foot = item => `<div class="foot"><span>${esc(item.source)}</span><span>${ago(item.date)}</span></div>`;
const card = item => `<article class="card">${wrapLink(item, img(item))}
    <div class="body">${chip(item)}<h3>${wrapLink(item, esc(item.title))}</h3>
      ${item.summary ? `<p>${esc(preview(item.summary))}</p>` : ""}${foot(item)}${adminRow(item)}</div></article>`;

function renderList(){
  let list = all.filter(i => CAT === "hepsi" ? true : CAT === "editor" ? i.manual : i.category === CAT);
  if (query) list = list.filter(i => (i.title + " " + i.summary).toLocaleLowerCase("tr").includes(query));
  const lead = !query && (list.find(i => i.pinned) || list.find(i => i.image));
  const pin = lead && lead.pinned;
  $("#hero").innerHTML = lead ? `<div class="hero${pin ? " hero-pin" : ""}">${wrapLink(lead, img(lead))}
      <div>${pin ? '<span class="badge"><i></i>Manşet</span> ' : ""}${chip(lead)}<h2>${wrapLink(lead, esc(lead.title))}</h2>
      <p>${esc(preview(lead.summary).slice(0, pin ? 300 : 260))}${preview(lead.summary).length > (pin ? 300 : 260) ? "…" : ""}</p>
      ${pin ? `<a class="more-btn" href="${esc(urlOf(lead))}">Haberin tamamını oku →</a>` : ""}${foot(lead)}${adminRow(lead)}</div></div>` : "";
  const rest = list.filter(i => i !== lead);
  $("#grid").innerHTML = rest.slice(0, shown).map(card).join("") || (lead ? "" : `<div class="empty">Bu bölümde henüz haber yok.</div>`);
  $("#more").hidden = rest.length <= shown;
}

function renderArticle(){
  const item = all.find(i => String(i.id) === ID);
  if (item) $("#adm-slot").innerHTML = adminRow(item);
  const cat = item ? item.category : document.body.dataset.itemcat;
  const related = all.filter(i => String(i.id) !== ID && i.category === cat).slice(0, 6);
  $("#related").innerHTML = related.length ? `<h2>Benzer haberler</h2><div class="grid">${related.map(card).join("")}</div>` : "";
}

async function load(){
  const get = f => fetch(f + "?t=" + Date.now()).then(r => r.ok ? r.json() : null).catch(() => null);
  const [news, manual, settings, fd] = await Promise.all(
    ["/data/news.json", "/data/manual.json", "/data/settings.json", "/data/feeds.json"].map(get));
  cfg = settings || {categories: {}};
  feeds = fd || {};
  all = [...(manual || []), ...(news?.items || [])]
    .sort((a, b) => (b.pinned|0) - (a.pinned|0) || new Date(b.date) - new Date(a.date));
  if (oldHash){
    const hit = all.find(i => String(i.id) === decodeURIComponent(oldHash[1]));
    if (hit) return location.replace(urlOf(hit));
  }
  const upd = $("#upd");
  if (upd && news?.updated) upd.textContent = "Son güncelleme: " + ago(news.updated);
  adminLinks();
  if (PAGE === "list") renderList(); else if (PAGE === "article") renderArticle();
}

if (PAGE === "list"){
  $("#q").oninput = e => { query = e.target.value.trim().toLocaleLowerCase("tr"); shown = 24; renderList(); };
  $("#more").onclick = () => { shown += 24; renderList(); };
}
// ---------------------------------------------------------------- paylaşım
document.querySelectorAll(".share").forEach(box => {
  const {url, title} = box.dataset;
  const native = box.querySelector(".sh-native");
  if (navigator.share && native){            // telefonda kendi paylaşım menüsü
    native.hidden = false;
    native.onclick = () => navigator.share({title, url}).catch(() => {});
  }
  const copy = box.querySelector(".sh-copy");
  copy.onclick = async () => {
    try { await navigator.clipboard.writeText(url); }
    catch {
      const t = document.createElement("textarea"); t.value = url; document.body.append(t);
      t.select(); document.execCommand("copy"); t.remove();
    }
    const old = copy.textContent; copy.textContent = "✅ Kopyalandı";
    setTimeout(() => copy.textContent = old, 1800);
  };
});

// ---------------------------------------------------------------- iletişim formu
const cf = document.getElementById("contact");
if (cf){
  const st = cf.querySelector(".status"), btn = cf.querySelector(".send");
  if (new URLSearchParams(location.search).has("gonderildi")){ st.className = "status ok"; st.textContent = "✅ Mesajınız alındı, teşekkürler!"; }
  cf.addEventListener("submit", async ev => {
    ev.preventDefault();
    if (cf.querySelector(".hp").value) return;                 // spam botu
    btn.disabled = true; st.className = "status"; st.textContent = "Gönderiliyor…";
    try {
      const r = await fetch(cf.dataset.ajax, {method: "POST", headers: {"Accept": "application/json"}, body: new FormData(cf)});
      const j = await r.json().catch(() => ({}));
      if (!r.ok || String(j.success) === "false") throw new Error(j.message || r.status);
      cf.reset(); st.className = "status ok"; st.textContent = "✅ Mesajınız alındı, teşekkürler! En kısa sürede dönüş yapacağız.";
    } catch (err) {
      st.className = "status err";
      st.textContent = "Mesaj gönderilemedi, lütfen biraz sonra tekrar deneyin.";
      console.warn("İletişim formu:", err);
    } finally { btn.disabled = false; }
  });
}

load();
setInterval(load, 5 * 60 * 1000);
