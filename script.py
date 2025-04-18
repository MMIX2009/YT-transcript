# Import necessary libraries
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs # Added for URL parsing

def extract_video_id(url):
    """
    Extracts the YouTube video ID from various URL formats.

    Args:
        url (str): The YouTube video URL.

    Returns:
        str or None: The extracted video ID, or None if it cannot be found.
    """
    # Examples:
    # - http://youtu.be/VIDEO_ID
    # - http://www.youtube.com/watch?v=VIDEO_ID&feature=feedu
    # - http://www.youtube.com/embed/VIDEO_ID
    # - http://www.youtube.com/v/VIDEO_ID?version=3&amp;hl=en_US
    try:
        parsed_url = urlparse(url)
        if parsed_url.hostname == 'youtu.be':
            # For short URLs like youtu.be/VIDEO_ID
            return parsed_url.path[1:] # Remove the leading '/'
        elif parsed_url.hostname in ('www.youtube.com', 'youtube.com'):
            if parsed_url.path == '/watch':
                # For standard watch URLs like youtube.com/watch?v=VIDEO_ID
                query_params = parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            elif parsed_url.path.startswith('/embed/'):
                # For embed URLs like youtube.com/embed/VIDEO_ID
                return parsed_url.path.split('/')[2]
            elif parsed_url.path.startswith('/v/'):
                 # For URLs like youtube.com/v/VIDEO_ID
                return parsed_url.path.split('/')[2]
        # Add more conditions here if needed for other URL formats
    except Exception as e:
        print(f"Error parsing URL '{url}': {e}")
        return None
    return None # Return None if no valid ID pattern was found

def get_youtube_transcript(video_id):
    """
    Fetches and formats the transcript for a given YouTube video ID.

    Args:
        video_id (str): The unique identifier of the YouTube video.

    Returns:
        str: The formatted transcript text, or an error message if the
             transcript cannot be fetched.
    """
    if not video_id: # Check if video_id is None or empty
        return "Error: Invalid or missing video ID."
    try:
        # Fetch the transcript using the video ID
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Format the transcript list into a single string
        formatted_transcript = ""
        for entry in transcript_list:
            formatted_transcript += entry['text'] + " "

        return formatted_transcript.strip()

    except TranscriptsDisabled:
        return f"Error: Transcripts are disabled for video ID: {video_id}"
    except NoTranscriptFound:
        return f"Error: No transcript found for video ID: {video_id}. It might be unavailable or still processing."
    except Exception as e:
        return f"An unexpected error occurred for video ID {video_id}: {e}"

# --- Example Usage ---
if __name__ == "__main__":
    # Provide the full YouTube video URL here
    # Example URL 1: 'https://www.youtube.com/watch?v=rfscVS0vtbw' (Python Tutorial)
    # Example URL 2: 'https://youtu.be/dQw4w9WgXcQ' (Short URL)
    target_video_url = 'https://www.youtube.com/watch?v=rfscVS0vtbw'

    print(f"Attempting to extract video ID from URL: {target_video_url}")

    # Extract the video ID from the URL
    video_id = extract_video_id(target_video_url)

    if video_id:
        print(f"Successfully extracted video ID: {video_id}")
        print(f"Fetching transcript for video ID: {video_id}...")

        # Call the function to get the transcript using the extracted ID
        transcript = get_youtube_transcript(video_id)

        # Print the result
        if transcript.startswith("Error:"):
            print(transcript)
        else:
            print("\n--- Transcript ---")
            print(transcript)
            print("\n--- End of Transcript ---")

            # Optional: Save the transcript to a file using the video ID
            # try:
            #     filename = f"{video_id}_transcript.txt"
            #     with open(filename, "w", encoding="utf-8") as f:
            #         f.write(transcript)
            #     print(f"\nTranscript saved to {filename}")
            # except Exception as e:
            #     print(f"\nError saving transcript to file: {e}")
    else:
        print("Error: Could not extract a valid YouTube video ID from the provided URL.")

