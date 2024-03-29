import asyncio
import dataclasses
import datetime
from typing import AsyncGenerator

import pytube
import youtube_transcript_api
from pytube.extract import video_id

from youtube_transcript_api import YouTubeTranscriptApi


async def search_youtube(query: str, max_results: int = 0) -> list[str]:
    pytube_result = pytube.Search(query)
    if 0 < max_results:
        results = pytube_result.results[:max_results]
    else:
        results = pytube_result.results

    return [each_video.watch_url for each_video in results]


@dataclasses.dataclass(frozen=True)
class VideoInfo:
    video_url: str
    title: str
    published: datetime.datetime
    description: str
    transcript: list[dict[str, str]]


def get_video_info(video_url: str) -> VideoInfo:
    video = pytube.YouTube(video_url)
    v_id = video_id(video_url)

    try:
        transcript = YouTubeTranscriptApi.get_transcript(v_id)

    except youtube_transcript_api._errors.TranscriptsDisabled as e:
        transcript = list()

    except youtube_transcript_api._errors.NoTranscriptFound as e:
        transcript = list()

    # noinspection PyTypeChecker
    published: datetime.datetime = video.publish_date

    return VideoInfo(video_url, video.title, published, video.description or "", transcript)


async def video_info_async(video_url: str) -> VideoInfo:
    loop = asyncio.get_event_loop()
    video_info = await loop.run_in_executor(None, get_video_info, video_url)
    return video_info


async def get_video_infos(video_urls: list[str]) -> AsyncGenerator[VideoInfo, None]:
    tasks = [video_info_async(url) for url in video_urls]
    for each_coroutine in asyncio.as_completed(tasks):
        each_info = await each_coroutine
        yield each_info


async def main() -> None:
    query = "your search query here"
    results = await search_youtube(query)
    async for each_info in get_video_infos(results):
        print(each_info.video_url)
        print(each_info.title)
        print(each_info.published)
        print(each_info.description)
        print(each_info.transcript)
        print()


if __name__ == "__main__":
    asyncio.run(main())
