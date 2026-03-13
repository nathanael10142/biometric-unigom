

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.database import LocalSessionLocal
from app.services.attendance_service import process_pushed_event
from app.services.websocket_manager import manager


logger = logging.getLogger("ehome")


async def start_ehome_server() -> None:
    port = settings.EHOME_PORT
    server = await asyncio.start_server(_handle_client, host="0.0.0.0", port=port)
    addr = server.sockets[0].getsockname()
    logger.info("[EHOME] listening for ISUP connections on %s", addr)
    try:
        async with server:
            await server.serve_forever()
    except asyncio.CancelledError:
        logger.info("[EHOME] server task cancelled, shutting down")
        server.close()
        await server.wait_closed()
        raise


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    logger.info("[EHOME] new connection from %s", peer)
    try:
        while not reader.at_eof():
            data = await reader.readline()
            if not data:
                break
            try:
                event = _parse_message(data)
            except ValueError as exc:
                logger.warning("[EHOME] parse failure from %s: %s", peer, exc)
                continue

            if not _authenticate(event):
                logger.warning("[EHOME] authentication failed from %s", peer)
                break

            await _process_event(event)

            try:
                writer.write(b"OK\r\n")
                await writer.drain()
            except Exception:
                pass
    except Exception as exc:
        logger.exception("[EHOME] error handling client %s: %s", peer, exc)
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info("[EHOME] connection closed %s", peer)



_RE_KV = re.compile(r"([A-Za-z]+)[:=]\s*([^;\r\n]+)")


def _parse_message(raw: bytes) -> Dict[str, str]:
    text = raw.decode("ascii", errors="ignore")
    kv: Dict[str, str] = {}
    for match in _RE_KV.finditer(text):
        k = match.group(1)
        v = match.group(2).strip()
        kv[k] = v

    for required in ("employeeNo", "serialNo", "eventType", "time"):
        if required not in kv:
            raise ValueError(f"missing field {required}")
    return kv


def _authenticate(payload: Dict[str, str]) -> bool:
    return (
        payload.get("deviceAccount") == settings.EHOME_DEVICE_ACCOUNT
        and payload.get("eHomeKey") == settings.EHOME_KEY
    )


async def _process_event(payload: Dict[str, str]) -> None:
    biometric_id = payload.get("employeeNo") or ""
    device_id = payload.get("deviceID") or payload.get("deviceId") or "UNKNOWN"
    try:
        serial = int(payload.get("serialNo", "0"))
    except ValueError:
        serial = None
    raw_time = payload.get("time", "")

    db: Session = LocalSessionLocal()
    try:
        processed = process_pushed_event(
            db, biometric_id, serial, raw_time,
            device_id=device_id,
            campus_id=settings.CAMPUS_ID
        )
        if processed:
            logger.debug("[EHOME] event handled serial=%s bio=%s device=%s campus=%s", serial, biometric_id, device_id, settings.CAMPUS_ID)
            # Ultra-pro real-time: broadcast to frontend
            await manager.broadcast({
                "type": "new_scan",
                "biometric_id": biometric_id,
                "serial_no": serial,
                "raw_time": raw_time,
                "device_id": device_id,
                "campus_id": settings.CAMPUS_ID,
                "processed": True
            })
        else:
            logger.debug("[EHOME] event ignored serial=%s bio=%s", serial, biometric_id)
    finally:
        db.close()
