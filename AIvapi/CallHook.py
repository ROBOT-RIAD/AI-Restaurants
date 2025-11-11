import json
from datetime import datetime, timezone
from typing import Any, Dict, Union
import re
import openai
from django.conf import settings
from openai import OpenAI
import pytz
from restaurants.models import Restaurant

openai.api_key = settings.OPENAI_API_KEY
client = OpenAI(api_key=openai.api_key)




def define_type(summary):
    try:
        response = client.responses.create(
                model="gpt-5-nano",
                input=f"""
                Based on the following call summary, classify the call type into one of these categories: 'reservation', 'order', 'service'.\n
                If user requests a reservation, classify as 'reservation'.\n
                If user places an order, classify as 'order'.\n
                If user asks for help or has a complaint or none of the above, classify as 'service'.\n\n
                Call Summary: {summary}\n
                Respond with only one word: 'reservation', 'order', or 'service'. No other text.
                """
            )

        return response.output_text.strip()
    except Exception as e:
        raise RuntimeError(f"Failed to classify call type: {e}")





def _parse_unix_numeric(value: Union[int, float]) -> Union[str, None]:
    ts_seconds = value / 1000 if value > 1e12 else value
    try:
        return datetime.fromtimestamp(ts_seconds, tz=timezone.utc).isoformat()  # includes both date and time
    except (OverflowError, OSError, ValueError):
        return None






def _parse_iso8601(value: str) -> Union[str, None]:
    s = value.strip()
    if s.endswith('Z'):
        s = s[:-1]  # Remove the 'Z' if it's there
    if ' ' in s and 'T' not in s:
        s = s.replace(' ', 'T')  # Ensure 'T' is there between date and time
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()  # Returns both date and time
    except ValueError:
        return None

        






def _parse_possible_numeric_string(value: str) -> Union[str, None]:
    s = value.strip()
    if s.isdigit():
        try:
            return _parse_unix_numeric(int(s))
        except Exception:
            return None
    if 'Date(' in s:
        m = re.search(r'Date\((\d{10,})\)', s)
        if m:
            try:
                return _parse_unix_numeric(int(m.group(1)))
            except Exception:
                return None
    return None






def extract_call_date_utc(started_at):
        if started_at is None:
            return None
        if isinstance(started_at, (int, float)):
            return _parse_unix_numeric(started_at)
        if isinstance(started_at, str):
            iso = _parse_iso8601(started_at)
            if iso:
                return iso
            num = _parse_possible_numeric_string(started_at)
            if num:
                return num
        return None






def get_call_date(msg: Dict[str, Any]):
    for c in _iter_candidates(msg):
        d = extract_call_date_utc(c)
        if d:
            return d
    return None





def _iter_candidates(msg: Dict[str, Any]):
        art = msg.get('artifact', {}) if isinstance(msg, dict) else {}
        keys = [
            ('artifact', 'startedAt'), ('artifact', 'started_at'),
            ('artifact', 'startTime'), ('artifact', 'started'),
            ('startedAt',), ('started_at',), ('startTime',), ('started',)
        ]
        for path in keys:
            cur = msg if path[0] != 'artifact' else art
            if len(path) == 2:
                cur = art.get(path[1])
            else:
                cur = msg.get(path[0])
            if cur is not None:
                yield cur




def get_time():
    germany_tz = pytz.timezone('Europe/Berlin')
    # Get the current time in Germany
    germany_time = datetime.now(germany_tz)
    
    return germany_time.strftime('%Y-%m-%d %H:%M:%S')




def vapi_webhook(request):
    payload = request.data
    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    artifact = message.get("artifact", {}) if isinstance(message, dict) else {}
    message_type = message.get("type")

    if message_type != "end-of-call-report":
        return {"status": "ignored", "reason": message_type}
    

    try:
        with open('text.txt', 'w') as f:
            json.dump(payload, f, indent=4)
    except Exception as e:
        print(f"Error saving payload to file: {e}")

    call_date = get_call_date(message)

    duration_seconds = (
        artifact.get("durationSeconds")
        or (artifact.get("durationMs", 0) / 1000 if artifact.get("durationMs") else None)
        or message.get("durationSeconds")
    )

    summary = (
        artifact.get("summary")
        or message.get("analysis", {}).get("summary")
    )

    recording_mono_combined_url = (
        (artifact.get("recording") or {})
        .get("mono", {})
        .get("combinedUrl")
    )

    


    assistant_id = message.get("assistant", {}).get("id")
    parsed = {
        "type": define_type(summary),
        "call_date": call_date,
        "phone" : message.get("customer" ,{}).get("number"),
        "duration_seconds": duration_seconds,
        "summary": summary,
        "recording": recording_mono_combined_url,
        "assistant_id": assistant_id,
        "cost": message.get("cost")
    }
    return parsed




