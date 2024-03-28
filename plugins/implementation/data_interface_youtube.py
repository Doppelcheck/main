from __future__ import annotations

import math
from typing import AsyncGenerator

import pytube
import youtube_transcript_api
from loguru import logger

from plugins.abstract import InterfaceData, Parameters, DictSerializableImplementation, InterfaceDataConfig, \
    DictSerializable, ConfigurationCallbacks, Uri, InterfaceLLM, Document
from thefuzz import fuzz
from tools.text_processing import extract_code_block


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
    def _find_text_in_transcript(transcript: list[dict[str, str | float]], keywords: list[str]) -> tuple[float, float]:
        window_size = len(keywords) * 3
        min_len = 2
        threshold = 80

        _keywords = tuple(x.lower() for x in keywords if len(x) >= min_len)

        best_time_index = -1.
        best_value = -1.

        indexed_words = Youtube._index_words(transcript, min_len=min_len)

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

    @staticmethod
    def _timestamped_youtube_video_url(youtube_url: str, timestamp: float) -> str:
        # Convert the timestamp from seconds to an integer
        timestamp = math.floor(timestamp)

        # Check if the URL already has query parameters
        if '?' in youtube_url:
            # If the URL already contains query parameters, append the timestamp with an '&'
            return f"{youtube_url}&t={timestamp:d}s"

        # If the URL does not contain any query parameters, append the timestamp with a '?'
        return f"{youtube_url}?t={timestamp:d}s"

    def _timestamped_url(self, youtube_url: str, keywords: list[str]) -> tuple[str, float] | None:
        min_mentions = 1

        v = pytube.YouTube(youtube_url)
        video_id = v.video_id

        try:
            transcript = self._get_transcript(video_id)

        except youtube_transcript_api._errors.TranscriptsDisabled:
            logger.warning("transcripts disabled.")
            return None

        time_index, match = Youtube._find_text_in_transcript(transcript, keywords)
        print(f"best time index: {time_index:.2f}, best match: {match:.2f}")
        if float(min_mentions) >= match:
            logger.warning("keywords not mentioned.")
            return None

        timestamped_url = Youtube._timestamped_youtube_video_url(youtube_url, time_index)
        return timestamped_url, match

    async def get_uris(self, query: str, doc_count: int) -> AsyncGenerator[Uri, None]:
        search = pytube.Search(query)
        search_results = search.results
        keyword_list = query.split()

        all_results = list()
        for each_result in search_results:
            each_url = each_result.watch_url
            each_result = self._timestamped_url(each_url, keyword_list)
            if each_result is not None:
                all_results.append(each_result)

        all_results.sort(key=lambda x: x[1], reverse=True)
        for ts_url, match in all_results:
            each_title = pytube.YouTube(ts_url).title
            yield Uri(uri_string=ts_url, title=each_title)

    def _get_transcript(self, video_id: str) -> list[dict[str, any]]:
        transcripts = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(video_id)
        if len(transcripts._manually_created_transcripts) > 0:
            transcript_lang = list(transcripts._manually_created_transcripts.keys())[0]

        elif len(transcripts._generated_transcripts) > 0:
            transcript_lang = list(transcripts._generated_transcripts.keys())[0]

        else:
            transcript_lang = "en"

        transcript = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id, languages=[transcript_lang])
        return transcript

    async def get_document_content(self, uri: str) -> Document:
        v = pytube.YouTube(uri)
        video_id = v.video_id
        transcript = self._get_transcript(video_id)
        full_text = " ".join(each_segment["text"].strip() for each_segment in transcript)
        return Document(uri, full_text)

    async def get_context(
            self, uri: str, full_content: str | None = None) -> str:
        each_video = pytube.YouTube(uri)
        return (
            f"TITLE: {each_video.title}\n"
            f"PUBLISHED: {each_video.publish_date}\n"
            f"\n"
            f"{each_video.description}\n"
        )
