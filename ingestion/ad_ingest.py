import os
import json
import time
import argparse
import datetime
from ldap3 import Server, Connection, ALL, NTLM, SUBTREE


def filetime_to_datetime(filetime):
    # Convert Windows FILETIME (100-ns since 1601) to datetime, handle 0/null
    try:
        if not filetime:
            return None
        # lastLogonTimestamp sometimes arrives as int or str
        val = int(filetime)
        if val <= 0:
            return None
        # FILETIME -> seconds since epoch
        us = val / 10
        # FILETIME epoch is Jan 1, 1601
        epoch_start = datetime.datetime(1601, 1, 1)
        return epoch_start + datetime.timedelta(microseconds=us)
    except Exception:
        return None


def build_event(entry):
    attrs = entry['attributes']
    last_logon = None
    if 'lastLogonTimestamp' in attrs:
        last_logon = filetime_to_datetime(attrs.get('lastLogonTimestamp'))
    event = {
        'source': 'active_directory',
        'collected_at': datetime.datetime.utcnow().isoformat() + 'Z',
        'sAMAccountName': attrs.get('sAMAccountName'),
        'displayName': attrs.get('displayName'),
        'mail': attrs.get('mail'),
        'userPrincipalName': attrs.get('userPrincipalName'),
        'distinguishedName': attrs.get('distinguishedName'),
        'lastLogon': last_logon.isoformat() + 'Z' if last_logon else None,
    }
    return event


def run_once(server_uri, user, password, base_dn, output_path, use_ntlm=False, search_filter=None):
    server = Server(server_uri, get_info=ALL)
    auth = NTLM if use_ntlm else None
    conn = Connection(server, user=user, password=password, authentication=auth, auto_bind=True)
    if not search_filter:
        search_filter = '(&(objectClass=user)(!(objectClass=computer)))'
    conn.search(search_base=base_dn, search_filter=search_filter, search_scope=SUBTREE, attributes=['sAMAccountName','displayName','mail','userPrincipalName','distinguishedName','lastLogonTimestamp'])
    entries = []
    for entry in conn.response:
        if entry.get('type') != 'searchResEntry':
            continue
        entries.append(entry)
    if not os.path.isdir(os.path.dirname(output_path)) and os.path.dirname(output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'a', encoding='utf-8') as fh:
        for e in entries:
            evt = build_event(e)
            fh.write(json.dumps(evt, default=str) + '\n')
    conn.unbind()
    print(f'Wrote {len(entries)} events to {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Active Directory ingestion to produce NDJSON user events')
    parser.add_argument('--once', action='store_true', help='Run one-time then exit')
    parser.add_argument('--interval', type=int, default=0, help='Polling interval seconds (0 disables loop)')
    args = parser.parse_args()

    server_uri = os.environ.get('LDAP_SERVER') or os.environ.get('AD_SERVER') or 'ldap://localhost'
    user = os.environ.get('LDAP_USER')
    password = os.environ.get('LDAP_PASSWORD')
    base_dn = os.environ.get('LDAP_BASE_DN') or os.environ.get('AD_BASE_DN')
    output_path = os.environ.get('OUTPUT_PATH') or 'logs/ad_users.log'

    if not user or not password or not base_dn:
        print('Missing required environment variables: LDAP_USER, LDAP_PASSWORD, LDAP_BASE_DN')
        return

    # If user looks like DOMAIN\\user or DOMAIN\user, use NTLM
    use_ntlm = '\\' in user and not user.startswith('cn=')

    if args.once or args.interval <= 0:
        run_once(server_uri, user, password, base_dn, output_path, use_ntlm=use_ntlm)
        return

    # Continuous polling
    while True:
        run_once(server_uri, user, password, base_dn, output_path, use_ntlm=use_ntlm)
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
