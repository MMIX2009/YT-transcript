# Import necessary libraries
import streamlit as st
import yt_dlp
import os               # For file operations
import re               # For parsing
from urllib.parse import urlparse, parse_qs # For URL parsing
import nltk             # For sentence tokenization and stopwords
from wordcloud import WordCloud # For generating word cloud
import matplotlib.pyplot as plt # For displaying word cloud

# --- Page Config (MUST be the first Streamlit command) ---
st.set_page_config(page_title="YouTube Transcript Viewer", layout="wide")

# --- NLTK Setup ---
# Download necessary NLTK data packages if not already downloaded
NLTK_RESOURCES = ['punkt', 'punkt_tab', 'stopwords']
missing_resources = []
for resource in NLTK_RESOURCES:
    try:
        # Check if the resource can be found
        # For punkt/punkt_tab, check tokenizers; for stopwords, check corpora
        resource_path = f'tokenizers/{resource}' if 'punkt' in resource else f'corpora/{resource}'
        nltk.data.find(resource_path)
    except LookupError:
        missing_resources.append(resource)

if missing_resources:
    st.info(f"Downloading necessary NLTK data ({', '.join(missing_resources)})... Please wait.")
    download_success = True
    for resource in missing_resources:
        try:
            nltk.download(resource) # Removed quiet=True for visibility
        except Exception as e:
            st.error(f"Failed to download NLTK resource '{resource}'. Please ensure you have internet connectivity and try running 'python -m nltk.downloader {' '.join(missing_resources)}' manually in your terminal. Error: {e}")
            download_success = False
            break # Stop trying if one fails
    if download_success:
        st.success("NLTK data download attempt complete.")
    else:
        st.stop() # Stop execution if essential NLTK download fails

# Load stopwords after ensuring download
try:
    from nltk.corpus import stopwords
    STOP_WORDS = set(stopwords.words('english'))
    # Add custom words to ignore if needed (e.g., common interjections)
    # STOP_WORDS.update(['yeah', 'like', 'uh', 'um'])
except Exception as e:
    st.error(f"Failed to load NLTK stopwords even after download attempt. Error: {e}")
    STOP_WORDS = set() # Use an empty set if loading fails


# --- Helper Functions ---

def extract_video_id(url):
    """ Extracts the YouTube video ID from various URL formats. """
    if not isinstance(url, str): return None
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query).get('v', [None])[0]
            elif parsed_url.path.startswith(('/embed/', '/v/')):
                return parsed_url.path.split('/')[2]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
    except Exception: return None
    return None

def parse_vtt_with_timestamps(vtt_content):
    """ Parses VTT, keeping timestamps and text, formatted line by line. """
    lines = vtt_content.strip().splitlines()
    formatted_transcript = []
    current_timestamp = ""
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'): continue
        if '-->' in line:
            current_timestamp = f"[{line}]"
            if i + 1 < len(lines):
                 next_line = lines[i+1].strip()
                 if next_line and '-->' not in next_line:
                      formatted_transcript.append(current_timestamp)
                 else: current_timestamp = "" # Cue settings line likely, skip timestamp
            continue
        if line and current_timestamp:
            cleaned_line = re.sub(r'<[^>]+>', '', line)
            cleaned_line = re.sub(r'\{[^}]+\}', '', cleaned_line)
            formatted_transcript.append(cleaned_line)
            formatted_transcript.append("") # Add blank line for readability
            current_timestamp = "" # Reset timestamp
    return "\n".join(formatted_transcript).strip()

def format_transcript_into_paragraphs(vtt_content, sentences_per_paragraph=5, lines_per_fallback_paragraph=8):
    """
    Parses VTT to extract text, then formats into sentences and paragraphs using NLTK.
    Includes a fallback method if sentence tokenization doesn't work well.
    """
    lines = vtt_content.strip().splitlines()
    text_segments = []
    for line in lines:
        line = line.strip()
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or '-->' in line or not line: continue
        cleaned_line = re.sub(r'<[^>]+>', '', line)
        cleaned_line = re.sub(r'\{[^}]+\}', '', cleaned_line)
        if cleaned_line and not re.match(r'^[a-zA-Z]+:.+', cleaned_line):
             text_segments.append(cleaned_line.strip())

    if not text_segments: return "Could not extract text content for formatting."

    full_text = " ".join(text_segments)
    # full_text = re.sub(r'\b(.+?)\b(\s+\1\b)+', r'\1', full_text, flags=re.IGNORECASE) # Keep disabled for now

    sentences = []
    try:
        sentences = nltk.sent_tokenize(full_text)
    except Exception as e:
        print(f"NLTK sent_tokenize error: {e}")
        if "Resource punkt" in str(e) or "punkt_tab" in str(e): return f"Error: NLTK resource 'punkt'/'punkt_tab' not found. Try manual download."
        else: return f"Error during sentence tokenization: {e}"

    formatted_output = []
    MIN_SENTENCE_THRESHOLD = max(5, len(text_segments) // 10)
    if len(sentences) > MIN_SENTENCE_THRESHOLD:
        print(f"Using NLTK sentence tokenization (found {len(sentences)} sentences).")
        paragraphs = []
        current_paragraph = []
        for i, sentence in enumerate(sentences):
            current_paragraph.append(sentence)
            if len(current_paragraph) >= sentences_per_paragraph or i == len(sentences) - 1:
                paragraphs.append(" ".join(current_paragraph))
                current_paragraph = []
        formatted_output = paragraphs
    else:
        print(f"Sentence tokenization ineffective (found {len(sentences)} sentences). Using fallback line grouping.")
        paragraphs = []
        current_paragraph_lines = []
        for i, segment in enumerate(text_segments):
            current_paragraph_lines.append(segment)
            if len(current_paragraph_lines) >= lines_per_fallback_paragraph or i == len(text_segments) - 1:
                paragraphs.append(" ".join(current_paragraph_lines))
                current_paragraph_lines = []
        formatted_output = paragraphs

    return "\n\n".join(formatted_output).strip()

def get_transcript_data(url, language='en'):
    """
    Fetches transcript using yt-dlp and returns both timestamped and paragraph formats.
    """
    video_id = extract_video_id(url)
    if not video_id: return {'error': "Error: Could not extract a valid YouTube video ID from the URL."}

    base_filename = f"{video_id}_transcript_{language}"
    subtitle_file_path = None
    result = {'timestamped': "", 'paragraph': "", 'error': None}

    ydl_opts = { 'writeautomaticsub': True, 'subtitleslangs': [language], 'skip_download': True, 'outtmpl': base_filename, 'quiet': True, 'noprogress': True, 'noplaylist': True, 'socket_timeout': 30, 'retries': 2 }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            with st.spinner(f'Downloading subtitles ({language})...'):
                info_dict = ydl.extract_info(url, download=True)
            possible_paths = [f"{base_filename}.{language}.vtt", f"{base_filename}.vtt"]
            for path in possible_paths:
                 if os.path.exists(path): subtitle_file_path = path; break
            if not subtitle_file_path:
                if not info_dict.get('automatic_captions') and not info_dict.get('subtitles'): result['error'] = f"Error: No subtitles/captions available (lang: '{language}')."
                else: result['error'] = f"Error: Subtitle file not created by yt-dlp."
                return result
            with st.spinner('Processing transcript formats...'):
                with open(subtitle_file_path, 'r', encoding='utf-8') as f: vtt_content = f.read()
                result['timestamped'] = parse_vtt_with_timestamps(vtt_content)
                result['paragraph'] = format_transcript_into_paragraphs(vtt_content)
                if not result['timestamped'] and not result['paragraph']: result['error'] = "Error: Parsing subtitle file resulted in empty content."
    except yt_dlp.utils.DownloadError as e:
        if "no automatic captions found" in str(e).lower() or "no subtitles found" in str(e).lower(): result['error'] = f"Error: No subtitles/captions found (lang: '{language}')."
        elif "Video unavailable" in str(e): result['error'] = f"Error: Video unavailable."
        elif "unable to download video data" in str(e).lower(): result['error'] = f"Error: Could not download video metadata."
        else: result['error'] = f"Error during download/extraction (yt-dlp)."
    except Exception as e:
        result['error'] = f"An unexpected error occurred during processing: {str(e)}"
        print(f"Unexpected Error: {e}")
    finally:
        if subtitle_file_path and os.path.exists(subtitle_file_path):
            try: os.remove(subtitle_file_path)
            except OSError as e: print(f"Warning: Could not delete temp file {subtitle_file_path}: {e}")
    return result

def generate_word_cloud(text):
    """Generates a WordCloud object from text, removing stopwords."""
    if not text or text.startswith("Error:") or text.startswith("Could not extract"):
        return None # Return None if text is invalid or empty

    # Generate word cloud
    try:
        wordcloud = WordCloud(width=800, height=400,
                              background_color='white',
                              stopwords=STOP_WORDS, # Use pre-loaded stopwords
                              max_words=100, # Limit number of words
                              collocations=False # Avoid treating pairs as single words
                              ).generate(text)
        return wordcloud
    except ValueError:
        # Handle cases where the text might be empty after stopword removal
        print("ValueError during word cloud generation (likely no non-stop words found).")
        return None
    except Exception as e:
        print(f"Error generating word cloud: {e}")
        return None


# --- Streamlit App UI ---

st.title("▶️ YouTube Transcript Viewer & Formatter")
st.write("Enter a YouTube URL to fetch its transcript. View with timestamps, as formatted paragraphs, or as a word cloud.")
st.write("_(Uses automatic captions by default)_")

# Initialize session state
if 'transcript_data' not in st.session_state:
    st.session_state.transcript_data = {'timestamped': "", 'paragraph': "", 'error': None}
if 'last_url' not in st.session_state:
    st.session_state.last_url = ""
if 'video_id' not in st.session_state:
    st.session_state.video_id = ""
if 'word_cloud' not in st.session_state:
    st.session_state.word_cloud = None


# --- Input Section ---
input_col, cloud_col = st.columns([2, 3]) # Make word cloud column wider

with input_col:
    url = st.text_input("YouTube Video URL:", placeholder="e.g., https://youtu.be/VIDEO_ID5", value=st.session_state.last_url, key="url_input")
    lang = 'en' # Language (Hardcoded for now)
    if st.button("Get Transcript", key="get_transcript_button"):
        if url:
            if url != st.session_state.last_url or not (st.session_state.transcript_data.get('timestamped') or st.session_state.transcript_data.get('paragraph') or st.session_state.transcript_data.get('error')):
                # Clear previous results
                st.session_state.transcript_data = {'timestamped': "", 'paragraph': "", 'error': None}
                st.session_state.word_cloud = None # Clear old word cloud
                st.session_state.last_url = url
                st.session_state.video_id = extract_video_id(url)
                # Call the main function
                st.session_state.transcript_data = get_transcript_data(url, language=lang)
                # Generate word cloud if paragraph text is available and no error
                if not st.session_state.transcript_data.get('error') and st.session_state.transcript_data.get('paragraph'):
                     with st.spinner("Generating word cloud..."):
                          st.session_state.word_cloud = generate_word_cloud(st.session_state.transcript_data['paragraph'])
            else:
                 st.info("Displaying previously fetched results for this URL.")
        else:
            st.warning("Please enter a YouTube URL.")
            # Clear results if URL is cleared
            st.session_state.transcript_data = {'timestamped': "", 'paragraph': "", 'error': None}
            st.session_state.word_cloud = None
            st.session_state.last_url = ""
            st.session_state.video_id = ""

# --- Word Cloud Display Area ---
with cloud_col:
    st.subheader("Word Cloud")
    if st.session_state.word_cloud:
        try:
            fig, ax = plt.subplots(figsize=(10, 5)) # Create matplotlib figure
            ax.imshow(st.session_state.word_cloud, interpolation='bilinear')
            ax.axis("off") # Hide axes
            st.pyplot(fig) # Display figure in Streamlit
            plt.close(fig) # Close the figure to free memory
        except Exception as e:
            st.error(f"Error displaying word cloud: {e}")
    elif st.session_state.transcript_data.get('paragraph') and not st.session_state.transcript_data.get('error'):
         # Handle case where word cloud generation failed (e.g., only stopwords found)
         st.info("Word cloud could not be generated (perhaps only common words were found).")
    else:
        st.caption("Word cloud will appear here after fetching a transcript.")


# --- Transcript Display Section ---
st.markdown("---") # Separator

# Check for errors first
if st.session_state.transcript_data.get('error'):
    st.error(st.session_state.transcript_data['error'])
# Display content if no error and at least one format has content
elif st.session_state.transcript_data.get('timestamped') or st.session_state.transcript_data.get('paragraph'):

    col1, col2 = st.columns(2) # Create two columns for transcripts

    # Column 1: Timestamped Transcript
    with col1:
        st.subheader("Transcript with Timestamps")
        timestamped_transcript = st.session_state.transcript_data.get('timestamped', "Not available.")
        st.text_area(label="Timestamped Text", value=timestamped_transcript, height=400, key="transcript_display_area_ts", help="Scroll to see the full transcript with timestamps.")
        ts_download_filename = f"{st.session_state.video_id}_transcript_{lang}_timestamps.txt" if st.session_state.video_id else "transcript_timestamps.txt"
        st.download_button(label="⬇️ Download Timestamps (.txt)", data=timestamped_transcript.encode('utf-8'), file_name=ts_download_filename, mime='text/plain', key="download_button_ts", disabled=not timestamped_transcript or timestamped_transcript == "Not available.")

    # Column 2: Formatted Paragraph Transcript
    with col2:
        st.subheader("Formatted Transcript")
        paragraph_transcript = st.session_state.transcript_data.get('paragraph', "Not available.")
        st.text_area(label="Formatted Text", value=paragraph_transcript, height=400, key="transcript_display_area_para", help="Scroll to see the transcript formatted into paragraphs.")
        para_download_filename = f"{st.session_state.video_id}_transcript_{lang}_formatted.txt" if st.session_state.video_id else "transcript_formatted.txt"
        st.download_button(label="⬇️ Download Formatted (.txt)", data=paragraph_transcript.encode('utf-8'), file_name=para_download_filename, mime='text/plain', key="download_button_para", disabled=not paragraph_transcript or paragraph_transcript == "Not available.")

# Footer
st.markdown("---")
st.markdown("Powered by [Streamlit](https://streamlit.io), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [NLTK](https://www.nltk.org/), and [wordcloud](https://github.com/amueller/word_cloud)")

