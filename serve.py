#!/usr/bin/env python3
"""
serve.py
Lightweight local HTTP development server for EBSBank
"""

import http.server
import json
import mimetypes
import socketserver
import os
import re
import smtplib
import ssl
import sys
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))
RECIPIENTS = ['zdary@bwh.harvard.edu', 'gmeyer3@bwh.harvard.edu']
MAX_REQUEST_BYTES = 16 * 1024 * 1024
CONTRIBUTION_TYPES = {
    'data': 'Upload New Dataset',
    'correction': 'Coordinate / Annotation Correction',
    'other': 'General Feedback / Note',
}


class EmailConfigurationError(Exception):
    pass


def parse_contribution(content_type, body):
    if not content_type.lower().startswith('multipart/form-data;'):
        raise ValueError('The contribution form must be submitted as multipart data.')

    try:
        headers = f'Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n'.encode('ascii')
        message = BytesParser(policy=policy.default).parsebytes(headers + body)
    except (UnicodeEncodeError, ValueError):
        raise ValueError('The submitted form data could not be read.')

    if not message.is_multipart():
        raise ValueError('The submitted form data could not be read.')

    fields = {}
    attachment = None
    for part in message.iter_parts():
        if part.get_content_disposition() != 'form-data':
            continue

        field_name = part.get_param('name', header='content-disposition')
        value = part.get_payload(decode=True) or b''
        if field_name == 'file':
            filename = part.get_filename()
            if filename:
                filename = filename.replace('\\', '/').rsplit('/', 1)[-1].strip()
                if not filename or os.path.splitext(filename)[1].lower() not in {'.csv', '.xls', '.xlsx'}:
                    raise ValueError('Upload a CSV or Excel file.')
                if not value:
                    raise ValueError('The uploaded file is empty.')
                attachment = (filename, value)
        elif field_name:
            charset = part.get_content_charset() or 'utf-8'
            fields[field_name] = value.decode(charset, errors='replace').strip()

    required_fields = ['name', 'institution', 'email', 'contribution_type']
    if any(not fields.get(field) for field in required_fields):
        raise ValueError('Complete all required contact and contribution fields.')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', fields['email']):
        raise ValueError('Enter a valid email address.')
    if fields['contribution_type'] not in CONTRIBUTION_TYPES:
        raise ValueError('Select a valid contribution type.')
    if not fields.get('notes') and attachment is None:
        raise ValueError('Add notes or upload a data file before submitting.')

    return fields, attachment


def send_contribution_email(fields, attachment):
    smtp_host = os.environ.get('STIMBANK_SMTP_HOST', '').strip()
    smtp_from = os.environ.get('STIMBANK_SMTP_FROM', '').strip()
    smtp_username = os.environ.get('STIMBANK_SMTP_USERNAME', '').strip()
    smtp_password = os.environ.get('STIMBANK_SMTP_PASSWORD', '')
    try:
        smtp_port = int(os.environ.get('STIMBANK_SMTP_PORT', '587'))
    except ValueError:
        raise EmailConfigurationError('The SMTP port must be a number.')

    if not smtp_host or not smtp_from:
        raise EmailConfigurationError('SMTP host and sender address are required.')
    if bool(smtp_username) != bool(smtp_password):
        raise EmailConfigurationError('Configure both SMTP username and password, or neither.')

    email_message = EmailMessage()
    email_message['Subject'] = f"StimBank contribution: {CONTRIBUTION_TYPES[fields['contribution_type']]}"
    email_message['From'] = smtp_from
    email_message['To'] = ', '.join(RECIPIENTS)
    email_message['Reply-To'] = fields['email']
    email_message.set_content(
        f"Name: {fields['name']}\n"
        f"Institution: {fields['institution']}\n"
        f"Email: {fields['email']}\n"
        f"Contribution type: {CONTRIBUTION_TYPES[fields['contribution_type']]}\n\n"
        f"Notes:\n{fields.get('notes', '') or '(none)'}\n"
    )

    if attachment:
        filename, file_data = attachment
        content_type, _ = mimetypes.guess_type(filename)
        maintype, subtype = (content_type or 'application/octet-stream').split('/', 1)
        email_message.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=filename)

    smtp_class = smtplib.SMTP_SSL if smtp_port == 465 else smtplib.SMTP
    with smtp_class(smtp_host, smtp_port, timeout=20) as smtp:
        if smtp_port != 465:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if smtp_username:
            smtp.login(smtp_username, smtp_password)
        smtp.send_message(email_message)

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for local testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def send_json(self, status_code, payload):
        response = json.dumps(payload).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_POST(self):
        if self.path.split('?', 1)[0] != '/api/contributions':
            self.send_json(404, {'error': 'Endpoint not found.'})
            return

        try:
            content_length = int(self.headers.get('Content-Length', ''))
        except ValueError:
            self.send_json(411, {'error': 'A content length is required.'})
            return

        if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
            self.send_json(413, {'error': 'The submission is empty or exceeds the 16 MB limit.'})
            return

        try:
            fields, attachment = parse_contribution(
                self.headers.get('Content-Type', ''),
                self.rfile.read(content_length),
            )
        except ValueError as error:
            self.send_json(400, {'error': str(error)})
            return

        try:
            send_contribution_email(fields, attachment)
        except EmailConfigurationError:
            self.send_json(503, {'error': 'Email delivery is not configured. Please contact the site administrator.'})
            return
        except (OSError, smtplib.SMTPException) as error:
            print(f'Contribution email delivery failed: {error}')
            self.send_json(502, {'error': 'The email could not be sent. Please try again later.'})
            return

        self.send_json(200, {'message': 'Contribution sent successfully.'})

def run_server():
    global PORT
    while PORT < 8095:
        try:
            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                print("=" * 60)
                print(f" EBSBank Local Development Server Started")
                print(f" Directory: {DIRECTORY}")
                print(f" Local URL: http://localhost:{PORT}/index.html")
                print(f" 3D Viewer: http://localhost:{PORT}/viewer.html")
                print(f" Explorer:   http://localhost:{PORT}/explorer.html")
                print(f" Importer:   http://localhost:{PORT}/importer.html")
                print("=" * 60)
                print("Press Ctrl+C to stop the server.")
                httpd.serve_forever()
        except OSError as e:
            if e.errno == 48: # Address already in use
                PORT += 1
            else:
                raise e

if __name__ == "__main__":
    run_server()
