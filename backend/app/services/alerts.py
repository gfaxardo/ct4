import logging
from datetime import date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.ops import Alert, AlertSeverity
from app.models.observational import ScoutingMatchCandidate
from app.api.v1.identity import (
    _get_scouting_processed_count,
    _get_scouting_candidates_count,
    _get_scouting_avg_time_to_match,
    _get_scouting_high_confidence_count
)

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def check_scouting_alerts(self, week_label: str, run_id: Optional[int] = None) -> List[Alert]:
        alerts = []
        
        processed = _get_scouting_processed_count(self.db, week_label)
        candidates = _get_scouting_candidates_count(self.db, week_label, run_id)
        avg_time = _get_scouting_avg_time_to_match(self.db, week_label, run_id)
        high_confidence = _get_scouting_high_confidence_count(self.db, week_label, run_id)
        
        alert_1 = self._check_no_echo_alert(week_label, processed, candidates, run_id)
        if alert_1:
            alerts.append(alert_1)
        
        alert_2 = self._check_high_delay_alert(week_label, avg_time, run_id)
        if alert_2:
            alerts.append(alert_2)
        
        alert_3 = self._check_strong_signal_alert(week_label, high_confidence, run_id)
        if alert_3:
            alerts.append(alert_3)
        
        for alert in alerts:
            existing = self.db.query(Alert).filter(
                Alert.alert_type == alert.alert_type,
                Alert.week_label == week_label,
                Alert.acknowledged_at.is_(None)
            ).first()
            
            if not existing:
                self.db.add(alert)
        
        self.db.commit()
        return alerts

    def _check_no_echo_alert(
        self,
        week_label: str,
        processed: int,
        candidates: int,
        run_id: Optional[int]
    ) -> Optional[Alert]:
        if processed > 50 and candidates == 0:
            prev_week = self._get_previous_week(week_label)
            if prev_week:
                prev_processed = _get_scouting_processed_count(self.db, prev_week)
                prev_candidates = _get_scouting_candidates_count(self.db, prev_week, run_id)
                
                if prev_processed > 50 and prev_candidates == 0:
                    return Alert(
                        alert_type="scouting_no_echo",
                        severity=AlertSeverity.WARNING,
                        week_label=week_label,
                        message="Scouting sin correlato posterior en fuentes confiables",
                        details={
                            "current_week": week_label,
                            "current_processed": processed,
                            "current_candidates": candidates,
                            "previous_week": prev_week,
                            "previous_processed": prev_processed,
                            "previous_candidates": prev_candidates
                        },
                        run_id=run_id
                    )
        return None

    def _check_high_delay_alert(
        self,
        week_label: str,
        avg_time: Optional[float],
        run_id: Optional[int]
    ) -> Optional[Alert]:
        if avg_time is not None and avg_time > 14:
            return Alert(
                alert_type="scouting_high_delay",
                severity=AlertSeverity.INFO,
                week_label=week_label,
                message="Alto delay entre scouting y aparición en Cabinet/Drivers",
                details={
                    "week_label": week_label,
                    "avg_time_to_match_days": avg_time
                },
                run_id=run_id
            )
        return None

    def _check_strong_signal_alert(
        self,
        week_label: str,
        high_confidence: int,
        run_id: Optional[int]
    ) -> Optional[Alert]:
        if high_confidence >= 5:
            return Alert(
                alert_type="scouting_strong_signal",
                severity=AlertSeverity.INFO,
                week_label=week_label,
                message="Scouting empieza a generar señales fuertes (pre-Fase 2)",
                details={
                    "week_label": week_label,
                    "high_confidence_candidates": high_confidence
                },
                run_id=run_id
            )
        return None

    def _get_previous_week(self, week_label: str) -> Optional[str]:
        try:
            year, week = week_label.split("-W")
            year = int(year)
            week = int(week)
            
            if week > 1:
                return f"{year}-W{week-1:02d}"
            else:
                return f"{year-1}-W52"
        except (ValueError, AttributeError):
            return None

    def get_active_alerts(self, limit: int = 100) -> List[Alert]:
        return self.db.query(Alert).filter(
            Alert.acknowledged_at.is_(None)
        ).order_by(Alert.created_at.desc()).limit(limit).all()

    def acknowledge_alert(self, alert_id: int) -> Optional[Alert]:
        from datetime import datetime
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.acknowledged_at = datetime.utcnow()
            self.db.commit()
        return alert


























