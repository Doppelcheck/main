import numpy
from sklearn.cluster import KMeans
import torch
from torch.nn import functional
from transformers import AutoTokenizer, AutoModel
import spacy
from spacy.lang.de.stop_words import STOP_WORDS
import logging
from tqdm import tqdm

from server.utils.gpu_stuff import clear_gpu_memory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class E5EmbeddingSelector:
    """Class for selecting diverse and important chunks from German text using E5 embeddings."""

    def __init__(self,
                 model_name: str = 'intfloat/multilingual-e5-large-instruct',
                 batch_size: int = 8,
                 max_length: int = 512,
                 use_preprocessing: bool = True,
                 device: str | None = None):
        """
        Initialize the German embedding-based chunk selector using E5 model.

        Args:
            model_name: Name of the E5 model
            batch_size: Batch size for embedding generation
            max_length: Maximum sequence length for tokenization
            use_preprocessing: Whether to use spaCy preprocessing
            device: Device to use ('cpu', 'cuda', or None for auto-detection)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_preprocessing = use_preprocessing

        # Set device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        logger.info(f"Loading E5 model: {model_name}")
        logger.info(f"Using device: {self.device}")

        # Initialize tokenizer and model
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            self.model = self.model.to(self.device)
            # Set model to evaluation mode
            self.model.eval()

        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise

        # Initialize spaCy for preprocessing if needed
        if self.use_preprocessing:
            try:
                self.nlp = spacy.load("de_core_news_lg", disable=["parser", "ner"])
                # Disable components we don't need for preprocessing
            except IOError:
                logger.warning("German spaCy model not found. Running without preprocessing.")
                self.use_preprocessing = False

    def preprocess_german_text(self, text: str) -> str:
        """
        Preprocess German text to improve embedding quality.

        Args:
            text: The input text to preprocess

        Returns:
            Preprocessed text
        """
        if not self.use_preprocessing:
            return text

        doc = self.nlp(text)
        # Remove stopwords and punctuation
        tokens = [token.text for token in doc if not token.is_stop and not token.is_punct]
        return " ".join(tokens)

    def average_pool(self,
                     last_hidden_states: torch.Tensor,
                     attention_mask: torch.Tensor) -> torch.Tensor:
        """
        Perform average pooling on the last hidden states.

        Args:
            last_hidden_states: Last hidden states from the model
            attention_mask: Attention mask from tokenization

        Returns:
            Pooled embeddings
        """
        last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

    def embed_chunks(self, chunks: list[str], task_description: str | None = None) -> numpy.ndarray:
        """
        Generate embeddings for text chunks using the E5 model.

        Args:
            chunks: List of text chunks to embed
            task_description: Optional task description for instruction

        Returns:
            NumPy array of embeddings
        """
        if not chunks:
            return numpy.array([])

        # Process chunks with preprocessing if needed
        if self.use_preprocessing:
            processed_chunks = [self.preprocess_german_text(chunk) for chunk in chunks]
        else:
            processed_chunks = chunks

        # Add instruction if task description is provided
        if task_description:
            # Format with E5 instruction format
            processed_chunks = [
                f"Instruct: {task_description}\nQuery: {chunk}"
                for chunk in processed_chunks
            ]

        # Generate embeddings in batches
        all_embeddings = []

        with torch.no_grad():
            for i in tqdm(range(0, len(processed_chunks), self.batch_size),
                          desc="Generating embeddings"):
                batch_chunks = processed_chunks[i:i + self.batch_size]

                # Tokenize the batch
                batch_dict = self.tokenizer(
                    batch_chunks,
                    max_length=self.max_length,
                    padding=True,
                    truncation=True,
                    return_tensors="pt"
                ).to(self.device)

                # Get model outputs
                outputs = self.model(**batch_dict)

                # Pool embeddings
                embeddings = self.average_pool(
                    outputs.last_hidden_state,
                    batch_dict['attention_mask']
                )

                # Normalize embeddings
                embeddings = functional.normalize(embeddings, p=2, dim=1)

                # Move to CPU and convert to numpy
                all_embeddings.append(embeddings.cpu().numpy())

        # Concatenate all batches
        return numpy.vstack(all_embeddings)

    def select_diverse_chunks(
            self, chunks: list[str], n: int = 5,
            task_description: str = "Select diverse and representative text chunks", random_state: int = 42
    ) -> list[str]:
        """
        Select diverse and important chunks using embedding-based clustering.

        Args:
            chunks: List of text chunks
            n: Number of chunks to select
            task_description: Task description for E5 model
            random_state: Random seed for KMeans

        Returns:
            List of selected chunks
        """
        if n < 1:
            return list()

        if n >= len(chunks):
            return chunks.copy()

        # Generate embeddings with task description
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        embeddings = self.embed_chunks(chunks, task_description)

        # Determine number of clusters
        num_clusters = min(n, len(chunks))

        # Perform KMeans clustering
        logger.info(f"Clustering into {num_clusters} clusters")
        kmeans = KMeans(
            n_clusters=num_clusters,
            random_state=random_state,
            n_init=10,
        ).fit(embeddings)

        labels = kmeans.labels_
        centers = kmeans.cluster_centers_

        # Find chunks closest to each centroid
        selected_indices = list()
        for j in range(num_clusters):
            # Get indices of chunks in this cluster
            cluster_indices = numpy.where(labels == j)[0]

            if len(cluster_indices) >= 1:
                # Find chunk closest to centroid
                centroid = centers[j]
                # Calculate L2 distances
                distances = numpy.linalg.norm(embeddings[cluster_indices] - centroid, axis=1)

                # Select chunk closest to centroid
                closest_idx = cluster_indices[numpy.argmin(distances)]
                selected_indices.append(int(closest_idx))

        return [chunks[j] for j in selected_indices]

    def select_with_importance(
            self, chunks: list[str], n: int = 5, importance_weight: float = 0.3,
            task_description: str = "Select important and diverse text chunks", random_state: int = 42
    ) -> list[str]:
        """
        Select diverse chunks while considering importance.

        This variant uses a combined approach: clusters based on embeddings,
        but also considers chunk "importance" based on similarity to all other chunks.

        Args:
            chunks: List of text chunks
            n: Number of chunks to select
            importance_weight: Weight given to importance vs. centrality (0-1)
            task_description: Task description for E5 model
            random_state: Random seed for reproducibility

        Returns:
            List of selected chunks
        """
        if 0 >= n:
            return list()

        if n >= len(chunks):
            return chunks.copy()

        # Generate embeddings
        embeddings = self.embed_chunks(chunks, task_description)

        # Calculate similarity matrix (cosine similarity)
        sim_matrix = numpy.dot(embeddings, embeddings.T)

        # Calculate importance as average similarity to all other chunks
        importance_scores = numpy.mean(sim_matrix, axis=1)

        # Determine number of clusters
        num_clusters = min(n, len(chunks))

        # Perform KMeans clustering
        kmeans = KMeans(n_clusters=num_clusters, random_state=random_state).fit(embeddings)
        labels = kmeans.labels_
        centers = kmeans.cluster_centers_

        # Find important chunks in each cluster
        selected_indices = list()
        for j in range(num_clusters):
            # Get indices of chunks in this cluster
            cluster_indices = numpy.where(labels == j)[0]

            if len(cluster_indices) > 0:
                # Calculate distances to centroid
                centroid = centers[j]
                distances = numpy.linalg.norm(embeddings[cluster_indices] - centroid, axis=1)

                # Normalize distances (smaller is better)
                max_dist = numpy.max(distances) if numpy.max(distances) > 0 else 1
                normalized_distances = 1 - (distances / max_dist)

                # Get importance scores for this cluster
                cluster_importance = importance_scores[cluster_indices]

                # Normalize importance
                max_imp = numpy.max(cluster_importance) if numpy.max(cluster_importance) > 0 else 1
                normalized_importance = cluster_importance / max_imp

                # Combined score: weighted sum of centrality and importance
                combined_scores = (1 - importance_weight) * normalized_distances + \
                                  importance_weight * normalized_importance

                # Select chunk with highest combined score
                best_idx = cluster_indices[numpy.argmax(combined_scores)]
                selected_indices.append(int(best_idx))

        return [chunks[j] for j in selected_indices]


# Convenience function for quick usage
def select_diverse_german_chunks(chunks: list[str], n: int = 5) -> list[str]:
    """
    Convenience function to select diverse German chunks using E5 embeddings.

    Args:
        chunks: List of German text chunks
        n: Number of chunks to select

    Returns:
        List of selected chunks
    """
    selector = E5EmbeddingSelector(use_preprocessing=True)
    # v = selector.select_diverse_chunks(chunks, n=n, task_description="Select diverse and representative German text chunks")
    v = selector.select_with_importance(chunks, n=n, task_description="Select diverse and representative German text chunks")
    clear_gpu_memory()
    return v


# Main function for testing
if __name__ == "__main__":
    import time

    # Sample German paragraphs about different topics
    test_chunks = [
        "Die Quantenphysik ist ein faszinierendes Gebiet der modernen Physik. Sie beschreibt die Natur auf atomarer und subatomarer Ebene und weicht stark von unserer klassischen Vorstellung der Realität ab. Phänomene wie Quantenverschränkung und Wellenfunktionen zeigen, dass die Welt auf kleinster Ebene ganz anderen Gesetzen folgt.",
        "Die deutsche Literatur hat eine lange und reiche Tradition. Von Goethe und Schiller über Hesse und Mann bis hin zu zeitgenössischen Autoren wie Herta Müller oder Daniel Kehlmann spiegelt sie die kulturelle und gesellschaftliche Entwicklung des Landes wider. Besonders die Romantik und der Expressionismus waren prägende Epochen.",
        "Künstliche Intelligenz revolutioniert zahlreiche Wirtschaftsbereiche. Machine Learning und neuronale Netze ermöglichen Anwendungen, die noch vor wenigen Jahren undenkbar waren. Von der automatisierten Bilderkennung bis zur Sprachverarbeitung verändern diese Technologien unseren Alltag nachhaltig.",
        "Der Klimawandel stellt eine der größten globalen Herausforderungen dar. Die Erderwärmung führt zu schmelzenden Polkappen, steigendem Meeresspiegel und häufigeren Extremwetterereignissen. Um diese Entwicklung einzudämmen, sind internationale Kooperation und nachhaltige Energiekonzepte unverzichtbar.",
        "Die Europäische Union steht vor bedeutenden Herausforderungen. Brexit, Migrationsfragen und wirtschaftliche Ungleichgewichte stellen den Zusammenhalt auf die Probe. Dennoch bleibt die EU ein einzigartiges Friedensprojekt und ein wichtiger Wirtschaftsraum mit globaler Bedeutung.",
        "Die deutsche Küche ist regional sehr vielfältig. Von bayerischen Spezialitäten wie Weißwurst und Brezeln über rheinische Sauerbraten bis zu norddeutschen Fischgerichten bietet sie eine große kulinarische Bandbreite. Traditionelle Gerichte werden heute oft modern interpretiert und international beeinflusst.",
        "Die Digitalisierung des Bildungssystems schreitet voran. Online-Lernplattformen, digitale Unterrichtsmaterialien und virtuelle Klassenzimmer verändern die Art, wie Wissen vermittelt wird. Die Corona-Pandemie hat diesen Prozess zusätzlich beschleunigt und neue Herausforderungen offenbart.",
        "Das deutsche Gesundheitssystem gilt international als vorbildlich. Die Kombination aus gesetzlicher und privater Krankenversicherung gewährleistet eine flächendeckende Versorgung. Dennoch stehen Herausforderungen wie der Fachkräftemangel und steigende Kosten im Raum.",
        "Die Philosophie des Existenzialismus betont die individuelle Freiheit und Verantwortung. Denker wie Jean-Paul Sartre und Albert Camus entwickelten ihre Ideen im Kontext der Nachkriegszeit. Der Grundgedanke, dass die Existenz der Essenz vorausgeht, prägt bis heute unser Verständnis von Individualität.",
        "Die Raumfahrt hat in den letzten Jahren neue Dynamik gewonnen. Private Unternehmen wie SpaceX und Blue Origin ergänzen staatliche Programme. Mars-Missionen, Weltraumtourismus und die Nutzung von Weltraumressourcen könnten die nächsten großen Schritte der Menschheit im All sein."
    ]

    print("E5 Embedding-basierter Clustering-Test für deutsche Texte\n")
    print(f"Originaltexte: {len(test_chunks)} Absätze\n")

    # Test different configurations
    test_configs = [
        {"name": "Standard", "preprocess": False, "importance": False, "n": 3},
        {"name": "Mit Preprocessing", "preprocess": True, "importance": False, "n": 3},
        {"name": "Mit Importance-Gewichtung", "preprocess": True, "importance": True, "n": 3},
        {"name": "Mehr Chunks auswählen", "preprocess": True, "importance": True, "n": 5}
    ]

    for config in test_configs:
        print(f"\n\nTest: {config['name']}")
        print(f"Parameter: n={config['n']}, preprocessing={config['preprocess']}, importance={config['importance']}")

        # Create selector with optimized settings
        selector = E5EmbeddingSelector(
            batch_size=4,  # Small batch size for demonstration
            use_preprocessing=config["preprocess"]
        )

        # Measure execution time
        start_time = time.time()

        task = "Select diverse and representative German text chunks"

        # Use appropriate selection method
        if config["importance"]:
            selected = selector.select_with_importance(
                test_chunks,
                n=config["n"],
                task_description=task
            )
        else:
            selected = selector.select_diverse_chunks(
                test_chunks,
                n=config["n"],
                task_description=task
            )

        end_time = time.time()

        # Print results
        print(f"\nAusgewählte Absätze ({len(selected)}):")
        for i, chunk in enumerate(selected, 1):
            print(f"{i}. {chunk[:100]}...")

        print(f"\nVerarbeitungszeit: {(end_time - start_time):.4f} Sekunden")