"""Reuse OpenShot's compositor and keyframes; normalize source coverage with FFmpeg."""
import json
from pathlib import Path
import subprocess
from .db import Asset
from .storage import run
from .platform_runtime import openshot_command


class OpenShotVisualService:
    def render(self, session, storage, timeline, settings, folder, width, height, total_frames, inputs, progress):
        visual_items=[]
        ordered=sorted(enumerate(timeline.items),key=lambda pair:({'video':0,'overlay':1,'title':2,'caption':3}.get(pair[1].track,4),pair[0]))
        for index,item in ordered:
            if item.muted or item.track not in ('video','overlay','title','caption'):continue
            if item.track=='caption' and not inputs.get('burn_captions',True):continue
            data=item.model_dump()
            if item.track in ('video','overlay') and item.asset_id:
                asset=session.get(Asset,item.asset_id)
                source=storage.path(asset.proxy if inputs.get('preview') and asset.proxy else asset.path)
                target=folder/f'clip-{index}.mp4'
                args=['ffmpeg','-v','error','-y','-threads','1']
                if asset.kind=='image':args+=['-loop','1']
                elif item.coverage=='loop':args+=['-stream_loop','-1']
                duration=settings.seconds(item.duration)
                args+=['-i',str(source),'-an','-vf',
                       f'trim=start={settings.seconds(item.source_in)},setpts=PTS-STARTPTS,fps={settings.fps_num}/{settings.fps_den},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,tpad=stop_mode=clone:stop_duration={duration},trim=duration={duration}',
                       '-frames:v',str(item.duration),'-c:v','libx264','-threads','1','-preset','ultrafast','-crf','18','-pix_fmt','yuv420p',str(target)]
                run(args)
                data['path']=str(target)
            elif item.track in ('video','overlay'):
                data.update(track='title',text='DRAFT • awaiting footage',x=.5,y=.5)
            visual_items.append(data)
        config={'folder':str(folder),'width':width,'height':height,'fps_num':settings.fps_num,
                'fps_den':settings.fps_den,'frames':total_frames,'items':visual_items,'project_id':inputs.get('project_id','scriptstudio')}
        config_path=folder/'openshot-input.json'
        config_path.write_text(json.dumps(config))
        with open(folder/'openshot.log','w') as log:
            process=subprocess.Popen(openshot_command('openshot_runner.py',config_path),stdout=subprocess.PIPE,stderr=log,text=True)
            try:
                for line in process.stdout:
                    try:
                        event=json.loads(line)
                        if 'progress' in event:progress(event['progress']*.6)
                    except ValueError:pass
                if process.wait(timeout=30):
                    raise ValueError('OpenShot compositor failed: '+(folder/'openshot.log').read_text()[-2000:])
            finally:
                if process.poll() is None:process.kill();process.wait()
        return folder/'visual.mp4'
