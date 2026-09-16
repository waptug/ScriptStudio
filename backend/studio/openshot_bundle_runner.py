#!/usr/bin/python3
"""Serialize the finished audio mix and source library through libopenshot itself."""
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PyQt5.QtWidgets import QApplication
import openshot

app=QApplication([])
config=json.loads(Path(sys.argv[1]).read_text())
project=json.loads(Path(config['native']).read_text())
rate=project['fps']['num']/project['fps']['den']
clip=openshot.Clip(config['mix'])
clip.Open()
clip.Start(0)
clip.End(config['frames']/rate)
clip.Position(0)
clip.Layer(5000000)
clip.has_video=openshot.Keyframe(0)
data=json.loads(clip.Json())
data.update(id='audio-mix',file_id='audio-mix',title='Finished audio mix (ducking and fades baked)')
project['clips'].append(data)
project['layers'].append({'id':'L5000000','number':5000000,'label':'Finished audio mix','y':0,'lock':False})
project['files'].append({**json.loads(clip.Reader().Json()),'id':'audio-mix','path':config['mix'],'media_type':'audio'})
for asset in config['sources']:
    source=openshot.Clip(asset['path'])
    source.Open()
    project['files'].append({**json.loads(source.Reader().Json()),'id':asset['id'],'path':asset['path'],'media_type':asset['kind']})
    source.Close()
Path(config['output']).write_text(json.dumps(project))
clip.Close()
