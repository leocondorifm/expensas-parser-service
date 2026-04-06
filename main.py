from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import JSONResponse
import os
import subprocess
import tempfile

app = FastAPI()

API_TOKEN = os.getenv("API_TOKEN", "")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/parse-expensas")
async def parse_expensas(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
):
    # Auth simple por Bearer
    if not API_TOKEN:
        raise HTTPException(status_code=500, detail="API_TOKEN no configurado")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization requerida")
    token = authorization.replace("Bearer ", "", 1).strip()
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Token inválido")

    # Guardar PDF temporal
    suffix = ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_pdf:
        content = await file.read()
        tmp_pdf.write(content)
        pdf_path = tmp_pdf.name

    txt_path = pdf_path + ".txt"

    try:
        # Poppler pdftotext
        cmd = ["pdftotext", "-layout", pdf_path, txt_path]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            # fallback sin -layout
            cmd = ["pdftotext", pdf_path, txt_path]
            p2 = subprocess.run(cmd, capture_output=True, text=True)
            if p2.returncode != 0:
                return JSONResponse(
                    status_code=400,
                    content={"ok": False, "error": f"pdftotext falló: {p.stderr or p2.stderr}"},
                )

        if not os.path.exists(txt_path):
            return JSONResponse(status_code=400, content={"ok": False, "error": "No se generó txt"})

        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()

        # Acá devolvemos texto crudo primero (MVP).
        # Después podemos portar tu parser PHP regex a Python si querés.
        return {"ok": True, "data": {"raw_text": text[:200000]}}

    finally:
        for pth in [pdf_path, txt_path]:
            try:
                if os.path.exists(pth):
                    os.unlink(pth)
            except Exception:
                pass
