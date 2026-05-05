import numpy
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel
import spacy
from spacy.lang.de.stop_words import STOP_WORDS
import logging
from tqdm import tqdm
import heapq

from server.utils.gpu_stuff import clear_gpu_memory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class E5SemanticRetriever:
    """Class for retrieving semantically similar chunks using E5 embeddings."""
    
    def __init__(self, 
                 model_name: str = 'intfloat/multilingual-e5-large-instruct',
                 batch_size: int = 8,
                 max_length: int = 512,
                 use_preprocessing: bool = True,
                 cache_embeddings: bool = True,
                 device: str | None = None):
        """
        Initialize the semantic retriever using E5 model.
        
        Args:
            model_name: Name of the E5 model
            batch_size: Batch size for embedding generation
            max_length: Maximum sequence length for tokenization
            use_preprocessing: Whether to use spaCy preprocessing
            cache_embeddings: Whether to cache embeddings for repeated queries
            device: Device to use ('cpu', 'cuda', or None for auto-detection)
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.max_length = max_length
        self.use_preprocessing = use_preprocessing
        self.cache_embeddings = cache_embeddings
        
        # Cache for document embeddings
        self._document_embeddings = None
        self._cached_documents = None
        
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
    
    def format_query(self, query: str, task_description: str) -> str:
        """
        Format the query with E5 instruction format.
        
        Args:
            query: The query text
            task_description: Task description for the instruction
            
        Returns:
            Formatted query
        """
        return f"Instruct: {task_description}\nQuery: {query}"
    
    def embed_chunks(self, 
                     chunks: list[str],
                     task_description: str | None = None,
                     is_query: bool = False) -> numpy.ndarray:
        """
        Generate embeddings for text chunks using the E5 model.
        
        Args:
            chunks: List of text chunks to embed
            task_description: Optional task description for instruction
            is_query: Whether the chunks are queries (for instruction formatting)
            
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
        
        # Add instruction if task description is provided and chunks are queries
        if task_description and is_query:
            # Format with E5 instruction format
            processed_chunks = [
                self.format_query(chunk, task_description) 
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
                embeddings = F.normalize(embeddings, p=2, dim=1)
                
                # Move to CPU and convert to numpy
                all_embeddings.append(embeddings.cpu().numpy())
        
        # Concatenate all batches
        return numpy.vstack(all_embeddings)
    
    def embed_collection(self, 
                         chunks: list[str],
                         force_recompute: bool = False) -> numpy.ndarray:
        """
        Embed a collection of chunks, with optional caching.
        
        Args:
            chunks: List of text chunks
            force_recompute: Whether to force recomputation of embeddings
            
        Returns:
            NumPy array of embeddings
        """
        # Check if we can use cached embeddings
        if (self._document_embeddings is not None and 
            self._cached_documents == chunks and 
            not force_recompute):
            logger.info("Using cached document embeddings")
            return self._document_embeddings
        
        # Generate new embeddings
        logger.info(f"Embedding {len(chunks)} documents")
        embeddings = self.embed_chunks(chunks)
        
        # Cache if enabled
        if self.cache_embeddings:
            self._document_embeddings = embeddings
            self._cached_documents = chunks.copy()
        
        return embeddings
    
    def retrieve_similar_chunks(self, 
                               query_chunk: str, 
                               document_chunks: list[str],
                               n: int = 5,
                               task_description: str = "Find text passages similar to this query",
                               return_scores: bool = False,
                               force_recompute: bool = False) -> list[str] | list[tuple[str, float]]:
        """
        Retrieve the n most similar chunks to the query from the document collection.
        
        Args:
            query_chunk: The query text chunk
            document_chunks: Collection of text chunks to search in
            n: Number of chunks to retrieve
            task_description: Task description for embedding instruction
            return_scores: Whether to return similarity scores
            force_recompute: Whether to force recomputation of document embeddings
            
        Returns:
            List of similar chunks or list of (chunk, score) tuples if return_scores=True
        """
        # Handle edge cases
        if not document_chunks:
            return [] if not return_scores else []
        
        n = min(n, len(document_chunks))
        
        # Embed query
        query_embedding = self.embed_chunks(
            [query_chunk], 
            task_description=task_description,
            is_query=True
        )
        
        # Embed documents or use cached embeddings
        doc_embeddings = self.embed_collection(document_chunks, force_recompute)
        
        # Calculate cosine similarities
        similarities = numpy.dot(query_embedding, doc_embeddings.T)[0]
        
        # Get top-n indices
        if n == len(document_chunks):
            # If we want all documents, just sort all indices
            top_indices = numpy.argsort(similarities)[::-1]
        else:
            # Use partial sort for efficiency when n < len(document_chunks)
            top_indices = numpy.argpartition(similarities, -n)[-n:]
            # Sort the top n by similarity
            top_indices = top_indices[numpy.argsort(similarities[top_indices])[::-1]]
        
        # Return results
        if return_scores:
            return [(document_chunks[i], float(similarities[i])) for i in top_indices]
        else:
            return [document_chunks[i] for i in top_indices]
    
    def retrieve_similar_by_chunk_id(self,
                                    query_chunk_id: int,
                                    document_chunks: list[str],
                                    n: int = 5,
                                    exclude_query: bool = True,
                                    task_description: str = "Find text passages similar to this query",
                                    return_scores: bool = False) -> list[str] | list[tuple[str, float]]:
        """
        Retrieve the n most similar chunks to the specified chunk from the collection.
        
        Args:
            query_chunk_id: Index of the query chunk in the document_chunks list
            document_chunks: Collection of text chunks 
            n: Number of chunks to retrieve
            exclude_query: Whether to exclude the query chunk from results
            task_description: Task description for embedding instruction
            return_scores: Whether to return similarity scores
            
        Returns:
            List of similar chunks or list of (chunk, score) tuples if return_scores=True
        """
        if query_chunk_id < 0 or query_chunk_id >= len(document_chunks):
            raise ValueError(f"Query chunk ID {query_chunk_id} is out of range for document_chunks of length {len(document_chunks)}")
        
        query_chunk = document_chunks[query_chunk_id]
        
        # If we need to exclude the query, we need to request one more result
        actual_n = n + 1 if exclude_query else n
        actual_n = min(actual_n, len(document_chunks))
        
        # Get similar chunks
        results = self.retrieve_similar_chunks(
            query_chunk,
            document_chunks,
            n=actual_n,
            task_description=task_description,
            return_scores=return_scores
        )
        
        # Filter out the query if needed
        if exclude_query:
            if return_scores:
                results = [(chunk, score) for chunk, score in results 
                          if chunk != query_chunk][:n]
            else:
                results = [chunk for chunk in results 
                          if chunk != query_chunk][:n]
        
        return results
    
    def batch_retrieve_similar(self,
                              query_chunks: list[str],
                              document_chunks: list[str],
                              n: int = 5,
                              task_description: str = "Find text passages similar to this query",
                              return_scores: bool = False) -> list[list[str] | list[tuple[str, float]]]:
        """
        Retrieve similar chunks for multiple queries.
        
        Args:
            query_chunks: List of query chunks
            document_chunks: Collection of text chunks to search in
            n: Number of chunks to retrieve for each query
            task_description: Task description for embedding instruction
            return_scores: Whether to return similarity scores
            
        Returns:
            List of results (one per query)
        """
        if not query_chunks or not document_chunks:
            return []
        
        # Embed all queries
        query_embeddings = self.embed_chunks(
            query_chunks,
            task_description=task_description,
            is_query=True
        )
        
        # Embed documents or use cached embeddings
        doc_embeddings = self.embed_collection(document_chunks)
        
        # Calculate all similarities at once (efficient matrix multiplication)
        all_similarities = numpy.dot(query_embeddings, doc_embeddings.T)
        
        results = []
        for i, similarities in enumerate(all_similarities):
            if n == len(document_chunks):
                # If we want all documents, just sort all indices
                top_indices = numpy.argsort(similarities)[::-1][:n]
            else:
                # Use partial sort for efficiency when n < len(document_chunks)
                top_indices = numpy.argpartition(similarities, -n)[-n:]
                # Sort the top n by similarity
                top_indices = top_indices[numpy.argsort(similarities[top_indices])[::-1]]
            
            # Add to results
            if return_scores:
                results.append([(document_chunks[j], float(similarities[j])) for j in top_indices])
            else:
                results.append([document_chunks[j] for j in top_indices])
        
        return results
    
    def find_semantic_clusters(self,
                              document_chunks: list[str],
                              similarity_threshold: float = 0.75,
                              min_cluster_size: int = 2) -> list[list[int]]:
        """
        Find clusters of semantically similar chunks.
        
        Args:
            document_chunks: Collection of text chunks
            similarity_threshold: Minimum similarity to consider chunks as related
            min_cluster_size: Minimum size for a valid cluster
            
        Returns:
            List of clusters, where each cluster is a list of chunk indices
        """
        if not document_chunks:
            return []
        
        # Embed documents
        doc_embeddings = self.embed_collection(document_chunks)
        
        # Calculate full similarity matrix
        similarity_matrix = numpy.dot(doc_embeddings, doc_embeddings.T)
        
        # Find clusters using a simple greedy approach
        remaining_indices = set(range(len(document_chunks)))
        clusters = []
        
        while remaining_indices:
            # Start a new cluster with the first remaining index
            seed_idx = next(iter(remaining_indices))
            cluster = {seed_idx}
            remaining_indices.remove(seed_idx)
            
            # Find all nodes that are similar to the seed
            similar_indices = {
                i for i in remaining_indices 
                if similarity_matrix[seed_idx, i] >= similarity_threshold
            }
            
            # Add similar nodes to the cluster
            cluster.update(similar_indices)
            remaining_indices -= similar_indices
            
            # Only keep clusters that meet the minimum size
            if len(cluster) >= min_cluster_size:
                clusters.append(sorted(list(cluster)))
        
        return clusters


# Convenience functions for quick usage
def retrieve_similar_chunks(query_chunk: str, document_chunks: list[str], n: int = 5) -> list[str]:
    """
    Retrieve n most similar chunks to the query from document_chunks.
    
    Args:
        query_chunk: Query text
        document_chunks: Collection of text chunks to search
        n: Number of chunks to retrieve
        
    Returns:
        List of similar chunks
    """

    retriever = E5SemanticRetriever(use_preprocessing=True)
    v = retriever.retrieve_similar_chunks(
        query_chunk,
        document_chunks,
        n=n,
        task_description="Find text passages that are semantically similar to this query"
    )

    clear_gpu_memory()

    return v

def retrieve_similar_with_scores(query_chunk: str, document_chunks: list[str], n: int = 5) -> list[tuple[str, float]]:
    """
    Retrieve n most similar chunks with similarity scores.
    
    Args:
        query_chunk: Query text
        document_chunks: Collection of text chunks to search
        n: Number of chunks to retrieve
        
    Returns:
        List of (chunk, similarity_score) tuples
    """
    retriever = E5SemanticRetriever(use_preprocessing=True)
    v = retriever.retrieve_similar_chunks(
        query_chunk,
        document_chunks,
        n=n,
        task_description="Find text passages that are semantically similar to this query",
        return_scores=True
    )
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
    
    # Additional paragraphs with similar themes to test retrieval
    additional_chunks = [
        "Die Teilchenphysik untersucht die kleinsten Bausteine unseres Universums. Das Standardmodell der Teilchenphysik beschreibt Quarks, Leptonen und die fundamentalen Kräfte. Experimente wie am CERN helfen uns, diese Teilchen und ihre Wechselwirkungen besser zu verstehen.",
        "Moderne deutsche Autoren wie Juli Zeh, Ferdinand von Schirach und Jenny Erpenbeck prägen die zeitgenössische Literaturszene. Ihre Werke reflektieren gesellschaftliche Entwicklungen und ethische Fragestellungen der Gegenwart. Die deutsche Literatur bleibt ein wichtiger Bestandteil der Weltliteratur.",
        "Deep Learning, ein Teilbereich der künstlichen Intelligenz, ermöglicht erstaunliche Fortschritte in der Mustererkennung. Convolutional Neural Networks revolutionieren die Bildverarbeitung, während Transformer-Modelle die natürliche Sprachverarbeitung dominieren. Diese Technologien finden Anwendung in autonomen Fahrzeugen, medizinischer Diagnostik und vielen anderen Bereichen."
    ]
    
    combined_chunks = test_chunks + additional_chunks
    
    print("E5 Semantic Retrieval Test für deutsche Texte\n")
    print(f"Dokumentsammlung: {len(combined_chunks)} Absätze\n")
    
    # Initialize retriever
    retriever = E5SemanticRetriever(batch_size=4)
    
    # Test 1: Basic similarity retrieval
    print("\n=== Test 1: Ähnlichkeitssuche ===")
    query = "Moderne Physik und Quantenmechanik"
    print(f"Query: \"{query}\"")
    
    start_time = time.time()
    results = retriever.retrieve_similar_chunks(
        query, 
        combined_chunks, 
        n=3, 
        return_scores=True
    )
    end_time = time.time()
    
    print("\nErgebnisse:")
    for i, (chunk, score) in enumerate(results, 1):
        print(f"{i}. [Score: {score:.4f}] {chunk[:100]}...")
    print(f"\nVerarbeitungszeit: {(end_time - start_time):.4f} Sekunden")
    
    # Test 2: Retrieve similar by chunk ID
    print("\n\n=== Test 2: Ähnliche Dokumente zu einem Chunk ===")
    query_id = 2  # Chunk about AI
    print(f"Query (Chunk #{query_id+1}): \"{combined_chunks[query_id][:100]}...\"")
    
    start_time = time.time()
    results = retriever.retrieve_similar_by_chunk_id(
        query_id, 
        combined_chunks, 
        n=3, 
        return_scores=True
    )
    end_time = time.time()
    
    print("\nErgebnisse:")
    for i, (chunk, score) in enumerate(results, 1):
        print(f"{i}. [Score: {score:.4f}] {chunk[:100]}...")
    print(f"\nVerarbeitungszeit: {(end_time - start_time):.4f} Sekunden")
    
    # Test 3: Batch retrieval
    print("\n\n=== Test 3: Batch-Verarbeitung mehrerer Queries ===")
    query_chunks = [
        "Physik und moderne Wissenschaft",
        "Deutsche Kultur und Traditionen",
        "Technologie und digitale Transformation"
    ]
    
    start_time = time.time()
    all_results = retriever.batch_retrieve_similar(
        query_chunks, 
        combined_chunks, 
        n=2, 
        return_scores=True
    )
    end_time = time.time()
    
    for i, (query, results) in enumerate(zip(query_chunks, all_results), 1):
        print(f"\nQuery {i}: \"{query}\"")
        print("Ergebnisse:")
        for j, (chunk, score) in enumerate(results, 1):
            print(f"  {j}. [Score: {score:.4f}] {chunk[:100]}...")
    
    print(f"\nVerarbeitungszeit für {len(query_chunks)} Queries: {(end_time - start_time):.4f} Sekunden")
    
    # Test 4: Find semantic clusters
    print("\n\n=== Test 4: Semantische Cluster finden ===")
    
    start_time = time.time()
    clusters = retriever.find_semantic_clusters(
        combined_chunks, 
        similarity_threshold=0.8, 
        min_cluster_size=2
    )
    end_time = time.time()
    
    print(f"Gefundene Cluster: {len(clusters)}")
    for i, cluster in enumerate(clusters, 1):
        print(f"\nCluster {i} (Größe: {len(cluster)}):")
        for idx in cluster:
            print(f"  - Chunk #{idx+1}: {combined_chunks[idx][:100]}...")
    
    print(f"\nVerarbeitungszeit: {(end_time - start_time):.4f} Sekunden")
