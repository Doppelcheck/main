import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi


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


def get_text(video_id: str) -> str:
    transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
    if len(transcripts._manually_created_transcripts) > 0:
        transcript_lang = list(transcripts._manually_created_transcripts.keys())[0]
    elif len(transcripts._generated_transcripts) > 0:
        transcript_lang = list(transcripts._generated_transcripts.keys())[0]
    else:
        transcript_lang = "en"

    transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[transcript_lang])
    lines = [each_line["text"].strip() for each_line in transcript]
    return " ".join(lines)


def main() -> None:
    search_keywords = "matthew mcconaughey interview"
    urls = search_youtube_urls(search_keywords)
    print(urls)

    video_mentions = ""

    for each_url in urls:
        print(each_url)
        video_id = each_url.rsplit("=", 1)[-1]
        transcript = get_text(video_id)
        print(transcript)
        print()


if __name__ == "__main__":
    main()
