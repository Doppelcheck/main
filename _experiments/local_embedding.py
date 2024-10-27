from typing import Generator

from transformers import AutoModel


def segment_text(text: str, max_length: int = 512, overlap: int = 0) -> Generator[str, None, None]:
    """
    Segment a long text into smaller chunks.
    :param text: The text to segment.
    :param max_length: The maximum length of each segment.
    :param overlap: The number of characters to overlap between segments.
    :return: A generator of text segments.
    """
    start = 0
    end = max_length
    while start < len(text):
        yield text[start:end]
        start = end - overlap
        end = start + max_length


def main() -> None:
    text = (
        "ab heute beraten die Außenminister der Natostaaten in Brüssel über die weitere Unterstützung für die Ukraine "
        "Generalsekretär Stolenberg schlug den Aufbau einer Ukraine Mission vor ihre Aufgabe Waffenlieferungen an die "
        "Ukraine und Ausbildung ukrainischer Soldaten zu koordinieren heißt es aus Diplomatenkreisen na bisher "
        "übernehmen das ja die USA Stoltenberg wolle die Natostaaten außerdem dazu bewegen der Ukraine für die "
        "kommenden 5 Jahre militärische Unterstützung im Wert von insgesamt 100 Milliarden Euro zuzusagen in Brüssel "
        "für uns Marco Reinke Marco interessant ist ja vor allem dass man der USA jetzt eine doch sehr wichtige "
        "Aufgabe abnehmen möchte die NATO soll sich auf den Wunsch von Stoltenberg künftig selbst darum kümmern die "
        "Ukraine mit Munition zu versorgen was steckt dahinter ja diese Idee kommt ja nicht von ungefähr sondern man "
        "reagiert damit auf die doch zuletzt immer wieder blockierten Hilfslieferung von Seiten der USA vor allem ja "
        "auch dort immer noch die feststeckenden Gelder ähm die noch immer nicht freigegeben sind und so will man "
        "sich unabhängiger machen von Seiten der USA aber gleichzeitig wäre dieser Schritt natürlich auch politisch "
        "durchaus besonders und auch ein großer Schritt denn damit würden sich ja am Ende die Natostaaten ähm doch "
        "viel mehr um die Ukraine kümmern oder viel organisierter um die Ukraine äh kümmern als man das äh bisher tut "
        "man hat der Ukraine ja zwar eine Beitrittsperspektive gegeben mehr oder minder doch das ist etwas was in "
        "sehr ferner Zukunft liegt aber interessant ist das natürlich trotzdem dass die NATO sich hier zu diesem "
        "Schritt nun offenbar entschließt und man hier jetzt viel stärker mit der Ukraine zusammenarbeiten will ich "
        "kann mir sehr gut vorstellen dass das in Moskau für entsprechende Reaktionen sorgen wird Marco sprechen wir "
        "noch mal über Generalsekretär Stoltenberg der ist ja nun allseits beliebt allerdings will er seinen Amt ja "
        "bald niederlegen ist denn schon ein geeigneter Nachfolger in Sicht ja es hat so einige Namen zuletzt gegeben "
        "die in den Ring geworfen wurden unter anderem selbst ins Spiel gebracht unter anderem beispielsweise der "
        "lettische Verteidigungsminister der sich immer wieder selber ins Spiel gebracht hat aber momentan scheint es "
        "so dass Mark Rütte aus den nieder landen da doch durchaus größere Chancen hat diesen Posten zu bekommen das "
        "ist zumindest der Name der so am heißesten hier in Brüssel gehandelt wird aber diese Frage die ist am Ende "
        "noch nicht abschließend beantwortet das ganze dürfte dann ein Punkt sein den man auf dem Natogipfel im Juli "
        "in Washington dann beantworten oder bzw dann beschließen will mit einem Nachfolger wie gesagt einige Namen "
        "zuletzt gehandelt am heißesten bisher Marrütte Mar danke schön für diese ersten Einordnungen du wirst "
        "natürlich diese Gespräche weiter für uns verfolgen danke nach Brüssel wenn ihr mehr News aus unserem Team "
        "wollt dann müsst ihr einmal hier klicken wenn ihr auf der Suche seid nach spannenden Dokus starken "
        "Reportagen dann geht's hier entlang und wenn ihr Welt abonnieren wollt neu entdecken wollt dann einmal hier "
        "klicken"
    )

    # Initialize the model
    model = AutoModel.from_pretrained("jinaai/jina-embeddings-v3", trust_remote_code=True)

    texts = list(segment_text(text, max_length=256, overlap=64))


    # When calling the `encode` function, you can choose a `task` based on the use case:
    # 'retrieval.query', 'retrieval.passage', 'separation', 'classification', 'text-matching'
    # Alternatively, you can choose not to pass a `task`, and no specific LoRA adapter will be used.
    embeddings = model.encode(texts, task="retrieval.passage")  # retrieval.passage

    reference_text = "Das ist eine Antwort auf die geleistete Unterstützung."
    reference_embedding = model.encode(reference_text, task="retrieval.query")  # retrieval.query
    for text, embedding in zip(texts, embeddings):
        print(f"Similarity between '{text}' and '{reference_text}': {embedding @ reference_embedding.T}")


if __name__ == "__main__":
    main()
