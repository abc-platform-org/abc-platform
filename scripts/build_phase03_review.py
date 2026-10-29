"""Build and verify two standalone synthetic UX review artifacts. No live data or network calls."""
from pathlib import Path
import argparse

ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'prototypes'/'phase03'

def build(stem, out_name, sister):
    html=(DIR/(stem+'.html')).read_text()
    css_name='style.css' if stem=='index' else 'management.css'
    model_name='model.mjs' if stem=='index' else 'management-model.mjs'
    app_name='app.mjs' if stem=='index' else 'management.mjs'
    model=(DIR/model_name).read_text().replace('export ','')
    app=(DIR/app_name).read_text().split('\n',1)[1]
    html=html.replace('<link rel="stylesheet" href="'+css_name+'">','<style>'+(DIR/css_name).read_text()+'</style>')
    html=html.replace('<script type="module" src="'+app_name+'"></script>','<script type="module">'+model+'\n'+app+'</script>')
    html=html.replace('href="./'+sister[0]+'"','href="./'+sister[1]+'"')
    if 'import {' in html or '<script type="module" src=' in html:
        raise SystemExit('Unbundled JS import in '+out_name)
    return DIR/out_name,html

parser=argparse.ArgumentParser()
parser.add_argument('--check',action='store_true',help='fail if tracked review files are stale')
args=parser.parse_args()
items=[
    build('index','review.html',('management.html','review-management.html')),
    build('management','review-management.html',('index.html','review.html'))
]
for file,content in items:
    if args.check:
        if not file.exists() or file.read_text()!=content:
            raise SystemExit('STALE_STANDALONE_REVIEW: '+str(file))
        print('PASS: synced '+str(file.relative_to(ROOT)))
    else:
        file.write_text(content)
        print('Built '+str(file.relative_to(ROOT)))
