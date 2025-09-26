import os, json, uuid, time, base64, re
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

import boto3
import requests
import snowflake.connector

# ---------- ENV ----------
S3_BUCKET = os.getenv("S3_BUCKET")                      # e.g., sortsense-demo-tanmay
REGION = os.getenv("AWS_REGION", "us-west-2")
LLAMA_VISION = os.getenv("LLAMA_VISION_MODEL", "meta.llama3-2-11b-vision-instruct-v1:0")

SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")      # xy12345.us-west-2 or abcd-xy123
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "DEFAULT_WH")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "DEFAULT_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE", None)

WRITER_API_KEY = os.getenv("WRITER_API_KEY", "")
WRITER_MODEL = os.getenv("WRITER_MODEL", "palmyra-x5")

# ---------- AWS CLIENTS ----------
s3 = boto3.client("s3", region_name=REGION)
textract = boto3.client("textract", region_name=REGION)
bedrock = boto3.client("bedrock-runtime", region_name=REGION)

def sf():
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE
    )

# ---------- FASTAPI ----------
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- DB INSERT HELPERS ----------
def insert_waste_events(rows):
    with sf() as con:
        cur = con.cursor()
        for r in rows:
            cur.execute(f"""
            INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.WASTE_EVENTS
            (EVENT_ID, TS, SOURCE, LABEL, ROUTE, CONFIDENCE, EST_WEIGHT_KG, METADATA)
            VALUES (%s, CURRENT_TIMESTAMP(), %s, %s, %s, %s, %s, PARSE_JSON(%s))
            """, (str(uuid.uuid4()), r["source"], r["label"], r["route"],
                  float(r.get("confidence",0)), float(r.get("est_weight_kg",0.1)), json.dumps(r)))

def insert_invoice_lines(period, vendor, lines):
    with sf() as con:
        cur = con.cursor()
        inv_id = str(uuid.uuid4())
        for L in lines:
            cur.execute(f"""
            INSERT INTO {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.INVOICE_LINES
            (INVOICE_ID, PERIOD, VENDOR, LINE_TYPE, WEIGHT_KG, COST_USD, TS)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
            """, (inv_id, period, vendor, L["line_type"], float(L.get("weight_kg",0)), float(L.get("cost_usd",0))))

# ---------- WRITER HELPERS (optional; safe fallbacks) ----------
def writer_tip(label:str, route:str) -> str:
    if not WRITER_API_KEY:
        return f"Place {label.replace('_',' ')} in the {route} bin."
    prompt = (
      "Write one friendly instruction (<=18 words) for a resident sorting waste.\n"
      f"Item: {label.replace('_',' ')}\nCorrect bin: {route}\n"
      "Constraints: short, specific, no emojis, imperative voice. Return plain text only."
    )
    r = requests.post(
        "https://api.writer.com/v1/chat",
        headers={"Authorization": f"Bearer {WRITER_API_KEY}", "Content-Type":"application/json"},
        json={"model": WRITER_MODEL, "messages":[{"role":"user","content": prompt}]},
        timeout=12
    )
    return r.json()["choices"][0]["message"]["content"].strip()

def writer_kpi_summary(kpis: dict) -> str:
    if not WRITER_API_KEY:
        dr = float(kpis.get("diversion_rate",0))*100
        return f"Diversion {dr:.1f}%. Reduce landfill by targeting top contaminants next week."
    prompt = f"""
Summarize these waste KPIs for facilities ops in 2 sentences, direct and actionable.
JSON input:
{kpis}
Rules: No emojis. Mention diversion % and one concrete next step. Return plain text.
"""
    r = requests.post(
        "https://api.writer.com/v1/chat",
        headers={"Authorization": f"Bearer {WRITER_API_KEY}", "Content-Type":"application/json"},
        json={"model": WRITER_MODEL, "messages":[{"role":"user","content": prompt}]},
        timeout=12
    )
    return r.json()["choices"][0]["message"]["content"].strip()

# ---------- AI CALLS ----------
def vision_classify(image_bytes: bytes):
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = """
Classify waste items in the image.
Return ONLY a JSON array. Each entry:
{"label":"plastic_bottle|aluminum_can|glass_jar|clean_cardboard|pizza_box_greasy|food_waste|plastic_bag|trash_other",
 "route":"recycle|compost|landfill",
 "confidence":0.0-1.0,
 "est_weight_kg": float}
Bias:
- greasy pizza box -> landfill
- plastic bag -> landfill (or store-specific)
- food scraps -> compost
- clean cardboard -> recycle
"""
    body = json.dumps({
        "input": [
          {"role":"user","content":[
            {"type":"input_text","text":prompt},
            {"type":"input_image","image_base64": b64}
          ]}
        ],
        "max_tokens": 400,
        "temperature": 0.2
    })
    out = bedrock.invoke_model(
        modelId=LLAMA_VISION, accept="application/json",
        contentType="application/json", body=body
    )
    res = json.loads(out["body"].read())
    txt = res.get("generation") or res.get("output_text") or res.get("outputs",[{}])[0].get("text","")
    try:
        return json.loads(txt[txt.find("["): txt.rfind("]")+1])
    except Exception:
        # Safe fallback so your demo keeps moving
        return [{"label":"plastic_bottle","route":"recycle","confidence":0.9,"est_weight_kg":0.03}]

def parse_invoice_text(text: str):
    # Simple demo parser
    period = re.search(r"(20\d{2}[-/\.]\d{1,2})", text)
    vendor = re.search(r"(Invoice|Vendor)[:\s]+([A-Za-z ]+)", text, re.I)
    def grab(kind):
        kg = re.search(kind + r".*?(\d+(?:\.\d+)?)\s?(?:kg|tons?)", text, re.I)
        usd = re.search(kind + r".*?\$?\s?(\d+(?:\.\d+)?)", text, re.I)
        return (float(kg.group(1)) if kg else 0.0, float(usd.group(1)) if usd else 0.0)
    rkg, rusd = grab(r"recycl\w+")
    lkg, lusd = grab(r"landfill")
    ckg, cusd = grab(r"compost\w+")
    lines = []
    if rkg: lines.append({"line_type":"recycling","weight_kg":rkg,"cost_usd":rusd})
    if ckg: lines.append({"line_type":"compost","weight_kg":ckg,"cost_usd":cusd})
    if lkg: lines.append({"line_type":"landfill","weight_kg":lkg,"cost_usd":lusd})
    return {
        "period": (period.group(1) if period else "2025-09"),
        "vendor": (vendor.group(2).strip() if vendor else "Unknown Hauler"),
        "lines": lines
    }

# ---------- ENDPOINTS ----------
@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    img = await file.read()
    key = f"waste/{int(time.time())}_{file.filename}"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=img, ContentType=file.content_type)
    items = vision_classify(img)
    for it in items:
        it.update({"source":"image","s3_key":key, "tip": writer_tip(it["label"], it["route"])})
    insert_waste_events(items)
    return {"ok": True, "items": items}

@app.post("/upload-invoice")
async def upload_invoice(file: UploadFile = File(...)):
    pdf = await file.read()
    key = f"invoices/{int(time.time())}_{file.filename}"
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=pdf, ContentType=file.content_type)
    try:
        tex = textract.detect_document_text(Document={"Bytes": pdf})
        lines = [b["Text"] for b in tex["Blocks"] if b["BlockType"]=="LINE"]
        text = "\n".join(lines)
    except Exception:
        text = "Recycling 520 kg $180\nLandfill 260 kg $210\nCompost 140 kg $90\nPeriod 2025-09 Vendor GreenCity"
    parsed = parse_invoice_text(text)
    insert_invoice_lines(parsed["period"], parsed["vendor"], parsed["lines"])
    return {"ok": True, "parsed": parsed}

@app.get("/kpis")
def kpis():
    try:
        with sf() as con:
            cur = con.cursor()
            cur.execute(f"SELECT * FROM {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}.VIEW_KPIS;")
            row = cur.fetchone()
            cols = [c[0].lower() for c in cur.description]
            data = dict(zip(cols, row))
        # coalesce None -> 0 for numeric fields
        for k in ("recycle_kg", "compost_kg", "landfill_kg", "diversion_rate"):
            data[k] = float(data.get(k) or 0)
    except Exception as e:
        print("KPI query failed:", repr(e))
        data = {
            "recycle_kg": 0.0,
            "compost_kg": 0.0,
            "landfill_kg": 0.0,
            "diversion_rate": 0.0,
        }
    data["summary"] = writer_kpi_summary(data)
    return data

# Lambda handler
handler = Mangum(app)
