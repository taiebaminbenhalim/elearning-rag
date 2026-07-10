"""Package cleaning : stratégies de nettoyage du texte OCR.

Le nettoyage est totalement indépendant du moteur OCR utilisé en amont.
Une nouvelle stratégie peut être ajoutée en implémentant `ICleaningStrategy`
sans modifier le reste du pipeline.
"""

from cleaning.basic_cleaning_strategy import BasicCleaningStrategy

__all__ = ["BasicCleaningStrategy"]
