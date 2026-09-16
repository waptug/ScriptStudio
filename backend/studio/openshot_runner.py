#!/usr/bin/python3
"""Process-isolated libopenshot bridge, using Debian's matching Python ABI.

The application never loads native C++ code into the API/worker process. Input is
our validated JSON contract, never executable script text. Native OpenShot Clip
serialization is used rather than hand-maintaining its keyframe schema.
"""
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('OMP_NUM_THREADS','2')
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QRect
import openshot


def text_image(path, text, width, height, item):
    image=QImage(width,height,QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter=QPainter(image)
    painter.setRenderHint(QPainter.TextAntialiasing)
    caption=item['track']=='caption'
    font=QFont('DejaVu Sans')
    font.setPixelSize(max(12,round(height*(.045 if caption else .06)*item.get('scale',1))))
    painter.setFont(font)
    bounds=painter.boundingRect(QRect(0,0,round(width*.9),height),Qt.TextWordWrap|Qt.AlignCenter,text)
    box_w=min(width,bounds.width()+20)
    box_h=min(height,bounds.height()+16)
    x=round((width-box_w)*(.5 if caption else item.get('x',.5)))
    y=round((height-box_h)*(.94 if caption else item.get('y',.5)))
    painter.fillRect(QRect(x,y,box_w,box_h),QColor(0,0,0,160))
    painter.setPen(QColor('white'))
    painter.drawText(QRect(x+10,y+8,box_w-20,box_h-16),Qt.TextWordWrap|Qt.AlignCenter,text)
    painter.end()
    if not image.save(str(path)):raise RuntimeError('Could not save title image')


def main():
    config=json.loads(Path(sys.argv[1]).read_text())
    app=QApplication([])
    folder=Path(config['folder'])
    width,height=config['width'],config['height']
    fps=openshot.Fraction(config['fps_num'],config['fps_den'])
    rate=config['fps_num']/config['fps_den']
    timeline=openshot.Timeline(width,height,fps,48000,2,openshot.LAYOUT_STEREO)
    timeline.Open()
    retained=[]
    clips=[]
    files=[]
    layers=[]
    for index,item in enumerate(config['items']):
        path=Path(item['path']) if item.get('path') else folder/f'text-{index}.png'
        if not item.get('path'):
            text_image(path,item['text'],width,height,item)
        clip=openshot.Clip(str(path))
        clip.Open()
        clip.Start(0)
        clip.End(item['duration']/rate)
        clip.Position(item['start']/rate)
        layer={'video':1000000,'overlay':2000000,'title':3000000,'caption':4000000}[item['track']]
        clip.Layer(layer)
        clip.has_audio=openshot.Keyframe(0)
        if item['track'] in ('video','overlay'):
            scale=item.get('scale',1)
            clip.scale_x=openshot.Keyframe(scale)
            clip.scale_y=openshot.Keyframe(scale)
            clip.location_x=openshot.Keyframe((item.get('x',0)-.5)*(1-scale))
            clip.location_y=openshot.Keyframe((item.get('y',0)-.5)*(1-scale))
        fade_in=item.get('fade_in',0)
        fade_out=item.get('fade_out',0)
        if item.get('transition')=='fade' and not fade_in:
            fade_in=min(round(rate*.5),item['duration']//2)
        if fade_in:
            clip.alpha=openshot.Keyframe(0)
            clip.alpha.AddPoint(min(item['duration'],fade_in)+1,1,openshot.LINEAR)
        if fade_out:
            clip.alpha.AddPoint(max(1,item['duration']-fade_out+1),1,openshot.LINEAR)
            clip.alpha.AddPoint(item['duration'],0,openshot.LINEAR)
        # AddClip wraps the reader in a runtime FrameMapper. Serialize the source
        # reader first so the native project can reopen it on another workstation.
        data=json.loads(clip.Json())
        data.update(id=item['id'],file_id=item['id'],title=item.get('text') or item['track'])
        clips.append(data)
        reader=json.loads(clip.Reader().Json())
        files.append({**reader,'id':item['id'],'path':str(path),'media_type':'image' if path.suffix=='.png' else 'video'})
        timeline.AddClip(clip)
        retained.append(clip)
        if not any(entry['number']==layer for entry in layers):
            layers.append({'id':f'L{layer}','number':layer,'label':item['track'],'y':0,'lock':False})
    project={'id':config['project_id'],'fps':{'num':config['fps_num'],'den':config['fps_den']},
             'width':width,'height':height,'sample_rate':48000,'channels':2,'channel_layout':3,
             'display_ratio':{'num':width,'den':height},'pixel_ratio':{'num':1,'den':1},
             'settings':{},'clips':clips,'effects':[],'files':files,'layers':layers,'markers':[],
             'duration':max(300,config['frames']/rate),'scale':15,'tick_pixels':100,'playhead_position':0,
             'profile':{'description':'ScriptStudio','width':width,'height':height,'fps':{'num':config['fps_num'],'den':config['fps_den']},'progressive':True,'pixel_ratio':{'num':1,'den':1},'display_ratio':{'num':width,'den':height}},
             'export_path':'','import_path':'','history':{'undo':[],'redo':[]},
             'version':{'openshot-qt':'2.6.1','libopenshot':openshot.OPENSHOT_VERSION_FULL}}
    (folder/'native-project.json').write_text(json.dumps(project))
    if config.get('serialize_only'):
        timeline.Close()
        return
    writer=openshot.FFmpegWriter(str(folder/'visual.mp4'))
    writer.SetVideoOptions(True,'libx264',fps,width,height,openshot.Fraction(1,1),False,False,4000000)
    writer.Open()
    for frame in range(1,config['frames']+1):
        writer.WriteFrame(timeline.GetFrame(frame))
        if frame%24==0:print(json.dumps({'progress':frame/config['frames']}),flush=True)
    writer.Close()
    timeline.Close()
    print(json.dumps({'engine':'libopenshot','version':openshot.OPENSHOT_VERSION_FULL,'frames':config['frames']}),flush=True)


if __name__=='__main__':main()
