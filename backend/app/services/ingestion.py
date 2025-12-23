import logging
import json
from datetime import datetime, date
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, PendingRollbackError, DisconnectionError
from uuid import uuid4, UUID
from app.models.canon import IdentityRegistry, IdentityLink, IdentityUnmatched, ConfidenceLevel, UnmatchedStatus
from app.models.ops import IngestionRun, RunStatus, JobType
import time
from app.services.normalization import normalize_phone, normalize_name, normalize_license, normalize_plate, parse_date
from app.services.matching import MatchingEngine, IdentityCandidateInput
from app.services.data_contract import DataContract
from app.db import SessionLocal

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.matching_engine = MatchingEngine(db)

    def run_ingestion(self, scope_date_from: Optional[date] = None, scope_date_to: Optional[date] = None,
                     scope_date: Optional[date] = None, source_tables: Optional[list] = None,
                     incremental: bool = True, run_id: Optional[int] = None, refresh_index: bool = False) -> IngestionRun:
        start_time = time.time()
        timings = {}
        
        if scope_date:
            scope_date_from = scope_date
            scope_date_to = scope_date
        
        if run_id:
            run = self.db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
            if not run:
                raise ValueError(f"Run con id {run_id} no encontrado")
            run_id = run.id
        else:
            if incremental and not scope_date_from:
                last_run = self.db.query(IngestionRun).filter(
                    IngestionRun.status == RunStatus.COMPLETED,
                    IngestionRun.job_type == JobType.IDENTITY_RUN
                ).order_by(IngestionRun.completed_at.desc()).first()
                
                if last_run and last_run.scope_date_to:
                    scope_date_from = last_run.scope_date_to
                    logger.info({"message": "Modo incremental activado", "last_run_date": str(scope_date_from)})
            
            run = IngestionRun(
                status=RunStatus.RUNNING,
                job_type=JobType.IDENTITY_RUN,
                scope_date_from=scope_date_from,
                scope_date_to=scope_date_to,
                incremental=incremental
            )
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)
            run_id = run.id

        try:
            logger.info({
                "message": "Iniciando ingesta",
                "run_id": run_id,
                "incremental": incremental,
                "scope_date_from": str(scope_date_from),
                "scope_date_to": str(scope_date_to),
                "source_tables": source_tables or ["module_ct_cabinet_leads", "module_ct_scouting_daily"],
                "refresh_index": refresh_index
            })

            if refresh_index:
                logger.info({"message": "Refrescando drivers_index", "run_id": run_id})
                refresh_start = time.time()
                self._refresh_drivers_index()
                refresh_elapsed = time.time() - refresh_start
                logger.info({"message": "drivers_index refrescado", "run_id": run_id, "elapsed_seconds": round(refresh_elapsed, 2)})

            stats = {
                "cabinet_leads": {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0},
                "scouting_daily": {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0},
            }

            source_tables = source_tables or ["module_ct_cabinet_leads", "module_ct_scouting_daily"]

            if "module_ct_cabinet_leads" in source_tables:
                stage_start = time.time()
                count_query = self._get_count_query("module_ct_cabinet_leads", scope_date_from, scope_date_to)
                total_count = self.db.execute(text(count_query["query"]), count_query["params"]).scalar()
                logger.info({"message": "Count cabinet_leads", "total": total_count})
                
                stats["cabinet_leads"] = self.process_cabinet_leads(run_id, scope_date_from, scope_date_to)
                timings["process_cabinet_leads"] = time.time() - stage_start
                logger.info({"message": "process_cabinet_leads completado", "elapsed": timings["process_cabinet_leads"], "stats": stats["cabinet_leads"]})

            if "module_ct_scouting_daily" in source_tables:
                stage_start = time.time()
                count_query = self._get_count_query("module_ct_scouting_daily", scope_date_from, scope_date_to)
                total_count = self.db.execute(text(count_query["query"]), count_query["params"]).scalar()
                logger.info({"message": "Count scouting_daily", "total": total_count})
                
                stats["scouting_daily"] = self.process_scouting_daily(run_id, scope_date_from, scope_date_to)
                timings["process_scouting_daily"] = time.time() - stage_start
                logger.info({"message": "process_scouting_daily completado", "elapsed": timings["process_scouting_daily"], "stats": stats["scouting_daily"]})

            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.stats = {**stats, "timings": timings}
            self.db.commit()

            matched_by_rule = {}
            unmatched_by_reason = {}
            
            try:
                matched_rules = self.db.query(IdentityLink.match_rule, func.count(IdentityLink.id)).filter(
                    IdentityLink.run_id == run_id
                ).group_by(IdentityLink.match_rule).all()
                matched_by_rule = {rule: count for rule, count in matched_rules}
                
                unmatched_reasons = self.db.query(IdentityUnmatched.reason_code, func.count(IdentityUnmatched.id)).filter(
                    IdentityUnmatched.run_id == run_id
                ).group_by(IdentityUnmatched.reason_code).order_by(func.count(IdentityUnmatched.id).desc()).limit(5).all()
                unmatched_by_reason = {reason: count for reason, count in unmatched_reasons}
            except Exception as e:
                logger.warning({"message": "Error obteniendo breakdown para logging", "run_id": run_id, "error": str(e)})

            total_elapsed = time.time() - start_time
            logger.info({
                "message": "Ingesta completada",
                "run_id": run_id,
                "stats": stats,
                "total_seconds": round(total_elapsed, 2),
                "timings": timings,
                "matched_by_rule": matched_by_rule,
                "unmatched_by_reason_top5": unmatched_by_reason
            })
            return run

        except (OperationalError, PendingRollbackError) as e:
            try:
                self.db.rollback()
            except:
                pass
            
            error_msg = str(e)[:500]
            logger.error({"message": "Error de conexión en ingesta", "run_id": run_id, "error": error_msg})
            
            db_new = SessionLocal()
            try:
                run_update = db_new.query(IngestionRun).filter(IngestionRun.id == run_id).first()
                if run_update:
                    run_update.status = RunStatus.FAILED
                    run_update.completed_at = datetime.utcnow()
                    run_update.error_message = error_msg
                    db_new.commit()
            except Exception as inner_e:
                logger.error({"message": "Error actualizando run estado con nueva sesión", "run_id": run_id, "error": str(inner_e)})
                db_new.rollback()
            finally:
                db_new.close()
            raise

        except Exception as e:
            error_msg = str(e)[:500]
            logger.error({"message": "Error en ingesta", "run_id": run_id, "error": error_msg})
            try:
                self.db.rollback()
                run.status = RunStatus.FAILED
                run.completed_at = datetime.utcnow()
                run.error_message = error_msg
                self.db.commit()
            except Exception as inner_e:
                logger.error({"message": "Error actualizando run estado", "run_id": run_id, "error": str(inner_e)})
                try:
                    self.db.rollback()
                except:
                    pass
                
                db_new = SessionLocal()
                try:
                    run_update = db_new.query(IngestionRun).filter(IngestionRun.id == run_id).first()
                    if run_update:
                        run_update.status = RunStatus.FAILED
                        run_update.completed_at = datetime.utcnow()
                        run_update.error_message = f"{error_msg} (Error al actualizar: {str(inner_e)[:200]})"
                        db_new.commit()
                except Exception as final_e:
                    logger.error({"message": "Error crítico actualizando run estado", "run_id": run_id, "error": str(final_e)})
                    db_new.rollback()
                finally:
                    db_new.close()
            raise

    def refresh_drivers_index_job(self) -> IngestionRun:
        run = IngestionRun(
            status=RunStatus.RUNNING,
            job_type=JobType.DRIVERS_INDEX_REFRESH
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        run_id = run.id

        try:
            logger.info({"message": "Iniciando refresh drivers_index", "run_id": run_id})
            run_date = datetime.utcnow().date()
            result = self.db.execute(text("SELECT canon.refresh_drivers_index(:run_date)"), {"run_date": run_date})
            rows_affected = result.scalar()
            self.db.commit()
            
            run.status = RunStatus.COMPLETED
            run.completed_at = datetime.utcnow()
            run.stats = {"rows_affected": rows_affected}
            self.db.commit()
            
            logger.info({"message": "Drivers index refrescado", "run_id": run_id, "rows_affected": rows_affected})
            return run
            
        except Exception as e:
            error_msg = str(e)[:500]
            logger.error({"message": "Error refrescando drivers_index", "run_id": run_id, "error": error_msg})
            try:
                self.db.rollback()
                run.status = RunStatus.FAILED
                run.completed_at = datetime.utcnow()
                run.error_message = error_msg
                self.db.commit()
            except Exception as inner_e:
                logger.error({"message": "Error actualizando run estado", "run_id": run_id, "error": str(inner_e)})
                db_new = SessionLocal()
                try:
                    run_update = db_new.query(IngestionRun).filter(IngestionRun.id == run_id).first()
                    if run_update:
                        run_update.status = RunStatus.FAILED
                        run_update.completed_at = datetime.utcnow()
                        run_update.error_message = error_msg
                        db_new.commit()
                finally:
                    db_new.close()
            raise

    def _get_count_query(self, source_table: str, date_from: Optional[date], date_to: Optional[date]) -> Dict[str, Any]:
        date_column = {
            "module_ct_cabinet_leads": "lead_created_at",
            "module_ct_scouting_daily": "registration_date"
        }.get(source_table, "created_at")
        
        query_str = f"SELECT COUNT(*) FROM public.{source_table}"
        params = {}
        
        if date_from or date_to:
            conditions = []
            if date_from:
                conditions.append(f"{date_column}::date >= :date_from")
                params["date_from"] = date_from
            if date_to:
                conditions.append(f"{date_column}::date <= :date_to")
                params["date_to"] = date_to
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)
        
        return {"query": query_str, "params": params}

    def _load_existing_links_cache(self, source_table: str, source_pks: list) -> set:
        if not source_pks:
            return set()
        
        existing = self.db.query(IdentityLink.source_pk).filter(
            IdentityLink.source_table == source_table,
            IdentityLink.source_pk.in_(source_pks)
        ).all()
        return {str(e[0]) for e in existing}

    def _refresh_drivers_index(self):
        try:
            run_date = datetime.utcnow().date()
            result = self.db.execute(text("SELECT canon.refresh_drivers_index(:run_date)"), {"run_date": run_date})
            rows_affected = result.scalar()
            self.db.commit()
            logger.info(f"Drivers index refrescado: {rows_affected} filas")
        except Exception as e:
            error_msg = str(e)
            if "function canon.refresh_drivers_index" in error_msg and "does not exist" in error_msg:
                logger.warning("La función canon.refresh_drivers_index no existe. Ejecuta la migración: alembic upgrade head")
                logger.warning("Continuando sin refrescar drivers_index. El matching puede ser más lento.")
                self.db.rollback()
            else:
                logger.error(f"Error refrescando drivers_index: {e}")
                self.db.rollback()
                raise

    def process_cabinet_leads(self, run_id: int, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict[str, int]:
        BATCH_SIZE = 1000
        stats = {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0}

        query_str = """
            SELECT *
            FROM public.module_ct_cabinet_leads
        """
        params = {}
        
        if date_from or date_to:
            conditions = []
            if date_from:
                conditions.append("lead_created_at::date >= :date_from")
                params["date_from"] = date_from
            if date_to:
                conditions.append("lead_created_at::date <= :date_to")
                params["date_to"] = date_to
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

        query = text(query_str)
        result = self.db.execute(query, params)
        rows = result.fetchall()
        
        source_pks = []
        for row in rows:
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                mapped = DataContract.map_row("module_ct_cabinet_leads", row_dict)
                source_pk = str(mapped.get("source_pk", ""))
                if source_pk:
                    source_pks.append(source_pk)
            except:
                continue
        
        existing_links_cache = self._load_existing_links_cache("module_ct_cabinet_leads", source_pks)
        
        batch_items = []
        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            except Exception as e:
                logger.error(f"Error procesando row {idx}: {e}")
                continue
            
            mapped = DataContract.map_row("module_ct_cabinet_leads", row_dict)
            
            missing_keys = DataContract.get_missing_keys("module_ct_cabinet_leads", row_dict, 
                ["source_pk", "snapshot_date"])
            
            if missing_keys:
                # Serializar mapped para evitar problemas con datetime en JSON
                mapped_serialized = self._serialize_for_json(mapped)
                batch_items.append({
                    "type": "unmatched",
                    "data": {
                        "source_table": "module_ct_cabinet_leads",
                        "source_pk": str(mapped.get("source_pk", f"unknown_{idx}")),
                        "snapshot_date": mapped.get("snapshot_date") or datetime.utcnow(),
                        "reason_code": "MISSING_KEYS",
                        "details": {"missing_keys": missing_keys, "mapped": mapped_serialized}
                    }
                })
                stats["unmatched"] += 1
                continue
            
            snapshot_date = mapped.get("snapshot_date")
            if not snapshot_date:
                date_raw = row_dict.get("lead_created_at")
                if date_raw and isinstance(date_raw, str):
                    # Serializar mapped para evitar problemas con datetime en JSON
                    mapped_serialized = self._serialize_for_json(mapped)
                    batch_items.append({
                        "type": "unmatched",
                        "data": {
                            "source_table": "module_ct_cabinet_leads",
                            "source_pk": str(mapped.get("source_pk", f"unknown_{idx}")),
                            "snapshot_date": datetime.utcnow(),
                            "reason_code": "INVALID_DATE_FORMAT",
                            "details": {"date_raw": str(date_raw), "mapped": mapped_serialized}
                        }
                    })
                    stats["unmatched"] += 1
                    continue

            source_pk = str(mapped["source_pk"])
            if source_pk in existing_links_cache:
                stats["skipped"] += 1
                continue

            snapshot_date = mapped.get("snapshot_date") or datetime.utcnow()
            if isinstance(snapshot_date, date):
                snapshot_date = datetime.combine(snapshot_date, datetime.min.time())

            candidate = IdentityCandidateInput(
                source_table="module_ct_cabinet_leads",
                source_pk=source_pk,
                snapshot_date=snapshot_date,
                park_id=mapped.get("park_id"),
                phone_norm=normalize_phone(mapped.get("phone_raw")),
                license_norm=normalize_license(mapped.get("license_raw")),
                plate_norm=normalize_plate(mapped.get("plate_raw")),
                name_norm=normalize_name(mapped.get("name_raw")),
                brand_norm=normalize_name(mapped.get("brand_raw")),
                model_norm=normalize_name(mapped.get("model_raw"))
            )

            match_result = self.matching_engine.match_person(candidate)

            if match_result.person_key and match_result.rule:
                batch_items.append({
                    "type": "match",
                    "candidate": candidate,
                    "match_result": match_result
                })
                stats["matched"] += 1
            else:
                batch_items.append({
                    "type": "unmatched",
                    "candidate": candidate,
                    "match_result": match_result
                })
                stats["unmatched"] += 1

            if len(batch_items) >= BATCH_SIZE:
                self._process_batch(batch_items, run_id)
                batch_items = []

        if batch_items:
            self._process_batch(batch_items, run_id)

        self.db.commit()
        return stats

    def process_scouting_daily(self, run_id: int, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict[str, int]:
        BATCH_SIZE = 1000
        stats = {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0}

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
        
        source_pks = []
        for row in rows:
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                mapped = DataContract.map_row("module_ct_scouting_daily", row_dict)
                source_pk = str(mapped.get("source_pk", ""))
                if source_pk:
                    source_pks.append(source_pk)
            except:
                continue
        
        existing_links_cache = self._load_existing_links_cache("module_ct_scouting_daily", source_pks)
        
        batch_items = []
        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            except Exception as e:
                logger.error(f"Error procesando row {idx}: {e}")
                continue
            
            mapped = DataContract.map_row("module_ct_scouting_daily", row_dict)
            
            missing_keys = DataContract.get_missing_keys("module_ct_scouting_daily", row_dict,
                ["source_pk", "snapshot_date"])
            
            if missing_keys:
                # Serializar mapped para evitar problemas con datetime en JSON
                mapped_serialized = self._serialize_for_json(mapped)
                batch_items.append({
                    "type": "unmatched",
                    "data": {
                        "source_table": "module_ct_scouting_daily",
                        "source_pk": str(mapped.get("source_pk", f"unknown_{idx}")),
                        "snapshot_date": mapped.get("snapshot_date") or datetime.utcnow(),
                        "reason_code": "MISSING_KEYS",
                        "details": {"missing_keys": missing_keys, "mapped": mapped_serialized}
                    }
                })
                stats["unmatched"] += 1
                continue
            
            snapshot_date = mapped.get("snapshot_date")
            if not snapshot_date:
                date_raw = row_dict.get("registration_date")
                if date_raw and isinstance(date_raw, str):
                    # Serializar mapped para evitar problemas con datetime en JSON
                    mapped_serialized = self._serialize_for_json(mapped)
                    batch_items.append({
                        "type": "unmatched",
                        "data": {
                            "source_table": "module_ct_scouting_daily",
                            "source_pk": str(mapped.get("source_pk", f"unknown_{idx}")),
                            "snapshot_date": datetime.utcnow(),
                            "reason_code": "INVALID_DATE_FORMAT",
                            "details": {"date_raw": str(date_raw), "mapped": mapped_serialized}
                        }
                    })
                    stats["unmatched"] += 1
                    continue

            source_pk = str(mapped["source_pk"])
            if source_pk in existing_links_cache:
                stats["skipped"] += 1
                continue

            snapshot_date = mapped.get("snapshot_date") or datetime.utcnow()
            if isinstance(snapshot_date, date):
                snapshot_date = datetime.combine(snapshot_date, datetime.min.time())

            candidate = IdentityCandidateInput(
                source_table="module_ct_scouting_daily",
                source_pk=source_pk,
                snapshot_date=snapshot_date,
                park_id=mapped.get("park_id"),
                phone_norm=normalize_phone(mapped.get("phone_raw")),
                license_norm=normalize_license(mapped.get("license_raw")),
                plate_norm=normalize_plate(mapped.get("plate_raw")),
                name_norm=normalize_name(mapped.get("name_raw")),
                brand_norm=normalize_name(mapped.get("brand_raw")),
                model_norm=normalize_name(mapped.get("model_raw"))
            )

            match_result = self.matching_engine.match_person(candidate)

            if match_result.person_key and match_result.rule:
                batch_items.append({
                    "type": "match",
                    "candidate": candidate,
                    "match_result": match_result
                })
                stats["matched"] += 1
            else:
                batch_items.append({
                    "type": "unmatched",
                    "candidate": candidate,
                    "match_result": match_result
                })
                stats["unmatched"] += 1

            if len(batch_items) >= BATCH_SIZE:
                self._process_batch(batch_items, run_id)
                batch_items = []

        if batch_items:
            self._process_batch(batch_items, run_id)

        self.db.commit()
        return stats

    def process_drivers(self, run_id: int, date_from: Optional[date] = None, date_to: Optional[date] = None) -> Dict[str, int]:
        stats = {"processed": 0, "matched": 0, "unmatched": 0}
        run_date = datetime.utcnow().date()

        query_str = """
            SELECT *
            FROM public.drivers
        """
        params = {"run_date": run_date}
        
        if date_from or date_to:
            conditions = []
            if date_from:
                conditions.append("created_at::date >= :date_from")
                params["date_from"] = date_from
            if date_to:
                conditions.append("created_at::date <= :date_to")
                params["date_to"] = date_to
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

        query = text(query_str)
        result = self.db.execute(query, params)
        rows = result.fetchall()

        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            
            mapped = DataContract.map_row("drivers", row_dict, run_date=run_date)
            
            existing_link = self.db.query(IdentityLink).filter(
                IdentityLink.source_table == "drivers",
                IdentityLink.source_pk == str(mapped["source_pk"])
            ).first()

            if existing_link:
                continue

            snapshot_date = mapped.get("snapshot_date") or datetime.utcnow()
            if isinstance(snapshot_date, date):
                snapshot_date = datetime.combine(snapshot_date, datetime.min.time())

            candidate = IdentityCandidateInput(
                source_table="drivers",
                source_pk=str(mapped["source_pk"]),
                snapshot_date=snapshot_date,
                park_id=mapped.get("park_id"),
                phone_norm=normalize_phone(mapped.get("phone_raw")),
                license_norm=normalize_license(mapped.get("license_raw")),
                plate_norm=normalize_plate(mapped.get("plate_raw")),
                name_norm=normalize_name(mapped.get("name_raw")),
                brand_norm=normalize_name(mapped.get("brand_raw")),
                model_norm=normalize_name(mapped.get("model_raw"))
            )

            match_result = self.matching_engine.match_person(candidate)

            if match_result.person_key and match_result.rule:
                self._create_or_update_person(match_result.person_key, candidate, match_result.confidence)
                self._create_link(candidate, match_result)
                stats["matched"] += 1
            else:
                self._create_unmatched_from_result(candidate, match_result)
                stats["unmatched"] += 1

            if stats["processed"] % 100 == 0:
                self.db.commit()

        self.db.commit()
        return stats

    def _process_batch(self, batch_items: list, run_id: int):
        for idx, item in enumerate(batch_items):
            try:
                if item["type"] == "match":
                    self._create_or_update_person(item["match_result"].person_key, item["candidate"], item["match_result"].confidence)
                    self._create_link(item["candidate"], item["match_result"], run_id)
                    
                    if item["match_result"].driver_id:
                        self._link_driver(item["match_result"].person_key, item["match_result"].driver_id, item["candidate"].snapshot_date, run_id)
                elif item["type"] == "unmatched":
                    if "candidate" in item:
                        self._create_unmatched_from_result(item["candidate"], item["match_result"], run_id)
                    else:
                        self._create_unmatched(run_id=run_id, **item["data"])
            except Exception as e:
                raise
        
        self.db.commit()

    def _create_or_update_person(self, person_key: UUID, candidate: IdentityCandidateInput, confidence: ConfidenceLevel):
        person = self.db.query(IdentityRegistry).filter(IdentityRegistry.person_key == person_key).first()

        if not person:
            person = IdentityRegistry(
                person_key=person_key,
                confidence_level=confidence,
                primary_phone=candidate.phone_norm,
                primary_license=candidate.license_norm,
                primary_full_name=candidate.name_norm,
            )
            self.db.add(person)
        else:
            if not person.primary_phone and candidate.phone_norm:
                person.primary_phone = candidate.phone_norm
            if not person.primary_license and candidate.license_norm:
                person.primary_license = candidate.license_norm
            if not person.primary_full_name and candidate.name_norm:
                person.primary_full_name = candidate.name_norm
            if confidence == ConfidenceLevel.HIGH and person.confidence_level != ConfidenceLevel.HIGH:
                person.confidence_level = confidence

        self.db.flush()

    def _create_link(self, candidate: IdentityCandidateInput, match_result, run_id: int):
        existing = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == candidate.source_table,
            IdentityLink.source_pk == candidate.source_pk
        ).first()

        if existing:
            existing.match_rule = match_result.rule
            existing.match_score = match_result.score or 0
            existing.confidence_level = match_result.confidence
            existing.evidence = match_result.evidence
            existing.snapshot_date = candidate.snapshot_date
            existing.run_id = run_id
        else:
            link = IdentityLink(
                person_key=match_result.person_key,
                source_table=candidate.source_table,
                source_pk=candidate.source_pk,
                snapshot_date=candidate.snapshot_date,
                match_rule=match_result.rule,
                match_score=match_result.score or 0,
                confidence_level=match_result.confidence,
                evidence=match_result.evidence,
                run_id=run_id
            )
            self.db.add(link)

        self.db.flush()

    def _link_driver(self, person_key: UUID, driver_id: str, snapshot_date: datetime, run_id: int):
        existing = self.db.query(IdentityLink).filter(
            IdentityLink.source_table == "drivers",
            IdentityLink.source_pk == driver_id
        ).first()

        if not existing:
            link = IdentityLink(
                person_key=person_key,
                source_table="drivers",
                source_pk=driver_id,
                snapshot_date=snapshot_date,
                match_rule="DRIVER_MATCH",
                match_score=100,
                confidence_level=ConfidenceLevel.HIGH,
                evidence={"driver_id": driver_id, "linked_from": "matching"},
                run_id=run_id
            )
            self.db.add(link)
            self.db.flush()

    def _serialize_for_json(self, obj: Any) -> Any:
        """Convierte objetos datetime/date a strings para serialización JSON"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, date):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_for_json(item) for item in obj]
        elif isinstance(obj, UUID):
            return str(obj)
        else:
            return obj

    def _create_unmatched_from_result(self, candidate: IdentityCandidateInput, match_result, run_id: int):
        candidates_preview = None
        if match_result.evidence and "candidates" in match_result.evidence:
            candidates_preview = match_result.evidence["candidates"]
            # Serializar datetime objects en candidates_preview
            candidates_preview = self._serialize_for_json(candidates_preview)

        self._create_unmatched(
            source_table=candidate.source_table,
            source_pk=candidate.source_pk,
            snapshot_date=candidate.snapshot_date,
            reason_code=match_result.reason_code or "NO_CANDIDATES",
            details={
                "phone_norm": candidate.phone_norm,
                "license_norm": candidate.license_norm,
                "name_norm": candidate.name_norm,
                "plate_norm": candidate.plate_norm,
            },
            candidates_preview=candidates_preview,
            run_id=run_id
        )

    def _create_unmatched(self, source_table: str, source_pk: str, snapshot_date: datetime,
                         reason_code: str, details: Dict[str, Any], candidates_preview: Optional[list] = None, run_id: int = None):
        # Serializar datetime objects en details
        details = self._serialize_for_json(details)
        
        existing = self.db.query(IdentityUnmatched).filter(
            IdentityUnmatched.source_table == source_table,
            IdentityUnmatched.source_pk == source_pk
        ).first()

        if existing:
            existing.reason_code = reason_code
            existing.details = details
            existing.candidates_preview = {"candidates": candidates_preview} if candidates_preview else None
            existing.status = UnmatchedStatus.OPEN
            existing.run_id = run_id
        else:
            unmatched = IdentityUnmatched(
                source_table=source_table,
                source_pk=source_pk,
                snapshot_date=snapshot_date,
                reason_code=reason_code,
                details=details,
                candidates_preview={"candidates": candidates_preview} if candidates_preview else None,
                status=UnmatchedStatus.OPEN,
                run_id=run_id
            )
            self.db.add(unmatched)

        self.db.flush()
