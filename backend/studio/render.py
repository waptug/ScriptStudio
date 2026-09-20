"""One OpenShot compositor and FFmpeg audio graph implement preview and export."""
from pathlib import Path
import subprocess
import os
from .db import Asset
from .schemas import Settings, Timeline
from .storage import LocalStorage
from .openshot_visual import OpenShotVisualService


def subtitle_time(seconds, web=False):
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f'{hours:02}:{minutes:02}:{sec:02}{"." if web else ","}{ms:03}'


class RenderService:
    def __init__(self, storage=None):
        self.storage = storage or LocalStorage()

    def subtitles(self, timeline, settings, web=False):
        lines = ['WEBVTT\n'] if web else []
        captions = sorted((i for i in timeline.items if i.track == 'caption' and not i.muted), key=lambda i:i.start)
        for number, item in enumerate(captions, 1):
            text = item.text.replace('-->', '→').replace('\r',' ').replace('\n\n','\n')
            lines.extend([str(number), f'{subtitle_time(settings.seconds(item.start),web)} --> {subtitle_time(settings.seconds(item.start+item.duration),web)}', text, ''])
        return '\n'.join(lines)

    def validate(self, session, project_id, timeline, draft):
        for item in timeline.items:
            if item.muted or item.track in ('title','caption'):
                continue
            asset = session.get(Asset, item.asset_id) if item.asset_id else None
            if asset is None:
                if draft and item.track in ('video','overlay'):
                    continue
                raise ValueError(f'Item {item.id} is missing media. Generate/select a take, remove it, or use draft export for visual placeholders.')
            if asset.project_id != project_id or not self.storage.path(asset.path).is_file():
                raise ValueError(f'Asset for {item.id} is unavailable in persistent storage')
        if not timeline.items:
            raise ValueError('Timeline is empty')

    def render(self, session, project_id, job_id, inputs, progress=lambda value:None, activity=None):
        timeline = Timeline.model_validate(inputs['timeline'])
        settings = Settings.model_validate(inputs['settings'])
        self.validate(session, project_id, timeline, inputs.get('draft',False))
        total_frames = max(i.start+i.duration for i in timeline.items)
        total = settings.seconds(total_frames)
        if total > 3600:
            raise ValueError('Export exceeds one hour; shorten the timeline')
        width, height = settings.width, settings.height
        if inputs.get('preview'):
            ratio = min(1, 640/max(width,height))
            width, height = max(2,round(width*ratio/2)*2), max(2,round(height*ratio/2)*2)
        fps = f'{settings.fps_num}/{settings.fps_den}'
        folder = self.storage.path(f'{project_id}/renders/{job_id}')
        folder.mkdir(parents=True, exist_ok=True)
        for ext in ('srt','vtt'):
            (folder/f'captions.{ext}').write_text(self.subtitles(timeline,settings,ext=='vtt'))
        output = folder/'output.mp4'
        if activity: activity('generate', None, 'Rendering timeline frames')
        visual_progress = (lambda value: activity('generate', min(1, value/.6), 'Rendering timeline frames')) if activity else progress
        visual_path = OpenShotVisualService().render(session,self.storage,timeline,settings,folder,width,height,total_frames,{**inputs,'project_id':project_id},visual_progress)
        args = ['ffmpeg','-v','warning','-y','-filter_complex_threads','1','-i',str(visual_path),
                '-f','lavfi','-i',f'anullsrc=r=48000:cl=stereo:d={total}']
        graph = ['[0:v]null[video]']
        video = 'video'
        audio_groups = {'narration':[], 'music':[], 'sfx':[]}
        index = 2
        for counter,item in enumerate(timeline.items):
            if item.muted or item.track not in audio_groups or not item.asset_id:continue
            asset=session.get(Asset,item.asset_id)
            if item.coverage=='loop':args+=['-stream_loop','-1']
            args+=['-i',str(self.storage.path(asset.path))]
            duration=settings.seconds(item.duration)
            delay=round(item.start*settings.fps_den*48000/settings.fps_num)
            chain=f'[{index}:a]atrim=start={settings.seconds(item.source_in)}:duration={duration},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,apad=whole_dur={duration},atrim=duration={duration},volume={item.volume}'
            if item.fade_in:
                chain+=f',afade=t=in:d={min(duration,settings.seconds(item.fade_in))}'
            if item.fade_out:
                fade=min(duration,settings.seconds(item.fade_out))
                chain+=f',afade=t=out:st={duration-fade}:d={fade}'
            label=f'a{counter}'
            graph.append(chain+f',adelay={delay}S:all=1[{label}]')
            audio_groups[item.track].append(label)
            index+=1
        buses = []
        for group, labels in audio_groups.items():
            if labels:
                graph.append(''.join(f'[{label}]' for label in labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0[{group}]')
                buses.append(group)
        if timeline.duck_music and 'narration' in buses and 'music' in buses:
            graph += ['[narration]asplit=2[narration_out][sidechain_raw]',
                      f'[sidechain_raw]apad=whole_dur={total},atrim=duration={total}[sidechain]',
                      '[music][sidechain]sidechaincompress=threshold=0.025:ratio=8:attack=20:release=400[ducked]']
            buses = ['narration_out' if b=='narration' else 'ducked' if b=='music' else b for b in buses]
        graph.append('[1:a]'+''.join(f'[{label}]' for label in buses)+f'amix=inputs={len(buses)+1}:duration=first:normalize=0,alimiter=limit=0.95:level=0,atrim=duration={total}[audio]')
        graph_file = folder/'graph.txt'
        graph_file.write_text(';\n'.join(graph))
        args += [os.getenv('FFMPEG_FILTER_SCRIPT_OPTION','-filter_complex_script'),str(graph_file),'-map',f'[{video}]','-map','[audio]',
                 '-t',str(total),'-r',fps,'-c:v','libx264','-threads','2','-preset','ultrafast' if inputs.get('preview') else 'veryfast',
                 '-crf','27' if inputs.get('preview') else '20','-pix_fmt','yuv420p','-c:a','aac','-ar','48000',
                 '-movflags','+faststart','-progress','pipe:1',str(output)]
        log_path = folder/'ffmpeg.log'
        if activity: activity('transfer', None, 'Encoding video and mixing audio')
        with open(log_path, 'w') as log:
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log, text=True)
            try:
                for line in process.stdout:
                    if line.startswith('out_time_us='):
                        fraction=min(1, int(line.split('=')[1])/1000000/total)
                        if activity: activity('transfer', fraction, 'Encoding video and mixing audio')
                        else: progress(.6+min(.39, fraction*.4))
                if process.wait(timeout=30):
                    raise ValueError('Render failed: '+log_path.read_text()[-2500:])
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
        if activity: activity('transfer', None, 'Finalizing output files')
        bundle = None
        if not inputs.get('preview'):
            from .openshot_bundle import OpenShotBundleService
            bundle = OpenShotBundleService().create(session,self.storage,project_id,folder,output,inputs)
        return output, {'openshot_bundle':bundle, 'engine':'libopenshot', 'srt':str((folder/'captions.srt').relative_to(self.storage.root)),
                        'vtt':str((folder/'captions.vtt').relative_to(self.storage.root)),
                        'log':str(log_path.relative_to(self.storage.root)), 'revision':inputs['revision']}
