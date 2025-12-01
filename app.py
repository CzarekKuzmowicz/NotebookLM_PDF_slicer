import streamlit as st
from pypdf import PdfReader, PdfWriter
import math, io, os, tempfile, zipfile, requests, gdown

# --- CONFIG ---
st.set_page_config(page_title="PDF Splitter", page_icon="✂️")
st.title("✂️ PDF Splitter (NotebookLM Optimized)")
LIMIT = 500000

# --- CORE LOGIC ---
def process_pdf(pdf_file, base_name):
    try:
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        total_chars = 0
        
        # 1. Analyze
        pbar = st.progress(0)
        status = st.empty()
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text: total_chars += len(text)
            
            if (i + 1) % 50 == 0 or (i + 1) == total_pages:
                prog = (i + 1) / total_pages
                pbar.progress(prog)
                status.caption(f"Analyzing... {int(prog*100)}%")
        
        pbar.empty()
        status.empty()
        
        st.caption(f"Stats: {total_chars:,} chars | {total_pages} pages")

        if total_chars == 0:
            st.error("No text found (OCR required).")
            return
        if total_chars <= LIMIT:
            st.success("File fits within limits.")
            return

        # 2. Split Strategy
        num_chunks = math.ceil(total_chars / LIMIT)
        pages_per_chunk = math.ceil(total_pages / num_chunks)
        
        st.warning(f"Splitting into {num_chunks} parts (~{pages_per_chunk} pages each).")
        st.divider()

        # 3. Generate Files
        zip_buffer = io.BytesIO()
        parts_data = []
        gen_bar = st.progress(0)
        
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for i in range(num_chunks):
                writer = PdfWriter()
                start = i * pages_per_chunk
                end = min(start + pages_per_chunk, total_pages)
                
                for p in range(start, end):
                    writer.add_page(reader.pages[p])
                
                buf = io.BytesIO()
                writer.write(buf)
                
                name = f"{base_name} part {i+1}.pdf"
                zf.writestr(name, buf.getvalue())
                parts_data.append((name, buf, start, end))
                
                gen_bar.progress((i + 1) / num_chunks)
        
        gen_bar.empty()
        
        # 4. Download Buttons
        zip_buffer.seek(0)
        st.download_button("📦 Download All (ZIP)", zip_buffer, f"{base_name}_split.zip", "application/zip", type="primary")
        
        st.write("") # Spacer
        
        for name, buf, s, e in parts_data:
            buf.seek(0)
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{name}** (p. {s+1}-{e})")
            c2.download_button("⬇️ Download", buf, name, "application/pdf", key=name)

    except Exception as e:
        st.error(f"Error: {e}")

# --- UI ---
t1, t2 = st.tabs(["Local Upload", "URL / Drive Link"])

with t1:
    f = st.file_uploader("Upload PDF", type="pdf")
    if f: process_pdf(f, f.name.replace(".pdf", ""))

with t2:
    url = st.text_input("Paste Link:")
    if st.button("Process Link") and url:
        with st.spinner("Downloading..."):
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    if "drive.google.com" in url:
                        gdown.download(url, tmp.name, quiet=True, fuzzy=True)
                    else:
                        r = requests.get(url, stream=True)
                        r.raise_for_status()
                        for chunk in r.iter_content(8192): tmp.write(chunk)
                    
                    path = tmp.name
                
                with open(path, "rb") as f:
                    process_pdf(io.BytesIO(f.read()), "downloaded_doc")
                os.remove(path)
            except Exception as e:
                st.error(f"Download failed: {e}")
