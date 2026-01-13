"""
Servicio para determinar el origen canónico de una persona.

Aplica reglas de prioridad y detecta violaciones del contrato canónico.
"""
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import LEAD_SYSTEM_START_DATE
from app.models.canon import (
    ConfidenceLevel,
    DecidedBy,
    IdentityLink,
    IdentityOrigin,
    IdentityRegistry,
    OriginResolutionStatus,
    OriginTag,
)

logger = logging.getLogger(__name__)


@dataclass
class OriginResult:
    """Resultado de la determinación de origen"""
    origin_tag: OriginTag
    origin_source_id: str
    origin_confidence: float
    origin_created_at: datetime
    evidence: Dict[str, Any]
    requires_manual_review: bool = False
    conflict_reason: Optional[str] = None


@dataclass
class ConflictResolution:
    """Resolución de conflicto de múltiples orígenes"""
    requires_manual_review: bool
    suggested_origin: Optional[OriginResult] = None
    conflict_details: Optional[Dict[str, Any]] = None


class OriginDeterminationService:
    """Servicio para determinar origen canónico de personas"""
    
    # Prioridad de orígenes (mayor número = mayor prioridad)
    ORIGIN_PRIORITY = {
        OriginTag.CABINET_LEAD: 4,
        OriginTag.SCOUT_REGISTRATION: 3,
        OriginTag.MIGRATION: 2,
        OriginTag.LEGACY_EXTERNAL: 1,
    }
    
    # Mapeo de source_table a OriginTag
    SOURCE_TABLE_TO_TAG = {
        "module_ct_cabinet_leads": OriginTag.CABINET_LEAD,
        "module_ct_scouting_daily": OriginTag.SCOUT_REGISTRATION,
        "module_ct_migrations": OriginTag.MIGRATION,
        "drivers": None,  # Drivers no son origen válido por sí solos
    }
    
    # Umbral de confianza para considerar conflicto fuerte
    HIGH_CONFIDENCE_THRESHOLD = 85.0
    
    def __init__(self, db: Session):
        self.db = db
        self.lead_system_start_date = LEAD_SYSTEM_START_DATE
    
    def determine_origin(self, person_key: UUID) -> Optional[OriginResult]:
        """
        Determina el origen canónico de una persona aplicando reglas de prioridad.
        
        Returns:
            OriginResult si se puede determinar automáticamente
            None si requiere revisión manual
        """
        # Obtener todos los links de la persona
        links = self.db.query(IdentityLink).filter(
            IdentityLink.person_key == person_key
        ).order_by(IdentityLink.linked_at).all()
        
        if not links:
            logger.warning(f"No links found for person_key {person_key}")
            return None
        
        # Inferir origen desde links
        origin_result = self.infer_origin_from_links(person_key, links)
        
        if origin_result and origin_result.requires_manual_review:
            logger.info(f"Person {person_key} requires manual review: {origin_result.conflict_reason}")
            return None
        
        return origin_result
    
    def infer_origin_from_links(self, person_key: UUID, links: List[IdentityLink]) -> Optional[OriginResult]:
        """
        Infiere el origen desde los links de identidad.
        
        Aplica reglas de prioridad:
        1. cabinet_lead > scout_registration > migration > legacy_external
        2. Si mismo tipo: mayor confidence/match_score
        3. Si mismo confidence: más temprano (linked_at)
        """
        # Agrupar links por origen válido
        origin_candidates: Dict[OriginTag, List[IdentityLink]] = {}
        
        for link in links:
            origin_tag = self.SOURCE_TABLE_TO_TAG.get(link.source_table)
            if origin_tag:
                if origin_tag not in origin_candidates:
                    origin_candidates[origin_tag] = []
                origin_candidates[origin_tag].append(link)
        
        # Si no hay orígenes válidos, verificar si es legacy
        if not origin_candidates:
            # Verificar si tiene link de driver
            driver_links = [l for l in links if l.source_table == "drivers"]
            if driver_links:
                # Verificar si es legacy_external
                first_driver_link = min(driver_links, key=lambda l: l.linked_at)
                if self._is_legacy_external(person_key, first_driver_link.linked_at.date()):
                    return OriginResult(
                        origin_tag=OriginTag.LEGACY_EXTERNAL,
                        origin_source_id=str(first_driver_link.source_pk),
                        origin_confidence=50.0,  # Baja confianza para legacy
                        origin_created_at=first_driver_link.linked_at,
                        evidence={
                            "reason": "legacy_external",
                            "first_seen_at": first_driver_link.linked_at.isoformat(),
                            "lead_system_start_date": self.lead_system_start_date.isoformat(),
                            "driver_link": {
                                "source_pk": first_driver_link.source_pk,
                                "linked_at": first_driver_link.linked_at.isoformat()
                            }
                        }
                    )
            return None
        
        # Aplicar prioridad: seleccionar el origen con mayor prioridad
        highest_priority_tag = max(
            origin_candidates.keys(),
            key=lambda tag: self.ORIGIN_PRIORITY[tag]
        )
        
        candidate_links = origin_candidates[highest_priority_tag]
        
        # Si hay múltiples candidatos del mismo tipo, seleccionar el mejor
        if len(candidate_links) > 1:
            # Seleccionar por: mayor match_score, luego mayor confidence, luego más temprano
            best_link = max(
                candidate_links,
                key=lambda l: (
                    l.match_score or 0,
                    self._confidence_to_numeric(l.confidence_level),
                    -(l.linked_at.timestamp())  # Negativo para más temprano = mayor
                )
            )
        else:
            best_link = candidate_links[0]
        
        # Verificar conflictos con otros orígenes de alta confianza
        conflict_check = self._check_conflicts(origin_candidates, highest_priority_tag, best_link)
        if conflict_check.requires_manual_review:
            return OriginResult(
                origin_tag=highest_priority_tag,
                origin_source_id=best_link.source_pk,
                origin_confidence=self._calculate_confidence(best_link),
                origin_created_at=best_link.snapshot_date,
                evidence=self._build_evidence(best_link, links),
                requires_manual_review=True,
                conflict_reason=conflict_check.conflict_details.get("reason") if conflict_check.conflict_details else "multiple_high_confidence_origins"
            )
        
        return OriginResult(
            origin_tag=highest_priority_tag,
            origin_source_id=best_link.source_pk,
            origin_confidence=self._calculate_confidence(best_link),
            origin_created_at=best_link.snapshot_date,
            evidence=self._build_evidence(best_link, links)
        )
    
    def _check_conflicts(
        self,
        origin_candidates: Dict[OriginTag, List[IdentityLink]],
        selected_tag: OriginTag,
        selected_link: IdentityLink
    ) -> ConflictResolution:
        """
        Verifica si hay conflictos con otros orígenes de alta confianza.
        
        Si hay dos orígenes distintos con confianza alta, requiere revisión manual.
        """
        selected_confidence = self._calculate_confidence(selected_link)
        
        # Buscar otros orígenes con alta confianza
        conflicting_origins = []
        for tag, links in origin_candidates.items():
            if tag == selected_tag:
                continue
            
            for link in links:
                confidence = self._calculate_confidence(link)
                if confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
                    conflicting_origins.append({
                        "tag": tag,
                        "link": link,
                        "confidence": confidence
                    })
        
        if conflicting_origins and selected_confidence >= self.HIGH_CONFIDENCE_THRESHOLD:
            return ConflictResolution(
                requires_manual_review=True,
                conflict_details={
                    "reason": "multiple_high_confidence_origins",
                    "selected": {
                        "tag": selected_tag.value,
                        "confidence": selected_confidence,
                        "source_pk": selected_link.source_pk
                    },
                    "conflicts": [
                        {
                            "tag": c["tag"].value,
                            "confidence": c["confidence"],
                            "source_pk": c["link"].source_pk
                        }
                        for c in conflicting_origins
                    ]
                }
            )
        
        return ConflictResolution(requires_manual_review=False)
    
    def _calculate_confidence(self, link: IdentityLink) -> float:
        """Calcula confianza numérica desde match_score y confidence_level"""
        base_score = link.match_score or 0
        
        # Ajustar según confidence_level
        confidence_multiplier = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.85,
            ConfidenceLevel.LOW: 0.70
        }.get(link.confidence_level, 0.70)
        
        return base_score * confidence_multiplier
    
    def _confidence_to_numeric(self, confidence: ConfidenceLevel) -> float:
        """Convierte ConfidenceLevel a valor numérico para comparación"""
        return {
            ConfidenceLevel.HIGH: 3.0,
            ConfidenceLevel.MEDIUM: 2.0,
            ConfidenceLevel.LOW: 1.0
        }.get(confidence, 1.0)
    
    def _build_evidence(self, primary_link: IdentityLink, all_links: List[IdentityLink]) -> Dict[str, Any]:
        """Construye evidencia auditable del origen"""
        evidence = {
            "primary_link": {
                "source_table": primary_link.source_table,
                "source_pk": primary_link.source_pk,
                "match_rule": primary_link.match_rule,
                "match_score": primary_link.match_score,
                "confidence_level": primary_link.confidence_level.value if hasattr(primary_link.confidence_level, 'value') else str(primary_link.confidence_level),
                "linked_at": primary_link.linked_at.isoformat(),
                "snapshot_date": primary_link.snapshot_date.isoformat()
            },
            "all_links": [
                {
                    "source_table": link.source_table,
                    "source_pk": link.source_pk,
                    "match_rule": link.match_rule,
                    "match_score": link.match_score,
                    "linked_at": link.linked_at.isoformat()
                }
                for link in all_links
            ],
            "total_links": len(all_links),
            "matched_fields": self._extract_matched_fields(primary_link)
        }
        
        if primary_link.evidence:
            evidence["link_evidence"] = primary_link.evidence
        
        return evidence
    
    def _extract_matched_fields(self, link: IdentityLink) -> List[str]:
        """Extrae campos que fueron usados para el match"""
        matched_fields = []
        
        if link.evidence:
            if link.evidence.get("phone_match"):
                matched_fields.append("phone")
            if link.evidence.get("license_match"):
                matched_fields.append("license")
            if link.evidence.get("plate_match"):
                matched_fields.append("plate")
            if link.evidence.get("name_similarity"):
                matched_fields.append("name")
        
        # Inferir desde match_rule
        if "PHONE" in link.match_rule:
            matched_fields.append("phone")
        if "LICENSE" in link.match_rule:
            matched_fields.append("license")
        if "PLATE" in link.match_rule:
            matched_fields.append("plate")
        if "NAME" in link.match_rule:
            matched_fields.append("name")
        
        return list(set(matched_fields))  # Eliminar duplicados
    
    def classify_legacy(self, driver_id: str, first_seen_at: date) -> bool:
        """
        Determina si un driver es legacy_external.
        
        Un driver es legacy si:
        - first_seen_at es anterior a LEAD_SYSTEM_START_DATE
        - Y no tiene links a fuentes válidas (cabinet/scouting/migration)
        """
        return first_seen_at < self.lead_system_start_date
    
    def _is_legacy_external(self, person_key: UUID, first_seen_at: date) -> bool:
        """Verifica si una persona es legacy_external"""
        # Verificar si tiene links a fuentes válidas
        valid_source_links = self.db.query(IdentityLink).filter(
            IdentityLink.person_key == person_key,
            IdentityLink.source_table.in_([
                "module_ct_cabinet_leads",
                "module_ct_scouting_daily",
                "module_ct_migrations"
            ])
        ).first()
        
        # Si tiene links válidos, no es legacy
        if valid_source_links:
            return False
        
        # Si first_seen_at es anterior a LEAD_SYSTEM_START_DATE, es legacy
        return first_seen_at < self.lead_system_start_date
    
    def get_first_seen_at(self, person_key: UUID) -> Optional[datetime]:
        """
        Calcula first_seen_at con prioridad:
        MIN( driver_linked_at, first_activity_at, registry_created_at )
        """
        # Obtener registry_created_at
        registry = self.db.query(IdentityRegistry).filter(
            IdentityRegistry.person_key == person_key
        ).first()
        
        if not registry:
            return None
        
        timestamps = [registry.created_at]
        
        # Obtener driver_linked_at (más temprano)
        driver_link = self.db.query(IdentityLink).filter(
            IdentityLink.person_key == person_key,
            IdentityLink.source_table == "drivers"
        ).order_by(IdentityLink.linked_at).first()
        
        if driver_link:
            timestamps.append(driver_link.linked_at)
        
        # Obtener first_activity_at (más temprano de todos los links)
        first_link = self.db.query(IdentityLink).filter(
            IdentityLink.person_key == person_key
        ).order_by(IdentityLink.linked_at).first()
        
        if first_link:
            timestamps.append(first_link.linked_at)
        
        return min(timestamps) if timestamps else None
