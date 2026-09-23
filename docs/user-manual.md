# ScriptStudio User Manual

A practical guide to writing, generating, editing, and exporting a video.

Edition: 20 September 2026. This guide covers the native Windows local-model workspace and the current browser editor. Your launcher chooses the workspace address; use its Open studio control rather than an old saved port.

## 1. Start here

ScriptStudio turns a written script into narration, visual shots, captions, and music. You review those results, arrange a timeline, and export a video. Generated media and project records are saved on the local workstation.

For the installed Windows workspace, open the ScriptStudio Local Models desktop shortcut. The executable is ScriptStudio-Local-Models.exe in the ScriptStudio folder. Wait for the launcher to open the editor. If the launcher is already running, use Open studio instead of launching another workspace. Keep the launcher open while generation or rendering is underway.

The browser is the control panel. The native app and its background worker perform the work. Closing a browser tab does not cancel a submitted job, but closing or stopping the launcher begins service shutdown. Use the launcher's normal Stop control and allow active work to drain before moving files or shutting down the computer. For a long demo, leave the app and computer running and prevent sleep.

The native Windows package includes its own Python, PostgreSQL database, OpenShot rendering support, and FFmpeg. You do not need to install Docker, Node, or Python to run that package. Ollama is a separate optional application for writing scripts and planning visual shots.

### Choose a starting point

- New project: create your own script and choose your providers.
- Try the 60-second mock demo: load sample content for learning the workflow with eSpeak narration and labeled synthetic media. Review its settings, plan, and start production.
- Create 60-second ScriptStudio demo · local AI: create and start a scripted introduction using Kokoro, twelve Wan shots, and ACE-Step music. It automatically assembles and exports when generation is ready.

The local AI demo can take several hours on a consumer GPU. It is not a one-minute processing job: one minute describes the finished video. Its unedited timeline is exactly 60 seconds. Ordinary projects use target duration as a planning guide and follow measured narration length.

## 2. Find your way around

The dashboard lists saved projects. Select a project card to reopen its script, assets, jobs, and timeline. Project data remains in the workspace across normal app restarts.

The header provides project controls, a light/dark theme switch, About this project, Admin, and export access. The User manual link opens this guide; the Word download is available from the guide and About. About also links to the README, licenses, component inventory, brand downloads, and the recreation specification.

Inside an editor, use the navigation tabs:

- Script: write or review narration and choose how to plan it.
- Storyboard: inspect scenes and shot prompts before production; regenerate visual takes afterward.
- Media: browse generated and imported assets, import files, or generate sound effects.
- Settings: choose output format, providers, voice, style, budget, and concurrency.

The main preview area plays either a rendered timeline preview or an individual completed clip. The side panel shows the clip inspector or production queue. The timeline is below the editor. Use its zoom control to spread out short clips or view a longer sequence.

## 3. Understand mock, local, and paid providers

Mock mode is a fast demonstration mode. It makes playable speech, synthetic footage, and instrumental audio locally, but it does not claim those visuals are model-generated.

Local AI uses installed media models. Kokoro supplies narration; Wan supplies generated video; ACE-Step supplies music; Stable Audio supplies sound effects. These jobs have no external provider fee. They still use your computer's memory, GPU, electricity, and disk space.

Paid providers are a separate workflow. Admin permissions, credentials, supported adapters, and a project budget are required. They are not needed for the local demo. Leave paid generation disabled if you only want local work. A project can mix provider types, so check narration, video, and music individually: local speech with mock video is not a fully model-generated video.

## 4. Install and reuse local models

Open Admin, then Local models. Read each model's description and displayed license/access conditions. Choose Install for the model you need and wait for Ready before selecting it in project settings. Installation may include downloading model files, unpacking a separate runtime, verifying files, and checking that runtime.

During installation, the progress panel identifies the stage, current file or measured bytes where available, elapsed time, and installer activity. A moving striped bar means there is no trustworthy percentage for that stage. A measured percentage applies to the current stage, not necessarily the entire installation.

Use Resume after an interrupted download when available. Verified files and partial downloads are reused where possible. Use Verify when you deliberately want to check an installation, and Repair when it is damaged. Repeatedly pressing Install on an already Ready model should not reinstall it.

### Installed does not mean permanently loaded

Model files stay on disk under ScriptStudioNative/local-models. Normal app launches and generation do not need to download and install them again when the pinned version is unchanged. However, a generation process still needs to load weights into RAM or GPU memory. Memory cannot survive a computer restart, and the app does not keep all four large models resident together.

Kokoro uses the CPU. GPU media work shares the NVIDIA GPU, and ScriptStudio coordinates with idle Ollama models to free memory. Other programs can still consume that memory. Avoid competing heavy GPU work while a video job is running. Increasing project concurrency does not make the GPU's memory larger.

Stable Audio can require upstream account access and an authorized Hugging Face token in Admin, in addition to accepting its displayed license. An app checkbox does not grant access on the model host. Keep credentials in Admin rather than in prompts or documents. Consult the displayed model terms for your intended use.

## 5. Write a clear script

Create a project, open Settings, and give it a descriptive name. Set the output size, aspect, and frame rate before production. Select Kokoro with a stock voice, Wan video, and ACE-Step music for a fully local AI workflow, then save the settings.

Write spoken words as ordinary text. Separate scenes with blank lines. Put unspoken visual directions inside square brackets. For example:

[Wide view of a quiet creative studio. Warm morning light. Slow camera movement.]
Meet ScriptStudio, a local workspace for turning ideas into finished videos.

Only the sentence outside brackets becomes narration. Close every bracket before planning. The live spoken-word estimate excludes visual directions; it is a planning estimate, not a promise about final speech duration.

For better visual results, describe what should be visible: the subject, setting, action, lighting, and camera movement. Keep one shot's request focused. A generated image of a software interface may contain imperfect text; use timeline titles or real imported screen footage when exact words or interface details matter.

### Optional writing with Ollama

Open Admin to discover a running Ollama server, list installed models, and choose a script-writing model. In Script, choose Write with AI, enter the idea, audience, tone, and target duration, then generate a draft. Review and edit the draft before choosing Use this script. Save the accepted script. Generating a draft does not automatically replace your saved narration.

If Ollama is unavailable, you can still write manually and use the deterministic planner. Installing a media model such as Wan does not install an Ollama writing model.

## 6. Plan scenes and start production

Choose a script planner and select Plan scenes & shots. The deterministic planner uses your paragraphs and spoken passages. The optional local Ollama planner can choose visuals and group adjacent passages while preserving the original narration.

Review the storyboard before starting. Check that every scene says the right words and every visual prompt describes what you actually want to see. Fix mistakes now to avoid generating unnecessary footage. Save any relevant project settings before beginning production.

Select Start production once. The app queues narration, measures its duration, creates captions and visual placeholders, then queues the required video and music jobs. Empty placeholders reserve space on the timeline while generation runs. Completed media fills its surviving eligible placeholder when automatic filling is enabled.

Do not repeatedly start or regenerate the same work merely because loading is slow. New generations are separate jobs and can create extra takes. After production begins, start a new project if you need a substantially rewritten narration or a fresh scene structure. Existing production captures its script and settings; changing defaults does not rewrite running jobs.

## 7. Read the color-coded production queue

Open Queue from the side panel or View queue near the preview. Each job shows its provider, state, applicable phase sequence, and available detail. Different providers have different phases; a mock job may omit model loading and transfer.

- Gray — Queued: waiting for its turn or required resources.
- Blue — Prepare or Load model: getting the runtime and model ready.
- Purple — Generate or Render: producing model output or composing video frames.
- Cyan — Save, Download, or Encode: writing, retrieving, or encoding the result.
- Amber — Check: validating media before publishing it as an asset.
- Green — Ready: the validated result is available.

Completed phases keep their color and checkmark. The current phase is outlined and may have a measured fill or moving stripes. Future phases are dimmed. These equal-width segments show sequence, not equal processing time and not a reliable overall percentage.

Step counts such as 19 / 30 are measured generation steps. Loading may report component or checkpoint counts. Those counts describe that subtask only. Elapsed time shows how long work has taken; it does not say how much remains. A process contact or heartbeat indicates communication, not necessarily new measured progress.

### A job says Loading for a long time

Large Wan weights can take many minutes to load, particularly under RAM pressure or on a busy disk. A growing elapsed timer alone proves neither a freeze nor successful progress. Check the reported phase, loading counts, activity/contact information, and whether the browser is connected. Allow a healthy loading process to continue rather than submitting duplicates.

A connection-lost message means the editor cannot confirm fresh status. Reopen through the launcher or retry after connectivity returns; the durable job may still be running. If the app reports an actual failure, read its error and retry the saved job after resolving the cause. Persistent uncertainty merits checking model readiness, free disk space, and the relevant local log with support.

## 8. Preview, locate, and name completed clips

When an audio or video job is Ready, its queue card offers Preview clip. Select it to play the original clip in the main preview window. If automatic playback is blocked by the browser, press Play there.

Previewing also selects and scrolls to an existing placement of that asset on the timeline. The selected clip has a visible outline. If you have multiple placements, the currently selected matching placement is preferred; otherwise the first matching placement is selected. If the asset has not been placed, the preview says Not on timeline yet.

Clip playback has its own timer. Watching it does not move the timeline insertion point. Return to timeline preview switches back to the project's rendered preview. Preview clip is useful immediately after generation; Build preview is for watching the complete edited timeline with its mixed audio.

### Add a clip to the timeline

Set the timeline playhead where you want the clip to begin, then choose Add to timeline on the ready job. The full clip is added to the appropriate video or audio track. Existing items are preserved; they are not automatically pushed aside, so inspect any overlaps you create.

If the asset is already placed, the button reads On timeline and is disabled to avoid accidental duplicates. For an intentional second instance, select the existing timeline item and use Duplicate, or use the media library's track selector.

### Give a clip a readable name

Choose Rename clip on the queue card, in the media library, or in the selected clip's inspector. Enter a descriptive name such as Opening studio shot or Gentle background music, then choose Save name. Cancel leaves the old name intact. Names cannot be blank and are limited to 200 characters.

The saved name appears wherever that asset is displayed or placed. Renaming does not rename the underlying media file, change its timing, or regenerate it. If another save changed the name first, refresh and try again. Naming is asset-wide: copies of the same asset share that name. Undo/Redo controls timeline edits; do not rely on them to undo a name change.

## 9. Edit the timeline

Select a timeline clip to open its inspector. Main video, overlays, titles, captions, narration, music, and sound effects occupy separate tracks. The ruler and time display help you locate the insertion point. Zoom changes the view, not the clip durations.

Drag an unlocked clip to move it. With Snap enabled, nearby starts and ends help align clips. Use inspector frame fields for precise positions, duration, and source trim. At 24 frames per second, 120 frames equals five seconds. Project frame rate is fixed once production begins.

- Split at playhead divides an eligible selected item at that position.
- Duplicate creates another timeline instance.
- Delete item removes the placement; it does not instruct the app to erase all saved source media.
- Lock protects an item from ordinary edits and automatic replacement. Unlock it to edit again.
- Mute excludes that item's contribution from the output.
- Undo and Redo restore timeline edits and are saved with the project.

Source in chooses where playback begins within a source. Short video can hold its last frame or loop according to Coverage. Audio is not accelerated to make it fit. Supported fades, volume, transform, and transition controls depend on the track. Use modest music volume so narration stays intelligible.

Regenerate a shot from Storyboard to request another take. Earlier takes are retained. In the inspector, choose Selected take to use the version you want. Background completion must not overwrite a take you explicitly selected, revive a deleted placeholder, or move/trim a clip you already edited.

## 10. Import media and add sound effects

Open Media and choose Import footage, audio, or images. The importer supports common video and audio formats plus PNG/JPEG images; the app validates media before publishing it. After import, use that asset's Add to timeline track selector. Importing a file and placing it are separate actions.

Supported extensions include MP4, MOV, WEBM, WAV, MP3, M4A, OGG, FLAC, PNG, JPG, and JPEG. The current API upload limit is 512 MiB. If import fails, check the error, file size, supported format, and whether the file plays correctly outside the app.

To create a sound effect, expand Generate a local sound effect in Media. Describe the sound in English, select a duration up to 11 seconds, position the playhead, and generate. Stable Audio must be Ready. The requested sound-effect placement is created at that playhead position.

Imported video source audio is not automatically included in the mix. Place separate audio on narration, music, or sound-effects tracks when it is needed. Uploaded reference images can guide supported providers; a reference asset does not guarantee that every local model uses image conditioning.

## 11. Build previews and export

After editing, choose Build preview. This renders a synchronized lower-resolution view of the timeline through the same compositor used for export. The preview revision tells you which edit it represents. If you edit afterward, rebuild it; the old preview does not change in real time.

For the finished file, open Export, review draft and caption options, and choose Render final MP4. Final rendering requires valid media for all required placements. Draft mode permits visibly marked missing visual placeholders and should not be mistaken for a completed model-generated video.

A render uses a snapshot of the timeline. Editing while it runs does not alter that snapshot. If you want those new edits in the file, submit a new render afterward. Completed renders provide Download MP4, subtitle downloads, and an OpenShot bundle. The render's queue card also supports Preview clip.

Download filenames include the project name and render timestamp. Browser downloads normally go to the native workspace's downloads area unless your browser asks for another location. Check the browser's Downloads list if a file is not where you expected.

### Continue editing in OpenShot

Download Continue in OpenShot, extract the entire ZIP, and open ScriptStudio.osp from the extracted folder. Keep its media together. The handoff is one-way: edits made in desktop OpenShot do not automatically return to ScriptStudio. Titles/captions are image clips, and the finished audio is provided as a mixed track with original sources retained for further work.

## 12. Use the built-in local AI introduction

On the dashboard, select Create 60-second ScriptStudio demo · local AI. Kokoro, Wan, and ACE-Step must already be Ready. The button creates a separate project called Introducing ScriptStudio with an introduction explaining scripts, planning, local generation, queue progress, previews, naming, editing, captions, and exporting.

The demo first creates natural narration. It then builds twelve five-second visual placements and a full-minute music track. Wan produces twelve distinct source clips; ACE-Step produces the music. The untouched timeline totals exactly 60 seconds at 24 fps. Shorter narration leaves the remaining time for the visuals and music rather than slowing or stretching speech.

Every generation job must reach Ready before automatic final export is queued. If a job fails, resolve its cause and use Retry on that saved job. If narration unexpectedly exceeds 60 seconds, assembly stops with an explanation rather than cutting or accelerating speech. Reopening the browser is safe; queue and assembly records are durable.

Manual edits are honored and can change the final duration. Turning off automatic placement also disables automatic export. If you remove or lock required placements, the app will not recreate or overwrite them merely to finish the demo. Once all media is ready, you can always inspect the timeline and render manually.

## 13. Save, back up, and move the workspace

Use the visible save controls for script and project settings. Timeline operations save through the server and update the saved revision. If a save fails, read the error instead of assuming that the screen's current text is persisted. A revision conflict means another update occurred; refresh and reapply your intended edit.

In this installed workspace, project data is under ScriptStudioNative/workspace-local-models beside the EXE. Other launcher modes can use a different data subfolder. Installed media models are under ScriptStudioNative/local-models. Generated media, original assets, previews, logs, and database files are all part of the larger workspace, not just the small launcher EXE.

Before a full-folder backup or move, stop the app normally and wait for shutdown. Copy the EXE and the complete ScriptStudioNative folder together to retain the native environment. Do not merge two database directories, delete database files to fix an error, or copy a running database and assume it is a consistent backup. See the README and operations guide for developer/database backup procedures.

Export important MP4 files separately as well. Do not remove original media or old takes until you understand which projects still reference them. Large models, generated clips, normalized media, and repeated exports can consume substantial disk space; leave room on the actual workspace drive.

## 14. Troubleshooting and getting help

App will not open: use the launcher and wait for its status. Try its Open studio control. An old bookmarked port may refer to another workspace. Check its error message and available disk space before launching extra copies.

Model is not selectable: open Admin → Local models and check Ready, license/access requirements, and any installation error. Resume an interrupted install; verify or repair only when needed.

Queue is waiting for GPU: allow the active GPU job to finish and close unrelated GPU-heavy workloads if appropriate. More queued copies do not help. The app may unload idle Ollama models to free memory.

Preview is blank or out of date: distinguish Preview clip from the full timeline preview. Check the selected asset and browser Play button, then rebuild the timeline preview after edits. A deleted or unavailable asset cannot be previewed.

Clip did not automatically appear: check the automatic-fill setting and whether its original placeholder still exists, is unlocked, and remains eligible. Use Add to timeline if the clip is ready and you want a new placement.

Export is blocked by missing media: inspect placeholders and selected takes. Finish generation, select valid media, or deliberately remove an unwanted item. Use draft export only when you want visibly unfinished visual placeholders.

Unknown paid submission outcome: do not blindly submit it again. Recover or reconcile the existing provider task through the available controls. This state is different from a local Wan loading phase.

For support, record the project name, short job ID, provider, state, phase, last visible activity, and exact error text. Native logs are in the active workspace; a local inference log is normally under media/tmp/local-JOB-ID/inference.log. Share the relevant error after reviewing it for private information. Never share API keys, saved credential fields, or runtime configuration containing passwords.

## 15. Quick reference and limits

To learn fast, start with mock content. To generate real media, choose local providers explicitly. To inspect one result, use Preview clip. To hear the complete mix, Build preview. To create a shareable file, Render final MP4. To understand a delay, read the current phase and measured detail rather than only its elapsed timer.

ScriptStudio is a local, single-user application. It does not provide automatic cloud collaboration, guaranteed lip synchronization, perfect text inside generated visuals, or a full real-time preview compositor. Model output can require another take or manual editing. The current Wan preset generates 81 frames at 16 fps, at 832 × 480; a longer placement may require explicit coverage behavior.

About this project contains the app's GPL license and third-party notices. Model and service terms are separate from the application license. The README provides the source repository, developer setup, architecture, validation commands, and supporting guides.
