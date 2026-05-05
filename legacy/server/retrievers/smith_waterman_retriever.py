import numpy
from enum import IntEnum
import spacy
from spacy.lang.de.stop_words import STOP_WORDS
import logging
from tqdm import tqdm
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Scoring constants for Smith-Waterman algorithm
class Score(IntEnum):
    MATCH = 3       # Higher match score for text comparison
    MISMATCH = -2   # Penalty for mismatches
    GAP = -1        # Penalty for gaps

# Traceback directions
class Trace(IntEnum):
    STOP = 0
    LEFT = 1        # Horizontal gap (insertion)
    UP = 2          # Vertical gap (deletion)
    DIAGONAL = 3    # Match/mismatch

class SmithWatermanRetriever:
    """Class for retrieving semantically similar chunks using Smith-Waterman local alignment."""
    
    def __init__(self, 
                 use_preprocessing: bool = True,
                 match_score: int = Score.MATCH,
                 mismatch_score: int = Score.MISMATCH,
                 gap_score: int = Score.GAP,
                 token_level: bool = False,
                 cache_preprocessed: bool = True):
        """
        Initialize the Smith-Waterman semantic retriever.
        
        Args:
            use_preprocessing: Whether to use spaCy preprocessing
            match_score: Score for matching characters/tokens
            mismatch_score: Penalty for mismatched characters/tokens
            gap_score: Penalty for gaps (insertions/deletions)
            token_level: Whether to compare at token level (True) or character level (False)
            cache_preprocessed: Whether to cache preprocessed texts
        """
        self.use_preprocessing = use_preprocessing
        self.match_score = match_score
        self.mismatch_score = mismatch_score
        self.gap_score = gap_score
        self.token_level = token_level
        self.cache_preprocessed = cache_preprocessed
        
        # Cache for preprocessed documents
        self._preprocessed_cache = {}
        
        # Initialize spaCy for preprocessing if needed
        if self.use_preprocessing:
            try:
                self.nlp = spacy.load("de_core_news_lg", disable=["parser", "ner"])
            except IOError:
                logger.warning("German spaCy model not found. Running without preprocessing.")
                self.use_preprocessing = False
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text to improve comparison quality.
        
        Args:
            text: The input text to preprocess
            
        Returns:
            Preprocessed text
        """
        # Check cache first if enabled
        if self.cache_preprocessed and text in self._preprocessed_cache:
            return self._preprocessed_cache[text]
        
        if not self.use_preprocessing:
            # Simple preprocessing without spaCy
            processed_text = text.lower()
            # Remove special characters but keep letters and spaces
            processed_text = re.sub(r'[^\w\s]', ' ', processed_text)
            # Remove extra whitespace
            processed_text = re.sub(r'\s+', ' ', processed_text).strip()
        else:
            # Use spaCy for more advanced preprocessing
            doc = self.nlp(text)
            # Remove stopwords and punctuation
            tokens = [token.text.lower() for token in doc 
                     if not token.is_stop and not token.is_punct]
            processed_text = " ".join(tokens)
        
        # Cache the result if enabled
        if self.cache_preprocessed:
            self._preprocessed_cache[text] = processed_text
            
        return processed_text
    
    def prepare_for_comparison(self, text: str) -> str | list[str]:
        """
        Prepare text for Smith-Waterman comparison.
        
        Args:
            text: The input text
            
        Returns:
            Processed text as string (character level) or list of tokens (token level)
        """
        processed = self.preprocess_text(text)
        
        if self.token_level:
            # Split into tokens for token-level comparison
            return processed.split()
        else:
            # Keep as string for character-level comparison
            return processed
    
    def smith_waterman(self, seq1: str | list[str], seq2: str | list[str]) -> tuple[float, str, str]:
        """
        Perform Smith-Waterman local alignment between two sequences.
        
        Args:
            seq1: First sequence (string or token list)
            seq2: Second sequence (string or token list)
            
        Returns:
            Tuple of (similarity_score, aligned_seq1, aligned_seq2)
        """
        # Generate the scoring matrix
        row = len(seq1) + 1
        col = len(seq2) + 1
        matrix = numpy.zeros(shape=(row, col), dtype=numpy.int32)
        tracing_matrix = numpy.zeros(shape=(row, col), dtype=numpy.int32)
        
        # Initialize variables to find the highest scoring cell
        max_score = 0
        max_index = (0, 0)
        
        # Calculate scores for all cells in the matrix
        for i in range(1, row):
            for j in range(1, col):
                # Calculate the diagonal score (match/mismatch)
                match_value = self.match_score if seq1[i - 1] == seq2[j - 1] else self.mismatch_score
                diagonal_score = matrix[i - 1, j - 1] + match_value
                
                # Calculate gap scores
                vertical_score = matrix[i - 1, j] + self.gap_score
                horizontal_score = matrix[i, j - 1] + self.gap_score
                
                # Take the highest score (including 0 for local alignment)
                matrix[i, j] = max(0, diagonal_score, vertical_score, horizontal_score)
                
                # Track the source of the cell's value
                if matrix[i, j] == 0: 
                    tracing_matrix[i, j] = Trace.STOP
                elif matrix[i, j] == horizontal_score: 
                    tracing_matrix[i, j] = Trace.LEFT
                elif matrix[i, j] == vertical_score: 
                    tracing_matrix[i, j] = Trace.UP
                elif matrix[i, j] == diagonal_score: 
                    tracing_matrix[i, j] = Trace.DIAGONAL 
                
                # Track the cell with the maximum score
                if matrix[i, j] > max_score:
                    max_index = (i, j)
                    max_score = matrix[i, j]
        
        # If no alignments found, return early
        if max_score == 0:
            return 0.0, "", ""
        
        # Initialize variables for traceback
        aligned_seq1 = ""
        aligned_seq2 = ""
        current_aligned_seq1 = ""
        current_aligned_seq2 = ""
        (max_i, max_j) = max_index
        
        # Traceback to compute the local alignment
        while tracing_matrix[max_i, max_j] != Trace.STOP:
            if tracing_matrix[max_i, max_j] == Trace.DIAGONAL:
                current_aligned_seq1 = str(seq1[max_i - 1])
                current_aligned_seq2 = str(seq2[max_j - 1])
                max_i = max_i - 1
                max_j = max_j - 1
            elif tracing_matrix[max_i, max_j] == Trace.UP:
                current_aligned_seq1 = str(seq1[max_i - 1])
                current_aligned_seq2 = '-'
                max_i = max_i - 1    
            elif tracing_matrix[max_i, max_j] == Trace.LEFT:
                current_aligned_seq1 = '-'
                current_aligned_seq2 = str(seq2[max_j - 1])
                max_j = max_j - 1
                
            aligned_seq1 = aligned_seq1 + current_aligned_seq1
            aligned_seq2 = aligned_seq2 + current_aligned_seq2
        
        # Reverse the aligned sequences
        aligned_seq1 = aligned_seq1[::-1]
        aligned_seq2 = aligned_seq2[::-1]
        
        # Calculate a normalized similarity score (0-1 range)
        # Max possible score would be match_score * length of shorter sequence
        shorter_len = min(len(seq1), len(seq2))
        perfect_score = self.match_score * shorter_len
        normalized_score = max_score / perfect_score if perfect_score > 0 else 0
        
        return normalized_score, aligned_seq1, aligned_seq2
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text chunks using Smith-Waterman.
        
        Args:
            text1: First text chunk
            text2: Second text chunk
            
        Returns:
            Similarity score (0-1 range)
        """
        # Prepare sequences for comparison
        seq1 = self.prepare_for_comparison(text1)
        seq2 = self.prepare_for_comparison(text2)
        
        # Perform Smith-Waterman alignment
        score, _, _ = self.smith_waterman(seq1, seq2)
        
        return score
    
    def calculate_similarity_matrix(self, chunks: list[str]) -> numpy.ndarray:
        """
        Calculate similarity matrix for a list of chunks.
        
        Args:
            chunks: List of text chunks
            
        Returns:
            Similarity matrix (n x n array)
        """
        n = len(chunks)
        similarity_matrix = numpy.zeros((n, n))
        
        # Prepare all sequences first
        prepared_chunks = [self.prepare_for_comparison(chunk) for chunk in chunks]
        
        # Calculate similarities (upper triangular matrix)
        for i in tqdm(range(n), desc="Calculating similarity matrix"):
            # Diagonal is perfect similarity
            similarity_matrix[i, i] = 1.0
            
            # Calculate upper triangular
            for j in range(i + 1, n):
                score, _, _ = self.smith_waterman(prepared_chunks[i], prepared_chunks[j])
                similarity_matrix[i, j] = score
                similarity_matrix[j, i] = score  # Matrix is symmetric
        
        return similarity_matrix
    
    def retrieve_similar_chunks(self, 
                               query_chunk: str, 
                               document_chunks: list[str],
                               n: int = 5,
                               return_scores: bool = False) -> list[str] | list[tuple[str, float]]:
        """
        Retrieve the n most similar chunks to the query from the document collection.
        
        Args:
            query_chunk: The query text chunk
            document_chunks: Collection of text chunks to search in
            n: Number of chunks to retrieve
            return_scores: Whether to return similarity scores
            
        Returns:
            List of similar chunks or list of (chunk, score) tuples if return_scores=True
        """
        # Handle edge cases
        if not document_chunks:
            return [] if not return_scores else []
        
        n = min(n, len(document_chunks))
        
        # Prepare query sequence
        query_seq = self.prepare_for_comparison(query_chunk)
        
        # Calculate similarities to all document chunks
        scores = []
        for i, doc_chunk in enumerate(tqdm(document_chunks, desc="Calculating similarities")):
            doc_seq = self.prepare_for_comparison(doc_chunk)
            sim_score, _, _ = self.smith_waterman(query_seq, doc_seq)
            scores.append((i, sim_score))
        
        # Sort by similarity score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top-n results
        top_results = scores[:n]
        
        # Return results
        if return_scores:
            return [(document_chunks[idx], each_score) for idx, each_score in top_results]
        else:
            return [document_chunks[idx] for idx, each_score in top_results]
    
    def retrieve_similar_by_chunk_id(self,
                                    query_chunk_id: int,
                                    document_chunks: list[str],
                                    n: int = 5,
                                    exclude_query: bool = True,
                                    return_scores: bool = False) -> list[str] | list[tuple[str, float]]:
        """
        Retrieve the n most similar chunks to the specified chunk from the collection.
        
        Args:
            query_chunk_id: Index of the query chunk in the document_chunks list
            document_chunks: Collection of text chunks 
            n: Number of chunks to retrieve
            exclude_query: Whether to exclude the query chunk from results
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
                              return_scores: bool = False,
                              use_similarity_matrix: bool = True) -> list[list[str] | list[tuple[str, float]]]:
        """
        Retrieve similar chunks for multiple queries.
        
        Args:
            query_chunks: List of query chunks
            document_chunks: Collection of text chunks to search in
            n: Number of chunks to retrieve for each query
            return_scores: Whether to return similarity scores
            use_similarity_matrix: Whether to precompute full similarity matrix
            
        Returns:
            List of results (one per query)
        """
        if not query_chunks or not document_chunks:
            return []
        
        if use_similarity_matrix and set(query_chunks).issubset(set(document_chunks)):
            # If queries are a subset of documents, use similarity matrix approach
            # First get all chunks in a single list with queries first
            all_chunks = list(query_chunks)
            remaining_docs = [doc for doc in document_chunks if doc not in query_chunks]
            all_chunks.extend(remaining_docs)
            
            # Calculate full similarity matrix
            logger.info("Calculating full similarity matrix")
            similarity_matrix = self.calculate_similarity_matrix(all_chunks)
            
            results = []
            for i, query in enumerate(query_chunks):
                # Get similarities from this query to all documents
                similarities = [(j, similarity_matrix[i, j]) 
                                for j in range(len(all_chunks))]
                
                # Sort by similarity (descending)
                similarities.sort(key=lambda x: x[1], reverse=True)
                
                # Exclude self if needed
                if i < len(similarities) and similarities[0][0] == i:
                    similarities = similarities[1:]
                
                # Get top n results
                top_n = similarities[:n]
                
                if return_scores:
                    query_results = [(all_chunks[idx], score) for idx, score in top_n]
                else:
                    query_results = [all_chunks[idx] for idx, score in top_n]
                    
                results.append(query_results)
                
            return results
        else:
            # Individual query approach
            logger.info("Processing queries individually")
            return [self.retrieve_similar_chunks(
                query, document_chunks, n=n, return_scores=return_scores
            ) for query in tqdm(query_chunks, desc="Processing queries")]
    
    def find_semantic_clusters(self,
                              document_chunks: list[str],
                              similarity_threshold: float = 0.7,
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
        
        # Calculate similarity matrix
        logger.info("Calculating similarity matrix for clustering")
        similarity_matrix = self.calculate_similarity_matrix(document_chunks)
        
        # Find clusters using a simple greedy approach
        remaining_indices = set(range(len(document_chunks)))
        clusters = []
        
        while remaining_indices:
            # Start a new cluster with the first remaining index
            seed_idx = next(iter(remaining_indices))
            cluster = {seed_idx}
            remaining_indices.remove(seed_idx)
            
            # Find all chunks that are similar to the seed
            similar_indices = {
                i for i in remaining_indices 
                if similarity_matrix[seed_idx, i] >= similarity_threshold
            }
            
            # Add similar chunks to the cluster
            cluster.update(similar_indices)
            remaining_indices -= similar_indices
            
            # Only keep clusters that meet the minimum size
            if len(cluster) >= min_cluster_size:
                clusters.append(sorted(list(cluster)))
        
        return clusters
    
    def get_alignment_details(self, 
                             query_chunk: str, 
                             document_chunk: str) -> dict[str, float | str | int]:
        """
        Get detailed alignment information between two chunks.
        
        Args:
            query_chunk: The query text chunk
            document_chunk: The document text chunk
            
        Returns:
            Dictionary with alignment details
        """
        # Prepare sequences
        query_seq = self.prepare_for_comparison(query_chunk)
        doc_seq = self.prepare_for_comparison(document_chunk)
        
        # Get alignment
        score, aligned_query, aligned_doc = self.smith_waterman(query_seq, doc_seq)
        
        # Count matches, mismatches, and gaps
        matches = 0
        mismatches = 0
        gaps = 0
        
        for q, d in zip(aligned_query, aligned_doc):
            if q == d:
                matches += 1
            elif q == '-' or d == '-':
                gaps += 1
            else:
                mismatches += 1
                
        return {
            "similarity_score": score,
            "alignment_length": len(aligned_query),
            "matches": matches,
            "mismatches": mismatches,
            "gaps": gaps,
            "aligned_query": aligned_query,
            "aligned_document": aligned_doc
        }


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
    retriever = SmithWatermanRetriever(use_preprocessing=True, token_level=False)
    return retriever.retrieve_similar_chunks(query_chunk, document_chunks, n=n)


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
    retriever = SmithWatermanRetriever(use_preprocessing=True, token_level=False)
    return retriever.retrieve_similar_chunks(query_chunk, document_chunks, n=n, return_scores=True)


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
    
    print("Smith-Waterman Semantic Retrieval Test für deutsche Texte\n")
    print(f"Dokumentsammlung: {len(combined_chunks)} Absätze\n")
    
    # Test different configurations
    test_configs = [
        {"name": "Token-Level mit Preprocessing", "token": True, "preproc": True},
        {"name": "Token-Level ohne Preprocessing", "token": True, "preproc": False},
        {"name": "Zeichen-Level mit Preprocessing", "token": False, "preproc": True}
    ]
    
    for config in test_configs:
        print(f"\n\n=== Test: {config['name']} ===")
        
        # Initialize retriever with this configuration
        retriever = SmithWatermanRetriever(
            use_preprocessing=config["preproc"],
            token_level=config["token"],
            match_score=3,
            mismatch_score=-2,
            gap_score=-1
        )
        
        # Test basic similarity retrieval
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
        
        # Test alignment details
        if i == 1:  # Get details for the top result only
            print("\nAlignment-Details für das beste Ergebnis:")
            details = retriever.get_alignment_details(query, results[0][0])
            print(f"Similarity Score: {details['similarity_score']:.4f}")
            print(f"Alignment Length: {details['alignment_length']}")
            print(f"Matches: {details['matches']}")
            print(f"Mismatches: {details['mismatches']}")
            print(f"Gaps: {details['gaps']}")
            
            # If results aren't too long, show the actual alignment
            if details['alignment_length'] < 50:
                print(f"Query Alignment: {details['aligned_query']}")
                print(f"Doc Alignment: {details['aligned_document']}")
