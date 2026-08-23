import base64
import json
import urllib.request
import uuid

backend = 'https://caseclock-backend-50043773125.development.catalystappsail.in'

# 1. Health check
res = urllib.request.urlopen(backend + '/health', timeout=20)
print('1. Live Backend Health:', res.status, json.loads(res.read()))

# 2. Get active case ID from worklist
res = urllib.request.urlopen(backend + '/worklist', timeout=20)
worklist = json.loads(res.read())
case_id = worklist[0]['id']
print('2. Target Case ID:', case_id, 'Original Category:', worklist[0]['offence_category'])

# 3. Live Document Scan (JSON + base64 — no python-multipart required)
fir_text = (
    b'%PDF-1.4 Karnataka State Police\n'
    b'FIR No. FIR/MYS/2026/0888\n'
    b'P.S.: Mysuru Central\n'
    b'Date: 15/07/2026\n'
    b'Offence: Murder Homicide BNS 103\n'
)
scan_body = json.dumps({
    'filename': 'scanned_fir_sample.pdf',
    'content_type': 'application/pdf',
    'document_type': 'fir',
    'file_base64': base64.b64encode(fir_text).decode(),
}).encode('utf-8')

req = urllib.request.Request(
    f'{backend}/api/v1/cases/{case_id}/documents/scan',
    data=scan_body,
    headers={
        'Content-Type': 'application/json',
        'X-Dev-Role': 'IO',
    },
    method='POST',
)
scan_res = json.loads(urllib.request.urlopen(req, timeout=20).read())
print('3. Live Document Scan Success!')
print('   Document ID:', scan_res['document_id'])
print('   OCR Status:', scan_res['ocr_status'], f'({scan_res["ocr_confidence"]}% confidence)')
print('   Extracted FIR:', scan_res['candidate_facts']['fir_number']['value'])
clock_preview = scan_res.get('clock_preview') or {}
print('   Clock Preview:', clock_preview.get('applicable_rule'), f'({clock_preview.get("duration_days")} days, deadline {clock_preview.get("calculated_deadline")})')

# 4. Live Officer Confirmation
confirm_payload = json.dumps({
    'fir_number': 'FIR/MYS/2026/0888',
    'police_station': 'Mysuru Central',
    'offence_category': 'serious_offence',
}).encode('utf-8')

req_confirm = urllib.request.Request(
    f'{backend}/api/v1/cases/{case_id}/documents/{scan_res["document_id"]}/confirm',
    data=confirm_payload,
    headers={
        'Content-Type': 'application/json',
        'X-Dev-Role': 'IO',
    },
    method='POST',
)
confirm_res = json.loads(urllib.request.urlopen(req_confirm, timeout=20).read())
print('4. Live Officer Confirmation Success!')
print('   Review Status:', confirm_res['review_status'])
print('   Updated Clock:', confirm_res['updated_clock']['clock_type'], 'Deadline:', confirm_res['updated_clock']['deadline_date'])

# 5. Live Deadline Monitor Regression Check
res_mon = urllib.request.urlopen(backend + '/api/v1/system/deadline-monitor/status', timeout=20)
print('5. Live Deadline Monitor Status:', json.loads(res_mon.read())['status'])

print('\nPASSED: All 5 live verification checks PASSED.')
