"""
Scouting observation service for matching scouting data with canonical identities.

Processes scouting daily records and attempts to match them with existing
identity records using multiple strategies (license, phone, name similarity).
"""
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, text
from sqlalchemy.orm import Session

from app.models.canon import IdentityLink, IdentityRegistry
from app.models.observational import ConfidenceLevelObs, MatchedSource, ScoutingMatchCandidate
from app.services.data_contract import DataContract
from app.services.normalization import (
    digits_only,
    name_similarity,
    normalize_license_simple,
    normalize_name,
    normalize_phone,
    normalize_phone_pe9,
)

logger = logging.getLogger(__name__)


class ScoutingObservationService:
    def __init__(self, db: Session):
        self.db = db

    def process_scouting_observations(
        self,
        run_id: Optional[int],
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, int]:
        stats = {
            "processed": 0,
            "candidates_s1_license": 0,
            "candidates_s2_phone": 0,
            "candidates_s3_name": 0,
            "no_candidates": 0
        }

        query_str = """
            SELECT *
            FROM public.module_ct_scouting_daily
        """
        params = {}

        if date_from or date_to:
            conditions = []
            if date_from:
                conditions.append("registration_date >= :date_from")
                params["date_from"] = date_from
            if date_to:
                conditions.append("registration_date <= :date_to")
                params["date_to"] = date_to
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

        query = text(query_str)
        result = self.db.execute(query, params)
        rows = result.fetchall()

        batch_size = 50
        for idx, row in enumerate(rows):
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            except Exception as e:
                logger.error(f"Error procesando row: {e}")
                continue

            stats["processed"] += 1

            mapped = DataContract.map_row("module_ct_scouting_daily", row_dict)
            scouting_row_id = str(mapped.get("source_pk", ""))
            scouting_date = mapped.get("snapshot_date")

            if not scouting_date or not scouting_row_id:
                continue

            if isinstance(scouting_date, datetime):
                scouting_date = scouting_date.date()
            elif isinstance(scouting_date, date):
                pass
            else:
                continue

            week_label = self._get_week_label(scouting_date)

            existing = self.db.query(ScoutingMatchCandidate).filter(
                ScoutingMatchCandidate.scouting_row_id == scouting_row_id,
                ScoutingMatchCandidate.scouting_date == scouting_date
            ).first()

            if existing:
                continue

            phone_raw = mapped.get("phone_raw")
            name_raw = mapped.get("name_raw")
            license_raw = mapped.get("license_raw")

            candidate_result = None

            if license_raw:
                candidate_result = self._apply_rule_s1(license_raw, scouting_date, scouting_row_id, week_label, run_id)

            if not candidate_result and phone_raw:
                candidate_result = self._apply_rule_s2(phone_raw, scouting_date, scouting_row_id, week_label, run_id)

            if not candidate_result and name_raw:
                candidate_result = self._apply_rule_s3(name_raw, scouting_date, scouting_row_id, week_label, run_id)

            if candidate_result:
                if candidate_result.get("rule") == "S1":
                    stats["candidates_s1_license"] += 1
                elif candidate_result.get("rule") == "S2":
                    stats["candidates_s2_phone"] += 1
                elif candidate_result.get("rule") == "S3":
                    stats["candidates_s3_name"] += 1
            else:
                self._insert_no_candidate(scouting_row_id, scouting_date, week_label, run_id)
                stats["no_candidates"] += 1

            # Commit intermedio cada batch_size registros
            if (idx + 1) % batch_size == 0:
                try:
                    self.db.commit()
                except Exception as e:
                    self.db.rollback()
                    raise

        self.db.commit()
        return stats

    def _apply_rule_s1(
        self,
        license_raw: str,
        scouting_date: date,
        scouting_row_id: str,
        week_label: str,
        run_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        license_norm = normalize_license_simple(license_raw)
        if not license_norm:
            return None

        query = text("""
            SELECT driver_id, license_number, hire_date, created_at
            FROM public.drivers
            WHERE UPPER(TRIM(license_number)) = :license_norm
            LIMIT 1
        """)

        result = self.db.execute(query, {"license_norm": license_norm})
        driver_row = result.first()

        if driver_row:
            driver_id = driver_row.driver_id
            person_key = self._get_person_key_for_driver(driver_id)
            
            driver_date = driver_row.hire_date or driver_row.created_at
            if isinstance(driver_date, datetime):
                driver_date = driver_date.date()
            elif not isinstance(driver_date, date):
                driver_date = scouting_date
            
            time_to_match = (driver_date - scouting_date).days

            try:
                self._insert_candidate(
                    scouting_row_id=scouting_row_id,
                    scouting_date=scouting_date,
                    week_label=week_label,
                    person_key_candidate=person_key,
                    matched_source=MatchedSource.DRIVERS.value,
                    match_rule="S1",
                    score=0.95,
                    confidence_level=ConfidenceLevelObs.HIGH.value,
                    matched_source_pk=driver_id,
                    matched_source_date=driver_date,
                    time_to_match_days=time_to_match,
                    run_id=run_id,
                    notes=f"Match por licencia exacta: {license_norm}"
                )
            except Exception as e:
                raise

            return {
                "rule": "S1",
                "person_key": person_key,
                "matched_source": "drivers",
                "matched_source_pk": driver_id
            }

        return None

    def _apply_rule_s2(
        self,
        phone_raw: str,
        scouting_date: date,
        scouting_row_id: str,
        week_label: str,
        run_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        phone_pe9 = normalize_phone_pe9(phone_raw)
        if not phone_pe9:
            return None

        query = text("""
            SELECT driver_id, phone, hire_date, created_at
            FROM public.drivers
            WHERE RIGHT(REGEXP_REPLACE(phone, '\\D', '', 'g'), 9) = :phone_pe9
            LIMIT 1
        """)

        result = self.db.execute(query, {"phone_pe9": phone_pe9})
        driver_row = result.first()

        if driver_row:
            driver_id = driver_row.driver_id
            person_key = self._get_person_key_for_driver(driver_id)
            
            driver_date = driver_row.hire_date or driver_row.created_at
            if isinstance(driver_date, datetime):
                driver_date = driver_date.date()
            elif not isinstance(driver_date, date):
                driver_date = scouting_date
            
            time_to_match = (driver_date - scouting_date).days

            try:
                self._insert_candidate(
                    scouting_row_id=scouting_row_id,
                    scouting_date=scouting_date,
                    week_label=week_label,
                    person_key_candidate=person_key,
                    matched_source=MatchedSource.DRIVERS.value,
                    match_rule="S2",
                    score=0.85,
                    confidence_level=ConfidenceLevelObs.HIGH.value,
                    matched_source_pk=driver_id,
                    matched_source_date=driver_date,
                    time_to_match_days=time_to_match,
                    run_id=run_id,
                    notes=f"Match por teléfono PE9: {phone_pe9}"
                )
            except Exception as e:
                raise

            return {
                "rule": "S2",
                "person_key": person_key,
                "matched_source": "drivers",
                "matched_source_pk": driver_id
            }

        return None

    def _apply_rule_s3(
        self,
        name_raw: str,
        scouting_date: date,
        scouting_row_id: str,
        week_label: str,
        run_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        name_norm = normalize_name(name_raw)
        if not name_norm:
            return None

        query = text("""
            SELECT driver_id, full_name, hire_date, created_at
            FROM public.drivers
            WHERE full_name IS NOT NULL
            LIMIT 100
        """)

        result = self.db.execute(query)
        drivers = result.fetchall()

        for driver_row in drivers:
            driver_name = driver_row.full_name
            if not driver_name:
                continue

            driver_name_norm = normalize_name(driver_name)
            if not driver_name_norm:
                continue

            similarity = name_similarity(name_norm, driver_name_norm)
            if similarity >= 0.5:
                driver_id = driver_row.driver_id
                person_key = self._get_person_key_for_driver(driver_id)
                
                driver_date = driver_row.hire_date or driver_row.created_at
                if isinstance(driver_date, datetime):
                    driver_date = driver_date.date()
                elif not isinstance(driver_date, date):
                    driver_date = scouting_date
                
                time_to_match = (driver_date - scouting_date).days

                self._insert_candidate(
                    scouting_row_id=scouting_row_id,
                    scouting_date=scouting_date,
                    week_label=week_label,
                    person_key_candidate=person_key,
                    matched_source=MatchedSource.DRIVERS.value,
                    match_rule="S3",
                    score=0.60,
                    confidence_level=ConfidenceLevelObs.LOW.value,
                    matched_source_pk=driver_id,
                    matched_source_date=driver_date,
                    time_to_match_days=time_to_match,
                    run_id=run_id,
                    notes=f"Match por nombre similar: {similarity:.2f}"
                )

                return {
                    "rule": "S3",
                    "person_key": person_key,
                    "matched_source": "drivers",
                    "matched_source_pk": driver_id
                }

        return None

    def _get_person_key_for_driver(self, driver_id: str) -> Optional[UUID]:
        link = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == "drivers",
            IdentityLink.source_pk == driver_id
        ).first()
        
        return link.person_key if link else None

    def _insert_candidate(
        self,
        scouting_row_id: str,
        scouting_date: date,
        week_label: str,
        person_key_candidate: Optional[UUID],
        matched_source: str,
        match_rule: str,
        score: float,
        confidence_level: str,
        matched_source_pk: str,
        matched_source_date: date,
        time_to_match_days: int,
        run_id: Optional[int],
        notes: Optional[str] = None
    ):
        try:
            # Pasar directamente el string (valor) al modelo
            # El TypeDecorator lo convertirá al enum correctamente
            # Asegurarnos de que tenemos el valor, no el nombre del enum
            if isinstance(matched_source, str):
                matched_source_value = matched_source
            elif isinstance(matched_source, MatchedSource):
                matched_source_value = matched_source.value
            else:
                matched_source_value = str(matched_source)
                
            if isinstance(confidence_level, str):
                confidence_level_value = confidence_level
            elif isinstance(confidence_level, ConfidenceLevelObs):
                confidence_level_value = confidence_level.value
            else:
                confidence_level_value = str(confidence_level)
            
            candidate = ScoutingMatchCandidate(
                week_label=week_label,
                scouting_row_id=scouting_row_id,
                scouting_date=scouting_date,
                person_key_candidate=person_key_candidate,
                matched_source=matched_source_value,
                match_rule=match_rule,
                score=score,
                confidence_level=confidence_level_value,
                matched_source_pk=matched_source_pk,
                matched_source_date=matched_source_date,
                time_to_match_days=time_to_match_days,
                notes=notes,
                run_id=run_id
            )
            self.db.add(candidate)
        except Exception as e:
            raise

    def _insert_no_candidate(
        self,
        scouting_row_id: str,
        scouting_date: date,
        week_label: str,
        run_id: Optional[int]
    ):
        candidate = ScoutingMatchCandidate(
            week_label=week_label,
            scouting_row_id=scouting_row_id,
            scouting_date=scouting_date,
            person_key_candidate=None,
            matched_source=MatchedSource.NONE.value,
            match_rule=None,
            score=0.00,
            confidence_level=ConfidenceLevelObs.LOW.value,
            matched_source_pk=None,
            matched_source_date=None,
            time_to_match_days=None,
            notes=None,
            run_id=run_id
        )
        self.db.add(candidate)

    def _get_week_label(self, date_obj: date) -> str:
        iso_calendar = date_obj.isocalendar()
        year = iso_calendar[0]
        week_num = iso_calendar[1]
        return f"{year}-W{week_num:02d}"

