import streamlit as st
from pypdf import PdfReader, PdfWriter
import math
import io

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="PDF Splitter dla NotebookLM", page_icon="✂️")

st.title("✂️ PDF Splitter dla NotebookLM")
st.write("Wgraj duży plik PDF, a ja podzielę go na części idealne dla NotebookLM (poniżej 500k znaków).")

# --- LIMIT ZNAKÓW ---
LIMIT = 475000

# --- WGRYWANIE PLIKU ---
uploaded_file = st.file_uploader("Wybierz plik PDF", type="pdf")

if uploaded_file is not None:
    st.info("Plik wgrany! Trwa analiza...")
    
    try:
        # Wczytanie pliku z pamięci
        reader = PdfReader(uploaded_file)
        total_pages = len(reader.pages)
        total_chars = 0
        
        # Pasek postępu
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Liczenie znaków
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                total_chars += len(text)
            
            # Aktualizacja paska co 10 stron
            if (i + 1) % 10 == 0 or (i + 1) == total_pages:
                prog = (i + 1) / total_pages
                progress_bar.progress(prog)
                status_text.text(f"Analiza strony {i + 1} z {total_pages}...")

        status_text.empty()
        progress_bar.empty()
        
        st.write(f"📊 **Statystyki:**")
        st.write(f"- Całkowita liczba znaków: `{total_chars}`")
        st.write(f"- Liczba stron: `{total_pages}`")

        # Logika podziału
        if total_chars == 0:
            st.error("Nie wykryto tekstu. To może być skan (zdjęcie). Ten program działa tylko na plikach tekstowych.")
        elif total_chars <= LIMIT:
            st.success("✅ Ten plik jest wystarczająco mały! Nie trzeba go dzielić.")
        else:
            num_chunks = math.ceil(total_chars / LIMIT)
            pages_per_chunk = math.ceil(total_pages / num_chunks)
            
            st.warning(f"⚠️ Plik jest za duży. Dzielę go na **{num_chunks}** części (po ok. {pages_per_chunk} stron).")
            
            st.write("---")
            st.subheader("📥 Pobierz swoje pliki:")

            # Dzielenie i tworzenie przycisków
            base_name = uploaded_file.name.replace(".pdf", "")
            
            for i in range(num_chunks):
                writer = PdfWriter()
                start_page = i * pages_per_chunk
                end_page = min(start_page + pages_per_chunk, total_pages)
                
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                
                # Zapis do pamięci RAM (wirtualny plik)
                output_buffer = io.BytesIO()
                writer.write(output_buffer)
                output_buffer.seek(0) # Przewiń na początek pliku
                
                part_name = f"{base_name}_part_{i+1}.pdf"
                
                # Przycisk pobierania
                st.download_button(
                    label=f"⬇️ Pobierz Część {i+1} (Strony {start_page+1}-{end_page})",
                    data=output_buffer,
                    file_name=part_name,
                    mime="application/pdf"
                )
                
    except Exception as e:
        st.error(f"Wystąpił błąd: {e}")