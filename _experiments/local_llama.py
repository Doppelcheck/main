from __future__ import annotations
import asyncio

import instructor
from dataclasses import dataclass
from typing import Mapping, Sequence

import pydantic_core
from ollama import AsyncClient
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
    """Base class for all actions."""

    def do(self, interface: SummarizationInterface) -> None:
        raise NotImplementedError("This method must be implemented in the derived class.")


class Next(Action):
    """Continue to the next segment of the document."""
    def do(self, interface: SummarizationInterface) -> None:
        interface.next()


class Previous(Action):
    """Go back to the previous segment of the document."""
    def do(self, interface: SummarizationInterface) -> None:
        interface.previous()


class AddKeyPoint(Action):
    """Extract the current document segment's keypoint."""
    line_start: int = Field(..., description="The starting line of the key point.")
    line_end: int = Field(..., description="The ending line of the key point.")
    content: str = Field(..., description="The key point of the current document segment.")

    def do(self, interface: SummarizationInterface) -> None:
        interface.add_keypoint(self.line_start, self.line_end, self.content)


class RemoveKeyPoint(Action):
    """Remove one of the extracted key points."""
    index: int = Field(..., description="The index of the key point to remove.")

    def do(self, interface: SummarizationInterface) -> None:
        interface.remove_keypoint(self.index)


class EditKeyPoint(Action):
    """Edit one of the extracted key points."""
    index: int = Field(..., description="The index of the key point to edit.")
    line_start: int = Field(..., description="The starting line of the key point.")
    line_end: int = Field(..., description="The ending line of the key point.")
    content: str = Field(..., description="The updated key point of the current document segment.")

    def do(self, interface: SummarizationInterface) -> None:
        interface.edit_keypoint(self.index, self.line_start, self.line_end, self.content)


class Finish(Action):
    """Finish the key point extraction. Call only when the required number of key points have been extracted."""
    def do(self, interface: SummarizationInterface) -> None:
        interface.finish()


class SelectedAction(BaseModel):
    """The best action choice for extracting the document's keypoints."""
    action: Next | AddKeyPoint | RemoveKeyPoint | EditKeyPoint | Finish = Field(
        ..., description=(
            "The single best action to call in order to extend and improve the document's most important key points."
        )
    )


class SummarizationInterface:
    def __init__(self, document_lines: Sequence[str], no_keypoints: int, line_window: int = 5, overlap: int = 1):
        self.document_lines = document_lines
        self.len_doc = len(document_lines)
        self.keypoints = list[KeyPoint]()
        self.no_keypoints = no_keypoints
        self.current_line = 0
        self.overlap = overlap
        self.line_window = line_window
        self.start_of_document = True
        self.end_of_document = False

    def _keypoints(self) -> str:
        if len(self.keypoints) < 1:
            return "No keypoints extracted yet."

        return "\n".join(
            f"{index + 1}. lines {each_kp.line_range[0]:04d}-{each_kp.line_range[1]:04d}: {each_kp.content}"
            for index, each_kp in enumerate(self.keypoints)
        )

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

    def execute_command(self, command: str) -> None:
        command_parts = command.split(sep="(", maxsplit=1)
        command_name = command_parts[0]
        command_arguments = command_parts[1].strip(")").split(",")

        if command_name == "next":
            self.next()

        elif command_name == "previous":
            self.previous()

        elif command_name == "add_keypoint":
            line_start, line_end, content = command_arguments
            self.add_keypoint(int(line_start), int(line_end), content)

        elif command_name == "remove_keypoint":
            index = int(command_arguments[0])
            self.remove_keypoint(index)

        elif command_name == "edit_keypoint":
            index, line_start, line_end, content = command_arguments
            self.edit_keypoint(int(index), int(line_start), int(line_end), content)

        elif command_name == "finish":
            self.finish()

        else:
            raise KeypointsError(f"Invalid command {command}.")

    def render(self):
        instruction_text = (
            f"What is the best single action to take in order to extend and improve the complete document's "
            f"{self.no_keypoints} most important key points below? "
            f"Choose only and exactly one of the available commands from the bottom of the screen."
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
            f"[Current Document Segment]\n"
            f"{document_content_text}\n"
            f"\n"
            f"[Extracted Key Points]\n"
            f"{keypoints_text}"
            # f"\n"
            # f"\n"
            # f"[Available Commands]\n"
            # f"{available_commands}"
        )

        return screen

    def _available_commands(self) -> str:
        options = list()
        if not self.end_of_document:
            options.append("`next()`: get next segment of the document")

        # if not self.start_of_document:
        #     options.append("`previous()`: get previous segment of the document")

        if len(self.keypoints) < self.no_keypoints:
            options.append("`add_keypoint([line start], [line end], [key point from segment])`: add new keypoint")

        if len(self.keypoints) >= 1:
            options.extend([
                "`remove_keypoint([keypoint_index])`: remove keypoint",
                "`edit_keypoint([keypoint index], [line start], [line end], [key point from segment])`: edit keypoint"
            ])

        if len(self.keypoints) == self.no_keypoints:
            options.append("`finish()`: finish summarization")

        return "\n".join(f"- {each_option}" for each_option in options)

    def next(self) -> None:
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

    def add_keypoint(self, start: int, end: int, content: str) -> None:
        if len(self.keypoints) >= self.no_keypoints:
            raise KeypointsError("You have reached the maximum number of key points.")

        self.keypoints.append(KeyPoint(line_range=(start, end), content=content))
        
    def remove_keypoint(self, index: int) -> None:
        if index < 1 or index > len(self.keypoints):
            raise KeypointsError(f"Key point index {index} is invalid.")

        self.keypoints.pop(index - 1)
        
    def edit_keypoint(self, index: int, start: int, end: int, content: str) -> None:
        if index < 1 or index > len(self.keypoints):
            raise KeypointsError(f"Key point index {index} is invalid.")

        self.keypoints[index - 1] = KeyPoint(line_range=(start, end), content=content)
        
    def finish(self) -> None:
        if len(self.keypoints) < self.no_keypoints:
            raise KeypointsError(f"You must extract {self.no_keypoints - len(self.keypoints)} more key points.")

        print("Summarization finished.")
        print("Key points:")
        for index, each_kp in enumerate(self.keypoints):
            print(f"{index + 1}. lines {each_kp.line_range[0]:04d}-{each_kp.line_range[1]:04d}: {each_kp.content}")
        exit()


async def chat_stream():

    # OLLAMA_HOST=0.0.0.0:8800 OLLAMA_MODELS=~/.ollama/.models ollama serve

    # todo:
    #  catch context exceeded exception
    #  implement continual interactive summarization

    client = AsyncClient(host="http://localhost:8800")

    with open("prompts/extract_short.txt", mode="r") as f:
        prompt_content = f.read()

    prompt = {
        'role': 'user',
        'content': prompt_content
    }

    async for part in await client.chat(model='mistral', messages=[prompt], stream=True):
        message: Mapping[str, any] = part['message']
        content = message['content']
        print(content, end='', flush=True)


async def chat_instructor(client: instructor.Instructor, model: str, screen_content: str) -> Action:
    prompt = {
        'role': 'user',
        'content': screen_content
    }

    while True:
        try:
            response = client.chat.completions.create(
                model=model, messages=[prompt], response_model=SelectedAction, max_retries=10
            )

        except pydantic_core._pydantic_core.ValidationError as e:
            continue

        return response.action


async def chat(client: AsyncClient, model: str, screen_content: str) -> str:
    prompt = {
        'role': 'user',
        'content': screen_content
    }

    response = await client.chat(model=model, messages=[prompt])
    response_txt = response['message']['content']
    return response_txt


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
        #mode=instructor.Mode.MD_JSON,
        mode = instructor.Mode.JSON
    )

    # model = 'llama2'
    model = 'mistral'

    interface = SummarizationInterface(text_lines, 3, line_window=10)
    while True:
        screen = interface.render()
        print(screen)
        command = await chat_instructor(client, model, screen)
        print()
        print(f"[Command]\n{str(command.__repr__())}\n\n")
        print()
        command.do(interface)


if __name__ == "__main__":
    # main()
    asyncio.run(main())
    # asyncio.run(chat())
