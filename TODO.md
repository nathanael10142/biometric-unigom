# Real-time Ultra-Pro Attendance App

## Objectif
Rendre chaque scan terminal **INSTANT** sur frontend (no poll):
- Backend EHome: déjà instant classify (PRESENT/retard/refusé) → DB
- Ajout: WebSocket broadcast new scan → frontend live table/stats

## Steps (✓ = done, update after each)

### Backend
- [x] 1. Create `backend/app/services/websocket_manager.py` (ConnectionManager)
- [x] 2. Create `backend/app/routers/websocket.py` (WS /api/v1/ws)
- [x] 3. Edit main.py include router
- [x] 4. Edit ehome_listener.py → broadcast new scan

### Frontend
- [x] 5. Create src/lib/websocket.ts client
- [x] 6. Edit dashboard/page.tsx → live with WS

## Test
- Backend: docker-compose up → curl ws://localhost:8000/api/v1/ws
- Frontend: npm run dev → scan → instant table/stats update



