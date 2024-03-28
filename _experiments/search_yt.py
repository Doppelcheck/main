import math

import yt_dlp
import youtube_transcript_api
import pytube

from thefuzz import fuzz


def search_youtube_urls(keywords: str) -> list[str]:
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL() as ydl:
        search_results = ydl.extract_info(f"ytsearch10:{keywords}", download=False)
        entries = search_results["entries"]
        urls = [each_result["webpage_url"] for each_result in entries]

    return urls


def get_transcript(video_id: str, default_lang: str = "en") -> list[dict[str, str | float]]:
    transcripts = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
    if len(transcripts._manually_created_transcripts) > 0:
        transcript_lang = list(transcripts._manually_created_transcripts.keys())[0]

    elif len(transcripts._generated_transcripts) > 0:
        transcript_lang = list(transcripts._generated_transcripts.keys())[0]

    else:
        transcript_lang = default_lang

    transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id, languages=[transcript_lang])
    return transcript


def index_words(transcript: list[dict[str, str | float]], min_len: int = 1) -> list[tuple[str, float]]:
    indexed_words = list[tuple[str, float]]()
    for i, each_segment in enumerate(transcript):
        each_index = each_segment["start"]
        each_text = each_segment["text"]
        for each_word in each_text.split():
            only_chars = "".join(x for x in each_word if x.isalpha())
            if len(only_chars) >= min_len:
                indexed_words.append((only_chars, each_index))

    return indexed_words


def find_text_in_transcript(transcript: list[dict[str, str | float]], keywords: list[str]) -> tuple[float, float]:
    window_size = len(keywords) * 3
    min_len = 2
    threshold = 80

    _keywords = tuple(x.lower() for x in keywords if len(x) >= min_len)

    best_time_index = -1.
    best_value = -1.

    indexed_words = index_words(transcript, min_len=min_len)

    for i in range(len(indexed_words) - window_size):
        window = indexed_words[i:i + window_size]
        word_list = [each_word[0].lower() for each_word in window]

        frequencies = {each_kw: 0 for each_kw in _keywords}
        full_match = 0.
        for each_word in word_list:
            best_match = 0.
            best_kw = None
            for each_kw in _keywords:
                each_match = fuzz.ratio(each_word, each_kw)
                if each_match > threshold and each_match > best_match:
                    best_match = each_match
                    best_kw = each_kw

            if best_kw is None:
                continue
            new_freq = frequencies[best_kw]
            full_match += .5 ** new_freq
            frequencies[best_kw] = new_freq + 1

        if full_match >= best_value:
            best_value = full_match
            best_time_index = indexed_words[i][1]

    return best_time_index, best_value


def timestamped_youtube_video_url(youtube_url: str, timestamp: float) -> str:
    # Convert the timestamp from seconds to an integer
    timestamp = math.floor(timestamp)

    # Check if the URL already has query parameters
    if '?' in youtube_url:
        # If the URL already contains query parameters, append the timestamp with an '&'
        return f"{youtube_url}&t={timestamp:d}s"

    # If the URL does not contain any query parameters, append the timestamp with a '?'
    return f"{youtube_url}?t={timestamp:d}s"


def main() -> None:
    search_keywords = "bernie sanders interview"
    urls = search_youtube_urls(search_keywords)

    video_mentions = ["israel", "palestine", "muslim"]

    for each_url in urls:
        print(each_url)
        each_video = pytube.YouTube(each_url)
        print(each_video.title)
        print(each_video.publish_date)
        print(each_video.description)
        # print(each_video.keywords)
        # print(each_video.metadata)

        video_id = each_url.rsplit("=", 1)[-1]
        try:
            transcript = get_transcript(video_id)

        except youtube_transcript_api._errors.TranscriptsDisabled:
            print("transcripts disabled.")
            continue

        time_index, match = find_text_in_transcript(transcript, video_mentions)
        print(f"best time index: {time_index:.2f}, best match: {match:.2f}")
        if 0. >= match:
            print(f"keywords not mentioned.")

        else:
            each_ts_url = timestamped_youtube_video_url(each_url, time_index)
            print(each_ts_url)

        print()


# search using google with 'site:youtube.com', provide links to timestamps
# compare statement with transcript, provide `each_video.title`, `each_video.publish_date`, `each_video.description`
# as context

if __name__ == "__main__":
    main()
