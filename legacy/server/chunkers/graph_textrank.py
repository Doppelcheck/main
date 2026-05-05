import numpy
import networkx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from spacy.lang.de.stop_words import STOP_WORDS
import re
from collections import defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GermanTextRankSelector:
    """Class for selecting diverse and important chunks from German text using TextRank."""
    
    def __init__(self, 
                 use_spacy: bool = True,
                 damping: float = 0.85,
                 min_diff: float = 1e-5,
                 max_iter: int = 50,
                 compound_split: bool = True):
        """
        Initialize the German TextRank-based chunk selector.
        
        Args:
            use_spacy: Whether to use spaCy for preprocessing
            damping: Damping factor for PageRank
            min_diff: Convergence threshold for PageRank
            max_iter: Maximum iterations for PageRank
            compound_split: Whether to split German compound words
        """
        self.use_spacy = use_spacy
        self.damping = damping
        self.min_diff = min_diff
        self.max_iter = max_iter
        self.compound_split = compound_split
        
        # German-specific settings
        self.german_stop_words = STOP_WORDS
        self.german_connectors = {
            "und", "oder", "aber", "denn", "sondern", "beziehungsweise", 
            "sowie", "als", "wie", "dass", "weil", "da", "wenn", "ob",
            "damit", "sodass", "indem", "während", "nachdem", "bevor"
        }
        
        # Load German spaCy model if needed
        if self.use_spacy:
            try:
                # Load with compound splitting if requested
                self.nlp = spacy.load("de_core_news_lg")
                if self.compound_split:
                    # Add compound splitter
                    self.nlp.add_pipe("compound_splitter")
            except IOError:
                logger.warning("German spaCy model not found. Installing with: python -m spacy download de_core_news_lg")
                self.use_spacy = False
            except ValueError:
                logger.warning("Compound splitter not available. Run: pip install spacy-compound-splitter")
                self.compound_split = False
    
    def preprocess_german_text(self, text: str) -> str:
        """
        Preprocess German text for improved semantic analysis.
        
        Args:
            text: The input text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not self.use_spacy:
            # Simple preprocessing without spaCy
            text = text.lower()
            # Remove special characters but keep German umlauts
            text = re.sub(r'[^\wäöüßÄÖÜ\s]', ' ', text)
            words = text.split()
            words = [w for w in words if w not in self.german_stop_words]
            return " ".join(words)
        
        # Using spaCy for better German language processing
        doc = self.nlp(text)
        
        # Process with compound splitting if enabled
        if self.compound_split:
            tokens = []
            for token in doc:
                if not token.is_stop and not token.is_punct and len(token.text) > 2:
                    # Add compound parts if available
                    if token._.compound_parts:
                        tokens.extend(token._.compound_parts)
                    else:
                        tokens.append(token.lemma_)
        else:
            # Standard processing
            tokens = [token.lemma_ for token in doc 
                     if not token.is_stop 
                     and not token.is_punct
                     and len(token.text) > 2]
        
        return " ".join(tokens)
    
    def build_similarity_graph(self, chunks: list[str], preprocess: bool = True) -> tuple[numpy.ndarray, numpy.ndarray]:
        """
        Build a similarity graph for TextRank.
        
        Args:
            chunks: List of text chunks
            preprocess: Whether to preprocess the text
            
        Returns:
            Tuple of (similarity matrix, importance scores)
        """
        # Preprocess texts if requested
        processed_chunks = chunks
        if preprocess:
            processed_chunks = [self.preprocess_german_text(chunk) for chunk in chunks]
        
        # Create TF-IDF vectors with German-specific settings
        tfidf = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),  # Include bigrams for German compound words
            min_df=1,            # Keep even terms that appear once
            max_df=0.9           # Ignore very common terms
        ).fit_transform(processed_chunks)
        
        # Calculate similarity matrix
        sim_matrix = cosine_similarity(tfidf)
        
        # Create graph
        G = networkx.from_numpy_array(sim_matrix)
        
        # Run PageRank to get importance scores
        scores = networkx.pagerank(
            G, 
            alpha=self.damping, 
            max_iter=self.max_iter,
            tol=self.min_diff
        )
        
        # Convert to numpy array
        importance_scores = numpy.array([scores[i] for i in range(len(chunks))])
        
        return sim_matrix, importance_scores
    
    def select_diverse_chunks(self, 
                             chunks: list[str], 
                             n: int = 5, 
                             lambda_param: float = 0.5,
                             preprocess: bool = True) -> list[str]:
        """
        Select diverse and important chunks using TextRank and diversity penalty.
        
        Args:
            chunks: List of text chunks
            n: Number of chunks to select
            lambda_param: Balance between relevance and diversity (0-1)
                          Higher values prioritize relevance
            preprocess: Whether to preprocess the text
            
        Returns:
            List of selected chunks
        """
        if n <= 0:
            return []
        
        if n >= len(chunks):
            return chunks.copy()
        
        # Build similarity graph
        sim_matrix, importance_scores = self.build_similarity_graph(chunks, preprocess)
        
        # Apply MMR for diversity
        selected: list[int] = list()
        selected.append(int(numpy.argmax(importance_scores)))
        
        while len(selected) < n:
            candidate_scores = []
            
            for i in range(len(chunks)):
                if i not in selected:
                    relevance = importance_scores[i]
                    diversity = min([1 - sim_matrix[i, j] for j in selected])
                    mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                    candidate_scores.append((i, mmr_score))
            
            if not candidate_scores:
                break
                
            best_candidate = max(candidate_scores, key=lambda x: x[1])[0]
            selected.append(best_candidate)
        
        return [chunks[i] for i in selected]
    
    def topic_guided_selection(self, 
                             chunks: list[str], 
                             n: int = 5,
                             min_topic_similarity: float = 0.1,
                             preprocess: bool = True) -> list[str]:
        """
        Select diverse chunks using topic-guided selection.
        
        This method identifies implicit topics and ensures coverage.
        
        Args:
            chunks: List of text chunks
            n: Number of chunks to select
            min_topic_similarity: Minimum similarity to consider chunks related
            preprocess: Whether to preprocess the text
            
        Returns:
            List of selected chunks
        """
        if n <= 0:
            return []
        
        if n >= len(chunks):
            return chunks.copy()
        
        # Build similarity graph
        sim_matrix, importance_scores = self.build_similarity_graph(chunks, preprocess)
        
        # Create topic clusters based on similarity
        topic_clusters: dict[int, set[int]] = defaultdict(set)
        visited = set()
        
        # For each chunk, create a topic cluster
        for i in range(len(chunks)):
            if i in visited:
                continue
                
            # Find other chunks similar to this one
            topic_clusters[i].add(i)
            visited.add(i)
            
            for j in range(len(chunks)):
                if j != i and j not in visited and sim_matrix[i, j] >= min_topic_similarity:
                    topic_clusters[i].add(j)
                    visited.add(j)
        
        # Sort topic clusters by size (descending)
        sorted_topics = sorted(topic_clusters.items(), 
                              key=lambda x: (len(x[1]), importance_scores[x[0]]), 
                              reverse=True)
        
        # Select most important chunk from each topic, up to n
        selected = []
        selected_indices = set()
        
        # First, iterate through topics
        for topic_id, cluster in sorted_topics:
            if len(selected) >= n:
                break
                
            # Find most important chunk in this topic that's not already selected
            available_chunks = [i for i in cluster if i not in selected_indices]
            if not available_chunks:
                continue
                
            best_chunk = max(available_chunks, key=lambda i: importance_scores[i])
            selected.append(best_chunk)
            selected_indices.add(best_chunk)
        
        # If we still need more chunks, fill with most important remaining
        if len(selected) < n:
            remaining = [i for i in range(len(chunks)) if i not in selected_indices]
            remaining_sorted = sorted(remaining, key=lambda i: importance_scores[i], reverse=True)
            selected.extend(remaining_sorted[:n-len(selected)])
        
        return [chunks[i] for i in selected]


# Convenience function for quick usage
def select_diverse_german_chunks(chunks: list[str], n: int = 5) -> list[str]:
    """
    Convenience function to select diverse German chunks using TextRank.
    
    Args:
        chunks: List of German text chunks
        n: Number of chunks to select
        
    Returns:
        List of selected chunks
    """
    selector = GermanTextRankSelector(use_spacy=True, compound_split=True)
    return selector.select_diverse_chunks(chunks, n=n, lambda_param=0.6)


# Additional function for topic-based selection
def select_topic_covering_chunks(chunks: list[str], n: int = 5) -> list[str]:
    """
    Select chunks that cover different topics in the document.

    Args:
        chunks: List of German text chunks
        n: Number of chunks to select

    Returns:
        List of selected chunks covering different topics
    """
    selector = GermanTextRankSelector(use_spacy=True)
    return selector.topic_guided_selection(chunks, n=n, min_topic_similarity=0.15)


# Main function for testing
if __name__ == "__main__":
    import time
    from pprint import pprint

    # Sample German paragraphs - news article style
    test_chunks = [
        "In Deutschland werden immer mehr erneuerbare Energien genutzt. Im ersten Halbjahr 2023 stammten bereits 52 Prozent des Stroms aus erneuerbaren Quellen. Besonders Windkraft und Solarenergie verzeichnen starkes Wachstum.",
        "Die Bundesregierung hat ein neues Klimaschutzgesetz verabschiedet. Es sieht vor, dass Deutschland bis 2045 klimaneutral wird. Kritiker bemängeln jedoch, dass konkrete Maßnahmen zur Umsetzung fehlen.",
        "Der Ausbau der Windenergie kommt in einigen Bundesländern nur schleppend voran. Bürgerproteste und komplizierte Genehmigungsverfahren verzögern viele Projekte. Die Regierung plant nun, die Verfahren zu beschleunigen.",
        "Solarenergie erlebt in Deutschland einen Boom. Immer mehr Privatpersonen installieren Photovoltaikanlagen auf ihren Dächern. Auch die Installation von Balkonkraftwerken hat stark zugenommen.",
        "Der Kohleausstieg bleibt ein umstrittenes Thema. Während Umweltverbände einen schnelleren Ausstieg fordern, betonen Wirtschaftsvertreter die Bedeutung der Versorgungssicherheit und warnen vor steigenden Energiepreisen.",
        "Die Elektromobilität gewinnt an Fahrt. Im vergangenen Jahr wurden in Deutschland erstmals mehr als 500.000 Elektroautos zugelassen. Die Ladeinfrastruktur wird kontinuierlich ausgebaut, bleibt aber ein Engpass.",
        "Wasserstoff gilt als Hoffnungsträger für die Energiewende. Die Bundesregierung hat eine nationale Wasserstoffstrategie vorgelegt und fördert Pilotprojekte mit Milliardensummen. Grüner Wasserstoff soll besonders in der Industrie fossile Brennstoffe ersetzen.",
        "Der Gasverbrauch in Deutschland ist im letzten Winter deutlich gesunken. Sowohl Unternehmen als auch Privatpersonen haben Energie eingespart. Experten sehen darin einen wichtigen Beitrag zur Versorgungssicherheit.",
        "Biogas spielt eine wichtige Rolle im Energiemix. Landwirte können durch Biogasanlagen zusätzliche Einnahmen generieren und gleichzeitig zur nachhaltigen Energieversorgung beitragen. Die Vergütung für Biogas wurde kürzlich angepasst.",
        "Energieeffizienz in Gebäuden wird zunehmend wichtiger. Die Sanierungsrate von Altbauten bleibt jedoch hinter den Zielen zurück. Förderprogramme sollen Anreize für energetische Sanierungen schaffen."
    ]

    print("TextRank-basierter Test für deutsche Texte\n")
    print(f"Originaltexte: {len(test_chunks)} Absätze\n")

    # Test different configurations
    test_configs = [
        {"name": "Standard TextRank", "spacy": True, "lambda": 0.5, "n": 3, "method": "diverse"},
        {"name": "Hohe Diversität", "spacy": True, "lambda": 0.3, "n": 3, "method": "diverse"},
        {"name": "Hohe Relevanz", "spacy": True, "lambda": 0.7, "n": 3, "method": "diverse"},
        {"name": "Ohne spaCy", "spacy": False, "lambda": 0.5, "n": 3, "method": "diverse"},
        {"name": "Themenbasierte Auswahl", "spacy": True, "lambda": 0.5, "n": 3, "method": "topic"}
    ]

    for config in test_configs:
        print(f"\n\nTest: {config['name']}")
        print(f"Parameter: λ={config['lambda']}, n={config['n']}, spaCy={config['spacy']}, Methode={config['method']}")

        # Create selector
        selector = GermanTextRankSelector(use_spacy=config["spacy"], compound_split=config["spacy"])

        # Measure execution time
        start_time = time.time()

        if config["method"] == "diverse":
            selected = selector.select_diverse_chunks(
                test_chunks,
                n=config["n"],
                lambda_param=config["lambda"]
            )
        else:
            selected = selector.topic_guided_selection(
                test_chunks,
                n=config["n"],
                min_topic_similarity=0.15
            )

        end_time = time.time()

        # Print results
        print(f"\nAusgewählte Absätze ({len(selected)}):")
        for i, chunk in enumerate(selected, 1):
            print(f"{i}. {chunk}")

        print(f"\nVerarbeitungszeit: {(end_time - start_time):.4f} Sekunden")

    # Compare graph structure with and without compound splitting
    print("\n\n=== Vergleich der Graphenstruktur mit und ohne Compound-Splitting ===")

    # Create two selectors
    selector_standard = GermanTextRankSelector(use_spacy=True, compound_split=False)
    selector_compound = GermanTextRankSelector(use_spacy=True, compound_split=True)

    # Build similarity graphs
    sim_standard, scores_standard = selector_standard.build_similarity_graph(test_chunks[:3])
    sim_compound, scores_compound = selector_compound.build_similarity_graph(test_chunks[:3])

    # Print scores
    print("\nTextRank-Scores ohne Compound-Splitting:")
    for i, score in enumerate(scores_standard):
        print(f"Absatz {i + 1}: {score:.4f}")

    print("\nTextRank-Scores mit Compound-Splitting:")
    for i, score in enumerate(scores_compound):
        print(f"Absatz {i + 1}: {score:.4f}")

    # Print similarity difference
    print("\nÄhnlichkeits-Differenz zwischen den Methoden:")
    diff = numpy.abs(sim_standard - sim_compound)
    print(f"Durchschnittliche Ähnlichkeitsdifferenz: {numpy.mean(diff):.4f}")
    print(f"Maximale Ähnlichkeitsdifferenz: {numpy.max(diff):.4f}")