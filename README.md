# YouTube Transcript Viewer & Formatter (Streamlit App)

This Streamlit application allows users to fetch transcripts (automatic captions) for YouTube videos, view them with timestamps or formatted into readable paragraphs, generate a word cloud, and download the transcript text.

## Features

* **URL Input:** Accepts a standard YouTube video URL.
* **Transcript Fetching:** Uses `yt-dlp` to download the automatic captions (currently defaults to English).
* **Dual Transcript View:** Displays the transcript in two side-by-side formats:
    * **With Timestamps:** Shows the original VTT timestamps alongside the text segments.
    * **Formatted Paragraphs:** Cleans the text, uses NLTK to attempt sentence tokenization, and groups sentences (or raw text lines as a fallback) into paragraphs for better readability.
* **Word Cloud Generation:** Creates a word cloud visualization from the formatted transcript text, excluding common English stop words (using NLTK).
* **Download Options:** Provides buttons to download both the timestamped and the formatted paragraph versions of the transcript as `.txt` files.
* **Automatic NLTK Data Download:** Attempts to automatically download required NLTK data packages (`punkt`, `punkt_tab`, `stopwords`) on first run if missing.

## Requirements

* Python 3.x
* The following Python libraries:
    * `streamlit`
    * `yt-dlp`
    * `nltk`
    * `wordcloud`
    * `matplotlib`
* NLTK data packages: `punkt`, `punkt_tab`, `stopwords`

## Installation

1.  **Clone the repository (if applicable):**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install streamlit yt-dlp nltk wordcloud matplotlib
    ```
3.  **NLTK Data:** The application will attempt to download the necessary NLTK data packages automatically when you first run it. If this fails (due to network issues, permissions, etc.), you may need to download them manually by running the following command in your terminal:
    ```bash
    python -m nltk.downloader punkt punkt_tab stopwords
    ```

## Usage

1.  Navigate to the directory containing the application script (e.g., `app.py`).
2.  Run the Streamlit application from your terminal:
    ```bash
    streamlit run app.py
    ```
    (Replace `app.py` with the actual name of your Python script).
3.  Streamlit will open the application in your default web browser.
4.  Paste a YouTube video URL into the input box.
5.  Click the "Get Transcript" button.
6.  View the timestamped transcript, formatted transcript, and word cloud.
7.  Use the download buttons to save the desired transcript format.

## How it Works

1.  The app takes a YouTube URL and extracts the video ID.
2.  `yt-dlp` is used to download the automatic captions for the specified language (default 'en') into a temporary VTT file.
3.  The VTT file content is parsed twice:
    * Once to create a version with timestamps preserved.
    * A second time to extract raw text segments.
4.  The raw text segments are joined, and NLTK's `sent_tokenize` is used to attempt splitting the text into sentences.
5.  Based on whether sentence tokenization was effective, the text is formatted into paragraphs either by grouping detected sentences or by grouping the original VTT text segments (fallback).
6.  NLTK's English stop words list is used to filter common words from the formatted text.
7.  The `wordcloud` library generates a word cloud image from the filtered, formatted text.
8.  Streamlit displays the input elements, the word cloud (using `matplotlib`), the two transcript views, and the download buttons.
9.  The temporary VTT file is deleted after processing.

