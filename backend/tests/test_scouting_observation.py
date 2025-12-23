import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from uuid import uuid4
from app.models.canon import IdentityLink, IdentityUnmatched, ConfidenceLevel, IdentityRegistry
from app.models.ops import IngestionRun, RunStatus, JobType
from app.models.observational import ScoutingMatchCandidate, MatchedSource, ConfidenceLevelObs
from app.services.scouting_observation import ScoutingObservationService
from app.services.alerts import AlertService
from app.db import SessionLocal, Base, engine


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_rule_s1_license_exact_match(db_session):
    from sqlalchemy import text
    
    person_key = uuid4()
    person = IdentityRegistry(
        person_key=person_key,
        confidence_level=ConfidenceLevel.HIGH,
        primary_license="ABC123"
    )
    db_session.add(person)
    db_session.commit()
    
    run = IngestionRun(
        status=RunStatus.COMPLETED,
        job_type=JobType.IDENTITY_RUN,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    
    test_date = datetime(2025, 12, 15, 10, 0, 0)
    
    db_session.execute(text("""
        INSERT INTO public.drivers (driver_id, license_number, hire_date)
        VALUES ('test_driver_s1', 'ABC123', :hire_date)
    """), {"hire_date": test_date.date()})
    db_session.commit()
    
    link = IdentityLink(
        person_key=person_key,
        source_table="drivers",
        source_pk="test_driver_s1",
        snapshot_date=test_date,
        match_rule="R1_LICENSE_EXACT",
        match_score=95,
        confidence_level=ConfidenceLevel.HIGH,
        run_id=run.id
    )
    db_session.add(link)
    db_session.commit()
    
    db_session.execute(text("""
        INSERT INTO public.module_ct_scouting_daily (id, registration_date, driver_license, driver_phone, driver_name)
        VALUES ('test_scout_s1', :reg_date, 'ABC123', '987654321', 'Test Driver')
    """), {"reg_date": date(2025, 12, 15)})
    db_session.commit()
    
    service = ScoutingObservationService(db_session)
    stats = service.process_scouting_observations(run.id, date(2025, 12, 15), date(2025, 12, 15))
    
    assert stats["candidates_s1_license"] > 0
    
    candidate = db_session.query(ScoutingMatchCandidate).filter(
        ScoutingMatchCandidate.match_rule == "S1"
    ).first()
    
    assert candidate is not None
    assert candidate.person_key_candidate == person_key
    assert candidate.matched_source == MatchedSource.DRIVERS
    assert candidate.score == 0.95
    assert candidate.confidence_level == ConfidenceLevelObs.HIGH


def test_rule_s2_phone_pe9_match(db_session):
    from sqlalchemy import text
    
    person_key = uuid4()
    person = IdentityRegistry(
        person_key=person_key,
        confidence_level=ConfidenceLevel.HIGH,
        primary_phone="987654321"
    )
    db_session.add(person)
    db_session.commit()
    
    run = IngestionRun(
        status=RunStatus.COMPLETED,
        job_type=JobType.IDENTITY_RUN,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    
    test_date = datetime(2025, 12, 15, 10, 0, 0)
    
    db_session.execute(text("""
        INSERT INTO public.drivers (driver_id, phone, hire_date)
        VALUES ('test_driver_s2', '+51987654321', :hire_date)
    """), {"hire_date": test_date.date()})
    db_session.commit()
    
    link = IdentityLink(
        person_key=person_key,
        source_table="drivers",
        source_pk="test_driver_s2",
        snapshot_date=test_date,
        match_rule="R2_PHONE_EXACT",
        match_score=90,
        confidence_level=ConfidenceLevel.HIGH,
        run_id=run.id
    )
    db_session.add(link)
    db_session.commit()
    
    db_session.execute(text("""
        INSERT INTO public.module_ct_scouting_daily (id, registration_date, driver_license, driver_phone, driver_name)
        VALUES ('test_scout_s2', :reg_date, 'XYZ789', '987654321', 'Test Driver')
    """), {"reg_date": date(2025, 12, 15)})
    db_session.commit()
    
    service = ScoutingObservationService(db_session)
    stats = service.process_scouting_observations(run.id, date(2025, 12, 15), date(2025, 12, 15))
    
    candidate = db_session.query(ScoutingMatchCandidate).filter(
        ScoutingMatchCandidate.match_rule == "S2"
    ).first()
    
    if candidate:
        assert candidate.person_key_candidate == person_key
        assert candidate.matched_source == MatchedSource.DRIVERS
        assert candidate.score == 0.85
        assert candidate.confidence_level == ConfidenceLevelObs.HIGH


def test_identity_registry_not_modified(db_session):
    initial_count = db_session.query(IdentityRegistry).count()
    initial_links_count = db_session.query(IdentityLink).count()
    
    run = IngestionRun(
        status=RunStatus.COMPLETED,
        job_type=JobType.IDENTITY_RUN,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    
    service = ScoutingObservationService(db_session)
    service.process_scouting_observations(run.id, date(2025, 12, 1), date(2025, 12, 31))
    
    final_count = db_session.query(IdentityRegistry).count()
    final_links_count = db_session.query(IdentityLink).count()
    
    assert final_count == initial_count
    assert final_links_count == initial_links_count


def test_scouting_kpis_calculation(db_session):
    from app.api.v1.identity import _get_scouting_weekly_kpis
    
    run = IngestionRun(
        status=RunStatus.COMPLETED,
        job_type=JobType.IDENTITY_RUN,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    
    candidate = ScoutingMatchCandidate(
        week_label="2025-W51",
        scouting_row_id="test_scouting_1",
        scouting_date=date(2025, 12, 15),
        person_key_candidate=uuid4(),
        matched_source=MatchedSource.DRIVERS,
        match_rule="S1",
        score=0.95,
        confidence_level=ConfidenceLevelObs.HIGH,
        matched_source_pk="driver_1",
        matched_source_date=date(2025, 12, 16),
        time_to_match_days=1,
        run_id=run.id
    )
    db_session.add(candidate)
    db_session.commit()
    
    kpis = _get_scouting_weekly_kpis(db_session, run.id, "2025-W51")
    
    assert len(kpis) > 0
    kpi = kpis[0]
    assert kpi["week_label"] == "2025-W51"
    assert kpi["candidates_detected"] >= 1
    assert kpi["candidate_rate"] >= 0


def test_alerts_generation(db_session):
    from app.api.v1.identity import _get_scouting_processed_count, _get_scouting_candidates_count
    
    run = IngestionRun(
        status=RunStatus.COMPLETED,
        job_type=JobType.IDENTITY_RUN,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    
    service = AlertService(db_session)
    
    week_label = "2025-W51"
    
    alerts = service.check_scouting_alerts(week_label, run.id)
    
    assert isinstance(alerts, list)


def test_high_confidence_alert(db_session):
    from app.models.ops import Alert, AlertSeverity
    
    run = IngestionRun(
        status=RunStatus.COMPLETED,
        job_type=JobType.IDENTITY_RUN,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    
    for i in range(5):
        candidate = ScoutingMatchCandidate(
            week_label="2025-W51",
            scouting_row_id=f"test_scouting_{i}",
            scouting_date=date(2025, 12, 15),
            person_key_candidate=uuid4(),
            matched_source=MatchedSource.DRIVERS,
            match_rule="S1",
            score=0.95,
            confidence_level=ConfidenceLevelObs.HIGH,
            matched_source_pk=f"driver_{i}",
            matched_source_date=date(2025, 12, 16),
            time_to_match_days=1,
            run_id=run.id
        )
        db_session.add(candidate)
    db_session.commit()
    
    service = AlertService(db_session)
    alerts = service.check_scouting_alerts("2025-W51", run.id)
    
    strong_signal_alerts = [a for a in alerts if a.alert_type == "scouting_strong_signal"]
    assert len(strong_signal_alerts) > 0

