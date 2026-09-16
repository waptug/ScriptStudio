"""Versioned interchange contracts. All timeline positions are integer frames."""
from enum import StrEnum
from fractions import Fraction
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field, model_validator


def uid() -> str:
    return str(uuid4())


class Settings(BaseModel):
    aspect: Literal['landscape', 'portrait', 'square'] = 'landscape'
    width: int = Field(1280, ge=128, le=3840, multiple_of=2)
    height: int = Field(720, ge=128, le=3840, multiple_of=2)
    fps_num: int = Field(24, ge=1, le=120000)
    fps_den: int = Field(1, ge=1, le=1001)
    style: str = Field('Cinematic nature documentary', max_length=2000)
    reference_assets: list[str] = []
    voice_provider: Literal['mock', 'elevenlabs'] = 'mock'
    voice_id: str = 'en-us'
    voice_settings: dict = {'stability': 0.5, 'similarity_boost': 0.75}
    video_provider: Literal['mock', 'runway'] = 'mock'
    music_provider: Literal['mock', 'import', 'suno'] = 'mock'
    music_mood: str = 'calm'
    target_duration: int = Field(60, ge=10, le=300)
    spending_limit: float = Field(0, ge=0, le=10000)
    max_concurrency: int = Field(2, ge=1, le=8)
    auto_assemble: bool = True
    @model_validator(mode='after')
    def valid_fps(self):
        if not 1 <= self.fps_num / self.fps_den <= 120:
            raise ValueError('Frame rate must be between 1 and 120 fps')
        return self
    def frames(self, seconds: float) -> int:
        return round(Fraction(str(seconds)) * self.fps_num / self.fps_den)
    def seconds(self, frames: int) -> float:
        return float(Fraction(frames * self.fps_den, self.fps_num))


class Shot(BaseModel):
    id: str = Field(default_factory=uid)
    scene_id: str
    position: int
    narration: str
    visual: str
    prompt: str
    camera: str = 'Slow establishing shot'
    references: list[str] = []
    estimated_duration: float = Field(5, gt=0, le=300)
    assigned_frames: int = 0


class Scene(BaseModel):
    id: str = Field(default_factory=uid)
    position: int
    narration: str
    shots: list[Shot] = Field(min_length=1,max_length=500)


class Storyboard(BaseModel):
    scenes: list[Scene] = Field(default_factory=list, max_length=100)


Track = Literal['video', 'overlay', 'title', 'caption', 'narration', 'music', 'sfx']
class Item(BaseModel):
    id: str = Field(default_factory=uid)
    track: Track
    start: int = Field(0, ge=0)
    duration: int = Field(120, gt=0)
    source_in: int = Field(0, ge=0)
    asset_id: str | None = None
    shot_id: str | None = None
    selected_take: str | None = None
    text: str = Field('', max_length=4000)
    locked: bool = False
    muted: bool = False
    volume: float = Field(1, ge=0, le=4)
    fade_in: int = Field(0, ge=0)
    fade_out: int = Field(0, ge=0)
    x: float = Field(0, ge=0, le=1)
    y: float = Field(0, ge=0, le=1)
    scale: float = Field(1, gt=0, le=1)
    coverage: Literal['hold', 'loop'] = 'hold'
    transition: Literal['cut', 'fade'] = 'cut'
    @property
    def source_out(self):
        return self.source_in + self.duration


class Timeline(BaseModel):
    version: Literal[1] = 1
    items: list[Item] = Field(default_factory=list, max_length=3000)
    duck_music: bool = True
    @model_validator(mode='after')
    def unique(self):
        if len({i.id for i in self.items}) != len(self.items):
            raise ValueError('Timeline item IDs must be unique')
        return self


class JobState(StrEnum):
    QUEUED='queued'
    SUBMITTING='submitting'
    SUBMITTED='submitted'
    GENERATING='generating'
    DOWNLOADING='downloading'
    VALIDATING='validating'
    READY='ready'
    FAILED='failed'
    CANCELED='canceled'
    UNKNOWN='submission_outcome_unknown'


class CreateProject(BaseModel):
    name: str = Field('Untitled project', min_length=1, max_length=200)
    script: str = Field('', max_length=50000)
    settings: Settings = Field(default_factory=Settings)


class Edit(BaseModel):
    revision: int
    operation: Literal['add','update','move','trim','split','delete','duplicate','undo','redo','select_take']
    item_id: str | None = None
    values: dict = {}


class RenderRequest(BaseModel):
    preview: bool = False
    draft: bool = False
    burn_captions: bool = True
