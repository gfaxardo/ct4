import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from sqlalchemy.exc import OperationalError, DisconnectionError, PendingRollbackError
from uuid import UUID, uuid4
from app.models.canon import IdentityRegistry, IdentityLink, IdentityUnmatched, ConfidenceLevel, UnmatchedStatus
from app.services.normalization import (
    normalize_phone, normalize_license, normalize_plate,
    normalize_name, name_similarity
)
from app.config import PARK_ID_OBJETIVO, NAME_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class IdentityCandidateInput:
    source_table: str
    source_pk: str
    snapshot_date: datetime
    park_id: Optional[str]
    phone_norm: Optional[str]
    license_norm: Optional[str]
    plate_norm: Optional[str]
    name_norm: Optional[str]
    brand_norm: Optional[str]
    model_norm: Optional[str]


class MatchingResult:
    def __init__(self, person_key: Optional[UUID], rule: Optional[str], score: Optional[int], 
                 confidence: Optional[ConfidenceLevel], reason_code: Optional[str] = None,
                 evidence: Optional[Dict[str, Any]] = None, driver_id: Optional[str] = None):
        self.person_key = person_key
        self.rule = rule
        self.score = score
        self.confidence = confidence
        self.reason_code = reason_code
        self.evidence = evidence or {}
        self.driver_id = driver_id


class MatchingEngine:
    def __init__(self, db: Session, park_id_objetivo: str = None, name_similarity_threshold: float = None):
        self.db = db
        self.park_id_objetivo = park_id_objetivo or PARK_ID_OBJETIVO
        self.name_similarity_threshold = name_similarity_threshold or NAME_SIMILARITY_THRESHOLD

    def match_person(self, candidate: IdentityCandidateInput) -> MatchingResult:
        results = []

        if candidate.phone_norm:
            result = self._apply_rule_r1_phone_exact(candidate)
            if result.person_key or result.reason_code:
                results.append(result)

        if candidate.license_norm:
            result = self._apply_rule_r2_license_exact(candidate)
            if result.person_key or result.reason_code:
                results.append(result)

        if candidate.plate_norm and candidate.name_norm:
            result = self._apply_rule_r3_plate_name(candidate)
            if result.person_key or result.reason_code:
                results.append(result)
            
            # Si R3 no encontró candidatos por restricción de fecha, intentar R3b (sin restricción de fecha)
            if result.reason_code == "NO_CANDIDATES":
                result_r3b = self._apply_rule_r3b_plate_name_no_date(candidate)
                if result_r3b.person_key or result_r3b.reason_code:
                    results.append(result_r3b)

        if candidate.brand_norm and candidate.model_norm and candidate.name_norm:
            result = self._apply_rule_r4_car_fingerprint_name(candidate)
            if result.person_key or result.reason_code:
                results.append(result)

        matched_results = [r for r in results if r.person_key]
        unmatched_results = [r for r in results if r.reason_code and not r.person_key]

        if not matched_results and not unmatched_results:
            return MatchingResult(
                None, None, None, None,
                reason_code="NO_CANDIDATES",
                evidence={"applied_rules": [r.rule for r in results if r.rule]}
            )

        if len(matched_results) == 1:
            return matched_results[0]

        unique_persons = {r.person_key for r in matched_results if r.person_key}
        if len(unique_persons) == 1:
            best_result = max(matched_results, key=lambda r: r.score or 0)
            return best_result

        if len(matched_results) > 1:
            candidates_preview = [
                {
                    "person_key": str(r.person_key),
                    "driver_id": r.driver_id,
                    "rule": r.rule,
                    "score": r.score
                }
                for r in matched_results[:3]
            ]
            return MatchingResult(
                None, None, None, None,
                reason_code="MULTIPLE_CANDIDATES",
                evidence={"candidates": candidates_preview}
            )

        if unmatched_results:
            return unmatched_results[0]

        return MatchingResult(
            None, None, None, None,
            reason_code="NO_CANDIDATES",
            evidence={}
        )

    def _apply_rule_r1_phone_exact(self, candidate: IdentityCandidateInput) -> MatchingResult:
        try:
            query_park = text("""
                SELECT driver_id, park_id
                FROM canon.drivers_index
                WHERE phone_norm = :phone_norm
                AND park_id = :park_id_objetivo
                LIMIT 10
            """)
            
            result_park = self.db.execute(query_park, {
                "phone_norm": candidate.phone_norm,
                "park_id_objetivo": self.park_id_objetivo
            })
            candidates_park = result_park.fetchall()
            
            if candidates_park:
                if len(candidates_park) > 1:
                    candidates_preview = [
                        {"driver_id": str(c.driver_id), "park_id": c.park_id}
                        for c in candidates_park[:3]
                    ]
                    return MatchingResult(
                        None, None, None, None,
                        reason_code="MULTIPLE_CANDIDATES",
                        evidence={"candidates": candidates_preview}
                    )
                
                driver_id = candidates_park[0].driver_id
                person_key = self._get_or_create_person_from_driver(driver_id, candidate)
                
                if person_key:
                    return MatchingResult(
                        person_key,
                        "R1_PHONE_EXACT",
                        95,
                        ConfidenceLevel.HIGH,
                        evidence={"phone_normalized": candidate.phone_norm, "driver_id": driver_id, "park_id": self.park_id_objetivo},
                        driver_id=driver_id
                    )
            
            query_global = text("""
                SELECT driver_id, park_id
                FROM canon.drivers_index
                WHERE phone_norm = :phone_norm
                AND park_id != :park_id_objetivo
                LIMIT 10
            """)
            
            result_global = self.db.execute(query_global, {
                "phone_norm": candidate.phone_norm,
                "park_id_objetivo": self.park_id_objetivo
            })
            candidates_global = result_global.fetchall()
            
            if not candidates_global:
                return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
            if len(candidates_global) > 1:
                candidates_preview = [
                    {"driver_id": str(c.driver_id), "park_id": c.park_id}
                    for c in candidates_global[:3]
                ]
                return MatchingResult(
                    None, None, None, None,
                    reason_code="MULTIPLE_CANDIDATES",
                    evidence={"candidates": candidates_preview}
                )
            
            driver_id = candidates_global[0].driver_id
            person_key = self._get_or_create_person_from_driver(driver_id, candidate)
            
            if person_key:
                return MatchingResult(
                    person_key,
                    "R1_PHONE_EXACT",
                    95,
                    ConfidenceLevel.HIGH,
                    evidence={"phone_normalized": candidate.phone_norm, "driver_id": driver_id, "park_id": candidates_global[0].park_id},
                    driver_id=driver_id
                )
            
            return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
        except Exception as e:
            logger.error(f"Error en R1: {e}")
            return MatchingResult(None, None, None, None, reason_code="ERROR")

    def _apply_rule_r2_license_exact(self, candidate: IdentityCandidateInput) -> MatchingResult:
        try:
            query_park = text("""
                SELECT driver_id, park_id
                FROM canon.drivers_index
                WHERE license_norm = :license_norm
                AND park_id = :park_id_objetivo
                LIMIT 10
            """)
            
            result_park = self.db.execute(query_park, {
                "license_norm": candidate.license_norm,
                "park_id_objetivo": self.park_id_objetivo
            })
            candidates_park = result_park.fetchall()
            
            if candidates_park:
                if len(candidates_park) > 1:
                    candidates_preview = [
                        {"driver_id": str(c.driver_id), "park_id": c.park_id}
                        for c in candidates_park[:3]
                    ]
                    return MatchingResult(
                        None, None, None, None,
                        reason_code="MULTIPLE_CANDIDATES",
                        evidence={"candidates": candidates_preview}
                    )
                
                driver_id = candidates_park[0].driver_id
                person_key = self._get_or_create_person_from_driver(driver_id, candidate)
                
                if person_key:
                    return MatchingResult(
                        person_key,
                        "R2_LICENSE_EXACT",
                        92,
                        ConfidenceLevel.HIGH,
                        evidence={"license_normalized": candidate.license_norm, "driver_id": driver_id, "park_id": self.park_id_objetivo},
                        driver_id=driver_id
                    )
            
            query_global = text("""
                SELECT driver_id, park_id
                FROM canon.drivers_index
                WHERE license_norm = :license_norm
                AND park_id != :park_id_objetivo
                LIMIT 10
            """)
            
            result_global = self.db.execute(query_global, {
                "license_norm": candidate.license_norm,
                "park_id_objetivo": self.park_id_objetivo
            })
            candidates_global = result_global.fetchall()
            
            if not candidates_global:
                return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
            if len(candidates_global) > 1:
                candidates_preview = [
                    {"driver_id": str(c.driver_id), "park_id": c.park_id}
                    for c in candidates_global[:3]
                ]
                return MatchingResult(
                    None, None, None, None,
                    reason_code="MULTIPLE_CANDIDATES",
                    evidence={"candidates": candidates_preview}
                )
            
            driver_id = candidates_global[0].driver_id
            person_key = self._get_or_create_person_from_driver(driver_id, candidate)
            
            if person_key:
                return MatchingResult(
                    person_key,
                    "R2_LICENSE_EXACT",
                    92,
                    ConfidenceLevel.HIGH,
                    evidence={"license_normalized": candidate.license_norm, "driver_id": driver_id, "park_id": candidates_global[0].park_id},
                    driver_id=driver_id
                )
            
            return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
        except Exception as e:
            logger.error(f"Error en R2: {e}")
            return MatchingResult(None, None, None, None, reason_code="ERROR")

    def _apply_rule_r3_plate_name(self, candidate: IdentityCandidateInput) -> MatchingResult:
        try:
            # Ampliado rango de fechas: de -30/+7 a -90/+30 días para capturar más candidatos
            date_from = candidate.snapshot_date - timedelta(days=90)
            date_to = candidate.snapshot_date + timedelta(days=30)
            
            query = text("""
                SELECT driver_id, park_id, full_name_norm, hire_date
                FROM canon.drivers_index
                WHERE plate_norm = :plate_norm
                AND park_id = :park_id_objetivo
                AND (hire_date IS NULL OR hire_date BETWEEN :date_from AND :date_to)
                LIMIT 20
            """)
            
            try:
                result = self.db.execute(query, {
                    "plate_norm": candidate.plate_norm,
                    "park_id_objetivo": self.park_id_objetivo,
                    "date_from": date_from,
                    "date_to": date_to
                })
                candidates = result.fetchall()
            except (OperationalError, DisconnectionError, PendingRollbackError) as e:
                raise
            
            if not candidates:
                return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
            scored_candidates = []
            for c in candidates:
                similarity = name_similarity(candidate.name_norm, c.full_name_norm, self.name_similarity_threshold)
                if similarity >= self.name_similarity_threshold:
                    scored_candidates.append({
                        "driver_id": c.driver_id,
                        "park_id": c.park_id,
                        "similarity": similarity
                    })
            
            if not scored_candidates:
                return MatchingResult(None, None, None, None, reason_code="WEAK_MATCH_ONLY")
            
            scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
            
            if len(scored_candidates) > 1:
                best_sim = scored_candidates[0]["similarity"]
                second_sim = scored_candidates[1]["similarity"]
                gap = best_sim - second_sim
                
                if gap < 0.15:
                    candidates_preview = [
                        {
                            "driver_id": str(c["driver_id"]),
                            "similarity": c["similarity"]
                        }
                        for c in scored_candidates[:3]
                    ]
                    return MatchingResult(
                        None, None, None, None,
                        reason_code="MULTIPLE_CANDIDATES",
                        evidence={"candidates": candidates_preview, "gap": gap}
                    )
            
            driver_id = scored_candidates[0]["driver_id"]
            person_key = self._get_or_create_person_from_driver(driver_id, candidate)
            
            if person_key:
                return MatchingResult(
                    person_key,
                    "R3_PLATE_EXACT_NAME_SIMILAR",
                    85,
                    ConfidenceLevel.MEDIUM,
                    evidence={
                        "plate_normalized": candidate.plate_norm,
                        "name_similarity": scored_candidates[0]["similarity"]
                    },
                    driver_id=driver_id
                )
            
            return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
        except Exception as e:
            logger.error(f"Error en R3: {e}")
            return MatchingResult(None, None, None, None, reason_code="ERROR")
    
    def _apply_rule_r3b_plate_name_no_date(self, candidate: IdentityCandidateInput) -> MatchingResult:
        """
        Regla R3b: Matching por placa + nombre SIN restricción de fecha.
        Se usa cuando R3 no encuentra candidatos por restricción de fecha.
        Menor confianza que R3 (MEDIUM en lugar de HIGH).
        """
        try:
            query = text("""
                SELECT driver_id, park_id, full_name_norm, hire_date
                FROM canon.drivers_index
                WHERE plate_norm = :plate_norm
                AND park_id = :park_id_objetivo
                LIMIT 20
            """)
            
            try:
                result = self.db.execute(query, {
                    "plate_norm": candidate.plate_norm,
                    "park_id_objetivo": self.park_id_objetivo
                })
                candidates = result.fetchall()
            except (OperationalError, DisconnectionError, PendingRollbackError) as e:
                raise
            
            if not candidates:
                return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
            scored_candidates = []
            for c in candidates:
                similarity = name_similarity(candidate.name_norm, c.full_name_norm, self.name_similarity_threshold)
                if similarity >= self.name_similarity_threshold:
                    scored_candidates.append({
                        "driver_id": c.driver_id,
                        "park_id": c.park_id,
                        "similarity": similarity
                    })
            
            if not scored_candidates:
                return MatchingResult(None, None, None, None, reason_code="WEAK_MATCH_ONLY")
            
            scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
            
            if len(scored_candidates) > 1:
                best_sim = scored_candidates[0]["similarity"]
                second_sim = scored_candidates[1]["similarity"]
                gap = best_sim - second_sim
                
                if gap < 0.15:
                    candidates_preview = [
                        {
                            "driver_id": str(c["driver_id"]),
                            "similarity": c["similarity"]
                        }
                        for c in scored_candidates[:3]
                    ]
                    return MatchingResult(
                        None, None, None, None,
                        reason_code="MULTIPLE_CANDIDATES",
                        evidence={"candidates": candidates_preview, "gap": gap}
                    )
            
            # Match exitoso - obtener person_key
            best_driver_id = scored_candidates[0]["driver_id"]
            best_similarity = scored_candidates[0]["similarity"]
            
            person_key_query = text("""
                SELECT person_key
                FROM canon.identity_links
                WHERE source_table = 'drivers'
                AND source_pk = :driver_id
                LIMIT 1
            """)
            
            person_key_result = self.db.execute(person_key_query, {"driver_id": best_driver_id})
            person_key_row = person_key_result.fetchone()
            
            if not person_key_row or not person_key_row.person_key:
                return MatchingResult(None, None, None, None, reason_code="NO_PERSON_KEY")
            
            return MatchingResult(
                person_key_row.person_key,
                "R3b",  # Regla R3b
                int(best_similarity * 100),
                ConfidenceLevel.MEDIUM,  # Menor confianza que R3
                evidence={
                    "driver_id": str(best_driver_id),
                    "similarity": best_similarity,
                    "rule": "R3b_PLATE_NAME_NO_DATE"
                }
            )
        
        except Exception as e:
            logger.error(f"Error en R3b matching: {e}", exc_info=True)
            return MatchingResult(None, None, None, None, reason_code="ERROR")

    def _apply_rule_r4_car_fingerprint_name(self, candidate: IdentityCandidateInput) -> MatchingResult:
        try:
            car_fingerprint = f"{candidate.brand_norm}|{candidate.model_norm}"
            date_from = candidate.snapshot_date - timedelta(days=30)
            date_to = candidate.snapshot_date + timedelta(days=7)
            
            query = text("""
                SELECT driver_id, park_id, full_name_norm, hire_date
                FROM canon.drivers_index
                WHERE park_id = :park_id_objetivo
                AND brand_norm = :brand_norm
                AND model_norm = :model_norm
                AND (hire_date IS NULL OR hire_date BETWEEN :date_from AND :date_to)
                LIMIT 20
            """)
            
            result = self.db.execute(query, {
                "park_id_objetivo": self.park_id_objetivo,
                "date_from": date_from,
                "date_to": date_to,
                "brand_norm": candidate.brand_norm,
                "model_norm": candidate.model_norm
            })
            candidates = result.fetchall()
            
            if not candidates:
                return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
            scored_candidates = []
            for c in candidates:
                similarity = name_similarity(candidate.name_norm, c.full_name_norm, self.name_similarity_threshold)
                if similarity >= self.name_similarity_threshold:
                    scored_candidates.append({
                        "driver_id": c.driver_id,
                        "park_id": c.park_id,
                        "similarity": similarity
                    })
            
            if not scored_candidates:
                return MatchingResult(None, None, None, None, reason_code="WEAK_MATCH_ONLY")
            
            scored_candidates.sort(key=lambda x: x["similarity"], reverse=True)
            
            if len(scored_candidates) > 1:
                best_sim = scored_candidates[0]["similarity"]
                second_sim = scored_candidates[1]["similarity"]
                gap = best_sim - second_sim
                
                if gap < 0.15:
                    candidates_preview = [
                        {
                            "driver_id": str(c["driver_id"]),
                            "similarity": c["similarity"]
                        }
                        for c in scored_candidates[:3]
                    ]
                    return MatchingResult(
                        None, None, None, None,
                        reason_code="MULTIPLE_CANDIDATES",
                        evidence={"candidates": candidates_preview, "gap": gap}
                    )
            
            driver_id = scored_candidates[0]["driver_id"]
            person_key = self._get_or_create_person_from_driver(driver_id, candidate)
            
            if person_key:
                return MatchingResult(
                    person_key,
                    "R4_CAR_FINGERPRINT_NAME_SIMILAR",
                    75,
                    ConfidenceLevel.LOW,
                    evidence={
                        "car_fingerprint": car_fingerprint,
                        "name_similarity": scored_candidates[0]["similarity"]
                    },
                    driver_id=driver_id
                )
            
            return MatchingResult(None, None, None, None, reason_code="NO_CANDIDATES")
            
        except Exception as e:
            logger.error(f"Error en R4: {e}")
            return MatchingResult(None, None, None, None, reason_code="ERROR")

    def _get_or_create_person_from_driver(self, driver_id: str, candidate: IdentityCandidateInput) -> Optional[UUID]:
        existing_link = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == "drivers",
            IdentityLink.source_pk == driver_id
        ).first()
        
        if existing_link:
            return existing_link.person_key
        
        query = text("""
            SELECT phone, license_number, license_normalized_number, full_name, first_name, middle_name, last_name
            FROM public.drivers
            WHERE driver_id = :driver_id
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"driver_id": driver_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        phone_norm = normalize_phone(row.phone)
        license_norm = normalize_license(row.license_normalized_number or row.license_number)
        name_norm = normalize_name(row.full_name or f"{row.first_name or ''} {row.middle_name or ''} {row.last_name or ''}".strip())
        
        existing_person = None
        if phone_norm:
            existing_person = self.db.query(IdentityRegistry).filter(
                IdentityRegistry.primary_phone == phone_norm
            ).first()
        
        if not existing_person and license_norm:
            existing_person = self.db.query(IdentityRegistry).filter(
                IdentityRegistry.primary_license == license_norm
            ).first()
        
        if existing_person:
            person_key = existing_person.person_key
        else:
            person_key = uuid4()
            person = IdentityRegistry(
                person_key=person_key,
                confidence_level=ConfidenceLevel.HIGH,
                primary_phone=phone_norm,
                primary_license=license_norm,
                primary_full_name=name_norm
            )
            self.db.add(person)
            self.db.flush()
        
        return person_key
