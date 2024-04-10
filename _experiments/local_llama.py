import asyncio
from dataclasses import dataclass
from typing import Mapping, Sequence

from ollama import AsyncClient

from tools.text_processing import get_text_lines


@dataclass
class KeyPoint:
    line_range: tuple[int, int]
    content: str


class SummarizationInterface:
    def __init__(self, document_lines: Sequence[str], line_window: int = 5, overlap: int = 1):
        self.document_lines = document_lines
        self.len_doc = len(document_lines)
        self.keypoints = list[KeyPoint]()
        self.current_line = 0
        self.overlap = overlap
        self.line_window = line_window
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

    def render(self):
        instruction_text = "Navigate the document content to extract all of its key points."
        document_content_text = self._document_window()
        keypoints_text = self._keypoints()

        screen = (
            f"[Instruction]\n"
            f"{instruction_text}\n"
            f"\n"
            f"[Document Content]\n"
            f"{document_content_text}\n"
            f"\n"
            f"[Extracted Key Points]\n"
            f"{keypoints_text}")

        return screen

    def next(self) -> None:
        self.current_line = min(
            self.current_line + self.line_window - self.overlap,
            self.len_doc - self.line_window + 1)
        self.end_of_document = self.current_line >= self.len_doc - self.line_window + 1

    def previous(self) -> None:
        self.current_line = max(self.current_line - self.line_window + self.overlap, 0)
        self.end_of_document = self.current_line >= self.len_doc - self.line_window + 1

    def add_keypoint(self, start: int, end: int, content: str) -> None:
        self.keypoints.append(KeyPoint(line_range=(start, end), content=content))
        
    def remove_keypoint(self, index: int) -> None:
        self.keypoints.pop(index - 1)
        
    def edit_keypoint(self, index: int, start: int, end: int, content: str) -> None:
        self.keypoints[index - 1] = KeyPoint(line_range=(start, end), content=content)
        
    def finish(self) -> Sequence[KeyPoint]:
        return self.keypoints


async def chat():

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


def main() -> None:
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

    interface = SummarizationInterface(document_lines=text_lines, line_window=10)
    screen = interface.render()
    print(screen)
    print()

    
if __name__ == "__main__":
    main()
    # asyncio.run(chat())
