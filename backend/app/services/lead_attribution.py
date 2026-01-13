"""
Lead attribution service for the CT4 system.

Manages the attribution of leads to scouts, including populating lead events
from various sources and processing the attribution ledger.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError, PendingRollbackError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import PARK_ID_OBJETIVO
from app.models.canon import ConfidenceLevel, IdentityLink, IdentityRegistry
from app.models.observational import (
    AttributionConfidence,
    DecisionStatus,
    LeadEvent,
    LeadLedger,
)
from app.services.data_contract import DataContract
from app.services.matching import IdentityCandidateInput, MatchingEngine
from app.services.normalization import (
    normalize_license,
    normalize_name,
    normalize_phone,
    normalize_phone_pe9,
    normalize_plate,
)

logger = logging.getLogger(__name__)


class LeadAttributionService:
    def __init__(self, db: Session):
        self.db = db
        self.matching_engine = MatchingEngine(db, park_id_objetivo=PARK_ID_OBJETIVO)

    def ensure_driver_identity_link(
        self, 
        driver_id: int | str, 
        metrics: dict, 
        run_id: int | None,
        snapshot_date: datetime | None = None
    ) -> Optional[str]:
        """
        Asegura que exista un vínculo driver_id → person_key.
        
        IMPORTANTE: Solo crea el link si hay un lead asociado (cabinet/scouting/migrations).
        Los drivers NO deben estar en el sistema sin un lead asociado.
        
        Si el vínculo ya existe, lo reutiliza.
        Si no existe y hay un lead asociado, crea un nuevo person_key y los registros necesarios.
        
        Retorna el person_key (como string UUID) o None si hay error o no hay lead asociado.
        """
        driver_id_str = str(driver_id)
        
        try:
            # Buscar IdentityLink existente
            identity_link = self.db.query(IdentityLink).filter(
                IdentityLink.source_table == "drivers",
                IdentityLink.source_pk == driver_id_str
            ).first()
            
            if identity_link:
                # Verificar que tiene un lead asociado
                has_lead = self.db.query(IdentityLink).filter(
                    IdentityLink.person_key == identity_link.person_key,
                    IdentityLink.source_table.in_(["module_ct_cabinet_leads", "module_ct_scouting_daily", "module_ct_migrations"])
                ).first()
                
                if has_lead:
                    metrics["reused_links"] += 1
                    return str(identity_link.person_key)
                else:
                    # Link existe pero sin lead - esto es un problema
                    logger.warning(
                        f"[IDENTITY] Driver {driver_id_str} tiene link pero NO tiene lead asociado. "
                        "Esto no debería ocurrir. El link será reutilizado pero debería investigarse."
                    )
                    metrics["reused_links"] += 1
                    return str(identity_link.person_key)
            
            # No existe el vínculo - verificar si hay un lead asociado antes de crear
            # Buscar si hay un lead_event o migration que referencia este driver_id
            has_lead = False
            lead_source = None
            
            # Buscar en lead_events por driver_id en payload_json
            lead_event = self.db.query(LeadEvent).filter(
                LeadEvent.payload_json['driver_id'].astext == driver_id_str
            ).first()
            
            if lead_event:
                has_lead = True
                lead_source = "lead_events"
            else:
                # Si no hay lead_event, buscar en migrations directamente
                migration_query = text("""
                    SELECT id
                    FROM public.module_ct_migrations
                    WHERE driver_id::text = :driver_id
                    LIMIT 1
                """)
                try:
                    migration_result = self.db.execute(migration_query, {"driver_id": driver_id_str})
                    migration_row = migration_result.fetchone()
                    if migration_row:
                        has_lead = True
                        lead_source = "migrations"
                except Exception:
                    pass
            
            if not has_lead:
                # NO hay lead asociado - NO crear link
                logger.warning(
                    f"[IDENTITY] Driver {driver_id_str} no tiene lead asociado. "
                    "No se creará link de driver sin lead."
                )
                metrics["link_missing_count"] += 1
                return None
            
            # Hay un lead asociado - proceder a crear el link
            # Obtener información del driver desde public.drivers
            query = text("""
                SELECT phone, license_number, license_normalized_number, full_name, first_name, middle_name, last_name
                FROM public.drivers
                WHERE driver_id = :driver_id
                LIMIT 1
            """)
            
            # Intentar con driver_id como string primero (puede ser UUID o string)
            try:
                result = self.db.execute(query, {"driver_id": driver_id_str})
                row = result.fetchone()
            except Exception as query_error:
                # Si falla, intentar con UUID explícito
                logger.debug(f"[IDENTITY] Error en query con driver_id={driver_id_str}, intentando con UUID: {query_error}")
                try:
                    driver_uuid = UUID(driver_id_str) if isinstance(driver_id_str, str) else driver_id_str
                    result = self.db.execute(query, {"driver_id": driver_uuid})
                    row = result.fetchone()
                except Exception:
                    logger.error(f"[IDENTITY] No se pudo encontrar driver {driver_id_str} en public.drivers")
                    metrics["link_missing_count"] += 1
                    return None
            
            if not row:
                logger.warning(f"[IDENTITY] Driver {driver_id_str} no encontrado en public.drivers después de query exitosa")
                metrics["link_missing_count"] += 1
                return None
            
            # Normalizar datos del driver
            phone_norm = normalize_phone(row.phone) if row.phone else None
            license_norm = normalize_license(row.license_normalized_number or row.license_number) if (row.license_normalized_number or row.license_number) else None
            name_norm = normalize_name(row.full_name or f"{row.first_name or ''} {row.middle_name or ''} {row.last_name or ''}".strip()) if (row.full_name or row.first_name or row.last_name) else None
            
            # Generar nuevo person_key
            person_key = uuid4()
            
            # Crear registro en IdentityRegistry
            person = IdentityRegistry(
                person_key=person_key,
                confidence_level=ConfidenceLevel.HIGH,
                primary_phone=phone_norm,
                primary_license=license_norm,
                primary_full_name=name_norm
            )
            self.db.add(person)
            self.db.flush()
            
            # Crear vínculo en IdentityLink
            if snapshot_date is None:
                snapshot_date = datetime.utcnow()
            
            identity_link = IdentityLink(
                person_key=person_key,
                source_table="drivers",
                source_pk=driver_id_str,
                snapshot_date=snapshot_date,
                match_rule="driver_direct",
                match_score=100,
                confidence_level=ConfidenceLevel.HIGH,
                evidence={
                    "created_by": "ensure_driver_identity_link",
                    "has_lead": True,
                    "lead_source": lead_source
                },
                run_id=run_id
            )
            self.db.add(identity_link)
            self.db.flush()
            
            metrics["created_links"] += 1
            logger.info(f"Created identity link drivers:{driver_id_str} -> {person_key} (with lead association)")
            
            return str(person_key)
            
        except (IntegrityError, SQLAlchemyError, PendingRollbackError) as e:
            # Si hay error de integridad o de base de datos, hacer rollback y retornar None
            try:
                self.db.rollback()
            except Exception:
                pass  # Ignorar errores en rollback
            logger.error(f"[IDENTITY] Error creando vínculo para driver_id={driver_id_str}: {e}")
            metrics["link_missing_count"] += 1
            return None

    def _load_existing_events_cache(self, source_table: str, source_pks: list) -> Dict[str, LeadEvent]:
        """Carga todos los eventos existentes de una vez para evitar consultas individuales"""
        if not source_pks:
            return {}
        
        existing = self.db.query(LeadEvent).filter(
            LeadEvent.source_table == source_table,
            LeadEvent.source_pk.in_(source_pks)
        ).all()
        return {str(e.source_pk): e for e in existing}

    def _match_by_plate_s3(self, plate_norm: str) -> Dict[str, Any]:
        """
        Matching S3 por placa: busca drivers con placa normalizada coincidente.
        Retorna dict con matched, person_key, driver_id, reason, candidates según resultado.
        NO crea registros en canon.*, solo usa IdentityLink existente.
        """
        if not plate_norm:
            return {"matched": False, "reason": "no_plate"}
        
        try:
            # Query usando canon.drivers_index que ya tiene plate_norm normalizado
            query = text("""
                SELECT driver_id
                FROM canon.drivers_index
                WHERE plate_norm = :plate_norm
            """)
            
            result = self.db.execute(query, {"plate_norm": plate_norm})
            drivers = result.fetchall()
            
            count = len(drivers)
            
            if count == 0:
                return {"matched": False, "reason": "no_match"}
            
            if count > 1:
                return {"matched": False, "reason": "ambiguous", "candidates": count}
            
            # count == 1: match único
            driver_id = str(drivers[0].driver_id)
            
            # Buscar person_key via IdentityLink existente (NO crear nuevos)
            identity_link = self.db.query(IdentityLink).filter(
                IdentityLink.source_table == "drivers",
                IdentityLink.source_pk == driver_id
            ).first()
            
            if identity_link:
                return {
                    "matched": True,
                    "person_key": identity_link.person_key,
                    "driver_id": driver_id
                }
            else:
                # Driver existe pero no tiene IdentityLink aún
                return {"matched": False, "reason": "no_identity_link", "driver_id": driver_id}
        except (SQLAlchemyError, PendingRollbackError) as e:
            # Si hay un error de base de datos, hacer rollback y retornar error
            try:
                self.db.rollback()
            except Exception:
                pass  # Ignorar errores en rollback
            logger.error(f"Error en _match_by_plate_s3 para plate_norm={plate_norm}: {e}")
            return {"matched": False, "reason": "db_error"}

    def populate_events_from_scouting(
        self, 
        date_from: Optional[date] = None, 
        date_to: Optional[date] = None,
        run_id: Optional[int] = None
    ) -> Dict[str, int]:
        stats = {
            "processed": 0, 
            "created": 0, 
            "skipped": 0, 
            "errors": 0,
            "created_links": 0,
            "reused_links": 0,
            "link_missing_count": 0
        }
        
        logger.info(f"Iniciando populate_events_from_scouting: date_from={date_from}, date_to={date_to}")

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
        
        total_rows = len(rows)
        logger.info(f"Total de filas a procesar: {total_rows}")
        
        # Cargar todos los source_pks primero
        source_pks = []
        for row in rows:
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                source_pk = str(row_dict.get("id", ""))
                if source_pk:
                    source_pks.append(source_pk)
            except (KeyError, AttributeError, TypeError):
                continue
        
        # Cargar caché de eventos existentes de una vez
        logger.info(f"Cargando caché de eventos existentes para {len(source_pks)} source_pks...")
        existing_events_cache = self._load_existing_events_cache("module_ct_scouting_daily", source_pks)
        logger.info(f"Encontrados {len(existing_events_cache)} eventos existentes")
        
        batch_size = 100
        batch_count = 0

        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                
                source_pk = str(row_dict.get("id", ""))
                if not source_pk:
                    stats["errors"] += 1
                    continue

                # Usar caché en lugar de consulta individual
                # Si el evento existe pero tiene person_key NULL, procesarlo de nuevo
                if source_pk in existing_events_cache:
                    existing_event = existing_events_cache[source_pk]
                    if existing_event.person_key is not None:
                        stats["skipped"] += 1
                        continue
                    # Si existe pero person_key es NULL, procesarlo para intentar asignar person_key

                event_date = row_dict.get("registration_date")
                if isinstance(event_date, str):
                    try:
                        event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
                    except ValueError:
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
                        # Asegurar que exista el vínculo driver_id → person_key
                        person_key_str = self.ensure_driver_identity_link(
                            driver_id=driver_id,
                            metrics=stats,
                            run_id=run_id,
                            snapshot_date=datetime.combine(event_date, datetime.min.time()) if event_date else None
                        )
                        
                        if person_key_str:
                            person_key = UUID(person_key_str)
                            matching_evidence["identity_link_found"] = True
                            matching_evidence["identity_link_missing"] = False
                        else:
                            stats["link_missing_count"] += 1
                            person_key = None
                            matching_evidence["identity_link_missing"] = True
                    else:
                        stats["link_missing_count"] += 1
                        person_key = None
                        matching_evidence["driver_not_found"] = True
                else:
                    stats["link_missing_count"] += 1
                    person_key = None
                    matching_evidence["no_matching_data"] = True

                payload = {
                    "origin_tag": "cabinet",  # CORREGIDO: scouting_daily debe ser 'cabinet' para aparecer en v_conversion_metrics (cabinet)
                    "driver_name": row_dict.get("driver_name"),
                    "driver_phone": driver_phone,
                    "driver_license": driver_license,
                    "acquisition_method": row_dict.get("acquisition_method"),
                    "matching_evidence": matching_evidence
                }

                if person_key is None:
                    payload["needs_identity_link"] = True

                # Verificar si el evento ya existe (para actualizarlo si person_key era NULL)
                existing_event = existing_events_cache.get(source_pk)
                if existing_event:
                    # Actualizar evento existente si person_key cambió o era NULL
                    if existing_event.person_key != person_key:
                        existing_event.person_key = person_key
                        existing_event.payload_json = payload
                        stats["created"] += 1  # Contar como "procesado" aunque sea update
                    else:
                        stats["skipped"] += 1
                else:
                    # Crear nuevo evento
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
                
                # Commit periódico cada batch_size registros creados
                if stats["created"] % batch_size == 0:
                    try:
                        self.db.commit()
                        batch_count += 1
                        logger.info(f"Procesados {stats['processed']}/{total_rows} filas. Creados: {stats['created']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
                    except IntegrityError as e:
                        self.db.rollback()
                        logger.error(f"Error de integridad en batch {batch_count}: {e}")

            except Exception as e:
                logger.error(f"Error procesando scouting row {idx}: {e}", exc_info=True)
                stats["errors"] += 1
                continue

        # Commit final
        try:
            self.db.commit()
            logger.info(f"Finalizado populate_events_from_scouting. Total procesados: {stats['processed']}, Creados: {stats['created']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al poblar eventos de scouting (commit final): {e}")
            stats["errors"] += stats["created"]
            stats["created"] = 0

        return stats

    def populate_events_from_cabinet(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None
    ) -> Dict[str, int]:
        stats = {"processed": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}
        
        logger.info(f"Iniciando populate_events_from_cabinet: date_from={date_from}, date_to={date_to}")

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
        
        total_rows = len(rows)
        logger.info(f"Total de filas a procesar: {total_rows}")
        
        # Cargar todos los source_pks primero
        source_pks = []
        for row in rows:
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                mapped = DataContract.map_row("module_ct_cabinet_leads", row_dict)
                source_pk = str(mapped.get("source_pk", ""))
                if source_pk:
                    source_pks.append(source_pk)
            except (KeyError, AttributeError, TypeError):
                continue
        
        # Cargar caché de eventos existentes de una vez
        logger.info(f"Cargando caché de eventos existentes para {len(source_pks)} source_pks...")
        existing_events_cache = self._load_existing_events_cache("module_ct_cabinet_leads", source_pks)
        logger.info(f"Encontrados {len(existing_events_cache)} eventos existentes")
        
        # Crear caché rápido de source_pk -> tiene_person_key (para skip rápido)
        existing_with_person_key = {pk: (evt.person_key is not None) for pk, evt in existing_events_cache.items()}
        
        batch_size = 100
        batch_count = 0

        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                
                # Extraer source_pk directamente (optimización temprana)
                source_pk = str(row_dict.get("external_id") or row_dict.get("id", ""))
                
                if not source_pk:
                    stats["errors"] += 1
                    continue

                # Verificar si el evento ya existe (idempotencia) - VERIFICACIÓN TEMPRANA Y RÁPIDA
                # Usar caché rápido primero para evitar acceder al objeto completo
                if existing_with_person_key.get(source_pk, False):
                    stats["skipped"] += 1
                    # Log periódico de progreso cada 100 registros procesados
                    if stats["processed"] % 100 == 0:
                        logger.info(f"Procesados {stats['processed']}/{total_rows} filas. Creados: {stats['created']}, Actualizados: {stats['updated']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
                    continue
                
                # Solo obtener el objeto completo si necesitamos procesarlo
                existing_event = existing_events_cache.get(source_pk)
                
                # Solo ahora hacer el mapeo completo (solo para eventos que necesitan procesamiento)
                mapped = DataContract.map_row("module_ct_cabinet_leads", row_dict)

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
                
                # Matching: primero phone/license (MatchingEngine)
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
                matched_by = None
                match_meta = {}
                
                # Determinar matched_by según resultado
                if match_result and match_result.person_key:
                    if match_result.rule == "R1":
                        matched_by = "phone_last9"
                    elif match_result.rule == "R2":
                        matched_by = "license"
                    else:
                        matched_by = "other"
                
                # Si no hay match, intentar S3 por placa
                plate_raw = row_dict.get("asset_plate_number")
                plate_norm = normalize_plate(plate_raw) if plate_raw else None
                
                if not person_key and plate_norm:
                    plate_match_result = self._match_by_plate_s3(plate_norm)
                    
                    if plate_match_result.get("matched"):
                        person_key = plate_match_result.get("person_key")
                        matched_by = "plate"
                        match_meta["plate_match"] = "unique"
                        match_meta["driver_id"] = plate_match_result.get("driver_id")
                    elif plate_match_result.get("reason") == "ambiguous":
                        matched_by = "plate"
                        match_meta["plate_match"] = "ambiguous"
                        match_meta["candidates"] = plate_match_result.get("candidates", 0)
                    elif plate_match_result.get("reason") == "no_match":
                        match_meta["plate_match"] = "no_match"
                    elif plate_match_result.get("reason") == "no_identity_link":
                        match_meta["plate_match"] = "no_identity_link"
                        match_meta["driver_id"] = plate_match_result.get("driver_id")
                
                # Si todavía no hay matched_by, es "none"
                if not matched_by:
                    matched_by = "none"
                
                # Construir payload_json con evidencia completa
                payload = {
                    "origin_tag": "cabinet",
                    "source": "cabinet",
                    "external_id": row_dict.get("external_id"),
                    "first_name": row_dict.get("first_name"),
                    "middle_name": row_dict.get("middle_name"),
                    "last_name": row_dict.get("last_name"),
                    "park_phone": row_dict.get("park_phone"),
                    "asset_plate_number": plate_raw,
                    "asset_model": row_dict.get("asset_model"),
                    "plate_norm": plate_norm,
                    "matched_by": matched_by,
                    "match_meta": match_meta if match_meta else None,
                    "match_rule": match_result.rule if match_result else None,
                    "match_score": match_result.score if match_result else None
                }

                # UPDATE si existe, INSERT si no
                if existing_event:
                    # Actualizar solo si person_key cambió o estaba null
                    if existing_event.person_key != person_key:
                        existing_event.person_key = person_key
                        existing_event.payload_json = payload
                        stats["updated"] += 1
                    else:
                        stats["skipped"] += 1
                        # Log periódico de progreso cada 100 registros procesados
                        if stats["processed"] % 100 == 0:
                            logger.info(f"Procesados {stats['processed']}/{total_rows} filas. Creados: {stats['created']}, Actualizados: {stats['updated']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
                        continue
                else:
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
                
                # Log periódico de progreso cada 100 registros procesados (después de procesar)
                if stats["processed"] % 100 == 0:
                    logger.info(f"Procesados {stats['processed']}/{total_rows} filas. Creados: {stats['created']}, Actualizados: {stats['updated']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
                
                # Commit periódico cada batch_size registros creados o actualizados
                if (stats["created"] + stats["updated"]) > 0 and (stats["created"] + stats["updated"]) % batch_size == 0:
                    try:
                        self.db.commit()
                        batch_count += 1
                        logger.info(f"Commit batch {batch_count}: Procesados {stats['processed']}/{total_rows} filas. Creados: {stats['created']}, Actualizados: {stats['updated']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
                    except (IntegrityError, PendingRollbackError, SQLAlchemyError) as e:
                        try:
                            self.db.rollback()
                        except Exception:
                            pass  # Ignorar errores en rollback
                        logger.error(f"Error de base de datos en batch {batch_count}: {e}")

            except (SQLAlchemyError, PendingRollbackError) as e:
                # Error de base de datos - hacer rollback antes de continuar
                try:
                    self.db.rollback()
                except Exception:
                    pass  # Ignorar errores en rollback
                logger.error(f"Error de base de datos procesando cabinet row {idx}: {e}", exc_info=True)
                stats["errors"] += 1
                continue
            except Exception as e:
                logger.error(f"Error procesando cabinet row {idx}: {e}", exc_info=True)
                stats["errors"] += 1
                continue

        # Commit final
        try:
            self.db.commit()
            logger.info(f"Finalizado populate_events_from_cabinet. Total procesados: {stats['processed']}, Creados: {stats['created']}, Actualizados: {stats['updated']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
        except (IntegrityError, PendingRollbackError, SQLAlchemyError) as e:
            try:
                self.db.rollback()
            except Exception:
                pass  # Ignorar errores en rollback
            logger.error(f"Error de base de datos al poblar eventos de cabinet (commit final): {e}")
            stats["errors"] += stats["created"] + stats["updated"]
            stats["created"] = 0
            stats["updated"] = 0

        return stats

    def populate_events_from_migrations(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        run_id: Optional[int] = None
    ) -> Dict[str, int]:
        stats = {
            "processed": 0,
            "created": 0,
            "skipped": 0,
            "errors": 0,
            "created_links": 0,
            "reused_links": 0,
            "link_missing_count": 0
        }
        
        logger.info(f"Iniciando populate_events_from_migrations: date_from={date_from}, date_to={date_to}")

        query_str = """
            SELECT *
            FROM public.module_ct_migrations
        """
        params = {}
        
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
        
        total_rows = len(rows)
        logger.info(f"Total de filas a procesar: {total_rows}")
        
        # Cargar todos los source_pks primero
        source_pks = []
        for row in rows:
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                source_pk = str(row_dict.get("id", ""))
                if source_pk:
                    source_pks.append(source_pk)
            except (KeyError, AttributeError, TypeError):
                continue
        
        # Cargar caché de eventos existentes de una vez
        logger.info(f"Cargando caché de eventos existentes para {len(source_pks)} source_pks...")
        existing_events_cache = self._load_existing_events_cache("module_ct_migrations", source_pks)
        logger.info(f"Encontrados {len(existing_events_cache)} eventos existentes")
        
        batch_size = 100
        batch_count = 0

        for idx, row in enumerate(rows):
            stats["processed"] += 1
            
            try:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                
                source_pk = str(row_dict.get("id", ""))
                if not source_pk:
                    stats["errors"] += 1
                    logger.error(f"Fila {idx} de module_ct_migrations sin id")
                    continue

                # Verificar idempotencia: si ya existe, skip
                if source_pk in existing_events_cache:
                    existing_event = existing_events_cache[source_pk]
                    if existing_event.person_key is not None:
                        stats["skipped"] += 1
                        continue
                    # Si existe pero person_key es NULL, procesarlo para intentar asignar person_key

                # Obtener event_date desde created_at
                created_at = row_dict.get("created_at")
                if isinstance(created_at, datetime):
                    event_date = created_at.date()
                elif isinstance(created_at, date):
                    event_date = created_at
                elif isinstance(created_at, str):
                    try:
                        event_date = datetime.strptime(created_at, "%Y-%m-%d").date()
                    except ValueError:
                        event_date = datetime.utcnow().date()
                else:
                    event_date = datetime.utcnow().date()

                # Obtener driver_id y scout_id
                driver_id = row_dict.get("driver_id")
                scout_id = row_dict.get("scout_id")

                # Validar que driver_id existe
                if not driver_id:
                    logger.error(f"Fila {idx} (id={source_pk}) de module_ct_migrations sin driver_id")
                    stats["errors"] += 1
                    continue

                # Obtener person_key usando ensure_driver_identity_link
                person_key_str = self.ensure_driver_identity_link(
                    driver_id=driver_id,
                    metrics=stats,
                    run_id=run_id,
                    snapshot_date=datetime.combine(event_date, datetime.min.time()) if event_date else None
                )

                # NO permitir que person_key quede NULL si driver_id existe
                if not person_key_str:
                    logger.error(f"Error: driver_id={driver_id} existe pero ensure_driver_identity_link retornó None para fila {idx} (id={source_pk})")
                    stats["errors"] += 1
                    continue

                person_key = UUID(person_key_str)

                # Construir payload_json con origin_tag y campos relevantes
                payload = {
                    "origin_tag": "fleet_migration",
                    "driver_id": driver_id,
                    "scout_id": scout_id
                }
                
                # Agregar todos los demás campos relevantes de la fila (sin transformar)
                for key, value in row_dict.items():
                    if key not in ["id", "driver_id", "scout_id", "created_at"]:
                        # Convertir tipos no serializables a string
                        if isinstance(value, (datetime, date)):
                            payload[key] = value.isoformat() if hasattr(value, 'isoformat') else str(value)
                        else:
                            payload[key] = value

                # Verificar si el evento ya existe (para actualizarlo si person_key era NULL)
                existing_event = existing_events_cache.get(source_pk)
                if existing_event:
                    # Actualizar evento existente si person_key cambió o era NULL
                    if existing_event.person_key != person_key:
                        existing_event.person_key = person_key
                        existing_event.payload_json = payload
                        stats["created"] += 1  # Contar como "procesado" aunque sea update
                    else:
                        stats["skipped"] += 1
                else:
                    # Crear nuevo evento
                    event = LeadEvent(
                        source_table="module_ct_migrations",
                        source_pk=source_pk,
                        event_date=event_date,
                        person_key=person_key,
                        scout_id=scout_id,
                        payload_json=payload
                    )

                    self.db.add(event)
                    stats["created"] += 1
                
                # Commit periódico cada batch_size registros creados
                if stats["created"] % batch_size == 0:
                    try:
                        self.db.commit()
                        batch_count += 1
                        logger.info(f"Procesados {stats['processed']}/{total_rows} filas. Creados: {stats['created']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
                    except IntegrityError as e:
                        self.db.rollback()
                        logger.error(f"Error de integridad en batch {batch_count}: {e}")

            except Exception as e:
                logger.error(f"Error procesando migrations row {idx}: {e}", exc_info=True)
                stats["errors"] += 1
                continue

        # Commit final
        try:
            self.db.commit()
            logger.info(f"Finalizado populate_events_from_migrations. Total procesados: {stats['processed']}, Creados: {stats['created']}, Omitidos: {stats['skipped']}, Errores: {stats['errors']}")
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error de integridad al poblar eventos de migrations (commit final): {e}")
            stats["errors"] += stats["created"]
            stats["created"] = 0

        return stats

    def _get_hire_dates_batch(self, person_keys: List[UUID]) -> Dict[UUID, Optional[date]]:
        """Obtiene hire_dates para múltiples person_keys en una sola consulta"""
        if not person_keys:
            return {}
        
        # Usar IN en lugar de ANY para mejor compatibilidad
        query = text("""
            SELECT DISTINCT ON (il.person_key) il.person_key, d.hire_date
            FROM canon.identity_links il
            JOIN public.drivers d ON d.driver_id::text = il.source_pk
            WHERE il.person_key IN :person_keys
            AND il.source_table = 'drivers'
            AND d.hire_date IS NOT NULL
            ORDER BY il.person_key, d.hire_date ASC
        """)
        
        # SQLAlchemy requiere que IN use una tupla
        result = self.db.execute(query, {"person_keys": tuple(person_keys)})
        hire_dates = {row.person_key: row.hire_date for row in result}
        return hire_dates

    def process_ledger(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        source_tables: Optional[List[str]] = None,
        person_keys: Optional[List[UUID]] = None
    ) -> Dict[str, int]:
        """
        Procesa attribution por person_key con lógica temporal y detección de conflictos.
        Implementa FASE 2.2 del sistema Lead Ledger v2.
        
        Reglas aplicadas (en orden de prioridad):
        - Regla C (CONFLICT): 2+ scout_id distintos en ventana de 7 días
        - Regla A (SCOUTING ASSIGNED): scouting_event más reciente
        - Regla B (CABINET ASSIGNED): solo cabinet_events
        - Regla U (UNASSIGNED): sin eventos
        """
        # Constantes FASE 2.2
        CONFLICT_WINDOW_DAYS = 7
        RECENCY_DAYS_FOR_SCOUT = 60  # No usado en esta fase, pero definido según especificación
        
        # Tablas fuente permitidas
        allowed_source_tables = source_tables or ['module_ct_scouting_daily', 'module_ct_cabinet_leads', 'module_ct_migrations']
        
        # Stats iniciales
        stats = {
            "processed_events": 0,
            "processed_person_keys": 0,
            "assigned_count": 0,
            "conflict_count": 0,
            "unassigned_count": 0,
            "errors_count": 0
        }
        
        logger.info(f"Iniciando process_ledger FASE 2.2: date_from={date_from}, date_to={date_to}, source_tables={allowed_source_tables}")
        
        # 1. Filtrar eventos según especificaciones
        events_query = self.db.query(LeadEvent).filter(
            LeadEvent.person_key.isnot(None),
            LeadEvent.source_table.in_(allowed_source_tables)
        )
        
        # Filtros adicionales
        if person_keys:
            events_query = events_query.filter(LeadEvent.person_key.in_(person_keys))
        
        if date_from:
            events_query = events_query.filter(LeadEvent.event_date >= date_from)
        
        if date_to:
            events_query = events_query.filter(LeadEvent.event_date <= date_to)
        
        events = events_query.all()
        stats["processed_events"] = len(events)
        logger.info(f"Eventos encontrados: {stats['processed_events']}")
        
        # 2. Agrupar por person_key
        person_events_map: Dict[UUID, List[LeadEvent]] = {}
        for event in events:
            if event.person_key:
                if event.person_key not in person_events_map:
                    person_events_map[event.person_key] = []
                person_events_map[event.person_key].append(event)
        
        total_persons = len(person_events_map)
        stats["processed_person_keys"] = total_persons
        logger.info(f"Person_keys únicos a procesar: {total_persons}")
        
        batch_size = 50
        batch_count = 0
        
        # Stats para tracking por origen
        stats_by_origin = {
            "fleet_migration": 0,
            "scouting": 0,
            "cabinet": 0,
            "unassigned": 0
        }
        
        # 3. Procesar cada person_key aplicando reglas con prioridad por origin_tag
        for idx, (person_key, events_list) in enumerate(person_events_map.items()):
            try:
                # Separar eventos por origin_tag desde payload_json
                fleet_migration_events = []
                scouting_events = []
                cabinet_events = []
                
                for e in events_list:
                    origin_tag = None
                    if e.payload_json and isinstance(e.payload_json, dict):
                        origin_tag = e.payload_json.get("origin_tag")
                    
                    # Si no hay origin_tag en payload, inferir desde source_table (backward compatibility)
                    if not origin_tag:
                        if e.source_table == 'module_ct_migrations':
                            origin_tag = 'fleet_migration'
                        elif e.source_table == 'module_ct_scouting_daily' and e.scout_id is not None:
                            origin_tag = 'scouting'
                        elif e.source_table == 'module_ct_cabinet_leads':
                            origin_tag = 'cabinet'
                    
                    if origin_tag == 'fleet_migration':
                        fleet_migration_events.append(e)
                    elif origin_tag == 'scouting':
                        scouting_events.append(e)
                    elif origin_tag == 'cabinet':
                        cabinet_events.append(e)
                
                # Extraer datos de eventos antes de commit para evitar errores de sesión
                fleet_migration_data = []
                for e in fleet_migration_events:
                    fleet_migration_data.append({
                        "event_id": e.id,
                        "scout_id": e.scout_id,
                        "event_date": e.event_date
                    })
                
                scouting_data = []
                for e in scouting_events:
                    scouting_data.append({
                        "scout_id": e.scout_id,
                        "event_date": e.event_date
                    })
                
                cabinet_data = []
                for e in cabinet_events:
                    cabinet_data.append({
                        "event_date": e.event_date
                    })
                
                # Aplicar reglas en orden de prioridad: fleet_migration > scouting > cabinet > unassigned
                
                # REGLA C (CONFLICT) - Prioridad máxima
                has_conflict = False
                if len(scouting_events) > 0:
                    # Agrupar por scout_id
                    scouts_map: Dict[int, List[date]] = {}
                    for data in scouting_data:
                        scout_id = data["scout_id"]
                        event_date = data["event_date"]
                        if scout_id not in scouts_map:
                            scouts_map[scout_id] = []
                        scouts_map[scout_id].append(event_date)
                    
                    # Detectar conflicto: 2+ scout_id distintos
                    if len(scouts_map) >= 2:
                        # Calcular diferencia entre primer y último scouting_event
                        all_dates = [d["event_date"] for d in scouting_data]
                        first_date = min(all_dates)
                        last_date = max(all_dates)
                        date_diff = (last_date - first_date).days
                        
                        # Conflicto si diferencia <= conflict_window_days
                        if date_diff <= CONFLICT_WINDOW_DAYS:
                            has_conflict = True
                            
                            # Construir evidence_json para conflicto
                            scouts_in_conflict = []
                            for scout_id, dates in scouts_map.items():
                                scouts_in_conflict.append({
                                    "scout_id": scout_id,
                                    "first_date": min(dates).isoformat(),
                                    "last_date": max(dates).isoformat(),
                                    "count_events": len(dates)
                                })
                            
                            evidence = {
                                "scouts_in_conflict": scouts_in_conflict,
                                "conflict_window_days": CONFLICT_WINDOW_DAYS,
                                "chosen_policy": "no_assignment_due_to_conflict"
                            }
                            
                            ledger_entry = LeadLedger(
                                person_key=person_key,
                                attributed_source="scouting",
                                attributed_scout_id=None,  # IMPORTANTE: NULL en conflictos
                                attribution_rule="C",
                                attribution_score=0.50,
                                confidence_level="low",
                                evidence_json=evidence,
                                decision_status="conflict"
                            )
                            
                            # UPSERT
                            existing = self.db.query(LeadLedger).filter(
                                LeadLedger.person_key == person_key
                            ).first()
                            
                            if existing:
                                existing.attributed_source = ledger_entry.attributed_source
                                existing.attributed_scout_id = ledger_entry.attributed_scout_id
                                existing.attribution_rule = ledger_entry.attribution_rule
                                existing.attribution_score = ledger_entry.attribution_score
                                existing.confidence_level = ledger_entry.confidence_level
                                existing.evidence_json = ledger_entry.evidence_json
                                existing.decision_status = ledger_entry.decision_status
                                existing.updated_at = datetime.utcnow()
                            else:
                                self.db.add(ledger_entry)
                            
                            stats["conflict_count"] += 1
                            logger.debug(f"Conflicto detectado para person_key {person_key}: scouts={list(scouts_map.keys())}, rango={first_date} a {last_date}")
                
                # REGLA A_FLEET (FLEET_MIGRATION ASSIGNED) - Prioridad más alta
                if len(fleet_migration_events) > 0:
                    # Evento fleet más reciente (max event_date)
                    most_recent_fleet = max(fleet_migration_data, key=lambda x: x["event_date"])
                    selected_scout_id = most_recent_fleet["scout_id"]
                    winning_event_id = most_recent_fleet["event_id"]
                    winning_event_date = most_recent_fleet["event_date"]
                    
                    evidence = {
                        "origin_tag_chosen": "fleet_migration",
                        "event_id": winning_event_id,
                        "event_date": winning_event_date.isoformat(),
                        "fleet_migration_events_count": len(fleet_migration_events),
                        "scouting_events_count": len(scouting_events),
                        "cabinet_events_count": len(cabinet_events),
                        "chosen_policy": "origin_priority"
                    }
                    
                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="fleet_migration",
                        attributed_scout_id=selected_scout_id,
                        attribution_rule="A_FLEET",
                        attribution_score=0.95,
                        confidence_level="high",
                        evidence_json=evidence,
                        decision_status="assigned"
                    )
                    
                    # UPSERT
                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()
                    
                    if existing:
                        existing.attributed_source = ledger_entry.attributed_source
                        existing.attributed_scout_id = ledger_entry.attributed_scout_id
                        existing.attribution_rule = ledger_entry.attribution_rule
                        existing.attribution_score = ledger_entry.attribution_score
                        existing.confidence_level = ledger_entry.confidence_level
                        existing.evidence_json = ledger_entry.evidence_json
                        existing.decision_status = ledger_entry.decision_status
                        existing.updated_at = datetime.utcnow()
                    else:
                        self.db.add(ledger_entry)
                    
                    stats["assigned_count"] += 1
                    stats_by_origin["fleet_migration"] += 1
                
                # REGLA A (SCOUTING ASSIGNED)
                elif not has_conflict and len(scouting_events) > 0:
                    # Scout más reciente (max event_date)
                    most_recent = max(scouting_data, key=lambda x: x["event_date"])
                    selected_scout_id = most_recent["scout_id"]
                    last_scout_date = most_recent["event_date"]
                    
                    # Encontrar el evento scouting más reciente para obtener event_id
                    most_recent_scouting_event = max(scouting_events, key=lambda x: x.event_date)
                    
                    evidence = {
                        "origin_tag_chosen": "scouting",
                        "event_id": most_recent_scouting_event.id,
                        "event_date": last_scout_date.isoformat(),
                        "last_scout_id": selected_scout_id,
                        "scouting_events_count": len(scouting_events),
                        "cabinet_events_count": len(cabinet_events),
                        "fleet_migration_events_count": len(fleet_migration_events),
                        "chosen_policy": "origin_priority"
                    }
                    
                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="scouting",
                        attributed_scout_id=selected_scout_id,
                        attribution_rule="A",
                        attribution_score=0.95,
                        confidence_level="high",
                        evidence_json=evidence,
                        decision_status="assigned"
                    )
                    
                    # UPSERT
                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()
                    
                    if existing:
                        existing.attributed_source = ledger_entry.attributed_source
                        existing.attributed_scout_id = ledger_entry.attributed_scout_id
                        existing.attribution_rule = ledger_entry.attribution_rule
                        existing.attribution_score = ledger_entry.attribution_score
                        existing.confidence_level = ledger_entry.confidence_level
                        existing.evidence_json = ledger_entry.evidence_json
                        existing.decision_status = ledger_entry.decision_status
                        existing.updated_at = datetime.utcnow()
                    else:
                        self.db.add(ledger_entry)
                    
                    stats["assigned_count"] += 1
                    stats_by_origin["scouting"] += 1
                
                # REGLA B (CABINET ASSIGNED)
                elif not has_conflict and len(cabinet_events) > 0:
                    # Calcular fechas de cabinet
                    cabinet_dates = [d["event_date"] for d in cabinet_data]
                    first_cabinet_date = min(cabinet_dates)
                    last_cabinet_date = max(cabinet_dates)
                    
                    # Encontrar el evento cabinet más reciente para obtener event_id
                    most_recent_cabinet_event = max(cabinet_events, key=lambda x: x.event_date)
                    
                    evidence = {
                        "origin_tag_chosen": "cabinet",
                        "event_id": most_recent_cabinet_event.id,
                        "event_date": last_cabinet_date.isoformat(),
                        "cabinet_events_count": len(cabinet_events),
                        "first_cabinet_date": first_cabinet_date.isoformat(),
                        "last_cabinet_date": last_cabinet_date.isoformat(),
                        "scouting_events_count": len(scouting_events),
                        "fleet_migration_events_count": len(fleet_migration_events),
                        "chosen_policy": "origin_priority"
                    }
                    
                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="cabinet",
                        attributed_scout_id=None,
                        attribution_rule="B",
                        attribution_score=0.80,
                        confidence_level="medium",
                        evidence_json=evidence,
                        decision_status="assigned"
                    )
                    
                    # UPSERT
                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()
                    
                    if existing:
                        existing.attributed_source = ledger_entry.attributed_source
                        existing.attributed_scout_id = ledger_entry.attributed_scout_id
                        existing.attribution_rule = ledger_entry.attribution_rule
                        existing.attribution_score = ledger_entry.attribution_score
                        existing.confidence_level = ledger_entry.confidence_level
                        existing.evidence_json = ledger_entry.evidence_json
                        existing.decision_status = ledger_entry.decision_status
                        existing.updated_at = datetime.utcnow()
                    else:
                        self.db.add(ledger_entry)
                    
                    stats["assigned_count"] += 1
                    stats_by_origin["cabinet"] += 1
                
                # REGLA U (UNASSIGNED)
                else:
                    evidence = {
                        "chosen_policy": "no_events"
                    }
                    
                    ledger_entry = LeadLedger(
                        person_key=person_key,
                        attributed_source="cabinet",  # Según especificación
                        attributed_scout_id=None,
                        attribution_rule="U",
                        attribution_score=0.00,
                        confidence_level="low",
                        evidence_json=evidence,
                        decision_status="unassigned"
                    )
                    
                    # UPSERT
                    existing = self.db.query(LeadLedger).filter(
                        LeadLedger.person_key == person_key
                    ).first()
                    
                    if existing:
                        existing.attributed_source = ledger_entry.attributed_source
                        existing.attributed_scout_id = ledger_entry.attributed_scout_id
                        existing.attribution_rule = ledger_entry.attribution_rule
                        existing.attribution_score = ledger_entry.attribution_score
                        existing.confidence_level = ledger_entry.confidence_level
                        existing.evidence_json = ledger_entry.evidence_json
                        existing.decision_status = ledger_entry.decision_status
                        existing.updated_at = datetime.utcnow()
                    else:
                        self.db.add(ledger_entry)
                    
                    stats["unassigned_count"] += 1
                    stats_by_origin["unassigned"] += 1
                
            except Exception as e:
                logger.error(f"Error procesando ledger para person_key {person_key}: {e}", exc_info=True)
                stats["errors_count"] += 1
                continue
            
            # Log progreso cada 50 person_keys
            if (idx + 1) % 50 == 0:
                logger.info(
                    f"Progreso: {idx + 1}/{total_persons} person_keys procesados. "
                    f"Asignados: {stats['assigned_count']}, "
                    f"Conflictos: {stats['conflict_count']}, "
                    f"Sin asignar: {stats['unassigned_count']}, "
                    f"Errores: {stats['errors_count']}"
                )
            
            # Commit periódico cada batch_size person_keys
            if (idx + 1) % batch_size == 0:
                try:
                    self.db.commit()
                    batch_count += 1
                except (IntegrityError, SQLAlchemyError, PendingRollbackError) as e:
                    try:
                        self.db.rollback()
                    except Exception:
                        pass
                    logger.error(f"Error de integridad en batch {batch_count}: {e}")
        
        # Commit final
        try:
            self.db.commit()
            logger.info(
                f"Finalizado process_ledger FASE 2.2. "
                f"Eventos procesados: {stats['processed_events']}, "
                f"Person_keys procesados: {stats['processed_person_keys']}, "
                f"Asignados: {stats['assigned_count']}, "
                f"Conflictos: {stats['conflict_count']}, "
                f"Sin asignar: {stats['unassigned_count']}, "
                f"Errores: {stats['errors_count']}"
            )
            logger.info(
                f"Distribución por origen: "
                f"fleet_migration={stats_by_origin['fleet_migration']}, "
                f"scouting={stats_by_origin['scouting']}, "
                f"cabinet={stats_by_origin['cabinet']}, "
                f"unassigned={stats_by_origin['unassigned']}"
            )
        except (IntegrityError, SQLAlchemyError, PendingRollbackError) as e:
            try:
                self.db.rollback()
            except Exception:
                pass
            logger.error(f"Error de integridad al procesar ledger (commit final): {e}")
            stats["errors_count"] += stats["processed_person_keys"]
            stats["processed_person_keys"] = 0
        
        return stats


# ============================================================================
# QUERIES SQL SUGERIDAS PARA VALIDACIÓN FASE 2.2
# ============================================================================
#
# a) Conteo por decision_status:
#    SELECT decision_status, COUNT(*) as count
#    FROM observational.lead_ledger
#    GROUP BY decision_status
#    ORDER BY count DESC;
#
# b) Conteo por attributed_source:
#    SELECT attributed_source, COUNT(*) as count
#    FROM observational.lead_ledger
#    GROUP BY attributed_source
#    ORDER BY count DESC;
#
# c) Top conflictos con evidence_json:
#    SELECT 
#        person_key,
#        attributed_source,
#        attribution_rule,
#        attribution_score,
#        confidence_level,
#        evidence_json->'scouts_in_conflict' as scouts_in_conflict,
#        evidence_json->'conflict_window_days' as conflict_window_days,
#        updated_at
#    FROM observational.lead_ledger
#    WHERE decision_status = 'conflict'
#    ORDER BY updated_at DESC
#    LIMIT 20;
#
# d) Validar regla A (scouting assigned):
#    SELECT 
#        person_key,
#        attributed_source,
#        attributed_scout_id,
#        attribution_rule,
#        attribution_score,
#        confidence_level,
#        evidence_json->'last_scout_id' as last_scout_id,
#        evidence_json->'last_scout_date' as last_scout_date,
#        evidence_json->'scouting_events_count' as scouting_events_count,
#        evidence_json->'cabinet_events_count' as cabinet_events_count
#    FROM observational.lead_ledger
#    WHERE attribution_rule = 'A'
#    ORDER BY updated_at DESC
#    LIMIT 20;
#
# e) Validar regla B (cabinet assigned):
#    SELECT 
#        person_key,
#        attributed_source,
#        attributed_scout_id,
#        attribution_rule,
#        attribution_score,
#        confidence_level,
#        evidence_json->'cabinet_events_count' as cabinet_events_count,
#        evidence_json->'first_cabinet_date' as first_cabinet_date,
#        evidence_json->'last_cabinet_date' as last_cabinet_date
#    FROM observational.lead_ledger
#    WHERE attribution_rule = 'B'
#    ORDER BY updated_at DESC
#    LIMIT 20;
#
# f) Validar regla U (unassigned):
#    SELECT 
#        person_key,
#        attributed_source,
#        attributed_scout_id,
#        attribution_rule,
#        attribution_score,
#        confidence_level,
#        evidence_json->'chosen_policy' as chosen_policy
#    FROM observational.lead_ledger
#    WHERE attribution_rule = 'U'
#    ORDER BY updated_at DESC
#    LIMIT 20;
#
# g) Verificar que conflictos NO tienen attributed_scout_id:
#    SELECT 
#        person_key,
#        attributed_source,
#        attributed_scout_id,
#        attribution_rule,
#        decision_status
#    FROM observational.lead_ledger
#    WHERE decision_status = 'conflict' AND attributed_scout_id IS NOT NULL;
#    -- Esta query debería retornar 0 filas
#
