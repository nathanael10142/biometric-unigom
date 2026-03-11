#!/usr/bin/env python
"""Test if Hikvision terminal is sending user 3 events."""
from app.services.hikvision import hikvision_client
from app.utils.time_utils import now_goma
from datetime import timedelta

end_time = now_goma()
start_time = end_time - timedelta(hours=24)

print('Récupération des événements du terminal Hikvision...')
print(f'Période: {start_time} à {end_time}')

try:
    events = hikvision_client.fetch_all_events(start_time, end_time)
    print(f'\n✓ {len(events)} événements reçus du terminal')
    
    # Afficher les biometric_ids uniques
    ids = set()
    for e in events:
        bio_id = (e.get('employeeNoString') or e.get('cardNo') or '').strip()
        if bio_id:
            ids.add(bio_id)
    
    print(f'IDs biométriques trouvés: {sorted(ids)}')
    
    # Afficher les événements pour l'utilisateur 3
    user3_events = [e for e in events if (e.get('employeeNoString') or '').strip() == '00000003']
    print(f'\n📌 Événements pour utilisateur 3: {len(user3_events)}')
    if user3_events:
        print('   Les 5 derniers:')
        for i, e in enumerate(user3_events[-5:]):
            print(f'   {i+1}. {e.get("time")} - ID: {e.get("employeeNoString")}')
    else:
        print('   ⚠️ Aucun événement pour utilisateur 3')
    
except Exception as exc:
    print(f'\n✗ Erreur: {exc}')
    import traceback
    traceback.print_exc()
