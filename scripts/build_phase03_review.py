from pathlib import Path
p=Path(__file__).resolve().parents[1]/'prototypes/phase03'
html=(p/'index.html').read_text()
model=(p/'model.mjs').read_text().replace('export ','')
app=(p/'app.mjs').read_text().split('\n',1)[1]
html=html.replace('<link rel="stylesheet" href="style.css">','<style>'+(p/'style.css').read_text()+'</style>')
html=html.replace('<script type="module" src="app.mjs"></script>','<script type="module">'+model+'\n'+app+'</script>')
(p/'review.html').write_text(html)
print('Built self-contained review.html')
