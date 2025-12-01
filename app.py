import streamlit as st
from pypdf import PdfReader, PdfWriter
import math
import io
import os
import gdown
import requests
import tempfile
import zipfile

# PAGE CONFIGURATION
st.set_page_config(page_title="PDF Splitter for NotebookLM", page_icon="✂️")

st.title("✂️ PDF Splitter for NotebookLM")
st.markdown("Optimize large PDF files to fit the NotebookLM limit (500k characters).")

# CHARACTER LIMIT
LIMIT = 500000

# PROCESSING FUNCTION
def process_pdf(pdf_file, file_name_base):
    try:
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        total_chars = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Counting characters
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                total_chars += len(text)
            
            if (i + 1) % 10 == 0 or (i + 1) == total_pages:
                prog = (i + 1) / total_pages
                progress_bar.progress(prog)
                status_text.text(f"Analyzing page {i + 1} of {total_pages}...")

        status_text.empty()
        progress_bar.empty()
        
        st.info(f"📊 **Result:** {total_chars} characters | {total_pages} pages")

        if total_chars == 0:
            st.error("No text detected. This might be a scanned image (OCR required).")
            return
        
        if total_chars <= LIMIT:
            st.success("✅ File fits within the limit! No need to split.")
            return

        # Splitting logic
        num_chunks = math.ceil(total_chars / LIMIT)
        pages_per_chunk = math.ceil(total_pages / num_chunks)
        
        st.warning(f"⚠️ File is too large for NotebookLM. Splitting into **{num_chunks}** parts (approx. {pages_per_chunk} pages each).")
        st.subheader("📥 Download files:")

        # ZIP PREPARATION
        zip_buffer = io.BytesIO()
        
        # List to store data for individual buttons later
        generated_parts = []

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for i in range(num_chunks):
                writer = PdfWriter()
                start_page = i * pages_per_chunk
                end_page = min(start_page + pages_per_chunk, total_pages)
                
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                # Save PDF to memory
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                pdf_bytes = output_buffer.getvalue()
                
                # New naming convention: "Name part X.pdf"
                part_name = f"{file_name_base} part {i+1}.pdf"
                
                # Add to ZIP
                zip_file.writestr(part_name, pdf_bytes)
                
                # Store for individual buttons
                generated_parts.append((part_name, output_buffer, start_page, end_page))
        
        # DOWNLOAD ALL BUTTON (ZIP)
        zip_buffer.seek(0)
        st.download_button(
            label="📦 Download All (ZIP)",
            data=zip_buffer,
            file_name=f"{file_name_base}_split.zip",
            mime="application/zip",
            type="primary" 
        )
        
        st.markdown("---") # separator
        
        # INDIVIDUAL BUTTONS
        for part_name, buffer, start, end in generated_parts:
            buffer.seek(0)
            st.download_button(
                label=f"⬇️ {part_name} (Pages {start+1}-{end})",
                data=buffer,
                file_name=part_name,
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Error processing PDF: {e}")

# TABS INTERFACE
tab1, tab2 = st.tabs(["📂 Upload from Computer", "🔗 Link (URL / Google Drive)"])

# Option 1: Local Upload
with tab1:
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file is not None:
        # Clean filename just in case
        clean_name = uploaded_file.name.replace(".pdf", "")
        process_pdf(uploaded_file, clean_name)

# Option 2: Link
with tab2:
    url = st.text_input("Paste PDF URL or Google Drive link:")
    st.caption("ℹ️ Note: Google Drive links must be public ('Anyone with the link').")
    
    if st.button("Download and Analyze"):
        if not url:
            st.error("Please paste a link!")
        else:
            with st.spinner("Downloading file from the web... (this may take a moment)"):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        if "drive.google.com" in url:
                            gdown.download(url, tmp_file.name, quiet=False, fuzzy=True)
                        else:
                            response = requests.get(url, stream=True)
                            response.raise_for_status()
                            for chunk in response.iter_content(chunk_size=8192):
                                tmp_file.write(chunk)
                        
                        tmp_path = tmp_file.name
                    
                    # Extract filename from URL or use generic default
                    # Simple heuristic for name
                    default_name = "downloaded_document"
                    
                    with open(tmp_path, "rb") as f:
                        file_stream = io.BytesIO(f.read())
                        process_pdf(file_stream, default_name)
                    
                    os.remove(tmp_path)
                    
                except Exception as e:
                    st.error(f"Failed to download file. Ensure the link is public. Error: {str(e)}")
