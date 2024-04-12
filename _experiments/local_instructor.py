from __future__ import annotations
import asyncio

import instructor
from dataclasses import dataclass
from typing import Sequence, Callable

import pydantic_core
from openai import OpenAI
from pydantic import BaseModel, Field

from tools.text_processing import get_text_lines


class KeypointsError(Exception):
    pass


@dataclass
class KeyPoint:
    line_range: tuple[int, int]
    content: str


class Action(BaseModel):
    """All actions for extracting the document's relevant keypoints."""

    def do(self, interface: SummarizationInterface) -> None:
        raise NotImplementedError("This method must be implemented in the derived class.")


class NextSegment(Action):
    """Read the next segment of the document."""
    def do(self, interface: SummarizationInterface) -> None:
        interface.next_segment()


class PreviousSegment(Action):
    """Read the previous segment of the document."""
    def do(self, interface: SummarizationInterface) -> None:
        interface.previous()


class ExtractKeypoint(Action):
    """Extract a relevant keypoint."""
    line_start: int = Field(..., description="The starting line number of the source document segment.")
    line_end: int = Field(..., description="The ending line number of the source document segment.")
    keypoint_number: int = Field(..., description="The number of the extracted keypoint.")
    content: str = Field(..., description="Summary of the document's keypoint.")

    def do(self, interface: SummarizationInterface) -> None:
        interface.edit_keypoint(self.keypoint_number, self.line_start, self.line_end, self.content)


class Finish(Action):
    """Finish the keypoint extraction."""
    def do(self, interface: SummarizationInterface) -> None:
        interface.finish()


action_criterion = "The best action to take for extracting the complete document's most important keypoints."


class StartFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints at the start of the document with
    suggestions for each keypoint already available.
    """
    action: NextSegment | ExtractKeypoint | Finish = Field(..., description=action_criterion)


class MiddleFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints in the middle of the document with
    suggestions for each keypoint already available.
    """
    action: PreviousSegment | NextSegment | ExtractKeypoint | Finish = Field(..., description=action_criterion)


class EndFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints at the end of the document with
    suggestions for each keypoint already available.
    """
    action: PreviousSegment | ExtractKeypoint | Finish = Field(..., description=action_criterion)


class TooSmallFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints when the full document is visible
    with suggestions for each keypoint already available.
    """
    action: ExtractKeypoint | Finish = Field(..., description=action_criterion)


class StartNotFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints at the start of the document with
    keypoints still missing.
    """
    action: NextSegment | ExtractKeypoint = Field(..., description=action_criterion)


class MiddleNotFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints in the middle of the document with
    keypoints still missing.
    """
    action: PreviousSegment | NextSegment | ExtractKeypoint = Field(..., description=action_criterion)


class EndNotFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints at the end of the document with
    keypoints still missing.
    """
    action: PreviousSegment | ExtractKeypoint = Field(..., description=action_criterion)


class TooSmallNotFinished(BaseModel):
    """
    The best action for extracting the document's most important keypoints when the full document is visible
    with keypoints still missing.
    """
    action: ExtractKeypoint = Field(..., description=action_criterion)


class SummarizationInterface:
    def __init__(self, document_lines: Sequence[str], no_keypoints: int, line_window: int = 5, overlap: int = 1):
        self.document_lines = document_lines
        self.len_doc = len(document_lines)
        self.keypoints: list[None | KeyPoint] = [None for _ in range(no_keypoints)]
        self.current_line = 0
        self.overlap = overlap
        self.line_window = line_window
        self.start_of_document = True
        self.end_of_document = self.len_doc <= self.line_window

    def get_response_model(self) -> type[BaseModel]:
        return TooSmallNotFinished

        if None in self.keypoints:
            if self.start_of_document and self.end_of_document:
                return TooSmallNotFinished

            if self.start_of_document:
                return StartNotFinished

            if self.end_of_document:
                return EndNotFinished

            return MiddleNotFinished

        if self.start_of_document and self.end_of_document:
            return TooSmallFinished

        if self.start_of_document:
            return StartFinished

        if self.end_of_document:
            return EndFinished

        return MiddleFinished

    def _keypoints(self) -> str:
        lines = list[str]()
        for index, each_kp in enumerate(self.keypoints):
            if each_kp is None:
                each_line = f"{index + 1}. [Not yet extracted]"
            else:
                each_line = (
                    f"{index + 1}. lines {each_kp.line_range[0]:04d}-{each_kp.line_range[1]:04d}: {each_kp.content}"
                )
            lines.append(each_line)

        return "\n".join(lines)

    def _document_window(self) -> str:
        window = tuple(
            f"{each_line_number + 1:04d}: {self.document_lines[each_line_number]}"
            for each_line_number in range(
                self.current_line, self.current_line + self.line_window - int(self.end_of_document)
            )
        )
        if self.end_of_document:
            window += ("END OF DOCUMENT",)
        return "\n".join(window)

    def render(self):
        instruction_text = (
            f"What is the best single action to take in order to improve the complete document's most important key "
            f"points below?"
            # f" Choose only and exactly one of the available commands from the bottom of the screen."
            # f"Navigate the document to extract the {self.no_keypoints} most important key points."
            # f" To do this, choose one of the available commands from the bottom of the screen."
        )
        document_content_text = self._document_window()
        keypoints_text = self._keypoints()
        available_commands = self._available_commands()

        screen = (
            # f"[Instruction]\n"
            # f"{instruction_text}"
            # f"\n"
            # f"\n"
            f"[Current Source Document Segment]\n"
            f"{document_content_text}\n"
            f"\n"
            f"[Extracted Keypoints]\n"
            f"{keypoints_text}"
            # f"\n"
            # f"\n"
            # f"[Available Commands]\n"
            # f"{available_commands}"
        )

        return screen

    def _available_commands(self) -> str:
        options = [
            "`extract_keypoint([keypoint_number], [start_line], [end_line], [content])`: "
            "extract keypoint from the current segment"
        ]

        if not self.end_of_document:
            options.append("`next_segment()`: get next segment of the document")

        if not self.start_of_document:
            options.append("`previous_segment()`: get previous segment of the document")

        if None not in self.keypoints:
            options.append("`finish()`: finish summarization")

        return "\n".join(f"- {each_option}" for each_option in options)

    def next_segment(self) -> None:
        if self.end_of_document:
            raise KeypointsError("You have reached the end of the document.")

        self.current_line = min(
            self.current_line + self.line_window - self.overlap,
            self.len_doc - self.line_window + 1)

        self.start_of_document = False
        self.end_of_document = self.current_line >= self.len_doc - self.line_window + 1

    def previous(self) -> None:
        if self.start_of_document:
            raise KeypointsError("You have reached the start of the document.")

        self.current_line = max(self.current_line - self.line_window + self.overlap, 0)

        self.start_of_document = self.current_line == 0
        self.end_of_document = False

    def edit_keypoint(self, keypoint_number: int, start: int, end: int, content: str) -> None:
        if keypoint_number < 1 or keypoint_number > len(self.keypoints):
            raise KeypointsError(f"Keypoint number {keypoint_number} is invalid.")

        self.keypoints[keypoint_number - 1] = KeyPoint(line_range=(start, end), content=content)
        
    def finish(self) -> None:
        if None in self.keypoints:
            raise KeypointsError("You must extract more keypoints.")

        print("Summarization finished.")
        print("Keypoints:")
        for index, each_kp in enumerate(self.keypoints):
            print(f"{index + 1}. lines {each_kp.line_range[0]:04d}-{each_kp.line_range[1]:04d}: {each_kp.content}")
        exit()


async def chat_instructor(
        client: instructor.Instructor, model: str, screen_content: str,
        get_response_model: Callable[..., type[BaseModel]]) -> Action:

    prompt = {
        'role': 'user',
        'content': screen_content
    }

    while True:
        response_model = get_response_model()
        try:
            response, completion = client.chat.completions.create_with_completion(
                model=model, messages=[prompt], response_model=response_model, max_retries=10
            )
            print(f"raw output: {completion.choices[0].message.content.strip().__repr__()}")
            return response.action

        except pydantic_core._pydantic_core.ValidationError as e:
            continue



async def main() -> None:
    # https://python.useinstructor.com/blog/2024/03/08/simple-synthetic-data-generation/?h=description#leveraging-complex-example
    # https://github.com/jxnl/instructor/discussions/296
    # https://python.useinstructor.com/examples/ollama/#ollama

    document = """ab heute beraten die Außenminister der natostaaten in Brüssel über die weitere Unterstützung für 
    die Ukraine Generalsekretär stolenberg schlug den Aufbau einer Ukraine Mission vor ihre Aufgabe Waffenlieferungen 
    an die Ukraine und Ausbildung ukrainischer Soldaten zu koordinieren heißt es aus Diplomatenkreisen na bisher 
    übernehmen das ja die USA Stoltenberg wolle die natostaaten außerdem dazu bewegen der Ukraine für die kommenden 5 
    Jahre militärische Unterstützung im Wert von insgesamt 100 Milliarden Euro zuzusagen in Brüssel für uns Marco 
    Reinke Marco interessant ist ja vor allem dass man der USA jetzt eine doch sehr wichtige Aufgabe abnehmen möchte 
    die NATO soll sich auf den Wunsch von Stoltenberg künftig selbst darum kümmern die Ukraine mit Munition zu 
    versorgen was steckt dahinter ja diese Idee kommt ja nicht von ungefähr sondern man reagiert damit auf die doch 
    zuletzt immer wieder blockierten Hilfslieferung von Seiten der USA vor allem ja auch dort immer noch die 
    feststeckenden Gelder ähm die noch immer nicht freigegeben sind und so will man sich unabhängiger machen von 
    Seiten der USA aber gleichzeitig wäre dieser Schritt natürlich auch politisch durchaus besonders und auch ein 
    großer Schritt denn damit würden sich ja am Ende die natostaaten ähm doch viel mehr um die Ukraine kümmern oder 
    viel organisierter um die Ukraine äh kümmern als man das äh bisher tut man hat der Ukraine ja zwar eine 
    Beitrittsperspektive gegeben mehr oder minder doch das ist etwas was in sehr ferner Zukunft liegt aber 
    interessant ist das natürlich trotzdem dass die NATO sich hier zu diesem Schritt nun offenbar entschließt und man 
    hier jetzt viel stärker mit der Ukraine zusammenarbeiten will ich kann mir sehr gut vorstellen dass das in Moskau 
    für entsprechende Reaktionen sorgen wird Marco sprechen wir noch mal über Generalsekretär Stoltenberg der ist ja 
    nun allseits beliebt allerdings will er seinen Amt ja bald niederlegen ist denn schon ein geeigneter Nachfolger 
    in Sicht ja es hat so einige Namen zuletzt gegeben die in den Ring geworfen wurden unter anderem selbst ins Spiel 
    gebracht unter anderem beispielsweise der lettische Verteidigungsminister der sich immer wieder selber ins Spiel 
    gebracht hat aber momentan scheint es so dass Mark rütte aus den nieder landen da doch durchaus größere Chancen 
    hat diesen Posten zu bekommen das ist zumindest der Name der so am heißesten hier in Brüssel gehandelt wird aber 
    diese Frage die ist am Ende noch nicht abschließend beantwortet das ganze dürfte dann ein Punkt sein den man auf 
    dem natogipfel im Juli in Washington dann beantworten oder bzw dann beschließen will mit einem Nachfolger wie 
    gesagt einige Namen zuletzt gehandelt am heißesten bisher marrütte Mar danke schön für diese ersten Einordnungen 
    du wirst natürlich diese Gespräche weiter für uns verfolgen danke nach Brüssel wenn ihr mehr News aus unserem 
    Team wollt dann müsst ihr einmal hier klicken wenn ihr auf der Suche seid nach spannenden Dokus starken 
    Reportagen dann geht's hier entlang und wenn ihr Welt abonnieren wollt neu entdecken wollt dann einmal hier 
    klicken"""

    text_lines = list(get_text_lines(document, line_length=30))

    client = instructor.from_openai(
        OpenAI(
            base_url="http://localhost:8800/v1",
            api_key="ollama"
        ),
        mode=instructor.Mode.JSON
    )

    # model = 'llama2'
    model = 'mistral'

    interface = SummarizationInterface(text_lines, 3, line_window=10)
    while True:
        screen = interface.render()
        print(screen)
        command = await chat_instructor(client, model, screen, interface.get_response_model)
        print()
        print(f"[Command]\n{str(command.__repr__())}\n\n")
        print()
        command.do(interface)


if __name__ == "__main__":
    asyncio.run(main())
