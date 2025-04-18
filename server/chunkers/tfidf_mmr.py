import numpy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
from spacy.lang.de.stop_words import STOP_WORDS

class GermanChunkSelector:
    """Class for selecting diverse and important chunks from German text."""
    
    def __init__(self, 
                 use_lemmatization: bool = True, 
                 min_word_length: int = 3,
                 use_spacy: bool = True):
        """
        Initialize the German chunk selector.
        
        Args:
            use_lemmatization: Whether to use lemmatization for German text
            min_word_length: Minimum length of words to consider
            use_spacy: Whether to use spaCy for preprocessing
        """
        self.use_lemmatization = use_lemmatization
        self.min_word_length = min_word_length
        self.use_spacy = use_spacy
        
        # Load German spaCy model if needed
        if self.use_spacy:
            try:
                self.nlp = spacy.load("de_core_news_lg")
            except IOError:
                # Provide a helpful message if model isn't installed
                print("German spaCy model not found. Installing with: python -m spacy download de_core_news_lg")
                self.use_spacy = False
    
    def preprocess_german_text(self, text: str) -> str:
        """
        Preprocess German text by removing stopwords and lemmatizing.
        
        Args:
            text: The input text to preprocess
            
        Returns:
            Preprocessed text
        """
        if not self.use_spacy:
            # Simple preprocessing without spaCy
            words = text.lower().split()
            words = [w for w in words if len(w) >= self.min_word_length and w not in STOP_WORDS]
            return " ".join(words)
        
        # Using spaCy for better German language processing
        doc = self.nlp(text)
        
        if self.use_lemmatization:
            # Use lemmatization (base forms) for German words
            tokens = [token.lemma_ for token in doc 
                     if not token.is_stop 
                     and not token.is_punct
                     and len(token.text) >= self.min_word_length]
        else:
            # Use original word forms
            tokens = [token.text for token in doc 
                     if not token.is_stop 
                     and not token.is_punct
                     and len(token.text) >= self.min_word_length]
        
        return " ".join(tokens)
    
    def select_diverse_chunks(
            self, chunks: list[str], n: int = 5, lambda_param: float = .5, preprocess: bool = True
    ) -> list[str]:
        """
        Select diverse and important chunks using TF-IDF and MMR.
        
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
            return list()
        
        if n >= len(chunks):
            return chunks.copy()
        
        # Preprocess texts if requested
        processed_chunks = chunks
        if preprocess:
            processed_chunks = [self.preprocess_german_text(chunk) for chunk in chunks]
        
        # Create TF-IDF vectors with German-specific settings
        tfidf = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),  # Include bigrams for German compound words
            min_df=2,            # Ignore very rare terms
            max_df=0.95          # Ignore very common terms
        ).fit_transform(processed_chunks)
        
        # Calculate importance scores (sum of TF-IDF values)
        importance_scores = numpy.array(tfidf.sum(axis=1)).flatten()
        
        # Calculate similarity matrix
        sim_matrix = cosine_similarity(tfidf)
        
        # Selected indices
        selected: list[int] = list()
        
        # Select the most important chunk first
        selected.append(int(numpy.argmax(importance_scores)))
        
        # Select remaining chunks using MMR
        while len(selected) < n:
            candidate_scores = []
            
            for i in range(len(chunks)):
                if i not in selected:
                    # MMR score combines importance with diversity
                    relevance = importance_scores[i]
                    diversity = min([1 - sim_matrix[i, j] for j in selected])
                    mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                    candidate_scores.append((i, mmr_score))
            
            if not candidate_scores:
                break
                
            # Get the highest scoring candidate
            best_candidate = max(candidate_scores, key=lambda x: x[1])[0]
            selected.append(best_candidate)
        
        # Return selected chunks
        return [chunks[i] for i in selected]


# Usage example
def select_diverse_german_chunks(chunks: list[str], n: int = 5) -> list[str]:
    """
    Convenience function to select diverse German chunks.

    Args:
        chunks: List of German text chunks
        n: Number of chunks to select

    Returns:
        List of selected chunks
    """
    selector = GermanChunkSelector(use_lemmatization=True)
    return selector.select_diverse_chunks(chunks, n=n, lambda_param=0.6)


# Main function for testing
if __name__ == "__main__":
    import time

    # Sample German paragraphs
    test_chunks = [
        "Der Klimawandel ist eine der größten Herausforderungen unserer Zeit. Die globale Erwärmung führt zu schmelzenden Polkappen, steigendem Meeresspiegel und extremen Wetterereignissen.",
        "Erneuerbare Energien wie Solarenergie und Windkraft spielen eine wichtige Rolle im Kampf gegen den Klimawandel. Deutschland hat in den letzten Jahren stark in diese Technologien investiert.",
        "Die Digitalisierung verändert unsere Arbeitswelt grundlegend. Viele traditionelle Berufe verschwinden, während neue Jobprofile entstehen.",
        "Künstliche Intelligenz und maschinelles Lernen revolutionieren zahlreiche Branchen. Diese Technologien ermöglichen Automatisierung und datengetriebene Entscheidungsfindung.",
        "Die deutsche Automobilindustrie steht vor einem Umbruch. Elektromobilität und autonomes Fahren sind die Zukunftstrends, die den Markt verändern werden.",
        "Der demografische Wandel stellt das deutsche Rentensystem vor große Herausforderungen. Eine alternde Bevölkerung bedeutet weniger Beitragszahler und mehr Rentenempfänger.",
        "Die Biodiversität ist durch menschliche Aktivitäten weltweit bedroht. Artenschutz und nachhaltige Landwirtschaft sind wichtige Maßnahmen zum Erhalt der biologischen Vielfalt.",
        "Die COVID-19-Pandemie hat gezeigt, wie wichtig ein robustes Gesundheitssystem ist. Deutschland hat im internationalen Vergleich relativ gut auf die Krise reagiert.",
        "Datenschutz und Informationssicherheit gewinnen im digitalen Zeitalter zunehmend an Bedeutung. Die DSGVO hat in Europa neue Standards für den Umgang mit persönlichen Daten gesetzt.",
        "Integration und Migration sind zentrale gesellschaftliche Themen in Deutschland. Eine erfolgreiche Integrationspolitik fördert den sozialen Zusammenhalt und die wirtschaftliche Entwicklung."
    ]

    print("TF-IDF + MMR Test für deutsche Texte\n")
    print(f"Originaltexte: {len(test_chunks)} Absätze\n")

    # Test with different configurations
    test_configs = [
        {"name": "Standard", "use_lemma": True, "lambda": 0.5, "n": 3},
        {"name": "Hohe Diversität", "use_lemma": True, "lambda": 0.3, "n": 3},
        {"name": "Hohe Relevanz", "use_lemma": True, "lambda": 0.7, "n": 3},
        {"name": "Ohne Lemmatisierung", "use_lemma": False, "lambda": 0.5, "n": 3},
        {"name": "Mehr Chunks", "use_lemma": True, "lambda": 0.5, "n": 5}
    ]

    for config in test_configs:
        print(f"\n\nTest: {config['name']}")
        print(f"Parameter: λ={config['lambda']}, n={config['n']}, Lemmatisierung={config['use_lemma']}")

        # Create selector
        selector = GermanChunkSelector(use_lemmatization=config["use_lemma"])

        # Measure execution time
        start_time = time.time()
        selected = selector.select_diverse_chunks(
            test_chunks,
            n=config["n"],
            lambda_param=config["lambda"]
        )
        end_time = time.time()

        # Print results
        print(f"\nAusgewählte Absätze ({len(selected)}):")
        for i, chunk in enumerate(selected, 1):
            print(f"{i}. {chunk[:100]}...")

        print(f"\nVerarbeitungszeit: {(end_time - start_time):.4f} Sekunden")