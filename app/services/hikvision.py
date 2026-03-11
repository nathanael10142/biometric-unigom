
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from app.config import settings

logger = logging.getLogger(__name__)



def _parse_challenge(www_auth: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key in ("realm", "nonce", "qop", "algorithm", "opaque"):
        m = re.search(rf'{key}="?([^",\s]*)"?', www_auth, re.IGNORECASE)
        if m:
            result[key] = m.group(1).strip('"')
    return result


def _md5(data: str) -> str:
    return hashlib.md5(data.encode("utf-8")).hexdigest()


def _build_digest_header(
    method: str,
    url: str,
    challenge: Dict[str, str],
    username: str,
    password: str,
) -> str:
    realm     = challenge.get("realm", "")
    nonce     = challenge.get("nonce", "")
    algorithm = challenge.get("algorithm", "MD5").upper()
    opaque    = challenge.get("opaque", "")
    qop_adv   = challenge.get("qop", "")
    path_only = urlparse(url).path

    ha1_raw = f"{username}:{realm}:{password}"
    ha1 = _md5(ha1_raw) if algorithm == "MD5" else hashlib.sha256(ha1_raw.encode()).hexdigest()
    ha2 = _md5(f"{method.upper()}:{path_only}")

    use_qop = "auth" in qop_adv
    if use_qop:
        nc     = "00000001"
        cnonce = _md5(os.urandom(8).hex())[:8]
        resp   = _md5(f"{ha1}:{nonce}:{nc}:{cnonce}:auth:{ha2}")
        header = (
            f'Digest username="{username}", realm="{realm}", '
            f'nonce="{nonce}", uri="{path_only}", '
            f'qop=auth, nc={nc}, cnonce="{cnonce}", '
            f'response="{resp}", algorithm={algorithm}'
        )
    else:
        resp   = _md5(f"{ha1}:{nonce}:{ha2}")
        header = (
            f'Digest username="{username}", realm="{realm}", '
            f'nonce="{nonce}", uri="{path_only}", '
            f'response="{resp}", algorithm={algorithm}'
        )

    if opaque:
        header += f', opaque="{opaque}"'
    return header


class HikvisionClient:

    def __init__(self) -> None:
        self._ip       = settings.HIKVISION_IP
        self._base_url = f"http://{self._ip}"
        self._timeout  = settings.HIKVISION_TIMEOUT


    def _digest_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: str,
    ) -> requests.Response:
        resp1 = requests.request(method, url, headers=headers, data=body, timeout=self._timeout)
        if resp1.status_code != 401:
            return resp1

        www_auth = resp1.headers.get("WWW-Authenticate", "")
        if not www_auth.lower().startswith("digest"):
            logger.warning("[HIKVISION] Non-Digest auth challenge: %r", www_auth)
            return resp1

        challenge   = _parse_challenge(www_auth)
        auth_header = _build_digest_header(
            method, url, challenge,
            settings.HIKVISION_USER, settings.HIKVISION_PASSWORD,
        )
        auth_headers = {**headers, "Authorization": auth_header}
        return requests.request(method, url, headers=auth_headers, data=body, timeout=self._timeout)


    def test_connection(self) -> bool:
        try:
            url  = f"{self._base_url}/ISAPI/System/deviceInfo"
            resp = self._digest_request("GET", url, {}, "")
            return resp.status_code == 200
        except Exception:
            return False

    def fetch_events(
        self,
        start_time:  Optional[datetime] = None,
        end_time:    Optional[datetime] = None,
        max_results: int = 50,
        position:    int = 0,
    ) -> Dict[str, Any]:
        cond: Dict[str, Any] = {
            "searchID":             "1",
            "searchResultPosition": position,
            "maxResults":           max_results,
            "major":                0,
            "minor":                0,
        }

        if start_time is not None and end_time is not None:
            cond["startTime"] = start_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            cond["endTime"]   = end_time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
            logger.debug(
                "[HIKVISION] Date-window page pos=%d [%s → %s]",
                position, cond["startTime"], cond["endTime"],
            )
        else:
            logger.debug("[HIKVISION] No-date page pos=%d max=%d", position, max_results)

        url  = f"{self._base_url}/ISAPI/AccessControl/AcsEvent?format=json"
        body = json.dumps({"AcsEventCond": cond})
        headers = {"Content-Type": "application/json"}

        for attempt in range(3):
            try:
                resp = self._digest_request("POST", url, headers, body)
                break
            except requests.exceptions.ConnectionError as exc:
                if attempt == 2:
                    raise
                logger.warning(
                    "[HIKVISION] Connection error, retrying (%d/3): %s", attempt + 1, exc
                )
                time.sleep(1)

        if resp.status_code == 401:
            logger.error(
                "[HIKVISION] Auth failed (401). Check HIKVISION_USER=%r / HIKVISION_PASSWORD.",
                settings.HIKVISION_USER,
            )
        resp.raise_for_status()
        return resp.json()

    def fetch_all_events(
        self,
        start_time:     Optional[datetime] = None,
        end_time:       Optional[datetime] = None,
        page_size:      int = 50,
        start_position: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        all_events: List[Dict[str, Any]] = []
        position       = start_position
        page_num       = 0
        total_matches: Optional[int] = None

        while True:
            page_num += 1
            try:
                data = self.fetch_events(start_time, end_time, page_size, position)
            except Exception as exc:
                logger.error(
                    "[HIKVISION] fetch_events failed page=%d pos=%d: %s",
                    page_num, position, exc,
                )
                raise

            acs       = data.get("AcsEvent", {})
            info_list = acs.get("InfoList") or []

            if total_matches is None:
                total_matches = acs.get("totalMatches")
                logger.info(
                    "[HIKVISION] Start pos=%d totalMatches=%s status=%r",
                    start_position,
                    total_matches,
                    acs.get("responseStatusStrg", "?"),
                )

            if not info_list:
                logger.debug(
                    "[HIKVISION] Empty InfoList at pos=%d — done after %d pages",
                    position, page_num - 1,
                )
                break

            all_events.extend(info_list)
            position += len(info_list)

            logger.info(
                "[HIKVISION] Page %d: fetched=%d cumulative=%d next_pos=%d",
                page_num, len(info_list), len(all_events), position,
            )

        logger.info(
            "[HIKVISION] ✅ Done: %d events fetched | next_position=%d",
            len(all_events), position,
        )
        return all_events, position


hikvision_client = HikvisionClient()
