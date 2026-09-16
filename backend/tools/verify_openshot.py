#!/usr/bin/python3
"""Load a relocated native .osp in libopenshot and render representative frames."""
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('OMP_NUM_THREADS','2')
from PyQt5.QtWidgets import QApplication
import openshot

app=QApplication([])
path=Path(sys.argv[1]).resolve()
data=json.loads(path.read_text())
def absolute(value):
    if isinstance(value,dict):
        return {k:str((path.parent/v).resolve()) if k=='path' and isinstance(v,str) and v else absolute(v) for k,v in value.items()}
    if isinstance(value,list):return [absolute(v) for v in value]
    return value
for file in data['files']:
    assert not Path(file['path']).is_absolute(),'Bundle media must use portable relative paths'
    assert (path.parent/file['path']).is_file(),file['path']
data=absolute(data)
fps=openshot.Fraction(data['fps']['num'],data['fps']['den'])
timeline=openshot.Timeline(data['width'],data['height'],fps,48000,2,openshot.LAYOUT_STEREO)
timeline.SetJson(json.dumps(data))
timeline.Open()
writer=openshot.FFmpegWriter(str(path.parent/'native-verification.mp4'))
writer.SetVideoOptions(True,'libx264',fps,data['width'],data['height'],openshot.Fraction(1,1),False,False,2000000)
writer.Open()
end=max(c['position']+c['duration'] for c in data['clips'])
for frame in (1,max(1,round(end*fps.num/fps.den/2)),max(1,round(end*fps.num/fps.den)-1)):
    writer.WriteFrame(timeline.GetFrame(frame))
writer.Close();timeline.Close()
print(json.dumps({'engine':openshot.OPENSHOT_VERSION_FULL,'clips':len(data['clips']),'files':len(data['files']),'rendered_frames':3}))
