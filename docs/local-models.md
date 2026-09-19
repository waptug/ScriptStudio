# Using local models

Use the native Windows app for local media generation. Open **Admin → Local
models** to install each model. Wait for **Ready** before selecting it in a
project. Downloads include an isolated Python runtime and pinned weights; Resume
continues interrupted downloads and Verify checks the installed files.

On this workstation, double-click **ScriptStudio Local Models** on the desktop.
It launches `D:\ScriptStudio\ScriptStudio-Local-Models.exe` and opens the editor
at `http://127.0.0.1:50757`. Keep the launcher open while working; use **Stop
studio** or close it to finish active jobs and stop safely.

Projects are in `ScriptStudioNative\workspace-local-models`; installed media
models and caches are in `ScriptStudioNative\local-models`. Keep the EXE and
its `ScriptStudioNative` folder together, and close the app before moving them.
The current Docker projects have been copied into this workspace: 65 imported
projects plus the 10 existing D: projects. Docker and the E: originals remain
untouched. Migration backups are under `ScriptStudioNative\migrations`.
Kokoro, Wan, and ACE-Step have all produced real media here. Stable Audio access
is approved, but its protected Admin token and installation are still pending.

Open **Real local Wan video verification** to inspect the completed local-video
example and its narrated preview.

| Task | Model | Where to use it |
| --- | --- | --- |
| Write a script | Installed Ollama model, such as `gemma3:4b` | Admin: discover Ollama and select the script writer. In a project, describe the video, generate a draft, review it, then use and save it. |
| Plan shots | Installed Ollama model | Select **Local Ollama model** under Script planner, then **Plan scenes & shots**. The deterministic planner is also available. |
| Narration | Kokoro-82M | Project settings: select Kokoro and a stock voice, save, plan, then start production. Visual directions in brackets are excluded from speech. |
| Video | Wan 2.1 T2V-1.3B | Project settings: select Wan, save, plan, review each shot prompt, then start production. The preset generates 832 × 480 video with 81 frames at 16 fps. |
| Music | ACE-Step 1.5 | Project settings: select ACE-Step, enter the music prompt and optional lyrics, save, then start production. Empty lyrics request instrumental music. |
| Sound effects | Stable Audio Open Small (pending installation) | After installation, Media library: expand **Generate a local sound effect**, describe the sound in English, choose up to 11 seconds, and generate at the playhead. |

Choose providers before starting production. Narration determines the timing;
the app does not speed up speech to match footage. Generated assets appear in
the media library and eligible timeline placeholders. Preview the result, adjust
the timeline, then build a preview or render the final MP4.

Local generation has no provider charge. Paid generation switches can remain
off. A project using mock video is still a mock-video project even if its speech
or music is real; select the local providers explicitly for a fully local result.

Kokoro runs on the CPU. GPU media jobs share the NVIDIA GPU and the app releases
idle Ollama models before media inference. Leave sufficient GPU memory available
and wait for the current job instead of submitting duplicates. Loading large
weights can take several minutes, especially while other applications use RAM
or the GPU. Other apps using Ollama can load a model again independently of
ScriptStudio; pause those workloads when you need the full GPU for video.
A model's Ready state confirms installation and a runtime probe; actual generation validation is
recorded separately in PLAN.md.

Stable Audio requires acceptance of its upstream license and access conditions
on its Hugging Face page, plus an authorized token saved through **Admin → API
credentials**. Its commercial-use conditions differ from the other models.
Never put the token into a project prompt or command line. The app's license
checkbox records your acceptance; it does not grant upstream access.

On the verified RTX 3060 12 GB workstation, the first five-second Wan sample
took about 39 minutes including model loading under RAM pressure. Its 30
generation steps took about 19 minutes. Start with one short shot and allow it
to finish; loading time depends strongly on available RAM and disk speed.
