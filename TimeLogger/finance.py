import PyPDF2
import sys
import os
from pathlib import Path

# Directory for extracted PDF content (relative to this script)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")



class PDFReader:
    """A PDF reader class that extracts content page by page."""
    
    def __init__(self, pdf_path):
        """
        Initialize the PDF reader with a PDF file path.
        
        Args:
            pdf_path (str): Path to the PDF file
        """
        self.pdf_path = pdf_path
        self.pdf_file = None
        self.pdf_reader = None
        
    def open_pdf(self):
        """Open and initialize the PDF file for reading."""
        try:
            if not os.path.exists(self.pdf_path):
                raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")
            
            self.pdf_file = open(self.pdf_path, 'rb')
            self.pdf_reader = PyPDF2.PdfReader(self.pdf_file)
            print(f"Successfully opened PDF: {self.pdf_path}")
            print(f"Total pages: {len(self.pdf_reader.pages)}")
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False
    
    def get_page_count(self):
        """Get the total number of pages in the PDF."""
        if self.pdf_reader:
            return len(self.pdf_reader.pages)
        return 0
    
    def extract_page_text(self, page_number):
        """
        Extract text content from a specific page.
        
        Args:
            page_number (int): Page number (1-indexed)
            
        Returns:
            str: Text content of the page
        """
        if not self.pdf_reader:
            return "PDF not opened. Call open_pdf() first."
        
        if page_number < 1 or page_number > len(self.pdf_reader.pages):
            returwwwwwwwwwwwwwwwwwwwwn f"Invalid page number. PDF has {len(self.pdf_reader.pages)} pages."
        
        try:
            page = self.pdf_reader.pages[page_number - 1]  # Convert to 0-indexed
            text = page.extract_text()
            return text
        except Exception as e:
            return f"Error extracting text from page {page_number}: {e}"
    
    def extract_all_pages(self):
        """
        Extract text content from all pages.
        
        Returns:
            list: List of text content for each page
        """
        if not self.pdf_reader:
            return ["PDF not opened. Call open_pdf() first."]
        
        all_pages_text = []
        for page_num in range(1, len(self.pdf_reader.pages) + 1):
            page_text = self.extract_page_text(page_num)
            all_pages_text.append(f"--- Page {page_num} ---\n{page_text}")
        
        return all_pages_text
    
    def save_text_to_file(self, output_path, page_number=None):
        """
        Save extracted text to a file.
        
        Args:
            output_path (str): Path to save the text file
            page_number (int, optional): Specific page to extract. If None, extracts all pages.
        """
        try:
            if page_number:
                text_content = self.extract_page_text(page_number)
                content = f"--- Page {page_number} ---\n{text_content}"
            else:
                all_pages = self.extract_all_pages()
                content = "\n\n".join(all_pages)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"Text saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error saving text to file: {e}")
            return False
    
    def close_pdf(self):
        """Close the PDF file."""
        if self.pdf_file:
            self.pdf_file.close()
            self.pdf_file = None
            self.pdf_reader = None
            print("PDF file closed.")
    
    def __enter__(self):
        """Context manager entry."""
        self.open_pdf()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_pdf()

import requests

class RAGSystem:
    def __init__(self, pdf_path, ollama_url="http://localhost:11434/api/generate", ollama_model="llama3"):
        self.pdf_path = pdf_path
        self.pdf_reader = PDFReader(pdf_path)
        self.pdf_reader.open_pdf()
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model

    def RagChunking(self):
        """
        Extracts and returns the text of all pages in the PDF as a list of strings,
        where each string contains the text of one page, prefixed with a page header.

        Returns:
            list of str: List of page texts, each with a header indicating the page number.
        """
        if not self.pdf_reader.pdf_reader:
            raise ValueError("PDF file is not open or loaded.")

        all_pages_text = []
        for page_num in range(1, len(self.pdf_reader.pdf_reader.pages) + 1):
            page_text = self.pdf_reader.extract_page_text(page_num)
            all_pages_text.append(f"--- Page {page_num} ---\n{page_text}")

        return all_pages_text

    def RagQuery(self, query):
        """
        Queries the RAG system with a given query and returns the answer using Ollama.
        The context is the concatenated text of all PDF pages.
        """
        # Gather all text as context
        context = "\n\n".join(self.RagChunking())
        prompt = (
            f"Given the following document content:\n{context}\n\n"
            f"Answer the following question concisely and accurately:\n{query}"
        )

        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            # Ollama returns {'response': '...'} or {'message': {'content': '...'}}
            if "response" in data:
                return data["response"].strip()
            elif "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            else:
                return "No response from Ollama."
        except Exception as e:
            return f"Error querying Ollama: {e}"
    def saveChunkToFile(self):
        """
        Asks the user what they want to save from the PDF, uses the LLM to find the relevant content,
        and saves it to a file (txt or csv) based on the content type, after confirming with the user.
        """
        # Ask the user what they want to save
        user_query = input("What do you want to save from the PDF? (e.g., 'summary table', 'all transactions', 'introduction', etc.): ").strip()
        if not user_query:
            print("No input provided. Aborting save.")
            return

        # Gather all PDF text as context
        context = "\n\n".join(self.RagChunking())

        # Use LLM to extract the relevant content
        extraction_prompt = (
            f"Given the following document content:\n{context}\n\n"
            f"Extract the content that best matches the following user request. "
            f"Return only the relevant content, no explanation or extra text.\n"
            f"User request: {user_query}"
        )
        try:
            relevant_content = self.RagQuery(extraction_prompt).strip()
        except Exception as e:
            print(f"Error extracting relevant content: {e}")
            return

        if not relevant_content:
            print("No relevant content found for the given request.")
            return

        # Show the user a preview and ask if they want to save
        preview = relevant_content[:500] + ("..." if len(relevant_content) > 500 else "")
        print("\nPreview of extracted content:\n")
        print(preview)
        print("\n")
        confirm = input("Do you want to save this content? (y/n): ").strip().lower()
        if confirm not in ("y", "yes"):
            print("Save cancelled by user.")
            return

        # Ask Ollama to classify the extracted content
        classification_prompt = (
            "You will be given a document chunk. "
            "If it is a table or tabular data, respond with 'csv'. "
            "If it is general text, respond with 'txt'. "
            "Respond with only 'csv' or 'txt'.\n\n"
            f"Chunk:\n{relevant_content[:2000]}"
        )
        try:
            result = self.RagQuery(classification_prompt).strip().lower()
        except Exception as e:
            print(f"Error classifying chunk: {e}")
            result = "txt"  # Default to txt on error

        if result == "csv":
            filename = os.path.join(DATA_DIR, "extracted_content.csv")
        else:
            filename = os.path.join(DATA_DIR, "extracted_content.txt")

        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(relevant_content)
            print(f"Relevant content saved to: {filename}")
            return filename
        except Exception as e:
            print(f"Failed to save content: {e}")
            return None
def main():
    """
    Main function to demonstrate PDF reading, RAG-based summarization, and chunk saving.
    Usage:
        python finance.py <pdf_file_path> [page_number]
    """
    import tkinter as tk
    from tkinter import filedialog
    from pathlib import Path

    # Hide the root window
    root = tk.Tk()
    root.withdraw()

    # Prompt user to select a PDF file
    pdf_path = filedialog.askopenfilename(
        title="Select PDF file",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
    )

    if not pdf_path:
        print("No PDF file selected. Exiting.")
        return

    # Optionally, ask for page number via input (since no CLI arg)
    page_number = None
    # Show total number of pages before asking for input
    with PDFReader(pdf_path) as temp_reader:
        total_pages = temp_reader.get_page_count() if temp_reader.pdf_reader else None
    if total_pages:
        print(f"Total number of pages in PDF: {total_pages}")
    else:
        print("Unable to determine total number of pages.")

    page_input = input("Enter page number to extract (leave blank for all pages): ").strip()
    if page_input:
        try:
            page_number = int(page_input)
        except ValueError:
            print("Invalid page number. Extracting all pages.")
            page_number = None

    # Use PDFReader and RAGSystem to extract and summarize PDF content
    with PDFReader(pdf_path) as reader:
        if not reader.pdf_reader:
            print("Failed to open PDF.")
            return None

        # Show basic info
        total_pages = reader.get_page_count()
        print(f"\nPDF loaded: {pdf_path}")
        print(f"Total pages: {total_pages}")

        if page_number:
            print(f"\n--- Extracting Page {page_number} ---")
            text = reader.extract_page_text(page_number)
            print(text)
        else:
            print(f"\n--- Extracting All Pages ---")
            all_pages = reader.extract_all_pages()
            for page_text in all_pages:
                print(page_text)
                print("\n" + "="*50 + "\n")

        # Ask user if they want to save the extracted text to a file
        save_choice = input("Would you like to save the extracted text to a file? (y/n): ").strip().lower()
        if save_choice == 'y':
            os.makedirs(DATA_DIR, exist_ok=True)
            output_file = os.path.join(DATA_DIR, f"extracted_text_{Path(pdf_path).stem}.txt")
            reader.save_text_to_file(output_file, page_number)
            print(f"Extracted text saved to: {output_file}")
        else:
            print("Extracted text was not saved.")

    # Use RAGSystem to generate a summary of the PDF
    try:
        rag = RAGSystem(pdf_path)
        summary_query = "Provide a concise summary of the main points or topics covered in this document."
        print("\n--- Generating PDF Summary using RAGSystem ---")
        summary = rag.RagQuery(summary_query)
        print(summary)

        # --- Ask user if they want to save a chunk of the PDF using RAGSystem.saveChunkToFile ---
        user_choice = input("\nWould you like to save a chunk of the PDF to a file? (y/n): ").strip().lower()
        if user_choice == 'y':
            saved_file = rag.saveChunkToFile()
            if saved_file:
                print(f"Chunk saved to: {saved_file}")
            else:
                print("No chunk was saved.")
        else:
            print("Chunk was not saved.")
        # --- End Added ---

    except Exception as e:
        print(f"Error generating summary: {e}")

if __name__ == "__main__":
    main()