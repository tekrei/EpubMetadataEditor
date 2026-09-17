import gradio as gr
from services._book_service import BookService

# BookService örneğini başlatıyoruz
book_service = BookService()

def load_epub(file_obj):
    """Yüklenen EPUB dosyasından metadataları ve kapağı çeker."""
    if file_obj is None:
        return "", "", "", "", None
    
    file_path = file_obj.name
    
    # Mevcut servis yapınızdan kitap bilgilerini okuma
    book = book_service.load_book(file_path)
    
    title = book.get("title", "")
    author = book.get("author", "")
    publisher = book.get("publisher", "")
    language = book.get("language", "")
    cover_image = book.get("cover_path", None)
    
    return title, author, publisher, language, cover_image

def save_epub(file_obj, title, author, publisher, language, cover_image):
    """Formdaki yeni bilgileri EPUB dosyasına kaydeder."""
    if file_obj is None:
        return "Lütfen önce bir EPUB dosyası seçin."
    
    try:
        book_service.save_metadata(
            file_path=file_obj.name,
            title=title,
            author=author,
            publisher=publisher,
            language=language,
            cover_image=cover_image
        )
        return "Meta veriler başarıyla güncellendi!"
    except Exception as e:
        return f"Hata oluştu: {str(e)}"

def create_app():
    """Gradio arayüzünü oluşturur."""
    with gr.Blocks(title="EPUB Metadata Editor") as demo:
        gr.Markdown("# 📚 EPUB Metadata Editor")
        
        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(label="EPUB Dosyası Yükle", file_types=[".epub"])
                cover_input = gr.Image(label="Kapak Resmi", type="filepath")
                
            with gr.Column(scale=2):
                title_input = gr.Textbox(label="Kitap Adı (Title)")
                author_input = gr.Textbox(label="Yazar (Author)")
                publisher_input = gr.Textbox(label="Yayıncı (Publisher)")
                language_input = gr.Textbox(label="Dil (Language)")
                
                save_button = gr.Button("Kaydet / Güncelle", variant="primary")
                status_output = gr.Textbox(label="Durum", interactive=False)

        # Olay Bağlantıları (Event Bindings)
        file_input.change(
            fn=load_epub,
            inputs=[file_input],
            outputs=[title_input, author_input, publisher_input, language_input, cover_input]
        )
        
        save_button.click(
            fn=save_epub,
            inputs=[file_input, title_input, author_input, publisher_input, language_input, cover_input],
            outputs=[status_output]
        )
        
    return demo

if __name__ == "__main__":
    app = create_app()
    app.launch()
