import re

def split_sentences(text):
    """
    Splits text into sentences, ignoring periods after common abbreviations
    and single letter initials.
    """
    # Common abbreviations that should not trigger a sentence split
    abbreviations = [
        'mr', 'mrs', 'ms', 'dr', 'prof', 'sr', 'jr',
        'vs', 'eg', 'ie', 'etc', 'al', 'co', 'corp', 'inc',
        'a.m', 'p.m', 'st', 'ave', 'rd', 'rd', 'oct', 'nov', 'dec',
        'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep'
    ]
    
    # Compile regex for sentence endings: period, exclamation, question mark followed by space or end of string.
    # We capture the trailing whitespace so we don't lose spaces when re-joining abbreviation segments.
    sentence_endings = re.compile(r'([.!?]+(?:\s+|$))')
    raw_splits = sentence_endings.split(text)
    
    sentences = []
    current_sentence = ""
    
    for i in range(0, len(raw_splits), 2):
        chunk = raw_splits[i]
        ending = raw_splits[i+1] if i + 1 < len(raw_splits) else ""
        
        if current_sentence:
            current_sentence += chunk + ending
        else:
            current_sentence = chunk + ending
            
        # Check if the last word of the chunk before punctuation is a known abbreviation
        # or a single letter initial (e.g., "A.")
        words = re.findall(r'\b\w+\b', chunk)
        if words:
            last_word = words[-1].lower()
            if last_word in abbreviations or (len(last_word) == 1 and last_word.isalpha()):
                # Continue building the sentence (do not split)
                continue
                
        sentences.append(current_sentence.strip())
        current_sentence = ""
        
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
        
    return [s for s in sentences if s]

def split_long_sentence(sentence, max_chars):
    """
    Splits a single long sentence into clauses (by comma, semicolon, colon, dashes),
    or by words if clauses are still too long.
    """
    clause_separators = re.compile(r'([,;:—]+)\s+')
    raw_splits = clause_separators.split(sentence)
    
    sub_chunks = []
    current_sub = ""
    
    for i in range(0, len(raw_splits), 2):
        part = raw_splits[i]
        separator = raw_splits[i+1] if i + 1 < len(raw_splits) else ""
        combined = part + separator
        
        if len(current_sub) + len(combined) <= max_chars:
            current_sub += combined
        else:
            if current_sub:
                sub_chunks.append(current_sub.strip())
            
            if len(combined) <= max_chars:
                current_sub = combined
            else:
                # Fallback to word splitting if the clause is too long
                words = combined.split()
                word_chunk = []
                word_len = 0
                for word in words:
                    if word_len + len(word) + (1 if word_chunk else 0) <= max_chars:
                        word_chunk.append(word)
                        word_len += len(word) + (1 if len(word_chunk) > 1 else 0)
                    else:
                        sub_chunks.append(" ".join(word_chunk))
                        word_chunk = [word]
                        word_len = len(word)
                if word_chunk:
                    current_sub = " ".join(word_chunk)
                else:
                    current_sub = ""
                    
    if current_sub.strip():
        sub_chunks.append(current_sub.strip())
        
    return sub_chunks

def group_sentences_into_chunks(sentences, max_chars=800):
    """
    Groups individual sentences into blocks of text that are less than max_chars.
    """
    chunks = []
    current_chunk = []
    current_len = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_len = len(sentence)
        
        if sentence_len > max_chars:
            # First, flush the current chunk if it has items
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
                current_len = 0
            # Split and add the parts
            chunks.extend(split_long_sentence(sentence, max_chars))
        else:
            # Check if this sentence fits in the current chunk
            # +1 accounts for the space added when joining
            space_padding = 1 if current_chunk else 0
            if current_len + sentence_len + space_padding <= max_chars:
                current_chunk.append(sentence)
                current_len += sentence_len + space_padding
            else:
                chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_len = sentence_len
                
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def split_into_chunks(text, max_chars=800):
    """
    Splits text by paragraphs first, then by sentences if paragraphs are too large.
    Ensures no chunk exceeds max_chars.
    """
    if not text or not text.strip():
        return []
        
    # Split into paragraphs (handles single or double newlines)
    paragraphs = re.split(r'\n+', text)
    all_chunks = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        if len(para) <= max_chars:
            all_chunks.append(para)
        else:
            sentences = split_sentences(para)
            para_chunks = group_sentences_into_chunks(sentences, max_chars)
            all_chunks.extend(para_chunks)
            
    return all_chunks
