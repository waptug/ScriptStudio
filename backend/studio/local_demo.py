"""Built-in local-model demo; ordinary durable jobs own every generated asset."""
import hashlib
import json
import math
from .db import Project, Job, Asset
from .schemas import Settings, Storyboard, Scene, Shot, Item, Timeline, uid
from .local_models import LocalModelService
from .timeline import TimelineService

TEMPLATE = 'scriptstudio-local-60-v1'
BEATS = [
 ('Meet ScriptStudio, your local workspace for turning scripts into finished videos.', 'A filmmaker at a warm modern desk opens a laptop, soft morning window light, cinematic medium shot'),
 ('Start with your story, and describe the scenes you want to see.', 'Close view of hands writing ideas in a notebook beside a laptop, gentle camera slide'),
 ('Organize your ideas into a storyboard, with directions for every shot.', 'A creative studio wall with a neat sequence of photographic storyboard cards, slow lateral camera movement'),
 ('Local models create narration, video clips, and music on your computer.', 'An elegant desktop computer in a creative studio, subtle blue lighting, slow cinematic push in'),
 ('Follow loading, generation, saving, and checks with color coded progress.', 'Abstract luminous colored blocks appearing sequentially from left to right on a dark background, smooth motion'),
 ('Preview completed clips and highlight their place on your timeline.', 'An editor watching nature footage on a large monitor, viewed over the shoulder, realistic studio'),
 ('Name your clips, choose your takes, and arrange your edit.', 'Hands arranging small photographic cards into an orderly horizontal sequence on a desk, overhead shot'),
 ('Adjust timing, balance sound, and add titles and captions.', 'Close cinematic view of a hand adjusting an audio mixing console, warm highlights'),
 ('Your project and generated media stay saved locally.', 'A quiet personal creative workstation at dusk, a desktop tower and external storage on a tidy desk'),
 ('Natural narration, visuals, and music bring your message to life.', 'Sweeping cinematic view of a sunlit river through a green landscape, slow smooth aerial movement'),
 ('Render your timeline into a video ready to share.', 'A filmmaker watching a finished colorful landscape film on a large screen, slow pull back'),
 ('ScriptStudio. From the first word to the final frame. Make your story yours.', 'Sunrise over a peaceful mountain landscape, golden light, wide cinematic shot with gentle forward movement'),
]


def create(session):
    for model in ('kokoro','wan','ace_step'):
        LocalModelService().require_ready(model)
    settings=Settings(width=832,height=480,fps_num=24,target_duration=60,voice_provider='kokoro',voice_id='af_heart',
        video_provider='wan',music_provider='ace_step',music_prompt='Warm inspiring cinematic electronic instrumental, gentle piano, soft pulse, subtle uplifting build, no vocals, suitable under a software introduction',
        max_concurrency=1,auto_assemble=True,spending_limit=0)
    scene_id=uid(); speech=' '.join(text for text,_ in BEATS)
    board=Storyboard(scenes=[Scene(id=scene_id,position=0,narration=speech,shots=[Shot(scene_id=scene_id,position=i,narration=text,visual=visual,prompt=visual,estimated_duration=5) for i,(text,visual) in enumerate(BEATS)])])
    p=Project(id=uid(),name='Introducing ScriptStudio • 60-second local AI demo',script=speech,original_script=speech,settings=settings.model_dump(),storyboard=board.model_dump())
    session.add(p);session.flush()
    from .coordinator import GenerationCoordinator
    GenerationCoordinator().produce(session,p)
    narration=session.query(Job).filter_by(project_id=p.id,kind='narration').one()
    narration.inputs={**narration.inputs,'demo_template':TEMPLATE}
    return p


def reconcile(session,project,narration,coordinator):
    """Called under the project lock, so restart/repeated completion cannot duplicate work."""
    from .coordinator import NarrationService
    from .render import RenderService
    if narration.state!='ready':return
    settings=Settings.model_validate(project.settings)
    if not narration.result.get('assembled'):
        asset=session.get(Asset,narration.asset_id)
        if asset.duration>60:
            raise ValueError('Demo narration exceeds 60 seconds. Shorten its script in a new demo; speech was not accelerated or cut.')
        if project.timeline['items']:
            raise ValueError('Demo timeline was edited before assembly; existing items were preserved.')
        total=settings.frames(60); shot_frames=settings.frames(5)
        items=[Item(track='narration',duration=math.ceil(asset.duration*settings.fps_num/settings.fps_den),asset_id=asset.id,selected_take=asset.id).model_dump()]
        items+=NarrationService().cues(project.script,narration.result.get('alignment'),asset.duration,settings,0)
        board=Storyboard.model_validate(project.storyboard)
        for i,shot in enumerate(board.scenes[0].shots):
            shot.assigned_frames=shot_frames
            item=Item(track='video',start=i*shot_frames,duration=shot_frames,shot_id=shot.id)
            items.append(item.model_dump())
            coordinator.enqueue(session,project,'video','wan',coordinator.video_request(session,project,shot,item.id,5))
        music=Item(track='music',duration=total,volume=.18,fade_in=settings.frames(2),fade_out=settings.frames(3))
        items.append(music.model_dump())
        coordinator.enqueue(session,project,'music','ace_step',{'duration':60,'prompt':settings.music_prompt,'lyrics':'','mood':'bright','placeholder_id':music.id})
        TimelineService().save(session,project,{**project.timeline,'items':items})
        project.storyboard=board.model_dump()
        narration.result={**narration.result,'assembled':True}
        narration.error=None
    jobs=session.query(Job).filter_by(project_id=project.id).all()
    if any(j.kind=='render' for j in jobs) or any(j.state!='ready' for j in jobs):return
    # Respect a manual opt-out; never fill a removed/locked placeholder to force export.
    if not project.settings.get('auto_assemble',True):return
    RenderService().validate(session,project.id,Timeline.model_validate(project.timeline),False)
    inputs={'preview':False,'draft':False,'burn_captions':True,'timeline':project.timeline,'settings':project.settings,'revision':project.revision,'project_name':project.name,'demo_template':TEMPLATE}
    session.add(Job(id=uid(),project_id=project.id,kind='render',provider='ffmpeg',model='h264-aac',state='queued',estimated_cost=0,inputs=inputs,fingerprint=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()))
