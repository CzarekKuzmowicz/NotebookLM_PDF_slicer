import streamlit as st
from pypdf import PdfReader, PdfWriter
import math
import io
import os
import gdown
import requests
import tempfile
import zipfile  # Nowa biblioteka do obsługi ZIP (wbudowana)

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="PDF Splitter for NotebookLM", page_icon="✂️")

st.title("✂️ PDF Splitter for NotebookLM")
st.markdown("Optimize large PDF files to fit the NotebookLM limit (500k characters).")

# --- CHARACTER LIMIT ---
LIMIT = 480000

# --- ZMODYFIKOWANA FUNKCJA PROCESS_PDF ---
def process_pdf(pdf_file, file_name_base):
    try:
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
        total_chars = 0
        
        # 1. FAZA ANALIZY (Liczenie znaków)
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                total_chars += len(text)
            
            if (i + 1) % 10 == 0 or (i + 1) == total_pages:
                prog = (i + 1) / total_pages
                progress_bar.progress(prog)
                status_text.text(f"Analyzing content... {int(prog*100)}%")

        status_text.empty()
        progress_bar.empty()
        
        st.info(f"📊 **Result:** {total_chars} characters | {total_pages} pages")

        if total_chars == 0:
            st.error("No text detected. This might be a scanned image (OCR required).")
            return
        
        if total_chars <= LIMIT:
            st.success("✅ File fits within the limit! No need to split.")
            return

        # Obliczenia podziału
        num_chunks = math.ceil(total_chars / LIMIT)
        pages_per_chunk = math.ceil(total_pages / num_chunks)
        
        st.warning(f"⚠️ File is too large. Splitting into **{num_chunks}** parts (approx. {pages_per_chunk} pages each).")
        
        st.markdown("---")
        st.subheader("📥 Download files:")
        
        # 2. FAZA GENEROWANIA (Tu program "myślał" w ciszy, teraz dodajemy wskaźnik)
        processing_message = st.empty()
        processing_bar = st.progress(0)
        
        zip_buffer = io.BytesIO()
        generated_parts = [] # Lista do przechowywania gotowych części

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for i in range(num_chunks):
                # Aktualizacja statusu dla użytkownika
                processing_message.info(f"⏳ Generating Part {i+1} of {num_chunks}... Please wait.")
                
                writer = PdfWriter()
                start_page = i * pages_per_chunk
                end_page = min(start_page + pages_per_chunk, total_pages)
                
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                # Zapis do pamięci
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                pdf_bytes = output_buffer.getvalue()
                
                part_name = f"{file_name_base} part {i+1}.pdf"
                
                # Dodaj do ZIP
                zip_file.writestr(part_name, pdf_bytes)
                
                # Dodaj do listy przycisków
                generated_parts.append((part_name, output_buffer, start_page, end_page))
                
                # Aktualizacja paska postępu
                processing_bar.progress((i + 1) / num_chunks)

        # Sprzątanie po paskach postępu
        processing_message.empty()
        processing_bar.empty()
        st.success("✅ Processing complete! Buttons are ready below.")

        # --- PRZYCISK ZIP ---
        zip_buffer.seek(0)
        st.download_button(
            label="📦 Download All (ZIP)",
            data=zip_buffer,
            file_name=f"{file_name_base}_split.zip",
            mime="application/zip",
            type="primary"
        )
        
        st.write("Or download individually:")
        
        # --- PRZYCISKI POJEDYNCZE ---
        for part_name, buffer, start, end in generated_parts:
            buffer.seek(0)
            col1, col2 = st.columns([3, 1]) # Ładniejszy układ
            with col1:
                st.write(f"📄 **{part_name}**")
                st.caption(f"Pages {start+1}-{end}")
            with col2:
                st.download_button(
                    label="⬇️ Download",
                    data=buffer,
                    file_name=part_name,
                    mime="application/pdf",
                    key=part_name # Unikalny klucz wymagany przez Streamlit w pętli
                )
            st.divider()

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
