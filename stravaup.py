from __future__ import print_function

from stravalib import Client, exc
from sys import stderr
import webbrowser, os.path, ConfigParser, gzip
import argparse
try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

from QueryGrabber import QueryGrabber

#####

p = argparse.ArgumentParser(description='''Uploads activities to Strava.''')
p.add_argument('-p', '--private', action='store_true', help='Make activities private')
p.add_argument('-P', '--no-popup', action='store_true', help="Don't browse to activities after upload.")
p.add_argument('-N', '--no-name', action='store_true', help="Don't parse name/notes fields of GPX/TCX files.")
p.add_argument('-E', '--env', help='Look for (CLIENT_ID, CLIENT_SECRET) or ACCESS_TOKEN in environment variables rather than ~/.stravacli')
p.add_argument('activities', nargs='+', type=argparse.FileType("rb"), help="Activity files to upload (.fit, .tcx, or .gpx -- possibly .gz)")
args = p.parse_args()

#####

# Authorize Strava

if args.env:
    cid = os.environ.get('CLIENT_ID')
    cs = os.environ.get('CLIENT_SECRET')
    cat = os.environ.get('ACCESS_TOKEN')
else:
    cp = ConfigParser.ConfigParser()
    cp.read(os.path.expanduser('~/.stravacli'))
    cid = cs = cat = None
    if not cp.has_section('CLIENT'):
        cid = cs = cat = None
    else:
        cid = cp.get('CLIENT', 'CLIENT_ID') if 'client_id' in cp.options('CLIENT') else None
        cs = cp.get('CLIENT', 'CLIENT_SECRET') if 'client_secret' in cp.options('CLIENT') else None
        cat = cp.get('CLIENT', 'ACCESS_TOKEN') if 'access_token' in cp.options('CLIENT') else None

if cat:
    client = Client(cat)
elif cid and cs:
    print("Authorizing Strava access via web browser...", file=stderr)
    client = Client()
    webserver = QueryGrabber(response='<title>Strava auth code received!</title>This window can be closed.')
    authorize_url = client.authorization_url(client_id=cid, redirect_uri=webserver.root_uri(), scope='write')
    webbrowser.open_new_tab(authorize_url)
    webserver.handle_request()
    cat=client.exchange_code_for_token(client_id=cid,client_secret=cs,code=webserver.received['code'])
    print("Authorization complete.")
    if not args.env:
        cp.set('CLIENT','CLIENT_ID', cid)
        cp.set('CLIENT','CLIENT_SECRET', cs)
        cp.set('CLIENT','ACCESS_TOKEN', cat)
        cp.write(open(os.path.expanduser('~/.stravacli'),"w"))
else:
    if args.env:
        p.error('(CLIENT_ID, CLIENT_SECRET) or (ACCESS_TOKEN) must be specified in environment variables')
    else:
        p.error('(CLIENT_ID, CLIENT_SECRET) or (ACCESS_TOKEN) must be specified in [CLIENT] section of ~/.stravacli')

#####

for ii,f in enumerate(args.activities):
    print("Uploading activity from {}...".format(f.name))

    # try to parse activity name, description from file if desired
    name = desc = None
    if not args.no_name:
        base, ext = os.path.splitext(f.name)
        if ext.lower()=='.gz':
            gz = True
            base, ext = os.path.splitext(base)
            fobj = gzip.GzipFile(fileobj=afile, mode='r')
        else:
            gz = False
            fobj = f

        if ext.lower()=='.gpx':
            x = etree.parse(fobj)
            nametag, desctag = x.find("{*}name"), root.find("{*}desc")
            if nametag:
                name = nametag.text
            if desctag:
                desc = desctag.text
        elif ext.lower()=='.tcx':
            x = etree.parse(fobj)
            notestag = x.find("{*}Activities/{*}Activity/{*}Notes")
            if notestag is not None:
                name, desc = (notestag.text.split('\n',1)+[None])[:2]

        if gz: fobj.close()
        f.seek(0, 0)

    # upload activity
    try:
        upstat = client.upload_activity(f, ext[1:] + ('.gz' if gz else ''), name, desc, private=args.private)
        activity = upstat.wait()
        duplicate = False
    except Exception as e:
        words = e.args[0].split()
        if words[-4:-1]==['duplicate','of','activity']:
            activity = client.get_activity(words[-1])
            duplicate = True
        else:
            raise
            
    uri = "http://strava.com/activities/{:d}".format(activity.id)
    print("  {}{}".format(uri, " (duplicate)" if duplicate else ''), file=stderr)
    if not args.no_popup:
        webbrowser.open_new_tab(uri)