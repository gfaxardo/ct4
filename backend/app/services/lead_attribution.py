import logging
from typing import Optional, Dict, Any, List
from datetime import date, datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from sqlalchemy.exc import IntegrityError

from app.models.observational import LeadEvent, LeadLedger, AttributionConfidence, DecisionStatus
from app.models.canon import IdentityLink
from app.services.data_contract import DataContract
from app.services.normalization import (
    normalize_phone, normalize_license, normalize_phone_pe9
)
from app.services.matching import MatchingEngine, IdentityCandidateInput
from app.config import PARK_ID_OBJETIVO

logger = logging.getLogger(__name__)


class LeadAttributionService:
    def __init__(self, db: Session):
        self.db = db
        self.matching_engine = MatchingEngine(db, park_id_objetivo=PARK_ID_OBJETIVO)

    def populate_events_from_scouting(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None
    ) -> Dict[str, int]:
        stats = {"processed": 0, "created": 0, "skipped": 0, "errors": 0}

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

        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                
                source_pk = str(row_dict.get("id", ""))
                if not source_pk:
                    stats["errors"] += 1
                    continue

                existing_event = self.db.query(LeadEvent).filter(
                    LeadEvent.source_table == "module_ct_scouting_daily",
                    LeadEvent.source_pk == source_pk
                ).first()

                if existing_event:
                    stats["skipped"] += 1
                    continue

                event_date = row_dict.get("registration_date")
                if isinstance(event_date, str):
                    try:
                        event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                    except:
                        event_date = None
                elif isinstance(event_date, datetime):
                    event_date = event_date.date()

                if not event_date:
                    stats["errors"] += 1
                    continue

                scout_id = row_dict.get("scout_id")
                driver_license = row_dict.get("driver_license")
                driver_phone = row_dict.get("driver_phone")

                person_key = None
                needs_identity_link = False
                matching_evidence = {}

                if driver_license or driver_phone:
                    driver_id = None
                    
                    if driver_license:
                        license_norm = normalize_license(driver_license)
                        if license_norm:
                            query_license = text("""
                                SELECT driver_id
                                FROM canon.drivers_index
                                WHERE license_norm = :license_norm
                                LIMIT 1
                            """)
                            result_license = self.db.execute(query_license, {"license_norm": license_norm})
                            driver_row = result_license.fetchone()
                            if driver_row:
                                driver_id = driver_row.driver_id
                                matching_evidence["s1_license_match"] = True
                                matching_evidence["license_norm"] = license_norm

                    if not driver_id and driver_phone:
                        phone_pe9 = normalize_phone_pe9(driver_phone)
                        if phone_pe9:
                            query_phone = text("""
                                SELECT driver_id
                                FROM canon.drivers_index
                                WHERE RIGHT(phone_norm, 9) = :phone_pe9
                                LIMIT 10
                            """)
                            result_phone = self.db.execute(query_phone, {"phone_pe9": phone_pe9})
                            candidates = result_phone.fetchall()
                            
                            if len(candidates) == 1:
                                driver_id = candidates[0].driver_id
                                matching_evidence["s2_phone_match"] = True
                                matching_evidence["phone_pe9"] = phone_pe9
                            elif len(candidates) > 1:
                                matching_evidence["s2_phone_ambiguous"] = True
                                matching_evidence["candidates_count"] = len(candidates)

                    if driver_id:
                        identity_link = self.db.query(IdentityLink).filter(
                            IdentityLink.source_table == "drivers",
                            IdentityLink.source_pk == str(driver_id)
                        ).first()

                        if identity_link:
                            person_key = identity_link.person_key
                            matching_evidence["identity_link_found"] = True
                        else:
                            needs_identity_link = True
                            matching_evidence["identity_link_missing"] = True
                    else:
                        needs_identity_link = True
                        matching_evidence["driver_not_found"] = True
                else:
                    needs_identity_link = True
                    matching_evidence["no_matching_data"] = True

                payload = {
                    "driver_name": row_dict.get("driver_name"),
                    "driver_phone": driver_phone,
                    "driver_license": driver_license,
                    "acquisition_method": row_dict.get("acquisition_method"),
                    "matching_evidence": matching_evidence
                }

                if needs_identity_link:
                    payload["needs_identity_link"] = True

                event = LeadEvent(
                    source_table="module_ct_scouting_daily",
                    source_pk=source_pk,
                    event_date=event_date,
                    person_key=person_key,
                    scout_id=scout_id,
                    payload_json=payload
                )

                self.db.add(event)
                stats["created"] += 1

            except Exception as e:
                logger.error(f"Error procesando scouting row {idx}: {e}")
                stats["errors"] += 1
                continue

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al poblar eventos de scouting: {e}")
            stats["errors"] += stats["created"]
            stats["created"] = 0

        return stats

    def populate_events_from_cabinet(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, int]:
        stats = {"processed": 0, "created": 0, "skipped": 0, "errors": 0}

        query_str = """
            SELECT *
            FROM public.module_ct_cabinet_leads
        """
        params = {}
        
        if date_from or date_to:
            conditions = []
            if date_from:
                conditions.append("(lead_created_at::date >= :date_from OR created_at::date >= :date_from)")
                params["date_from"] = date_from
            if date_to:
                conditions.append("(lead_created_at::date <= :date_to OR created_at::date <= :date_to)")
                params["date_to"] = date_to
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

        query = text(query_str)
        result = self.db.execute(query, params)
        rows = result.fetchall()

        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                
                mapped = DataContract.map_row("module_ct_cabinet_leads", row_dict)
                source_pk = str(mapped.get("source_pk", ""))
                
                if not source_pk:
                    stats["errors"] += 1
                    continue

                existing_event = self.db.query(LeadEvent).filter(
                    LeadEvent.source_table == "module_ct_cabinet_leads",
                    LeadEvent.source_pk == source_pk
                ).first()

                if existing_event:
                    stats["skipped"] += 1
                    continue

                event_date = mapped.get("snapshot_date")
                if isinstance(event_date, datetime):
                    event_date = event_date.date()
                elif isinstance(event_date, date):
                    pass
                else:
                    lead_created_at = row_dict.get("lead_created_at")
                    created_at = row_dict.get("created_at")
                    if lead_created_at:
                        if isinstance(lead_created_at, datetime):
                            event_date = lead_created_at.date()
                        elif isinstance(lead_created_at, date):
                            event_date = lead_created_at
                    elif created_at:
                        if isinstance(created_at, datetime):
                            event_date = created_at.date()
                        elif isinstance(created_at, date):
                            event_date = created_at
                    else:
                        event_date = datetime.utcnow().date()

                if not event_date:
                    stats["errors"] += 1
                    continue

                snapshot_date = datetime.combine(event_date, datetime.min.time())
                candidate = IdentityCandidateInput(
                    source_table="module_ct_cabinet_leads",
                    source_pk=source_pk,
                    snapshot_date=snapshot_date,
                    park_id=mapped.get("park_id"),
                    phone_norm=normalize_phone(mapped.get("phone_raw")),
                    license_norm=normalize_license(mapped.get("license_raw")),
                    plate_norm=None,
                    name_norm=None,
                    brand_norm=None,
                    model_norm=None
                )

                match_result = self.matching_engine.match_person(candidate)
                person_key = match_result.person_key if match_result else None

                payload = {
                    "first_name": row_dict.get("first_name"),
                    "middle_name": row_dict.get("middle_name"),
                    "last_name": row_dict.get("last_name"),
                    "park_phone": row_dict.get("park_phone"),
                    "asset_plate_number": row_dict.get("asset_plate_number"),
                    "asset_model": row_dict.get("asset_model"),
                    "match_rule": match_result.rule if match_result else None,
                    "match_score": match_result.score if match_result else None
                }

                event = LeadEvent(
                    source_table="module_ct_cabinet_leads",
                    source_pk=source_pk,
                    event_date=event_date,
                    person_key=person_key,
                    scout_id=None,
                    payload_json=payload
                )

                self.db.add(event)
                stats["created"] += 1

            except Exception as e:
                logger.error(f"Error procesando cabinet row {idx}: {e}")
                stats["errors"] += 1
                continue

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al poblar eventos de cabinet: {e}")
            stats["errors"] += stats["created"]
            stats["created"] = 0

        return stats

    def _get_hire_date_for_person(self, person_key: UUID) -> Optional[date]:
        query = text("""
            SELECT d.hire_date
            FROM canon.identity_links il
            JOIN public.drivers d ON d.driver_id = il.source_pk
            WHERE il.person_key = :person_key
            AND il.source_table = 'drivers'
            AND d.hire_date IS NOT NULL
            ORDER BY d.hire_date ASC
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"person_key": person_key})
        row = result.fetchone()
        return row.hire_date if row else None

    def process_ledger(self, person_keys: Optional[List[UUID]] = None) -> Dict[str, int]:
        stats = {"processed": 0, "assigned": 0, "unassigned": 0, "conflict": 0, "errors": 0}

        if person_keys:
            events_query = self.db.query(LeadEvent).filter(
                LeadEvent.person_key.in_(person_keys),
                LeadEvent.person_key.isnot(None)
            )
        else:
            events_query = self.db.query(LeadEvent).filter(
                LeadEvent.person_key.isnot(None)
            )

        events = events_query.all()
        
        person_events_map: Dict[UUID, List[LeadEvent]] = {}
        for event in events:
            if event.person_key:
                if event.person_key not in person_events_map:
                    person_events_map[event.person_key] = []
                person_events_map[event.person_key].append(event)

        for person_key, events_list in person_events_map.items():
            stats["processed"] += 1
            
            try:
                hire_date = self._get_hire_date_for_person(person_key)
                
                scouting_events = [e for e in events_list if e.scout_id is not None]
                cabinet_events = [e for e in events_list if e.scout_id is None]
                
                if not scouting_events and not cabinet_events:
                    continue

                window_anchor = None
                window_from = None
                window_to = None
                
                if hire_date:
                    window_anchor = hire_date
                    window_from = hire_date - timedelta(days=7)
                    window_to = hire_date + timedelta(days=7)
                elif scouting_events:
                    first_scouting = min(scouting_events, key=lambda e: e.event_date)
                    window_anchor = first_scouting.event_date
                    window_from = window_anchor - timedelta(days=7)
                    window_to = window_anchor + timedelta(days=7)

                scouting_in_window = []
                if window_from and window_to:
                    scouting_in_window = [
                        e for e in scouting_events
                        if window_from <= e.event_date <= window_to
                    ]
                else:
                    scouting_in_window = scouting_events

                unique_scouts = {}
                for event in scouting_in_window:
                    if event.scout_id:
                        if event.scout_id not in unique_scouts:
                            unique_scouts[event.scout_id] = {
                                "count": 0,
                                "dates": []
                            }
                        unique_scouts[event.scout_id]["count"] += 1
                        unique_scouts[event.scout_id]["dates"].append(event.event_date.isoformat())

                has_conflict = len(unique_scouts) >= 2

                if has_conflict:
                    sorted_scouts = sorted(
                        unique_scouts.items(),
                        key=lambda x: x[1]["count"],
                        reverse=True
                    )
                    top2_scouts = [
                        {
                            "scout_id": scout_id,
                            "count": data["count"],
                            "dates": data["dates"]
                        }
                        for scout_id, data in sorted_scouts[:2]
                    ]

                    evidence = {
                        "scout_ids": top2_scouts,
                        "window_anchor": window_anchor.isoformat() if window_anchor else None,
                        "window_range": [
                            window_from.isoformat() if window_from else None,
                            window_to.isoformat() if window_to else None
                        ],
                        "total_scouts": len(unique_scouts)
                    }

                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="scouting",
                        attributed_scout_id=None,
                        attribution_rule="C",
                        attribution_score=0.0,
                        confidence_level=AttributionConfidence.LOW,
                        evidence_json=evidence,
                        decision_status=DecisionStatus.CONFLICT
                    )

                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()

                    if existing:
                        for key, value in ledger_entry.__dict__.items():
                            if not key.startswith("_") and key != "person_key":
                                setattr(existing, key, value)
                    else:
                        self.db.add(ledger_entry)

                    stats["conflict"] += 1

                elif scouting_events:
                    all_scouts_data = []
                    for event in scouting_events:
                        if event.scout_id:
                            all_scouts_data.append({
                                "scout_id": event.scout_id,
                                "event_date": event.event_date.isoformat()
                            })

                    most_recent_event = max(scouting_events, key=lambda e: e.event_date)
                    selected_scout_id = most_recent_event.scout_id

                    candidates_for_tiebreak = []
                    if window_anchor:
                        for event in scouting_events:
                            if event.scout_id:
                                days_from_anchor = abs((event.event_date - window_anchor).days)
                                candidates_for_tiebreak.append({
                                    "scout_id": event.scout_id,
                                    "event_date": event.event_date.isoformat(),
                                    "days_from_anchor": days_from_anchor
                                })

                    evidence = {
                        "all_scouts": all_scouts_data,
                        "selected_scout_id": selected_scout_id,
                        "selection_reason": "temporal_most_recent",
                        "candidates_for_tiebreak": candidates_for_tiebreak,
                        "window_anchor": window_anchor.isoformat() if window_anchor else None
                    }

                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="scouting",
                        attributed_scout_id=selected_scout_id,
                        attribution_rule="A",
                        attribution_score=0.95,
                        confidence_level=AttributionConfidence.HIGH,
                        evidence_json=evidence,
                        decision_status=DecisionStatus.ASSIGNED
                    )

                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()

                    if existing:
                        for key, value in ledger_entry.__dict__.items():
                            if not key.startswith("_") and key != "person_key":
                                setattr(existing, key, value)
                    else:
                        self.db.add(ledger_entry)

                    stats["assigned"] += 1

                elif cabinet_events:
                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="cabinet",
                        attributed_scout_id=None,
                        attribution_rule="B",
                        attribution_score=0.80,
                        confidence_level=AttributionConfidence.MEDIUM,
                        evidence_json=None,
                        decision_status=DecisionStatus.ASSIGNED
                    )

                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()

                    if existing:
                        for key, value in ledger_entry.__dict__.items():
                            if not key.startswith("_") and key != "person_key":
                                setattr(existing, key, value)
                    else:
                        self.db.add(ledger_entry)

                    stats["assigned"] += 1

                else:
                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source=None,
                        attributed_scout_id=None,
                        attribution_rule=None,
                        attribution_score=0.0,
                        confidence_level=AttributionConfidence.LOW,
                        evidence_json=None,
                        decision_status=DecisionStatus.UNASSIGNED
                    )

                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()

                    if existing:
                        for key, value in ledger_entry.__dict__.items():
                            if not key.startswith("_") and key != "person_key":
                                setattr(existing, key, value)
                    else:
                        self.db.add(ledger_entry)

                    stats["unassigned"] += 1

            except Exception as e:
                logger.error(f"Error procesando ledger para person_key {person_key}: {e}")
                stats["errors"] += 1
                continue

        try:
            self.db.commit()
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al procesar ledger: {e}")
            stats["errors"] += stats["processed"]
            stats["processed"] = 0

        return stats

