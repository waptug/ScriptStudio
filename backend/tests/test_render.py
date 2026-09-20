import json
from pathlib import Path
import pytest
from studio.db import transaction, Session, Project, Asset
from studio.schemas import Item, Settings, Timeline, uid
from studio.storage import LocalStorage, AssetRepository, probe, run
from studio.render import RenderService
from studio.providers import MockVideoProvider, MockMusicProvider
from studio.planner import LocalScriptPlanner


def test_planner_removes_visual_directions_and_validates():
    board=LocalScriptPlanner().plan('[Camera tracks river] Water flows. Trees grow.',Settings())
    assert board.scenes[0].narration=='Water flows. Trees grow.'
    assert 'Camera tracks river' in board.scenes[0].shots[0].prompt
    assert len(board.scenes[0].shots)==2


def test_fractional_frame_rate_no_accumulated_conversion_drift():
    settings=Settings(fps_num=30000,fps_den=1001)
    assert settings.frames(settings.seconds(9000))==9000
    assert abs(settings.seconds(9000)-300.3)<1e-9


def test_render_missing_assets_blocked(project_id):
    with Session() as s:
        timeline=Timeline(items=[Item(track='video')])
        with pytest.raises(ValueError,match='missing media'):
            RenderService().validate(s,project_id,timeline,False)
        RenderService().validate(s,project_id,timeline,True)


def test_preview_export_duration_audio_and_immutable_snapshot(project_id):
    settings=Settings(width=320,height=180)
    visual=MockVideoProvider().submit(uid(),{'duration':2,'prompt':'Green test'})['local_path']
    audio=MockMusicProvider().submit(uid(),{'duration':3,'mood':'calm'})['local_path']
    with transaction() as s:
        v=AssetRepository().ingest(s,project_id,visual,'Test video',{})
        a=AssetRepository().ingest(s,project_id,audio,'Test tone',{})
        timeline=Timeline(items=[Item(track='video',asset_id=v.id,duration=72,fade_in=6,fade_out=6),
            Item(track='music',asset_id=a.id,duration=72,volume=.5,fade_in=4,fade_out=6),
            Item(track='narration',asset_id=a.id,start=12,duration=36),
            Item(track='title',text="A title: 100% safe ' text",start=6,duration=24,x=.5,y=.3),
            Item(track='caption',text='Caption one',start=24,duration=24)])
        snapshot={'timeline':timeline.model_dump(),'settings':settings.model_dump(),'revision':7,'burn_captions':True,'draft':False}
        p=s.get(Project,project_id);p.timeline=Timeline(items=[]).model_dump();p.revision=8
    paths=[]
    with Session() as s:
        for preview in (True,False):
            phases=[]
            path,meta=RenderService().render(s,project_id,uid(),{**snapshot,'preview':preview},activity=lambda phase,fraction=None,detail='': phases.append((phase,fraction)))
            assert phases[0][0]=='generate'
            assert phases[-1][0]=='transfer'
            assert any(phase=='transfer' and fraction is not None and 0<=fraction<=1 for phase,fraction in phases)
            info=probe(path)
            assert abs(float(info['format']['duration'])-3)<.06
            video_stream=next(st for st in info['streams'] if st['codec_type']=='video')
            audio_stream=next(st for st in info['streams'] if st['codec_type']=='audio')
            assert video_stream['nb_frames']=='72'
            assert abs(float(audio_stream['duration'])-float(video_stream['duration']))<.05
            assert meta['revision']==7
            assert '00:00:01,000 --> 00:00:02,000' in LocalStorage().path(meta['srt']).read_text()
            paths.append(path)
        # Same dimensions in this fixture: decoded first frame should match despite different CRF.
        frames=[run(['ffmpeg','-v','error','-ss','1.2','-i',str(p),'-frames:v','1','-vf','scale=16:9','-f','rawvideo','-pix_fmt','rgb24','-']) for p in paths]
        assert sum(abs(a-b) for a,b in zip(*frames))/len(frames[0])<8
        assert sum(frames[0])/len(frames[0])>20, 'Compositor must produce visible content, not a black video'
        from zipfile import ZipFile
        bundle=LocalStorage().path(meta['openshot_bundle'])
        extracted=bundle.parent/'relocated-native-project'
        with ZipFile(bundle) as archive:archive.extractall(extracted)
        import os
        result=run([os.getenv('OPENSHOT_PYTHON','/usr/bin/python3'),str(Path(__file__).resolve().parents[1]/'tools/verify_openshot.py'),str(extracted/'ScriptStudio.osp')])
        assert b'"rendered_frames": 3' in result
        assert probe(extracted/'native-verification.mp4')['streams'][0]['nb_frames']=='3'


def test_path_traversal_and_download_allowlist():
    storage=LocalStorage()
    with pytest.raises(ValueError):storage.path('../../etc/passwd')
    with pytest.raises(ValueError):storage.download('http://127.0.0.1/secret',storage.temporary())
    with pytest.raises(ValueError):storage.download('https://not-authorized.example/video',storage.temporary())


@pytest.mark.parametrize('width,height,fps_num,fps_den',[(180,320,24,1),(240,240,30000,1001)])
def test_native_overlay_geometry_and_rational_output(project_id,width,height,fps_num,fps_den):
    storage=LocalStorage()
    settings=Settings(width=width,height=height,fps_num=fps_num,fps_den=fps_den)
    frames=round(fps_num/fps_den)
    with transaction() as s:
        ids=[]
        for color in ('red','blue'):
            path=storage.temporary('.mp4')
            run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c={color}:s={width}x{height}:d=2:r=30','-c:v','libx264','-pix_fmt','yuv420p',str(path)])
            ids.append(AssetRepository().ingest(s,project_id,path,color,{}).id)
    with Session() as s:
        timeline=Timeline(items=[Item(track='video',asset_id=ids[0],duration=frames),
                                 Item(track='overlay',asset_id=ids[1],duration=frames,scale=.5,x=1,y=1)])
        output,_=RenderService().render(s,project_id,uid(),{'timeline':timeline.model_dump(),'settings':settings.model_dump(),'revision':1,'preview':True,'burn_captions':False})
        stream=probe(output)['streams'][0]
        assert (stream['width'],stream['height'],int(stream['nb_frames']))==(width,height,frames)
        pixels=run(['ffmpeg','-v','error','-ss','0.5','-i',str(output),'-frames:v','1','-vf','scale=2:2:flags=neighbor','-f','rawvideo','-pix_fmt','rgb24','-'])
        assert pixels[0]>150 and pixels[2]<80, 'Top left must show red base clip'
        assert pixels[9]<80 and pixels[11]>150, 'Bottom right must show blue overlay'


def test_audio_content_starts_on_timeline_frame(project_id):
    import array
    storage=LocalStorage();path=storage.temporary('.wav')
    run(['ffmpeg','-v','error','-y','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=1',str(path)])
    with transaction() as s:a=AssetRepository().ingest(s,project_id,path,'Tone',{});aid=a.id
    with Session() as s:
        timeline=Timeline(items=[Item(track='title',text='Audio timing',duration=48),Item(track='narration',asset_id=aid,start=24,duration=24)])
        outputs=[]
        for preview in (True,False):
            output,_=RenderService().render(s,project_id,uid(),{'timeline':timeline.model_dump(),'settings':Settings(width=320,height=180).model_dump(),'revision':1,'preview':preview})
            samples=array.array('h',run(['ffmpeg','-v','error','-i',str(output),'-vn','-ac','1','-ar','48000','-f','s16le','-']))
            before=sum(abs(x) for x in samples[24000:40000])/16000
            after=sum(abs(x) for x in samples[53000:68000])/15000
            assert before<2 and after>1000
            outputs.append(samples)
        assert len(outputs[0])==len(outputs[1])
