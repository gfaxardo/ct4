import pytest
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from uuid import uuid4
from app.models.canon import IdentityLink, IdentityUnmatched, ConfidenceLevel, IdentityRegistry
from app.models.ops import IngestionRun, RunStatus, JobType
from app.api.v1.identity import _parse_event_week, _get_available_weeks, _calculate_weekly_trend
from app.db import SessionLocal, Base, engine


def test_week_label_iso():
    week_start, week_end = _parse_event_week("2025-W51")
    assert week_start.weekday() == 0
    assert week_end.weekday() == 6
    assert week_end - week_start == timedelta(days=6)
    
    iso_year, iso_week, iso_day = week_start.isocalendar()
    assert iso_year == 2025
    assert iso_week == 51
    
    week_start2, week_end2 = _parse_event_week("2024-W01")
    iso_year2, iso_week2, iso_day2 = week_start2.isocalendar()
    assert iso_year2 == 2024
    assert iso_week2 == 1


def test_parse_event_week_invalid_format():
    with pytest.raises(Exception):
        _parse_event_week("invalid")
    
    with pytest.raises(Exception):
        _parse_event_week("2025-W")
    
    with pytest.raises(Exception):
        _parse_event_week("2025")


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_weekly_counts_structure(db_session):
    person_key1 = uuid4()
    person_key2 = uuid4()
    
    person1 = IdentityRegistry(
        person_key=person_key1,
        confidence_level=ConfidenceLevel.HIGH
    )
    person2 = IdentityRegistry(
        person_key=person_key2,
        confidence_level=ConfidenceLevel.HIGH
    )
    db_session.add_all([person1, person2])
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
    
    test_date1 = datetime(2025, 12, 15, 10, 0, 0)
    test_date2 = datetime(2025, 12, 22, 10, 0, 0)
    
    link1 = IdentityLink(
        person_key=person_key1,
        source_table="module_ct_cabinet_leads",
        source_pk="test1",
        snapshot_date=test_date1,
        match_rule="R1_PHONE_EXACT",
        match_score=95,
        confidence_level=ConfidenceLevel.HIGH,
        run_id=run.id
    )
    
    link2 = IdentityLink(
        person_key=person_key2,
        source_table="module_ct_cabinet_leads",
        source_pk="test2",
        snapshot_date=test_date2,
        match_rule="R2_LICENSE_EXACT",
        match_score=92,
        confidence_level=ConfidenceLevel.HIGH,
        run_id=run.id
    )
    
    unmatched1 = IdentityUnmatched(
        source_table="module_ct_cabinet_leads",
        source_pk="test3",
        snapshot_date=test_date1,
        reason_code="MISSING_KEYS",
        details={"missing_keys": ["phone", "document"]},
        run_id=run.id
    )
    
    db_session.add_all([link1, link2, unmatched1])
    db_session.commit()
    
    weeks = _get_available_weeks(db_session, run.id)
    assert len(weeks) > 0
    assert all("W" in week for week in weeks)


def test_week_filter_event_week(db_session):
    person_key = uuid4()
    person = IdentityRegistry(
        person_key=person_key,
        confidence_level=ConfidenceLevel.HIGH
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
    
    link = IdentityLink(
        person_key=person_key,
        source_table="module_ct_cabinet_leads",
        source_pk="test1",
        snapshot_date=test_date,
        match_rule="R1_PHONE_EXACT",
        match_score=95,
        confidence_level=ConfidenceLevel.HIGH,
        run_id=run.id
    )
    
    db_session.add(link)
    db_session.commit()
    
    week_start, week_end = _parse_event_week("2025-W51")
    assert week_start <= test_date.date() <= week_end


def test_trend_deltas():
    weekly_data = [
        {
            "week_start": "2025-12-08",
            "week_label": "2025-W50",
            "source_table": "module_ct_cabinet_leads",
            "matched": 10,
            "unmatched": 5,
            "processed_total": 15,
            "match_rate": 66.67
        },
        {
            "week_start": "2025-12-15",
            "week_label": "2025-W51",
            "source_table": "module_ct_cabinet_leads",
            "matched": 15,
            "unmatched": 3,
            "processed_total": 18,
            "match_rate": 83.33
        }
    ]
    
    trends = _calculate_weekly_trend(weekly_data)
    assert len(trends) > 0
    
    trend = trends[0]
    assert trend["delta_match_rate"] is not None
    assert trend["delta_match_rate"] == pytest.approx(16.66, abs=0.1)
    assert trend["delta_matched"] == 5
    assert trend["delta_unmatched"] == -2


def test_trend_single_week():
    weekly_data = [
        {
            "week_start": "2025-12-15",
            "week_label": "2025-W51",
            "source_table": "module_ct_cabinet_leads",
            "matched": 15,
            "unmatched": 3,
            "processed_total": 18,
            "match_rate": 83.33
        }
    ]
    
    trends = _calculate_weekly_trend(weekly_data)
    assert len(trends) > 0
    
    trend = trends[0]
    assert trend["delta_match_rate"] is None
    assert trend["delta_matched"] is None
    assert trend["delta_unmatched"] is None
    assert trend["current_match_rate"] == 83.33


def test_missing_keys_unnest_structure(db_session):
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
    
    unmatched = IdentityUnmatched(
        source_table="module_ct_cabinet_leads",
        source_pk="test1",
        snapshot_date=test_date,
        reason_code="MISSING_KEYS",
        details={"missing_keys": ["phone", "document", "license"]},
        run_id=run.id
    )
    
    db_session.add(unmatched)
    db_session.commit()
    
    assert unmatched.details is not None
    assert "missing_keys" in unmatched.details
    assert isinstance(unmatched.details["missing_keys"], list)
    assert len(unmatched.details["missing_keys"]) == 3


def test_backward_compatibility_structure():
    from app.schemas.identity import RunReportResponse
    
    response_data = {
        "run": {
            "id": 1,
            "status": "COMPLETED",
            "started_at": "2025-12-15T10:00:00",
            "completed_at": "2025-12-15T10:05:00"
        },
        "counts_by_source_table": {
            "module_ct_cabinet_leads": {
                "total_processed": 10,
                "matched_count": 7,
                "unmatched_count": 3,
                "skipped_count": 0
            }
        },
        "matched_breakdown": {
            "by_match_rule": {"R1_PHONE_EXACT": 5},
            "by_confidence": {"HIGH": 7}
        },
        "unmatched_breakdown": {
            "by_reason_code": {"MISSING_KEYS": 3},
            "top_missing_keys": []
        },
        "samples": {
            "top_unmatched": [],
            "top_matched": []
        }
    }
    
    response = RunReportResponse(**response_data)
    assert response.weekly is None
    assert response.weekly_trend is None
    assert response.available_event_weeks is None
    assert response.run["id"] == 1
    assert response.counts_by_source_table["module_ct_cabinet_leads"]["matched_count"] == 7

