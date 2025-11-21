"""
CKCIAS Drought Monitor - Trigger Evaluation Engine
Evaluates drought alert triggers against live weather data and manages notifications

This module provides the core logic for:
- Evaluating individual conditions against weather data
- Applying combination rules (any_1, any_2, any_3, all)
- Managing notification rate limiting (6-hour window)
- Generating actionable recommendations based on triggered conditions
"""

import operator as op
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from database import (
    get_db_connection,
    get_user_triggers,
    get_trigger_conditions,
    log_notification
)

# Create FastAPI router
router = APIRouter(prefix="/triggers", tags=["trigger-evaluation"])

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Operator mapping for condition evaluation
OPERATORS = {
    '>': op.gt,
    '<': op.lt,
    '>=': op.ge,
    '<=': op.le,
    '==': op.eq
}


# Indicator mapping from database to weather data keys
INDICATOR_MAP = {
    'temp': 'temperature',
    'rainfall': 'rainfall',
    'humidity': 'humidity',
    'wind_speed': 'wind_speed'
}


def evaluate_condition(condition: Dict[str, Any], weather_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Evaluate a single condition against weather data.

    Args:
        condition: Dictionary with keys:
            - indicator: Weather metric to check (temp, rainfall, humidity, wind_speed)
            - operator: Comparison operator (>, <, >=, <=, ==)
            - threshold_value: Threshold to compare against
        weather_data: Dictionary containing current weather measurements

    Returns:
        Tuple of (condition_met: bool, error_message: Optional[str])

    Example:
        condition = {"indicator": "temp", "operator": ">", "threshold_value": 25.0}
        weather_data = {"temperature": 27.5, "humidity": 55}
        result, error = evaluate_condition(condition, weather_data)
        # Returns: (True, None)
    """
    try:
        indicator = condition.get('indicator')
        operator_str = condition.get('operator')
        threshold = condition.get('threshold_value')

        # Validate required fields
        if not all([indicator, operator_str, threshold is not None]):
            error_msg = f"Invalid condition: missing required fields"
            logger.warning(error_msg)
            return False, error_msg

        # Validate operator
        if operator_str not in OPERATORS:
            error_msg = f"Invalid operator: {operator_str}"
            logger.warning(error_msg)
            return False, error_msg

        # Map indicator to weather data key
        weather_key = INDICATOR_MAP.get(indicator)
        if not weather_key:
            error_msg = f"Invalid indicator: {indicator}"
            logger.warning(error_msg)
            return False, error_msg

        # Check if weather data contains the indicator
        if weather_key not in weather_data:
            error_msg = f"Weather data missing indicator: {weather_key}"
            logger.warning(error_msg)
            return False, error_msg

        # Get actual value from weather data
        actual_value = weather_data[weather_key]

        # Handle None/null values
        if actual_value is None:
            error_msg = f"Weather data has null value for: {weather_key}"
            logger.warning(error_msg)
            return False, error_msg

        # Perform comparison
        operator_func = OPERATORS[operator_str]
        result = operator_func(float(actual_value), float(threshold))

        logger.info(
            f"Condition evaluation: {weather_key} ({actual_value}) "
            f"{operator_str} {threshold} = {result}"
        )

        return result, None

    except Exception as e:
        error_msg = f"Error evaluating condition: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg


def apply_combination_rule(
    rule: str,
    conditions_met_count: int,
    total_conditions: int
) -> bool:
    """
    Apply K-of-N combination rule logic to determine if trigger should fire.

    Implements the following logic:
    - any_1: At least 1 condition met (1+ conditions met)
    - any_2: At least 2 conditions met (2+ conditions met)
    - any_3: At least 3 conditions met (3+ conditions met)
    - all: All conditions met

    Args:
        rule: One of 'any_1', 'any_2', 'any_3', 'all'
        conditions_met_count: Number of conditions that were met
        total_conditions: Total number of conditions evaluated

    Returns:
        Boolean indicating if trigger should fire based on the rule

    Examples:
        apply_combination_rule('any_1', 1, 3) -> True
        apply_combination_rule('any_2', 2, 3) -> True
        apply_combination_rule('any_2', 1, 3) -> False
        apply_combination_rule('any_3', 3, 5) -> True
        apply_combination_rule('all', 3, 3) -> True
        apply_combination_rule('all', 2, 3) -> False
    """
    if rule == 'any_1':
        return conditions_met_count >= 1
    elif rule == 'any_2':
        return conditions_met_count >= 2
    elif rule == 'any_3':
        return conditions_met_count >= 3
    elif rule == 'all':
        return conditions_met_count == total_conditions
    else:
        logger.warning(f"Unknown combination rule: {rule}")
        return False


def evaluate_trigger(
    trigger: Dict[str, Any],
    weather_data: Dict[str, Any]
) -> Tuple[bool, List[Dict[str, Any]], List[str]]:
    """
    Evaluate a complete trigger against weather data.

    Args:
        trigger: Trigger dictionary with:
            - id: Trigger ID
            - combination_rule: How to combine conditions
            - (other trigger metadata)
        weather_data: Current weather measurements

    Returns:
        Tuple of:
        - triggered: Boolean indicating if trigger fired
        - conditions_met: List of dicts with condition details and results
        - errors: List of error messages encountered

    Example:
        trigger = {
            "id": 1,
            "name": "Taranaki Drought Alert",
            "combination_rule": "any_2"
        }
        weather_data = {"temperature": 27, "rainfall": 1.5, "humidity": 55}
        triggered, conditions, errors = evaluate_trigger(trigger, weather_data)
    """
    trigger_id = trigger.get('id')
    combination_rule = trigger.get('combination_rule')
    errors = []

    logger.info(f"Evaluating trigger {trigger_id}: {trigger.get('name')}")

    try:
        # Get all conditions for this trigger
        conditions = get_trigger_conditions(trigger_id)

        if not conditions:
            error_msg = f"No conditions found for trigger {trigger_id}"
            logger.warning(error_msg)
            return False, [], [error_msg]

        # Evaluate each condition
        conditions_results = []
        conditions_met_flags = []

        for condition in conditions:
            met, error = evaluate_condition(condition, weather_data)

            if error:
                errors.append(error)

            conditions_met_flags.append(met)

            # Build detailed result
            condition_result = {
                'id': condition.get('id'),
                'indicator': condition.get('indicator'),
                'operator': condition.get('operator'),
                'threshold_value': condition.get('threshold_value'),
                'actual_value': weather_data.get(
                    INDICATOR_MAP.get(condition.get('indicator')),
                    None
                ),
                'met': met,
                'error': error
            }
            conditions_results.append(condition_result)

        # Apply combination rule
        conditions_met_count = sum(conditions_met_flags)
        total_conditions = len(conditions_met_flags)
        triggered = apply_combination_rule(combination_rule, conditions_met_count, total_conditions)

        logger.info(
            f"Trigger {trigger_id} evaluation complete: "
            f"triggered={triggered}, "
            f"conditions_met={sum(conditions_met_flags)}/{len(conditions_met_flags)}, "
            f"rule={combination_rule}"
        )

        return triggered, conditions_results, errors

    except Exception as e:
        error_msg = f"Error evaluating trigger {trigger_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, [], [error_msg]


def evaluate_all_triggers(
    user_id: int,
    weather_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluate all active triggers for a user against weather data.

    Args:
        user_id: User ID to evaluate triggers for
        weather_data: Current weather measurements

    Returns:
        List of triggered alerts with full details:
        - trigger: Original trigger object
        - conditions_met: List of conditions and their results
        - recommendations: Actionable recommendations
        - evaluated_at: Timestamp of evaluation
        - errors: Any errors encountered

    Example:
        alerts = evaluate_all_triggers(user_id=2, weather_data={...})
        for alert in alerts:
            print(f"ALERT: {alert['trigger']['name']}")
            print(f"Recommendations: {alert['recommendations']}")
    """
    logger.info(f"Evaluating all triggers for user {user_id}")

    triggered_alerts = []

    try:
        # Get all triggers for the user
        triggers = get_user_triggers(user_id)

        if not triggers:
            logger.info(f"No triggers found for user {user_id}")
            return []

        # Filter only active triggers
        active_triggers = [t for t in triggers if t.get('is_active')]

        logger.info(
            f"Found {len(triggers)} total triggers, "
            f"{len(active_triggers)} active for user {user_id}"
        )

        # Evaluate each active trigger
        for trigger in active_triggers:
            triggered, conditions_met, errors = evaluate_trigger(trigger, weather_data)

            if triggered:
                # Get recommendations based on conditions met
                recommendations = get_trigger_recommendations(conditions_met)

                alert = {
                    'trigger': trigger,
                    'conditions_met': conditions_met,
                    'recommendations': recommendations,
                    'evaluated_at': datetime.utcnow().isoformat() + 'Z',
                    'errors': errors
                }

                triggered_alerts.append(alert)

                logger.info(
                    f"ALERT TRIGGERED: Trigger {trigger['id']} - {trigger['name']}"
                )

        logger.info(
            f"Evaluation complete: {len(triggered_alerts)} alerts triggered "
            f"out of {len(active_triggers)} active triggers"
        )

        return triggered_alerts

    except Exception as e:
        error_msg = f"Error evaluating triggers for user {user_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return []


def get_trigger_recommendations(conditions_met: List[Dict[str, Any]]) -> List[str]:
    """
    Generate actionable recommendations based on conditions that were met.

    Args:
        conditions_met: List of condition evaluation results

    Returns:
        List of recommendation strings

    Example:
        conditions_met = [
            {"indicator": "temp", "met": True, "actual_value": 28},
            {"indicator": "rainfall", "met": True, "actual_value": 1.2}
        ]
        recommendations = get_trigger_recommendations(conditions_met)
        # Returns: [
        #     "High temperature detected (28°C). Consider irrigation scheduling...",
        #     "Low rainfall detected (1.2mm). Monitor soil moisture levels..."
        # ]
    """
    recommendations = []

    # Recommendation templates based on indicators
    recommendation_templates = {
        'temp': {
            'high': "High temperature detected ({value}°C). Consider irrigation scheduling and provide shade for livestock. Monitor heat stress in animals.",
            'description': "temperature conditions"
        },
        'rainfall': {
            'low': "Low rainfall detected ({value}mm). Monitor soil moisture levels closely. Consider reducing stock numbers if pasture condition deteriorates.",
            'description': "rainfall levels"
        },
        'humidity': {
            'low': "Low humidity detected ({value}%). Increased evapotranspiration expected. Irrigation systems may need adjustment.",
            'high': "High humidity detected ({value}%). Monitor for disease pressure in crops and pasture.",
            'description': "humidity levels"
        },
        'wind_speed': {
            'high': "High wind speed detected ({value}km/h). Increased moisture loss expected. Protect young plants and check irrigation coverage.",
            'description': "wind conditions"
        }
    }

    # Generate recommendations for each met condition
    for condition in conditions_met:
        if not condition.get('met'):
            continue

        indicator = condition.get('indicator')
        operator = condition.get('operator')
        actual_value = condition.get('actual_value')

        if indicator not in recommendation_templates:
            continue

        template = recommendation_templates[indicator]

        # Determine if it's a high or low threshold breach
        if indicator == 'temp':
            if operator in ['>', '>=']:
                recommendation = template['high'].format(value=actual_value)
            else:
                continue
        elif indicator == 'rainfall':
            if operator in ['<', '<=']:
                recommendation = template['low'].format(value=actual_value)
            else:
                continue
        elif indicator == 'humidity':
            if operator in ['<', '<=']:
                recommendation = template['low'].format(value=actual_value)
            elif operator in ['>', '>=']:
                recommendation = template['high'].format(value=actual_value)
            else:
                continue
        elif indicator == 'wind_speed':
            if operator in ['>', '>=']:
                recommendation = template['high'].format(value=actual_value)
            else:
                continue
        else:
            continue

        recommendations.append(recommendation)

    # Add general drought management recommendation if multiple conditions met
    if len([c for c in conditions_met if c.get('met')]) >= 2:
        recommendations.append(
            "Multiple drought indicators detected. Review your drought management plan "
            "and consider consulting with local agricultural advisors."
        )

    return recommendations


def check_notification_rate_limit(
    trigger_id: int,
    user_id: int,
    rate_limit_hours: int = 6
) -> Tuple[bool, Optional[datetime]]:
    """
    Check if a notification should be sent based on rate limiting.

    Prevents notification spam by enforcing a minimum time window
    between notifications for the same trigger.

    Args:
        trigger_id: ID of the trigger
        user_id: ID of the user
        rate_limit_hours: Minimum hours between notifications (default: 6)

    Returns:
        Tuple of:
        - should_send: Boolean indicating if notification should be sent
        - last_sent_at: DateTime of last notification (None if never sent)

    Example:
        should_send, last_sent = check_notification_rate_limit(
            trigger_id=1,
            user_id=2,
            rate_limit_hours=6
        )
        if should_send:
            send_notification(...)
            log_notification(...)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get the most recent notification for this trigger and user
            cursor.execute("""
                SELECT sent_at
                FROM notification_log
                WHERE trigger_id = ? AND user_id = ?
                ORDER BY sent_at DESC
                LIMIT 1
            """, (trigger_id, user_id))

            row = cursor.fetchone()

            if not row:
                # No previous notification, safe to send
                logger.info(
                    f"No previous notification found for trigger {trigger_id}, "
                    f"user {user_id}"
                )
                return True, None

            # Parse last sent timestamp
            last_sent_str = row['sent_at']
            last_sent_at = datetime.fromisoformat(last_sent_str.replace('Z', '+00:00'))

            # Calculate time since last notification
            now = datetime.utcnow()
            time_since_last = now - last_sent_at
            rate_limit_delta = timedelta(hours=rate_limit_hours)

            should_send = time_since_last >= rate_limit_delta

            logger.info(
                f"Rate limit check for trigger {trigger_id}, user {user_id}: "
                f"last_sent={last_sent_at}, "
                f"time_since={time_since_last}, "
                f"should_send={should_send}"
            )

            return should_send, last_sent_at

    except Exception as e:
        error_msg = f"Error checking notification rate limit: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # On error, err on the side of caution and don't send
        return False, None


def log_trigger_evaluation(
    trigger_id: int,
    user_id: int,
    triggered: bool,
    conditions_met: List[Dict[str, Any]],
    notification_sent: bool = False
) -> Optional[int]:
    """
    Log the results of a trigger evaluation.

    This function logs notifications when triggers fire and optionally
    when notifications are sent to users.

    Args:
        trigger_id: ID of the evaluated trigger
        user_id: ID of the user
        triggered: Whether the trigger fired
        conditions_met: List of condition evaluation results
        notification_sent: Whether a notification was actually sent

    Returns:
        ID of the log entry, or None if not logged
    """
    if not triggered:
        # Only log when trigger actually fires
        return None

    try:
        # Prepare conditions data for logging
        conditions_data = {
            'conditions': [
                {
                    'indicator': c.get('indicator'),
                    'operator': c.get('operator'),
                    'threshold': c.get('threshold_value'),
                    'actual': c.get('actual_value'),
                    'met': c.get('met')
                }
                for c in conditions_met
            ],
            'notification_sent': notification_sent
        }

        # Log to notification_log table
        log_id = log_notification(
            trigger_id=trigger_id,
            user_id=user_id,
            trigger_conditions_met=conditions_data,
            notification_type='email'
        )

        logger.info(
            f"Logged trigger evaluation: trigger_id={trigger_id}, "
            f"user_id={user_id}, log_id={log_id}, "
            f"notification_sent={notification_sent}"
        )

        return log_id

    except Exception as e:
        logger.error(f"Error logging trigger evaluation: {str(e)}", exc_info=True)
        return None


# ===========================
# FastAPI Endpoint Models
# ===========================

class TriggerEvaluationRequest(BaseModel):
    """Request model for trigger evaluation endpoint"""
    user_id: int = Field(..., description="User ID whose triggers to evaluate")
    weather_data: Dict[str, Any] = Field(..., description="Current weather data")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 2,
                "weather_data": {
                    "temperature": 27.5,
                    "rainfall": 1.2,
                    "humidity": 55.0,
                    "wind_speed": 15.0
                }
            }
        }


class TriggerEvaluationResponse(BaseModel):
    """Response model for trigger evaluation endpoint"""
    alerts: List[Dict[str, Any]]
    total_alerts: int
    evaluated_at: str
    user_id: int


# ===========================
# FastAPI Endpoint
# ===========================

# ============================================
# FastAPI Endpoint
# ============================================

@router.options("/evaluate")
async def options_evaluate_triggers(response: Response):
    """
    Handle OPTIONS request for CORS preflight explicitly.
    This fixes the 400 Bad Request issue on preflight checks.
    """
    # The CORSMiddleware in main.py will attach the necessary headers
    # provided we return a 200 OK response.
    response.status_code = 200
    return {}

@router.post("/evaluate", response_model=TriggerEvaluationResponse)
async def evaluate_triggers_endpoint(request: TriggerEvaluationRequest):
    """
    POST /api/triggers/evaluate

    Evaluate all active triggers for a user against current weather data.

    This endpoint is the core of the drought monitoring system. It:
    1. Retrieves all active triggers for the specified user
    2. Evaluates each trigger's conditions against the provided weather data
    3. Applies combination rules (any_1, any_2, any_3, all)
    4. Returns triggered alerts with actionable recommendations

    **Request Body:**
    - **user_id**: ID of the user whose triggers to evaluate
    - **weather_data**: Current weather measurements including:
        - temperature (°C)
        - rainfall (mm)
        - humidity (%)
        - wind_speed (km/h)

    **Response:**
    - **alerts**: List of triggered alerts with:
        - trigger: Trigger details (name, region, combination_rule)
        - conditions_met: List of conditions and their results
        - recommendations: Actionable recommendations for farmers
        - evaluated_at: Timestamp of evaluation
        - errors: Any errors encountered
    - **total_alerts**: Count of alerts triggered
    - **evaluated_at**: Timestamp of evaluation
    - **user_id**: User ID that was evaluated

    **Example Usage:**
    ```python
    import requests

    response = requests.post('http://localhost:9100/api/triggers/evaluate', json={
        "user_id": 2,
        "weather_data": {
            "temperature": 27.5,
            "rainfall": 1.2,
            "humidity": 55.0,
            "wind_speed": 15.0
        }
    })

    alerts = response.json()['alerts']
    for alert in alerts:
        print(f"ALERT: {alert['trigger']['name']}")
        for rec in alert['recommendations']:
            print(f"  - {rec}")
    ```
    """
    try:
        logger.info(f"Evaluating triggers for user {request.user_id} via API endpoint")

        # Evaluate all triggers for the user
        alerts = evaluate_all_triggers(
            user_id=request.user_id,
            weather_data=request.weather_data
        )

        # Return evaluation results
        return TriggerEvaluationResponse(
            alerts=alerts,
            total_alerts=len(alerts),
            evaluated_at=datetime.utcnow().isoformat() + 'Z',
            user_id=request.user_id
        )

    except Exception as e:
        error_msg = f"Trigger evaluation error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
