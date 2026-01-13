import re
from typing import Optional, List
from datetime import datetime


STOPWORDS = {"DE", "DEL", "LA", "LOS", "LAS", "EL", "Y", "E"}


def normalize_phone(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    if not cleaned:
        return None
    if len(cleaned) < 8:
        return None
    return cleaned


def normalize_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name = name.upper().strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[ÀÁÂÃÄÅ]', 'A', name)
    name = re.sub(r'[ÈÉÊË]', 'E', name)
    name = re.sub(r'[ÌÍÎÏ]', 'I', name)
    name = re.sub(r'[ÒÓÔÕÖ]', 'O', name)
    name = re.sub(r'[ÙÚÛÜ]', 'U', name)
    name = re.sub(r'[Ñ]', 'N', name)
    name = re.sub(r'[Ç]', 'C', name)
    name = re.sub(r'[^A-Z\s]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip() if name else None


def tokenize_name(name: Optional[str]) -> List[str]:
    if not name:
        return []
    normalized = normalize_name(name)
    if not normalized:
        return []
    tokens = [t for t in normalized.split() if t and t not in STOPWORDS]
    return tokens


def name_similarity(name1: Optional[str], name2: Optional[str], threshold: float = 0.66) -> float:
    tokens1 = set(tokenize_name(name1))
    tokens2 = set(tokenize_name(name2))
    
    if not tokens1 or not tokens2:
        return 0.0
    
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    
    if not union:
        return 0.0
    
    jaccard = len(intersection) / len(union)
    
    max_len = max(len(tokens1), len(tokens2))
    if max_len == 0:
        return 0.0
    
    overlap = len(intersection) / max_len
    
    similarity = (jaccard + overlap) / 2.0
    return similarity


def normalize_license(license: Optional[str]) -> Optional[str]:
    if not license:
        return None
    cleaned = re.sub(r'[\s\-]', '', license.upper())
    return cleaned if cleaned else None


def normalize_plate(plate: Optional[str]) -> Optional[str]:
    """
    Normaliza placa: quita todo lo que no sea alfanumérico y convierte a MAYÚSCULAS.
    Coincide con la normalización usada en canon.drivers_index.
    """
    if not plate:
        return None
    # Primero quitar espacios y guiones, luego quitar todo lo que no sea alfanumérico
    cleaned = re.sub(r'[\s\-]', '', plate.upper())
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned)
    return cleaned if cleaned else None


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    
    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    
    return None


def digits_only(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return re.sub(r'\D', '', text)


def normalize_license_simple(license: Optional[str]) -> Optional[str]:
    if not license:
        return None
    return license.upper().strip()


def normalize_phone_pe9(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    digits = digits_only(phone)
    if not digits or len(digits) < 9:
        return None
    return digits[-9:]
