"use client";
import { useState } from "react";

// Local backend API URL
const API = "http://localhost:8000";

type Item = {
  label: string;
  route: "recycle" | "compost" | "landfill";
  confidence?: number;
  est_weight_kg?: number;
  tip?: string;
};

type Kpis = {
  recycle_kg: number;
  compost_kg: number;
  landfill_kg: number;
  diversion_rate: number;
  summary?: string;
};

export default function Home() {
  const [items, setItems] = useState<Item[]>([]);
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  async function upload(path: string, file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API}${path}`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    return (await res.json()) as any;
  }
  async function refreshKpis() {
    const res = await fetch(`${API}/kpis`);
    if (!res.ok) throw new Error(await res.text());
    setKpis(await res.json());
  }
  
  async function resetKpis() {
    try {
      const res = await fetch(`${API}/reset-kpis`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      await refreshKpis();
    } catch (err: any) {
      alert("Reset failed: " + (err?.message || err));
    }
  }

  return (
    <main style={{maxWidth:920, margin:"40px auto", fontFamily:"Inter, system-ui, sans-serif" }}>
      <h1 style={{fontSize:32, marginBottom:6}}>SortSense ♻️ — AI Waste Sorter</h1>
      <p style={{color:"#555"}}>
        Upload a trash photo or an invoice PDF. Items are classified (Bedrock Vision or fallback),
        invoices parsed (Textract or fallback), and KPIs are computed in Snowflake.
      </p>

      <section style={{display:"grid", gap:16, marginTop:20}}>
        <label style={{display:"block"}}>
          <b>Upload trash photo</b><br/>
          <input
            type="file"
            accept="image/*"
            onChange={async e => {
              const f = e.target.files?.[0]; if (!f) return;
              try {
                setLoading(true); setMsg("Classifying image…");
                const out = await upload("/upload-image", f);
                setItems(out.items || []);
                setMsg("Refreshing KPIs…");
                await refreshKpis();
              } catch (err: any) {
                alert("Upload failed: " + (err?.message || err));
              } finally { setLoading(false); setMsg(""); }
            }}
          />
        </label>

        <label style={{display:"block"}}>
          <b>Upload waste invoice (PDF)</b><br/>
          <input
            type="file"
            accept="application/pdf"
            onChange={async e => {
              const f = e.target.files?.[0]; if (!f) return;
              try {
                setLoading(true); setMsg("Parsing invoice…");
                await upload("/upload-invoice", f);
                setMsg("Refreshing KPIs…");
                await refreshKpis();
              } catch (err: any) {
                alert("Upload failed: " + (err?.message || err));
              } finally { setLoading(false); setMsg(""); }
            }}
          />
        </label>

        {loading && (
          <div style={{padding:"8px 10px", background:"#fffbe6", border:"1px solid #ffe58f", borderRadius:8}}>
            ⏳ {msg}
          </div>
        )}

        <div style={{display:"grid", gridTemplateColumns:"1fr", gap:16}}>
          <div style={{border:"1px solid #eee", borderRadius:8, padding:12}}>
            <h3 style={{marginTop:0}}>Detected items</h3>
            {items.length === 0 ? (
              <div>No items yet.</div>
            ) : (
              <ul style={{margin:0, paddingLeft:18}}>
                {items.map((it, i) => (
                  <li key={i} style={{marginBottom:6}}>
                    {it.label} → <b>{it.route}</b>
                    {typeof it.confidence === "number" ? ` (${Math.round(it.confidence * 100)}%)` : ""}
                    {typeof it.est_weight_kg === "number" ? ` · ~${it.est_weight_kg} kg` : ""}
                    {it.tip ? <div style={{color:"#2a6", fontSize:14}}>{it.tip}</div> : null}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div style={{border:"1px solid #eee", borderRadius:8, padding:12}}>
            <div style={{display:"flex", alignItems:"center", gap:10}}>
              <h3 style={{margin:0}}>KPIs (from Snowflake)</h3>
              <button onClick={refreshKpis}>Refresh KPIs</button>
              <button onClick={resetKpis} style={{background:"#ff6b6b", color:"white", border:"none", padding:"6px 12px", borderRadius:"4px", cursor:"pointer"}}>Reset KPIs</button>
            </div>
            {!kpis ? (
              <div style={{marginTop:8}}>—</div>
            ) : (
              <>
                <div style={{display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:8, marginTop:10}}>
                  <div>Recycle: <b>{kpis.recycle_kg}</b> kg</div>
                  <div>Compost: <b>{kpis.compost_kg}</b> kg</div>
                  <div>Landfill: <b>{kpis.landfill_kg}</b> kg</div>
                  <div>Diversion: <b>{(kpis.diversion_rate * 100).toFixed(1)}%</b></div>
                </div>
                {kpis.summary && (
                  <div style={{marginTop:10, padding:12, background:"#fafafa", borderRadius:8}}>
                    <strong>Coach summary:</strong> {kpis.summary}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      <details style={{marginTop:18}}>
        <summary>Debug info</summary>
        <pre style={{whiteSpace:"pre-wrap"}}>API = {API}</pre>
      </details>
    </main>
  );
}
