import yt_dlp
import youtube_transcript_api


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
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_results = ydl.extract_info(f"ytsearch10:{keywords}", download=False)
        entries = search_results["entries"]
        urls = [each_result["webpage_url"] for each_result in entries]

    return urls


def get_transcript(video_id: str) -> list[dict[str, str | float]]:
    transcripts = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
    if len(transcripts._manually_created_transcripts) > 0:
        transcript_lang = list(transcripts._manually_created_transcripts.keys())[0]
    elif len(transcripts._generated_transcripts) > 0:
        transcript_lang = list(transcripts._generated_transcripts.keys())[0]
    else:
        transcript_lang = "en"
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


def find_text_in_transcript(transcript: list[dict[str, str | float]], keywords: list[str]) -> float:
    window_size = len(keywords) * 3

    best_time_index = -1.
    best_value = -1.

    indexed_words = index_words(transcript, min_len=2)

    for i in range(len(indexed_words) - window_size):
        window = indexed_words[i:i + window_size]
        window_words = [each_word[0].lower() for each_word in window]
        window_index = indexed_words[i][1]

        count = 0.
        for each_keyword in keywords:
            count += sum(.5 ** i for i in range(window_words.count(each_keyword.lower())))

        if count >= best_value:
            best_value = count
            best_time_index = window_index

    if best_value < 1.:
        return -1.

    return best_time_index


def test_transcript() -> list[dict[str, str | float]]:
    return [
        {"text": "(upbeat music)", "start": 1.366, "duration": 2.583},
        {"text": "(water drips)", "start": 7.172, "duration": 2.298},
        {"text": "- Sorry about the leaky pipes.", "start": 9.47, "duration": 1.12},
        {
            "text": "It shouldn't affect the interview at all.",
            "start": 10.59,
            "duration": 1.9,
        },
        {
            "text": "- They give us sound\nand everything on that?",
            "start": 12.49,
            "duration": 1.47,
        },
        {"text": "- We'll take it out in post.", "start": 13.96, "duration": 1.5},
        {"text": "- That's just plumbing,", "start": 15.46, "duration": 0.98},
        {"text": "cause it's not even raining outside.", "start": 16.44, "duration": 1.8},
        {"text": "- Hi, welcome to another edition", "start": 19.3, "duration": 1.84},
        {"text": 'of "Between Two Ferns".', "start": 21.14, "duration": 0.9},
        {"text": "I'm your host, Zach Galifianakis,", "start": 22.04, "duration": 1.44},
        {
            "text": "and today my guest is\nMatthew McConach, McCanaway,",
            "start": 23.48,
            "duration": 4.29,
        },
        {
            "text": "Matthew McConnyw-, Matthew\nMcConajee, McConaughey.",
            "start": 30.437,
            "duration": 4.167,
        },
        {"text": "- Good to be here Zach.", "start": 36.114, "duration": 1.436},
        {"text": "All right. All right. All right.", "start": 37.55, "duration": 2.613},
        {
            "text": "Sorry, I was just reading\nthe box office returns",
            "start": 41.81,
            "duration": 1.86,
        },
        {"text": "for your last three movies.", "start": 43.67, "duration": 1.35},
        {"text": "All right.", "start": 46.75, "duration": 1.67},
        {"text": "All right.", "start": 48.42, "duration": 1.413},
        {
            "text": "And then I guess that one was all right.",
            "start": 49.833,
            "duration": 1.34,
        },
        {"text": "(Matthew clears his throat)", "start": 51.173, "duration": 1.327},
        {"text": "I noticed that you're wearing a shirt.", "start": 52.5, "duration": 2.3},
        {"text": "Is everything okay?", "start": 54.8, "duration": 0.95},
        {"text": "- Are you fucking kidding me?", "start": 57.53, "duration": 1.32},
        {
            "text": "- Of all the things you\ncan win an Oscar for,",
            "start": 58.85,
            "duration": 1.94,
        },
        {
            "text": "how surprised are you that\nyou won one for acting?",
            "start": 60.79,
            "duration": 3.23,
        },
        {"text": "- Here we go.", "start": 64.02, "duration": 0.833},
        {
            "text": "- But so did that guy\nfrom 30 Seconds to Mars.",
            "start": 64.853,
            "duration": 2.797,
        },
        {"text": "So, how proud can you really be?", "start": 67.65, "duration": 2.313},
    ]


def timestamped_youtube_video_url(youtube_url: str, timestamp: float) -> str:
    # Convert the timestamp from seconds to an integer
    timestamp = int(timestamp)

    # Check if the URL already has query parameters
    if '?' in youtube_url:
        # If the URL already contains query parameters, append the timestamp with an '&'
        return f"{youtube_url}&t={timestamp}s"

    # If the URL does not contain any query parameters, append the timestamp with a '?'
    return f"{youtube_url}?t={timestamp}s"


def main() -> None:
    search_keywords = "bernie sanders interview"
    urls = search_youtube_urls(search_keywords)
    print(urls)

    video_mentions = ["israel", "palestine", "muslim"]

    for each_url in urls:
        print(each_url)
        video_id = each_url.rsplit("=", 1)[-1]
        try:
            transcript = get_transcript(video_id)

        except youtube_transcript_api._errors.TranscriptsDisabled:
            print("transcripts disabled.")
            continue

        time_index = find_text_in_transcript(transcript, video_mentions)
        if time_index < 0.:
            print(f"keywords not mentioned.")
        else:
            each_ts_url = timestamped_youtube_video_url(each_url, time_index)
            print(each_ts_url)
        print()


if __name__ == "__main__":
    main()
