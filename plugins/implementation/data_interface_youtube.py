from __future__ import annotations

import asyncio
import dataclasses
import datetime
import math
from typing import AsyncGenerator

import pytube
import youtube_transcript_api
from loguru import logger
from pytube.extract import video_id

from plugins.abstract import InterfaceData, Parameters, DictSerializableImplementation, InterfaceDataConfig, \
    DictSerializable, ConfigurationCallbacks, Uri, InterfaceLLM, Document
from thefuzz import fuzz

from tools.text_processing import extract_code_block

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


def get_video_info(video_url: str, default_lang: str = "en") -> VideoInfo:
    video = pytube.YouTube(video_url)
    v_id = video_id(video_url)

    try:
        transcripts = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(v_id)
        if 0 < len(transcripts._manually_created_transcripts):
            transcript_lang = list(transcripts._manually_created_transcripts.keys())[0]

        elif 0 < len(transcripts._generated_transcripts):
            transcript_lang = list(transcripts._generated_transcripts.keys())[0]

        else:
            transcript_lang = default_lang

        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(v_id, languages=[transcript_lang])

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


class Youtube(InterfaceData):
    @staticmethod
    def _get_query(claim: str, context: str | None = None, language: str | None = None) -> str:
        context_data = (
            f"```context\n"
            f"{context}\n"
            f"```\n"
            f"\n"
        ) if context else ""

        context_instruction = (
            f" Refine your queries according to the provided context."
        ) if context else ""

        language_instruction = f"Respond in {language}" if language else "Respond in the language of the claim"

        return (
            f"{context_data}"
            f"```claim\n"
            f"{claim}\n"
            f"```\n"
            f"\n"
            f"Generate five space separated keywords that describe the claim above.{context_instruction}\n"
            f"\n"
            f"{language_instruction} and exactly and only with the search query requested in a fenced code block "
            f"according to the following pattern.\n"
            f"\n"
            f"IMPORTANT: Split up compound words! Don't wrap the keywords in double quotes!\n"
            f"\n"
            f"```\n"
            f"[space separated keywords]\n"
            f"```\n"
        )

    @staticmethod
    def name() -> str:
        return "Youtube"

    class ConfigParameters(Parameters):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            return Youtube.ConfigParameters(**state)

        def __init__(self, **kwargs: any) -> None:
            pass

    class ConfigInterface(InterfaceDataConfig):
        @classmethod
        def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
            parameters = DictSerializable.from_object_dict(state["parameters"])
            return Youtube.ConfigInterface(
                name=state["name"], parameters=parameters, from_admin=state["from_admin"]
            )

        def object_to_state(self) -> dict[str, any]:
            return {
                "name": self.name,
                "parameters": self.parameters.to_object_dict(),
                "from_admin": self.from_admin
            }

        def __init__(self, name: str, parameters: Youtube.ConfigParameters, from_admin: bool) -> None:
            super().__init__(name, from_admin)
            self.parameters = parameters

    @staticmethod
    def configuration(user_id: str | None, user_accessible: bool) -> ConfigurationCallbacks:
        async def _get_config() -> Youtube.ConfigInterface:
            logger.info(f"adding data interface: {user_id}")
            parameters = Youtube.ConfigParameters()
            new_interface = Youtube.ConfigInterface(name="", parameters=parameters, from_admin=user_id is None)
            return new_interface

        _default = Youtube.ConfigParameters()

        return ConfigurationCallbacks(reset=lambda: None, get_config=_get_config)

    @staticmethod
    def from_object_dict(object_dict: dict[str, any]) -> DictSerializableImplementation:
        return Youtube(**object_dict)

    @classmethod
    def from_state(cls, state: dict[str, any]) -> DictSerializableImplementation:
        parameters = DictSerializable.from_object_dict(state["parameters"])
        return Youtube(
            name=state["name"], parameters=parameters, from_admin=state["from_admin"]
        )

    def __init__(self, name: str, parameters: Youtube.ConfigParameters, from_admin: bool) -> None:
        super().__init__(name, parameters, from_admin)

    async def get_search_query(
            self, llm_interface: InterfaceLLM, keypoint_text: str,
            context: str | None = None, language: str | None = None):
        prompt = Youtube._get_query(keypoint_text, context=context, language=language)

        response = await llm_interface.reply_to_prompt(prompt)
        query = extract_code_block(response)
        return query

    @staticmethod
    def _index_words(transcript: list[dict[str, str | float]], min_len: int = 1) -> list[tuple[str, float]]:
        indexed_words = list[tuple[str, float]]()
        for i, each_segment in enumerate(transcript):
            each_index = each_segment["start"]
            each_text = each_segment["text"]
            for each_word in each_text.split():
                only_chars = "".join(x for x in each_word if x.isalpha())
                if len(only_chars) >= min_len:
                    indexed_words.append((only_chars, each_index))

        return indexed_words

    @staticmethod
    def _find_text_in_transcript(
            transcript: list[dict[str, str | float]], keywords: list[str], no_results: int = 1
    ) -> list[tuple[float, float]]:

        results = list[tuple[float, float]]()
        min_secs_apart = 10.
        min_match = 1.1

        window_size = len(keywords) * 3
        min_len = 2
        threshold = 80

        keywords = tuple(x.lower() for x in keywords if len(x) >= min_len)

        indexed_words = Youtube._index_words(transcript, min_len=min_len)

        for i in range(len(indexed_words) - window_size):
            window = indexed_words[i:i + window_size]
            word_list = [each_word[0].lower() for each_word in window]
            each_timestamp = indexed_words[i][1]

            frequencies = {each_kw: 0 for each_kw in keywords}
            full_match = 0.
            for each_word in word_list:
                best_match = 0.
                best_kw = None
                for each_kw in keywords:
                    each_match = fuzz.ratio(each_word, each_kw)
                    if each_match > threshold and each_match > best_match:
                        best_match = each_match
                        best_kw = each_kw

                if best_kw is None:
                    continue
                new_freq = frequencies[best_kw]
                full_match += .5 ** new_freq
                frequencies[best_kw] = new_freq + 1

            if full_match >= min_match:
                results.append((each_timestamp, full_match))

        filtered_results = list()
        results.sort(key=lambda x: x[1], reverse=True)
        for each_result in results:
            each_timestamp = each_result[0]
            if 0 < len(filtered_results):
                distance_to_closest = min(abs(each_timestamp - x[0]) for x in filtered_results)
                if distance_to_closest < min_secs_apart:
                    continue
            filtered_results.append(each_result)
            if len(filtered_results) >= no_results:
                return filtered_results

        return filtered_results

    @staticmethod
    def _timestamp_youtube_video_url(youtube_url: str, timestamp: int) -> str:
        if '?' in youtube_url:
            return f"{youtube_url}&t={timestamp:d}s"

        return f"{youtube_url}?t={timestamp:d}s"

    def _timestamped_urls(self, video_info: VideoInfo, keywords: list[str]) -> list[tuple[str, int, float]] | None:
        transcript = video_info.transcript
        timestamp_results = Youtube._find_text_in_transcript(transcript, keywords, no_results=1)

        results = [
            (
                Youtube._timestamp_youtube_video_url(video_info.video_url, math.floor(time_index)),
                math.floor(time_index),
                match
            )
            for time_index, match in timestamp_results
        ]
        return results

    async def get_uris(self, query: str, doc_count: int) -> AsyncGenerator[Uri, None]:
        results = await search_youtube(query, max_results=doc_count)
        keyword_list = query.split()

        async for each_info in get_video_infos(results):
            for each_url, each_ts, each_match in self._timestamped_urls(each_info, keyword_list):
                each_title = f"{math.floor(each_ts):d}s @ {each_info.title}"
                yield Uri(uri_string=each_url, title=each_title)

    async def _get_transcript(self, video_id: str) -> list[dict[str, any]]:
        transcripts = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
        if 0 < len(transcripts._manually_created_transcripts):
            transcript_lang = list(transcripts._manually_created_transcripts.keys())[0]

        elif 0 < len(transcripts._generated_transcripts):
            transcript_lang = list(transcripts._generated_transcripts.keys())[0]

        else:
            transcript_lang = "en"

        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id, languages=[transcript_lang])
        return transcript

    async def get_document_content(self, uri: str) -> Document:
        v_id = video_id(uri)
        transcript = await self._get_transcript(v_id)
        full_text = " ".join(each_segment["text"].strip() for each_segment in transcript)
        return Document(uri, full_text)

    async def get_context(self, uri: str, full_content: str | None = None) -> str:
        each_video = pytube.YouTube(uri)
        return (
            f"TITLE: {each_video.title}\n"
            f"PUBLISHED: {each_video.publish_date}\n"
            f"\n"
            f"{each_video.description}\n"
        )
