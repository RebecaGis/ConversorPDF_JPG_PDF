import streamlit as st
import fitz  # PyMuPDF: Extremamente rápido e eficiente com memória
import io
import zipfile
import re

# Configuração da Página
st.set_page_config(page_title="Conversor em Lote", page_icon="🔄", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# Função de ordenação natural
def natural_sort_key(file_obj):
    name = file_obj.name.split('.')[0]
    numbers = re.findall(r'\d+', name)
    if numbers:
        return (0, int(numbers[0]), name)
    return (1, 0, name)

st.title("🔄 Super Conversor em Lote 🔄")
st.markdown("Otimizado para converter **centenas de arquivos** sem travar seu computador.")

tab1, tab2 = st.tabs(["🖼️ Imagens para PDF", "📄 PDF para Imagens"])

# ==========================================================
# ABA 1: JPG/PNG para PDF (Lote)
# ==========================================================
with tab1:
    st.subheader("Converter centenas de JPGs/PNGs para PDF")
    
    uploaded_images = st.file_uploader(
        "Selecione suas imagens", 
        type=['jpg', 'jpeg', 'png'], 
        accept_multiple_files=True
    )

    if uploaded_images:
        uploaded_images = sorted(uploaded_images, key=natural_sort_key)
        
        # Calcula o tamanho total para informar o usuário
        total_size_mb = sum([f.size for f in uploaded_images]) / (1024 * 1024)
        st.info(f"📦 **{len(uploaded_images)} arquivos** selecionados. Tamanho total: **{total_size_mb:.1f} MB**")

        combine_pdf = st.checkbox("Combinar todas as imagens em um ÚNICO PDF?", value=True)
        
        if st.button("🚀 Iniciar Conversão para PDF", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                if combine_pdf:
                    # Cria um PDF vazio
                    merged_pdf = fitz.open()
                    
                    for i, img_file in enumerate(uploaded_images):
                        status_text.text(f"Processando imagem {i+1} de {len(uploaded_images)}: {img_file.name}")
                        
                        img_bytes = img_file.read()
                        ext = img_file.name.split('.')[-1].lower()
                        if ext == 'jpeg': ext = 'jpg'
                        
                        # Converte imagem direta para PDF via PyMuPDF (CORRIGIDO: usando filetype=ext)
                        doc_img = fitz.open(stream=img_bytes, filetype=ext)
                        pdf_bytes = doc_img.convert_to_pdf()
                        doc_img.close()  # Libera memória da imagem
                        
                        img_pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
                        merged_pdf.insert_pdf(img_pdf)
                        img_pdf.close()  # Libera memória da página em PDF
                        
                        progress_bar.progress((i + 1) / len(uploaded_images))
                    
                    status_text.text("Gerando arquivo final para download...")
                    final_pdf_bytes = merged_pdf.write()
                    merged_pdf.close()
                    
                    st.success("✅ PDF Combinado gerado com sucesso!")
                    st.download_button("📥 Baixar PDF Combinado", data=final_pdf_bytes, file_name="imagens_combinadas.pdf", mime="application/pdf")
                
                else:
                    # Escreve direto no ZIP na memória
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for i, img_file in enumerate(uploaded_images):
                            status_text.text(f"Convertendo {i+1} de {len(uploaded_images)}: {img_file.name}")
                            
                            img_bytes = img_file.read()
                            ext = img_file.name.split('.')[-1].lower()
                            if ext == 'jpeg': ext = 'jpg'
                            
                            # CORRIGIDO: usando filetype=ext
                            doc_img = fitz.open(stream=img_bytes, filetype=ext)
                            pdf_bytes = doc_img.convert_to_pdf()
                            doc_img.close()
                            
                            base_name = img_file.name.rsplit('.', 1)[0]
                            zip_file.writestr(f"{base_name}.pdf", pdf_bytes)
                            
                            progress_bar.progress((i + 1) / len(uploaded_images))
                            
                    st.success("✅ PDFs gerados com sucesso!")
                    st.download_button("📥 Baixar todos os PDFs (ZIP)", data=zip_buffer.getvalue(), file_name="pdfs_individuais.zip", mime="application/zip")
                    
            except Exception as e:
                st.error(f"Erro durante a conversão: {e}")

# ==========================================================
# ABA 2: PDF para Imagens (Lote)
# ==========================================================
with tab2:
    st.subheader("Extrair JPGs de vários PDFs")
    
    uploaded_pdfs = st.file_uploader(
        "Selecione seus arquivos PDF", 
        type=['pdf'], 
        accept_multiple_files=True
    )

    if uploaded_pdfs:
        st.info(f"📄 **{len(uploaded_pdfs)} PDF(s)** selecionado(s).")
        dpi_quality = st.slider("Qualidade (DPI)", 72, 300, 150, help="150 é um bom balanço entre tamanho e qualidade.")
        
        if st.button("🚀 Iniciar Extração de Imagens", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                zip_buffer = io.BytesIO()
                total_pages = 0
                
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    
                    for idx, pdf_file in enumerate(uploaded_pdfs):
                        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                        base_name = pdf_file.name.rsplit('.', 1)[0]
                        num_pages = len(doc)
                        
                        for page_num in range(num_pages):
                            status_text.text(f"Lendo PDF {idx+1}/{len(uploaded_pdfs)} | Página {page_num+1}/{num_pages}...")
                            
                            page = doc.load_page(page_num)
                            pix = page.get_pixmap(dpi=dpi_quality)
                            
                            img_name = f"{base_name}_pag{page_num + 1}.jpg"
                            zip_file.writestr(img_name, pix.tobytes("jpeg"))
                            total_pages += 1
                            
                        doc.close()
                        progress_bar.progress((idx + 1) / len(uploaded_pdfs))

                if total_pages > 0:
                    status_text.text("✅ Processamento finalizado! Preparando download...")
                    st.success(f"Sucesso! {total_pages} páginas extraídas no total.")
                    st.download_button(
                        label="📥 Baixar Todas as Imagens (ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="imagens_extraidas.zip",
                        mime="application/zip"
                    )
            except Exception as e:
                st.error(f"Erro durante a extração: {e}")
