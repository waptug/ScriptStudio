type Clip={id:string;kind:string;name:string;duration:number};
export function QueueClipActions({asset,onTimeline,busy,onPreview,onAdd}:{asset:Clip;onTimeline:boolean;busy:boolean;onPreview:()=>void;onAdd:()=>void}){
 return <div className="queue-clip-actions"><button onClick={onPreview}>Preview clip</button><button disabled={busy||onTimeline} onClick={onAdd} title={onTimeline?'This clip is already on the timeline':'Add the full clip at the timeline playhead'}>{onTimeline?'On timeline ✓':'Add to timeline'}</button></div>;
}
