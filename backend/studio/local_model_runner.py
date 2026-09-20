"""Executed only by the isolated model Python. Never imported by API services."""
import json
import sys
from pathlib import Path
import time


def main():
    import torch
    name=sys.argv[2] if sys.argv[1]=='--probe' else sys.argv[1]
    if name!='kokoro':
        if not torch.cuda.is_available(): raise RuntimeError('CUDA unavailable; a compatible NVIDIA driver is required')
        # Exercise an actual kernel, not just driver/device enumeration.
        torch.ones(16,device='cuda').sum().item();torch.cuda.synchronize()
    if sys.argv[1]=='--probe':
        if name=='kokoro': import kokoro, soundfile, en_core_web_sm
        elif name=='wan':
            from diffusers import WanPipeline
            import ftfy, imageio, imageio_ffmpeg
        elif name=='ace_step': from acestep.handler import AceStepHandler
        elif name=='stable_audio':
            from stable_audio_tools.models.diffusion import create_diffusion_cond_from_config
            from stable_audio_tools.inference.generation import generate_diffusion_cond
            from transformers import T5EncoderModel, AutoTokenizer
            import soundfile
        print(json.dumps({'cuda':torch.version.cuda,'ready':True}));return
    request=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    base=Path(request['model_root']); model=base/'model'
    def report(state,progress=0,steps=None,phase=None,detail=None):
        file=Path(request['status']);temp=file.with_suffix('.new')
        temp.write_text(json.dumps(dict(state=state,progress=progress,steps=steps,phase=phase,detail=detail)));temp.replace(file)
    torch.manual_seed(request['seed'])
    report('loading')
    if name=='kokoro':
        import numpy as np
        import soundfile as sf
        from kokoro import KModel,KPipeline
        voice=request['voice_id']
        network=KModel(config=str(model/'config.json'),model=str(model/'kokoro-v1_0.pth')).to('cpu').eval()
        pipeline=KPipeline(lang_code=voice[0],model=network,device='cpu')
        report('generating')
        audio=[result.audio.numpy() for result in pipeline(request['text'],voice=str(model/'voices'/(voice+'.pt')),speed=1)]
        if not audio: raise ValueError('Narration produced no audio')
        report('generating',phase='transfer',detail='Saving audio file')
        sf.write(request['output'],np.concatenate(audio),24000)
    elif name=='wan':
        from diffusers import WanPipeline,AutoencoderKLWan
        from diffusers.utils import export_to_video
        vae=AutoencoderKLWan.from_pretrained(str(model/'vae'),torch_dtype=torch.float32,local_files_only=True)
        pipeline=WanPipeline.from_pretrained(str(model),vae=vae,torch_dtype=torch.bfloat16,local_files_only=True)
        pipeline.enable_model_cpu_offload()
        pipeline.vae.enable_tiling()
        def step(pipe,index,timestep,kwargs):
            report('generating',(index+1)/30,{'current':index+1,'total':30});return kwargs
        report('generating')
        frames=pipeline(prompt=request['prompt'],negative_prompt='blurred, low quality, text, watermark',height=480,width=832,num_frames=81,
                        num_inference_steps=30,guidance_scale=5,generator=torch.Generator('cpu').manual_seed(request['seed']),callback_on_step_end=step).frames[0]
        report('generating',phase='transfer',detail='Encoding video file')
        export_to_video(frames,request['output'],fps=16)
    elif name=='ace_step':
        import soundfile as sf
        from acestep.handler import AceStepHandler
        from acestep.llm_inference import LLMHandler
        from acestep.inference import GenerationParams,GenerationConfig,generate_music
        class OfflineAceStepHandler(AceStepHandler):
            def _ensure_models_present(self, *, checkpoint_path, config_path, prefer_source, vae_variant=None):
                # The upstream default also checks for an optional language
                # model. This preset uses thinking=False and installs only the
                # three components it needs; generation must never download.
                for component in (config_path, 'vae', 'Qwen3-Embedding-0.6B'):
                    if not (checkpoint_path/component/'config.json').is_file():
                        raise RuntimeError('Missing pinned ACE-Step component; Resume installation to repair')
                return None

            @staticmethod
            def _sync_model_code_if_needed(config_path, checkpoint_path):
                from acestep.model_downloader import _check_code_mismatch
                if _check_code_mismatch(config_path, checkpoint_path):
                    raise RuntimeError('ACE-Step checkpoint code differs from its pinned runtime; Resume installation to repair')

        handler=OfflineAceStepHandler()
        _,ok=handler.initialize_service(project_root=str(model),config_path='acestep-v15-turbo',device='cuda',use_flash_attention=False,offload_to_cpu=True,offload_dit_to_cpu=True)
        if not ok: raise RuntimeError('ACE-Step initialization failed')
        report('generating')
        params=GenerationParams(caption=request.get('prompt') or request.get('mood','calm instrumental'),lyrics=request.get('lyrics') or '[Instrumental]',instrumental=not bool(request.get('lyrics')),duration=max(10,request['duration']),inference_steps=8,seed=request['seed'],thinking=False,dcw_enabled=False)
        config=GenerationConfig(batch_size=1,audio_format='wav',use_random_seed=False)
        result=generate_music(handler,LLMHandler(),params,config,save_dir=str(Path(request['output']).parent))
        if not result.success: raise RuntimeError(result.error)
        audio,rate=sf.read(result.audios[0]['path'],dtype='float32',always_2d=True)
        # ACE-Step's minimum is ten seconds. Short projects use a trimmed excerpt,
        # preserving pitch and tempo rather than stretching the generated music.
        report('generating',phase='transfer',detail='Saving audio file')
        sf.write(request['output'],audio[:round(request['duration']*rate)],rate)
    elif name=='stable_audio':
        import soundfile as sf
        from stable_audio_tools.models.factory import create_model_from_config
        from stable_audio_tools.models.utils import load_ckpt_state_dict
        from stable_audio_tools.inference.generation import generate_diffusion_cond
        config=json.loads((model/'model_config.json').read_text())
        for conditioner in config['model']['conditioning']['configs']:
            if conditioner['type']=='t5':
                if conditioner['config']['t5_model_name']!='t5-base':
                    raise RuntimeError('Unsupported Stable Audio text encoder')
                conditioner['config']['model_path']=str(model/'t5-base')
        network=create_model_from_config(config)
        network.load_state_dict(load_ckpt_state_dict(str(model/'model.safetensors')))
        network.to('cuda').eval().requires_grad_(False)
        report('generating')
        audio=generate_diffusion_cond(network,steps=8,cfg_scale=1.0,conditioning=[{'prompt':request['prompt'],'seconds_total':request['duration']}],sample_size=config['sample_size'],sampler_type='pingpong',device='cuda',seed=request['seed'])
        audio=audio[0,:,:int(request['duration']*config['sample_rate'])].float().cpu()
        audio=audio/audio.abs().max().clamp(min=1e-8)
        report('generating',phase='transfer',detail='Saving audio file')
        sf.write(request['output'],audio.T.numpy(),config['sample_rate'])
    report('validating',1)
    if name!='kokoro':
        print(json.dumps({'peak_cuda_bytes':torch.cuda.max_memory_allocated()}))


if __name__=='__main__': main()
